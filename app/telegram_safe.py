import asyncio
from typing import Awaitable, Callable, TypeVar

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from loguru import logger

T = TypeVar("T")


async def safe_telegram_call(
    operation: str,
    call: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    raise_on_forbidden: bool = False,
    raise_on_bad_request: bool = False,
) -> T | None:
    attempt = 0
    while True:
        attempt += 1
        try:
            return await call()
        except TelegramRetryAfter as exc:
            if attempt >= retries:
                logger.error(
                    "Telegram flood limit (retry_after={}s), operation='{}' failed after {} attempts",
                    exc.retry_after,
                    operation,
                    attempt,
                )
                return None
            wait_seconds = max(float(exc.retry_after), 1.0)
            logger.warning(
                "Telegram flood limit for operation='{}', wait {}s (attempt {}/{})",
                operation,
                wait_seconds,
                attempt,
                retries,
            )
            await asyncio.sleep(wait_seconds)
        except (TelegramNetworkError, TelegramServerError) as exc:
            if attempt >= retries:
                logger.error(
                    "Temporary Telegram API error for operation='{}' after {} attempts: {}",
                    operation,
                    attempt,
                    exc,
                )
                return None
            wait_seconds = float(attempt)
            logger.warning(
                "Temporary Telegram API error for operation='{}': {}. Retry in {}s (attempt {}/{})",
                operation,
                exc,
                wait_seconds,
                attempt,
                retries,
            )
            await asyncio.sleep(wait_seconds)
        except TelegramForbiddenError as exc:
            logger.warning("Forbidden Telegram API operation='{}': {}", operation, exc)
            if raise_on_forbidden:
                raise
            return None
        except TelegramBadRequest as exc:
            logger.error("Bad request Telegram API operation='{}': {}", operation, exc)
            if raise_on_bad_request:
                raise
            return None
        except TelegramAPIError as exc:
            logger.error("Telegram API error operation='{}': {}", operation, exc)
            return None
