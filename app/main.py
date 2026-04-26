import asyncio
import os
import sys

# Support both запуск как модуль (`python -m app.main`)
# и запуск как файл (`python app/main.py`).
if __package__ is None or __package__ == "":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram_dialog import setup_dialogs
from loguru import logger
from app.config import Settings
from app.context import AppContext
from app.db import DB
from app.handlers.manager import build_manager_router
from app.handlers.user import build_user_dialog, build_user_router
from app.texts import CMD_DESC_HELP, CMD_DESC_REVIEW, CMD_DESC_START, CMD_HELP, CMD_REVIEW, CMD_START


def _stdout_sink(message: str) -> None:
    print(message, end="")


def build_startup_handler(ctx: AppContext):
    async def _startup_handler(bot: Bot, **_: object) -> None:
        await on_startup(bot, ctx)

    return _startup_handler


async def on_startup(bot: Bot, ctx: AppContext) -> None:
    await ctx.db.init()
    try:
        chat = await bot.get_chat(ctx.settings.managers_group_id)
        bot_me = await bot.get_me()
        bot_member = await bot.get_chat_member(ctx.settings.managers_group_id, bot_me.id)
        logger.info(
            "Managers chat configured: id={}, type={}, is_forum={}",
            chat.id,
            chat.type,
            getattr(chat, "is_forum", False),
        )
        logger.info(
            "Bot rights in managers chat: status={}, can_manage_topics={}",
            getattr(bot_member, "status", None),
            getattr(bot_member, "can_manage_topics", None),
        )
        if chat.type != "supergroup" or not getattr(chat, "is_forum", False):
            logger.warning(
                "Managers chat must be forum supergroup with topics enabled. "
                "Current type={}, is_forum={}",
                chat.type,
                getattr(chat, "is_forum", False),
            )
        can_manage_topics = getattr(bot_member, "can_manage_topics", False)
        if not can_manage_topics and getattr(bot_member, "status", "") != "creator":
            logger.warning(
                "Bot cannot create topics. Grant admin right: Manage Topics."
            )
    except Exception:
        logger.exception(
            "Cannot access managers chat id={}. Check MANAGERS_GROUP_ID and bot permissions.",
            ctx.settings.managers_group_id,
        )
    await bot.set_my_commands(
        commands=[
            BotCommand(command=CMD_START, description=CMD_DESC_START),
            BotCommand(command=CMD_HELP, description=CMD_DESC_HELP),
            BotCommand(command=CMD_REVIEW, description=CMD_DESC_REVIEW),
        ]
    )
    logger.info("Bot started")


async def run() -> None:
    settings = Settings.from_env()
    logger.remove()
    logger.add(
        sink=_stdout_sink,
        colorize=True,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{message}</cyan>"
        ),
    )
    db = DB(settings.sqlite_path)
    bot = Bot(
        token=settings.tg_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    ctx = AppContext(settings=settings, db=db, bot=bot)
    dp = Dispatcher()
    dp.include_router(build_user_router(ctx))
    dp.include_router(build_manager_router(ctx))
    dp.include_router(build_user_dialog(ctx))
    setup_dialogs(dp)
    dp.startup.register(build_startup_handler(ctx))
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
