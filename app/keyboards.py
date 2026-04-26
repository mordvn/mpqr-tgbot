from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.texts import (
    BTN_CONTACT_SELLER,
    BTN_MANAGER_APPROVE,
    BTN_MANAGER_REJECT,
    BTN_MANAGER_REQUEST_REVIEW,
    BTN_PHONE_OK,
    BTN_PHONE_RETRY,
    BTN_SHARE_CONTACT,
)


def contact_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_SHARE_CONTACT, request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def present_already_inline_help() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=BTN_CONTACT_SELLER,
        callback_data="usr:open_help",
    )
    builder.adjust(1)
    return builder.as_markup()


def support_case_manager_inline(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=BTN_MANAGER_REQUEST_REVIEW,
        callback_data=f"mgr:request_review:{user_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def phone_confirmation_inline(present_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=BTN_PHONE_OK,
        callback_data=f"usr:phone_ok:{present_id}",
    )
    builder.button(
        text=BTN_PHONE_RETRY,
        callback_data=f"usr:phone_retry:{present_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def review_moderation_inline(present_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=BTN_MANAGER_APPROVE,
        callback_data=f"mgr:approve:{present_id}",
    )
    builder.button(
        text=BTN_MANAGER_REJECT,
        callback_data=f"mgr:reject:{present_id}",
    )
    builder.adjust(2)
    return builder.as_markup()
