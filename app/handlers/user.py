from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const
from loguru import logger

from app.context import AppContext
from app.keyboards import (
    contact_reply_keyboard,
    present_already_inline_help,
    phone_confirmation_inline,
    review_moderation_inline,
    support_case_manager_inline,
)
from app.states import AppSG
from app.telegram_safe import safe_telegram_call
from app.texts import (
    BTN_BACK,
    BTN_CONTACT_SELLER,
    BTN_GET_PRESENT,
    CB_ACCEPTED,
    CB_INVALID_ACTION,
    CB_MANAGER_GROUP_CONFIG_ERROR,
    CB_NOT_FOUND,
    CB_OPEN_HELP,
    CB_UNKNOWN_COMMAND,
    CATEGORY_BUNDLE,
    CATEGORY_OTHER,
    CATEGORY_QUALITY,
    CMD_HELP,
    CMD_REVIEW,
    CMD_START,
    ERR_MANAGER_GROUP_CONFIG,
    MAIN_TEXT,
    PHONE_CONFIRM_PROMPT,
    PHONE_CONFIRMED,
    PHONE_NOT_RECOGNIZED,
    PHONE_NOT_SPECIFIED,
    PHONE_RETRY_CALLBACK,
    PHONE_RETRY_PROMPT,
    PRESENT_ALREADY_RECEIVED,
    PRESENT_PHONE_PROMPT,
    REVIEW_PRESENT_TEXT,
    REVIEW_SCREENSHOT_PROMPT,
    REVIEW_SCREENSHOT_REQUIRED,
    REVIEW_SEND_RETRY,
    REVIEW_SENT_THANKS,
    REVIEW_TOPIC_CAPTION,
    REVIEW_TOPIC_CREATE_ERROR,
    REVIEW_TOPIC_TITLE,
    SESSION_NOT_FOUND_REVIEW,
    SUPPORT_REQUEST_DETAILS,
    SUPPORT_TEXT,
    SUPPORT_TOPIC_GREETING,
    SUPPORT_TOPIC_TITLE,
    USE_START_HINT,
)
from app.validators import normalize_phone


async def _hide_reply_keyboard_silent(message: Message) -> None:
    # Telegram reply keyboard is sticky; remove it silently.
    cleanup_message = await safe_telegram_call(
        "user.hide_reply_keyboard",
        lambda: message.answer("\u2060", reply_markup=ReplyKeyboardRemove()),
    )
    if cleanup_message:
        await safe_telegram_call(
            "user.delete_cleanup_message",
            lambda: cleanup_message.delete(),
        )


def _extract_phone_callback_action(callback_data: str) -> tuple[str, int] | None:
    parts = callback_data.split(":")
    if len(parts) != 3:
        return None
    try:
        present_id = int(parts[2])
    except ValueError:
        return None
    return parts[1], present_id


def _extract_support_category(widget_id: str) -> str:
    category_map = {
        "cat_quality": CATEGORY_QUALITY,
        "cat_bundle": CATEGORY_BUNDLE,
        "cat_other": CATEGORY_OTHER,
    }
    return category_map.get(widget_id, CATEGORY_OTHER)


def _extract_image_file_id(message: Message) -> tuple[str | None, str | None]:
    if message.photo:
        return message.photo[-1].file_id, "photo"
    if (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
    ):
        return message.document.file_id, "document"
    return None, None


async def _handle_phone_ok_callback(
    ctx: AppContext,
    callback: CallbackQuery,
    present_id: int,
) -> None:
    await ctx.db.set_present_waiting_screenshot(present_id)
    await ctx.db.set_user_state(callback.from_user.id, "present_waiting_screenshot")
    await _hide_reply_keyboard_silent(callback.message)
    await callback.message.edit_text(REVIEW_SCREENSHOT_PROMPT)
    await ctx.db.add_event(callback.from_user.id, "phone_confirmed", {"present_id": present_id})
    await callback.answer(PHONE_CONFIRMED)


