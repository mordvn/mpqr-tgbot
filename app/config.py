from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.validators import normalize_manager_group_id


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tg_bot_token: str = Field(..., alias="TG_BOT_TOKEN")
    managers_group_id: int | str = Field(..., alias="MANAGERS_GROUP_ID")
    sqlite_path: str = Field("./data/bot.sqlite3", alias="SQLITE_PATH")
    bot_username: str = Field("", alias="BOT_USERNAME")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @model_validator(mode="after")
    def _normalize(self) -> "Settings":
        self.managers_group_id = normalize_manager_group_id(str(self.managers_group_id))
        self.log_level = self.log_level.strip().upper()
        self.bot_username = self.bot_username.strip()
        self.sqlite_path = self.sqlite_path.strip()
        self.tg_bot_token = self.tg_bot_token.strip()
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()
