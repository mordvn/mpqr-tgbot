from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from loguru import logger

from app.context import AppContext
from app.keyboards import contact_reply_keyboard
from app.telegram_safe import safe_telegram_call
from app.texts import (
    CB_INVALID_ACTION,
    CB_NOT_FOUND,
    CB_UNKNOWN_COMMAND,
    CLIENT_APPROVED,
    CLIENT_REJECTED,
    CLIENT_REVIEW_REQUEST,
    CLIENT_SUPPORT_RESOLVED_ONLY,
    MANAGER_APPROVED_TOPIC,
    MANAGER_CB_ALREADY_SENT,
    MANAGER_CB_DONE,
    MANAGER_CB_ALREADY_PROCESSED,
    MANAGER_CB_REJECTED,
    MANAGER_CB_SENT_TO_CLIENT,
    MANAGER_REJECTED_TOPIC,
    MANAGER_REVIEW_ALREADY_REQUESTED,
)


# ===== Internal parsing / UI helpers =====

async def _safe_clear_inline_keyboard(callback: CallbackQuery, log_hint: str) -> None:
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        logger.exception("Failed to clear inline keyboard: {}", log_hint)


def _extract_manager_action(callback_data: str) -> tuple[str, str] | None:
    parts = callback_data.split(":")
    if len(parts) != 3:
        return None
    return parts[1], parts[2]


# ===== Internal support/review flow helpers =====

async def _notify_client_after_support_resolved(
    ctx: AppContext,
    user_id: int,
) -> None:
    user_name = await ctx.db.get_user_name(user_id)
    if await ctx.db.has_approved_present(user_id):
        await ctx.db.set_user_state(user_id, "idle")
        await safe_telegram_call(
            "manager.notify_resolved_without_present",
            lambda: ctx.bot.send_message(
                chat_id=user_id,
                text=CLIENT_SUPPORT_RESOLVED_ONLY.format(user_name=user_name),
                reply_markup=ReplyKeyboardRemove(),
            ),
        )
        return

    present_id = await ctx.db.upsert_present_waiting_phone(user_id)
    await ctx.db.set_user_state(user_id, "present_waiting_phone")
    await ctx.db.add_event(
        user_id,
        "present_started",
        {"present_id": present_id, "source": "manager_request_review"},
    )
    await safe_telegram_call(
        "manager.notify_review_request_to_user",
        lambda: ctx.bot.send_message(
            chat_id=user_id,
            text=CLIENT_REVIEW_REQUEST.format(user_name=user_name),
            reply_markup=contact_reply_keyboard(),
        ),
    )


async def _resolve_user_id_for_manager_reply(
    ctx: AppContext,
    message: Message,
    topic_id: int,
) -> int | None:
    if message.reply_to_message:
        user_id = await ctx.db.get_user_by_manager_message(
            message.reply_to_message.message_id,
            topic_id,
        )
        if user_id is not None:
            return user_id
    return await ctx.db.get_user_by_topic(topic_id)


# ===== Router factory =====