async def _handle_phone_retry_callback(
    ctx: AppContext,
    callback: CallbackQuery,
) -> None:
    await ctx.db.set_user_state(callback.from_user.id, "present_waiting_phone")
    await callback.message.edit_text(PHONE_RETRY_PROMPT)
    # Reply keyboard cannot be attached via edit_message_text,
    # so we send a separate message only for contact share keyboard.
    await callback.message.answer(
        PRESENT_PHONE_PROMPT,
        reply_markup=contact_reply_keyboard(),
    )
    await callback.answer(PHONE_RETRY_CALLBACK)


async def _handle_support_waiting_message(ctx: AppContext, message: Message) -> None:
    topic_id = await ctx.db.get_open_support_topic(message.from_user.id)
    if topic_id is None:
        topic_id = await ensure_support_topic_and_open(
            ctx=ctx, user_id=message.from_user.id, category=CATEGORY_OTHER
        )
        await ctx.db.set_user_state(message.from_user.id, "support_waiting")
    forwarded = await safe_telegram_call(
        "user.forward_to_manager_topic",
        lambda: ctx.bot.forward_message(
            chat_id=ctx.settings.managers_group_id,
            message_thread_id=topic_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        ),
    )
    if forwarded is None:
        logger.warning("Failed to forward user message to manager topic_id={}", topic_id)
        return
    await ctx.db.add_message_link(message.from_user.id, topic_id, forwarded.message_id)
    await ctx.db.add_event(
        message.from_user.id,
        "support_message_from_user",
        {"topic_id": topic_id, "source_message_id": message.message_id},
    )


async def _handle_present_waiting_phone_message(ctx: AppContext, message: Message) -> None:
    raw_phone = (
        message.contact.phone_number if message.contact and message.contact.phone_number else message.text
    )
    phone = normalize_phone(raw_phone or "")
    if not phone:
        await message.answer(PHONE_NOT_RECOGNIZED)
        return

    present = await ctx.db.get_latest_present(message.from_user.id)
    if not present:
        await message.answer(SESSION_NOT_FOUND_REVIEW)
        return
    await ctx.db.set_user_phone(message.from_user.id, phone)
    await ctx.db.set_present_phone(present["id"], phone)
    await ctx.db.add_event(
        message.from_user.id,
        "phone_received",
        {"present_id": present["id"], "phone": phone},
    )
    await message.answer(
        PHONE_CONFIRM_PROMPT.format(phone=phone),
        reply_markup=phone_confirmation_inline(present["id"]),
    )


async def _handle_present_waiting_screenshot_message(ctx: AppContext, message: Message) -> None:
    file_id, media_kind = _extract_image_file_id(message)
    if not file_id:
        await message.answer(REVIEW_SCREENSHOT_REQUIRED)
        return

    present = await ctx.db.get_latest_present(message.from_user.id)
    if not present:
        await message.answer(SESSION_NOT_FOUND_REVIEW)
        return
    user_name = await ctx.db.get_user_name(message.from_user.id)
    try:
        topic = await safe_telegram_call(
            "user.create_review_topic",
            lambda: ctx.bot.create_forum_topic(
                chat_id=ctx.settings.managers_group_id,
                name=REVIEW_TOPIC_TITLE.format(user_name=user_name),
            ),
            raise_on_bad_request=True,
            raise_on_forbidden=True,
        )
        if topic is None:
            await message.answer(REVIEW_TOPIC_CREATE_ERROR)
            return
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception("Cannot create review topic for user_id={}", message.from_user.id)
        await message.answer(REVIEW_TOPIC_CREATE_ERROR)
        return
    caption = REVIEW_TOPIC_CAPTION.format(
        user_name=user_name,
        phone=present.get("phone") or PHONE_NOT_SPECIFIED,
    )
    if media_kind == "photo":
        sent = await safe_telegram_call(
            "user.send_review_photo_to_manager",
            lambda: ctx.bot.send_photo(
                chat_id=ctx.settings.managers_group_id,
                message_thread_id=topic.message_thread_id,
                photo=file_id,
                caption=caption,
                reply_markup=review_moderation_inline(present["id"]),
            ),
        )
    else:
        sent = await safe_telegram_call(
            "user.send_review_document_to_manager",
            lambda: ctx.bot.send_document(
                chat_id=ctx.settings.managers_group_id,
                message_thread_id=topic.message_thread_id,
                document=file_id,
                caption=caption,
                reply_markup=review_moderation_inline(present["id"]),
            ),
        )
    if sent is None:
        await message.answer(REVIEW_SEND_RETRY)
        return

    await ctx.db.set_present_pending_review(present["id"], file_id, topic.message_thread_id)
    await ctx.db.set_user_state(message.from_user.id, "idle")
    await ctx.db.add_event(
        message.from_user.id,
        "review_screenshot_sent",
        {"present_id": present["id"], "topic_id": topic.message_thread_id},
    )
    await message.answer(
        REVIEW_SENT_THANKS,
        reply_markup=ReplyKeyboardRemove(),
    )


