import json
import os
from datetime import datetime, timezone

import aiosqlite
from aiogram.types import Message
from loguru import logger


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DB:
    def __init__(self, path: str):
        self.path = path

    def _ensure_writable_path(self) -> str:
        db_dir = os.path.dirname(self.path) or "."
        try:
            os.makedirs(db_dir, exist_ok=True)
            return self.path
        except OSError as exc:
            fallback_path = "./data/bot.sqlite3"
            fallback_dir = os.path.dirname(fallback_path)
            os.makedirs(fallback_dir, exist_ok=True)
            logger.warning(
                "SQLite path '{}' is not writable ({}). Fallback to '{}'.",
                self.path,
                exc,
                fallback_path,
            )
            self.path = fallback_path
            return self.path

    async def init(self) -> None:
        db_path = self._ensure_writable_path()
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    flow_state TEXT NOT NULL DEFAULT 'idle',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS support_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    topic_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS presents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    phone TEXT,
                    screenshot_file_id TEXT,
                    topic_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS message_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    manager_message_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            await conn.commit()

    async def upsert_user(self, message: Message) -> None:
        created_at = now_iso()
        full_name = (message.from_user.full_name or "").strip() or str(message.from_user.id)
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """
                INSERT INTO users(user_id, username, full_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name,
                    updated_at=excluded.updated_at
                """,
                (message.from_user.id, message.from_user.username, full_name, created_at, created_at),
            )
            await conn.commit()

    async def set_user_state(self, user_id: int, state: str) -> None:
        updated_at = now_iso()
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE users SET flow_state = ?, updated_at = ? WHERE user_id = ?",
                (state, updated_at, user_id),
            )
            await conn.commit()

    async def get_user_state(self, user_id: int) -> str:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute("SELECT flow_state FROM users WHERE user_id = ?", (user_id,))
            ).fetchone()
            return row["flow_state"] if row else "idle"

    async def set_user_phone(self, user_id: int, phone: str) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE users SET phone = ?, updated_at = ? WHERE user_id = ?",
                (phone, now_iso(), user_id),
            )
            await conn.commit()

    async def get_user_name(self, user_id: int) -> str:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
            ).fetchone()
            return row["full_name"] if row else str(user_id)

    async def create_support_case(self, user_id: int, category: str, topic_id: int) -> None:
        stamp = now_iso()
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """
                INSERT INTO support_cases(user_id, category, status, topic_id, created_at, updated_at)
                VALUES (?, ?, 'open', ?, ?, ?)
                """,
                (user_id, category, topic_id, stamp, stamp),
            )
            await conn.commit()

    async def get_open_support_topic(self, user_id: int) -> int | None:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute(
                    """
                    SELECT topic_id
                    FROM support_cases
                    WHERE user_id = ? AND status = 'open'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id,),
                )
            ).fetchone()
            return row["topic_id"] if row else None

    async def resolve_support_topic(self, topic_id: int) -> int | None:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute(
                    """
                    SELECT id, user_id
                    FROM support_cases
                    WHERE topic_id = ? AND status = 'open'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (topic_id,),
                )
            ).fetchone()
            if not row:
                return None
            await conn.execute(
                "UPDATE support_cases SET status = 'resolved', updated_at = ? WHERE id = ?",
                (now_iso(), row["id"]),
            )
            await conn.commit()
            return row["user_id"]

    async def get_user_by_topic(self, topic_id: int) -> int | None:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute(
                    """
                    SELECT user_id
                    FROM support_cases
                    WHERE topic_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (topic_id,),
                )
            ).fetchone()
            return row["user_id"] if row else None

    async def has_approved_present(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as conn:
            row = await (
                await conn.execute(
                    "SELECT 1 FROM presents WHERE user_id = ? AND status = 'approved' LIMIT 1",
                    (user_id,),
                )
            ).fetchone()
            return bool(row)

    async def upsert_present_waiting_phone(self, user_id: int) -> int:
        stamp = now_iso()
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute("SELECT id, status FROM presents WHERE user_id = ?", (user_id,))
            ).fetchone()
            if row:
                await conn.execute(
                    """
                    UPDATE presents
                    SET status = 'waiting_phone', phone = NULL, screenshot_file_id = NULL, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (stamp, user_id),
                )
                await conn.commit()
                return row["id"]
            cursor = await conn.execute(
                """
                INSERT INTO presents(user_id, status, created_at, updated_at)
                VALUES (?, 'waiting_phone', ?, ?)
                """,
                (user_id, stamp, stamp),
            )
            await conn.commit()
            return cursor.lastrowid

    async def set_present_phone(self, present_id: int, phone: str) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE presents SET phone = ?, status = 'phone_confirm', updated_at = ? WHERE id = ?",
                (phone, now_iso(), present_id),
            )
            await conn.commit()

    async def set_present_waiting_screenshot(self, present_id: int) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE presents SET status = 'waiting_screenshot', updated_at = ? WHERE id = ?",
                (now_iso(), present_id),
            )
            await conn.commit()

    async def get_latest_present(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute(
                    """
                    SELECT id, status, phone
                    FROM presents
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id,),
                )
            ).fetchone()
            return dict(row) if row else None

    async def set_present_pending_review(self, present_id: int, screenshot_file_id: str, topic_id: int) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """
                UPDATE presents
                SET status = 'pending_review',
                    screenshot_file_id = ?,
                    topic_id = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (screenshot_file_id, topic_id, now_iso(), present_id),
            )
            await conn.commit()

    async def get_present_by_id(self, present_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute(
                    """
                    SELECT id, user_id, status, phone, screenshot_file_id, topic_id
                    FROM presents
                    WHERE id = ?
                    """,
                    (present_id,),
                )
            ).fetchone()
            return dict(row) if row else None

    async def set_present_result(self, present_id: int, status: str) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE presents SET status = ?, updated_at = ? WHERE id = ?",
                (status, now_iso(), present_id),
            )
            await conn.commit()

    async def add_message_link(self, user_id: int, topic_id: int, manager_message_id: int) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """
                INSERT INTO message_links(user_id, topic_id, manager_message_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, topic_id, manager_message_id, now_iso()),
            )
            await conn.commit()

    async def get_user_by_manager_message(self, manager_message_id: int, topic_id: int) -> int | None:
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            row = await (
                await conn.execute(
                    """
                    SELECT user_id
                    FROM message_links
                    WHERE manager_message_id = ? AND topic_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (manager_message_id, topic_id),
                )
            ).fetchone()
            return row["user_id"] if row else None

    async def add_event(self, user_id: int, event_type: str, payload: dict) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """
                INSERT INTO events(user_id, event_type, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, event_type, json.dumps(payload, ensure_ascii=False), now_iso()),
            )
            await conn.commit()