def build_manager_router(ctx: AppContext) -> Router:
    router = Router()

    # Inline callbacks from manager-side buttons in forum topics.
    @router.callback_query(F.data.startswith("mgr:"))
    async def manager_callbacks(callback: CallbackQuery) -> None:
        if callback.message.chat.id != ctx.settings.managers_group_id:
            await callback.answer()
            return
        if not callback.from_user or callback.from_user.is_bot:
            await callback.answer()
            return

        action_payload = _extract_manager_action(callback.data)
        if action_payload is None:
            await callback.answer(CB_INVALID_ACTION)
            return

        action, item_id_raw = action_payload
        if action == "noop":
            await callback.answer()
            return

        if action == "request_review":
            topic_id = callback.message.message_thread_id
            resolved_user_id = await ctx.db.resolve_support_topic(topic_id)
            if resolved_user_id is None:
                await safe_telegram_call(
                    "manager.notify_review_already_requested_in_topic",
                    lambda: ctx.bot.send_message(
                        chat_id=ctx.settings.managers_group_id,
                        message_thread_id=topic_id,
                        text=MANAGER_REVIEW_ALREADY_REQUESTED,
                    ),
                )
                await callback.answer(MANAGER_CB_ALREADY_SENT)
                return

            await _safe_clear_inline_keyboard(callback, "request_review")

            await ctx.db.add_event(
                resolved_user_id, "support_resolved", {"topic_id": topic_id}
            )
            await _notify_client_after_support_resolved(ctx, resolved_user_id)
            await safe_telegram_call(
                "manager.notify_review_requested_in_topic",
                lambda: ctx.bot.send_message(
                    chat_id=ctx.settings.managers_group_id,
                    message_thread_id=topic_id,
                    text=MANAGER_REVIEW_ALREADY_REQUESTED,
                ),
            )
            await callback.answer(MANAGER_CB_SENT_TO_CLIENT)
            return

        try:
            present_id = int(item_id_raw)
        except ValueError:
            await callback.answer(CB_INVALID_ACTION)
            return
        if action == "approve":
            result, present = await ctx.db.moderate_present_if_status(
                present_id,
                status="approved",
                expected_status="pending_review",
                event_type="present_approved",
            )
            if result == "not_found":
                await callback.answer(CB_NOT_FOUND)
                return
            if result != "ok":
                await callback.answer(MANAGER_CB_ALREADY_PROCESSED)
                return
            manager_topic_id = (
                present.get("topic_id") or callback.message.message_thread_id
            )
            await _safe_clear_inline_keyboard(callback, "approve")
            await safe_telegram_call(
                "manager.notify_user_approved",
                lambda: ctx.bot.send_message(
                    chat_id=present["user_id"],
                    text=CLIENT_APPROVED.format(phone=present["phone"]),
                    reply_markup=ReplyKeyboardRemove(),
                ),
            )
            if manager_topic_id:
                await safe_telegram_call(
                    "manager.notify_topic_approved",
                    lambda: ctx.bot.send_message(
                        chat_id=ctx.settings.managers_group_id,
                        message_thread_id=manager_topic_id,
                        text=MANAGER_APPROVED_TOPIC.format(phone=present["phone"]),
                    ),
                )
            else:
                logger.warning(
                    "Missing manager topic id for approved present_id={}",
                    present_id,
                )
            await callback.answer(MANAGER_CB_DONE)
            return

        if action == "reject":
            result, present = await ctx.db.moderate_present_if_status(
                present_id,
                status="rejected",
                expected_status="pending_review",
                event_type="present_rejected",
            )
            if result == "not_found":
                await callback.answer(CB_NOT_FOUND)
                return
            if result != "ok":
                await callback.answer(MANAGER_CB_ALREADY_PROCESSED)
                return
            manager_topic_id = (
                present.get("topic_id") or callback.message.message_thread_id
            )
            await _safe_clear_inline_keyboard(callback, "reject")
            await safe_telegram_call(
                "manager.notify_user_rejected",
                lambda: ctx.bot.send_message(
                    chat_id=present["user_id"],
                    text=CLIENT_REJECTED,
                    reply_markup=ReplyKeyboardRemove(),
                ),
            )
            if manager_topic_id:
                await safe_telegram_call(
                    "manager.notify_topic_rejected",
                    lambda: ctx.bot.send_message(
                        chat_id=ctx.settings.managers_group_id,
                        message_thread_id=manager_topic_id,
                        text=MANAGER_REJECTED_TOPIC,
                    ),
                )
            else:
                logger.warning(
                    "Missing manager topic id for rejected present_id={}",
                    present_id,
                )
            await callback.answer(MANAGER_CB_REJECTED)
            return

        await callback.answer(CB_UNKNOWN_COMMAND)

    # Free-form manager replies in topic chats are mirrored back to the user.
    @router.message(lambda m: m.chat.id == ctx.settings.managers_group_id)
    async def manager_topic_messages(message: Message) -> None:
        if not message.from_user or message.from_user.is_bot:
            return
        topic_id = message.message_thread_id
        if not topic_id:
            return

        user_id = await _resolve_user_id_for_manager_reply(ctx, message, topic_id)
        if user_id is None:
            return

        copied = await safe_telegram_call(
            "manager.copy_message_to_user",
            lambda: ctx.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            ),
        )
        if copied is None:
            return
        await ctx.db.add_event(
            user_id,
            "manager_reply_delivered",
            {"topic_id": topic_id, "copied_message_id": copied.message_id},
        )

    return router