def build_user_dialog(ctx: AppContext) -> Dialog:
    async def on_go_present(
        callback: CallbackQuery, _: Button, manager: DialogManager
    ) -> None:
        await start_present_flow(
            callback.message,
            callback.from_user.id,
            ctx=ctx,
            intro_text=REVIEW_PRESENT_TEXT,
        )
        await callback.answer()
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(AppSG.main)

    async def on_go_support(
        callback: CallbackQuery, _: Button, manager: DialogManager
    ) -> None:
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(AppSG.support_category)
        await callback.answer()

    async def on_back_main(
        callback: CallbackQuery, _: Button, manager: DialogManager
    ) -> None:
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(AppSG.main)
        await callback.answer()

    async def on_pick_category(
        callback: CallbackQuery, button: Button, manager: DialogManager
    ) -> None:
        category = _extract_support_category(button.widget_id)
        user_id = callback.from_user.id
        try:
            await ensure_support_topic_and_open(
                ctx=ctx, user_id=user_id, category=category
            )
        except (TelegramBadRequest, TelegramForbiddenError, RuntimeError):
            await callback.message.answer(ERR_MANAGER_GROUP_CONFIG)
            await callback.answer(CB_MANAGER_GROUP_CONFIG_ERROR)
            logger.exception("Cannot create support topic")
            return
        await ctx.db.set_user_state(user_id, "support_waiting")
        await callback.message.edit_text(SUPPORT_REQUEST_DETAILS)
        await ctx.db.add_event(user_id, "support_started", {"category": category})
        await callback.answer(CB_ACCEPTED)
        await manager.done(show_mode=ShowMode.NO_UPDATE)

    def category_button(title: str, key: str) -> Button:
        return Button(Const(title), id=f"cat_{key}", on_click=on_pick_category)

    return Dialog(
        Window(
            Const(MAIN_TEXT),
            Button(Const(BTN_GET_PRESENT), id="go_present", on_click=on_go_present),
            Button(Const(BTN_CONTACT_SELLER), id="go_support", on_click=on_go_support),
            state=AppSG.main,
        ),
        Window(
            Const(SUPPORT_TEXT),
            category_button(CATEGORY_QUALITY, "quality"),
            category_button(CATEGORY_BUNDLE, "bundle"),
            category_button(CATEGORY_OTHER, "other"),
            Button(Const(BTN_BACK), id="back_main", on_click=on_back_main),
            state=AppSG.support_category,
        ),
    )


async def ensure_support_topic_and_open(
    ctx: AppContext, user_id: int, category: str
) -> int:
    topic_id = await ctx.db.get_open_support_topic(user_id)
    if topic_id:
        return topic_id

    user_name = await ctx.db.get_user_name(user_id)
    topic = await safe_telegram_call(
        "user.create_support_topic",
        lambda: ctx.bot.create_forum_topic(
            chat_id=ctx.settings.managers_group_id,
            name=SUPPORT_TOPIC_TITLE.format(user_name=user_name),
        ),
        raise_on_bad_request=True,
        raise_on_forbidden=True,
    )
    if topic is None:
        raise RuntimeError("failed to create support topic")
    await ctx.db.create_support_case(user_id, category, topic.message_thread_id)
    await safe_telegram_call(
        "user.send_support_topic_greeting",
        lambda: ctx.bot.send_message(
            chat_id=ctx.settings.managers_group_id,
            message_thread_id=topic.message_thread_id,
            text=SUPPORT_TOPIC_GREETING.format(user_name=user_name, category=category),
            reply_markup=support_case_manager_inline(user_id),
        ),
    )
    return topic.message_thread_id


