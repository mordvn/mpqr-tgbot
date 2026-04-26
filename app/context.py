from dataclasses import dataclass

from aiogram import Bot

from app.config import Settings
from app.db import DB


@dataclass(slots=True)
class AppContext:
    settings: Settings
    db: DB
    bot: Bot
