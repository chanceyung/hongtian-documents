"""本地 KV 存储 — 用 SQLite 替代 Redis，零外部依赖。

提供与 Redis 兼容的异步接口，数据持久化到本地 SQLite 文件。
桌面版不需要 Redis 服务器，所有数据存在 app_data/kv_store.db。
"""
import json
from pathlib import Path
from typing import Optional

import aiosqlite

from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalKVStore:
    """基于 SQLite 的键值存储，模拟 Redis Hash 操作。"""

    def __init__(self, db_path: str = ""):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        if not self._db_path:
            from app.core.config import settings
            db_dir = Path(settings.DATABASE_URL.replace("sqlite:///", "")).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = str(db_dir / "kv_store.db")

        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_strings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL DEFAULT 0
            )
        """)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_hashes (
                hash_key TEXT NOT NULL,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                expires_at REAL DEFAULT 0,
                PRIMARY KEY (hash_key, field)
            )
        """)
        await self._conn.commit()
        logger.info("KV store initialized", db_path=self._db_path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ---- String operations ----

    async def get(self, key: str) -> Optional[str]:
        await self._cleanup_expired()
        cursor = await self._conn.execute(
            "SELECT value FROM kv_strings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set(self, key: str, value: str, ex: int = 0) -> None:
        import time
        expires_at = (time.time() + ex) if ex > 0 else 0
        await self._conn.execute(
            "INSERT OR REPLACE INTO kv_strings (key, value, expires_at) VALUES (?, ?, ?)",
            (key, value, expires_at),
        )
        await self._conn.commit()

    async def delete(self, key: str) -> None:
        await self._conn.execute("DELETE FROM kv_strings WHERE key = ?", (key,))
        await self._conn.execute("DELETE FROM kv_hashes WHERE hash_key = ?", (key,))
        await self._conn.commit()

    # ---- Hash operations ----

    async def hset(self, hash_key: str, mapping: dict[str, str]) -> None:
        for field, value in mapping.items():
            await self._conn.execute(
                "INSERT OR REPLACE INTO kv_hashes (hash_key, field, value, expires_at) "
                "VALUES (?, ?, ?, COALESCE("
                "  (SELECT expires_at FROM kv_hashes WHERE hash_key = ? AND field = ?), 0))",
                (hash_key, field, value, hash_key, field),
            )
        await self._conn.commit()

    async def hget(self, hash_key: str, field: str) -> Optional[str]:
        await self._cleanup_expired()
        cursor = await self._conn.execute(
            "SELECT value FROM kv_hashes WHERE hash_key = ? AND field = ?",
            (hash_key, field),
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def hgetall(self, hash_key: str) -> dict[str, str]:
        await self._cleanup_expired()
        cursor = await self._conn.execute(
            "SELECT field, value FROM kv_hashes WHERE hash_key = ?", (hash_key,)
        )
        rows = await cursor.fetchall()
        return {row["field"]: row["value"] for row in rows}

    async def exists(self, key: str) -> bool:
        await self._cleanup_expired()
        cursor = await self._conn.execute(
            "SELECT 1 FROM kv_strings WHERE key = ? UNION ALL "
            "SELECT 1 FROM kv_hashes WHERE hash_key = ? LIMIT 1",
            (key, key),
        )
        return await cursor.fetchone() is not None

    async def expire(self, key: str, seconds: int) -> None:
        import time
        expires_at = time.time() + seconds
        await self._conn.execute(
            "UPDATE kv_strings SET expires_at = ? WHERE key = ?", (expires_at, key)
        )
        await self._conn.execute(
            "UPDATE kv_hashes SET expires_at = ? WHERE hash_key = ?", (expires_at, key)
        )
        await self._conn.commit()

    async def ttl(self, key: str) -> int:
        import time
        now = time.time()
        cursor = await self._conn.execute(
            "SELECT expires_at FROM kv_strings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if not row:
            return -2
        if row["expires_at"] == 0:
            return -1
        remaining = int(row["expires_at"] - now)
        return max(remaining, 0)

    # ---- Internal ----

    async def _cleanup_expired(self) -> None:
        import time
        now = time.time()
        await self._conn.execute(
            "DELETE FROM kv_strings WHERE expires_at > 0 AND expires_at < ?", (now,)
        )
        await self._conn.execute(
            "DELETE FROM kv_hashes WHERE expires_at > 0 AND expires_at < ?", (now,)
        )


kv_store = LocalKVStore()