async def start_present_flow(
    message: Message,
    user_id: int,
    ctx: AppContext,
    intro_text: str | None = None,
) -> None:
    if await ctx.db.has_approved_present(user_id):
        await message.answer(
            PRESENT_ALREADY_RECEIVED,
            reply_markup=present_already_inline_help(),
        )
        return
    present_id = await ctx.db.upsert_present_waiting_phone(user_id)
    await ctx.db.set_user_state(user_id, "present_waiting_phone")
    await ctx.db.add_event(user_id, "present_started", {"present_id": present_id})
    await message.answer(
        intro_text or PRESENT_PHONE_PROMPT,
        reply_markup=contact_reply_keyboard(),
    )


def build_user_router(ctx: AppContext) -> Router:
    router = Router()

    @router.message(Command(CMD_START))
    async def cmd_start(message: Message, dialog_manager: DialogManager) -> None:
        if message.chat.type != "private":
            return
        await ctx.db.upsert_user(message)
        await ctx.db.set_user_state(message.from_user.id, "idle")
        await ctx.db.add_event(message.from_user.id, "start", {})
        await _hide_reply_keyboard_silent(message)
        await dialog_manager.start(
            AppSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND
        )

    @router.message(Command(CMD_HELP))
    async def cmd_help(message: Message, dialog_manager: DialogManager) -> None:
        if message.chat.type != "private":
            return
        await ctx.db.upsert_user(message)
        await _hide_reply_keyboard_silent(message)
        await dialog_manager.start(
            AppSG.support_category,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND,
        )

    @router.message(Command(CMD_REVIEW))
    async def cmd_review(message: Message, dialog_manager: DialogManager) -> None:
        if message.chat.type != "private":
            return
        await ctx.db.upsert_user(message)
        await start_present_flow(
            message,
            message.from_user.id,
            ctx=ctx,
            intro_text=REVIEW_PRESENT_TEXT,
        )

    @router.callback_query(F.data.startswith("usr:phone_"))
    async def user_phone_callbacks(callback: CallbackQuery) -> None:
        if callback.message.chat.type != "private":
            await callback.answer()
            return
        action_payload = _extract_phone_callback_action(callback.data)
        if action_payload is None:
            await callback.answer(CB_INVALID_ACTION)
            return
        action, present_id = action_payload
        present = await ctx.db.get_present_by_id(present_id)
        if not present or present["user_id"] != callback.from_user.id:
            await callback.answer(CB_NOT_FOUND)
            return

        if action == "phone_ok":
            await _handle_phone_ok_callback(ctx, callback, present_id)
            return

        if action == "phone_retry":
            await _handle_phone_retry_callback(ctx, callback)
            return

        await callback.answer(CB_UNKNOWN_COMMAND)

    @router.callback_query(F.data == "usr:open_help")
    async def open_help_from_inline(
        callback: CallbackQuery, dialog_manager: DialogManager
    ) -> None:
        if callback.message.chat.type != "private":
            await callback.answer()
            return
        await callback.answer(CB_OPEN_HELP)
        await dialog_manager.start(
            AppSG.support_category,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.EDIT,
        )

    @router.message(F.chat.type == "private")
    async def private_user_messages(message: Message) -> None:
        if not message.from_user or message.from_user.is_bot:
            return
        if message.text and message.text.startswith("/"):
            return

        await ctx.db.upsert_user(message)
        state = await ctx.db.get_user_state(message.from_user.id)

        if state == "support_waiting":
            await _handle_support_waiting_message(ctx, message)
            return

        if state == "present_waiting_phone":
            await _handle_present_waiting_phone_message(ctx, message)
            return

        if state == "present_waiting_screenshot":
            await _handle_present_waiting_screenshot_message(ctx, message)
            return

        await message.answer(USE_START_HINT)

    return router
