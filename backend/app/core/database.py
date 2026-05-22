"""SQLite 任务状态持久化"""
import aiosqlite
from pathlib import Path
from typing import Optional

from app.core.config import settings


class TaskDB:
    def __init__(self):
        self._db_url = settings.DATABASE_URL
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self):
        db_path = self._db_url.replace("sqlite:///", "")
        if db_path == ":memory:":
            self._conn = await aiosqlite.connect(":memory:")
        else:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(str(path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                progress REAL NOT NULL DEFAULT 0.0,
                message TEXT DEFAULT '',
                fidelity_score REAL,
                output_path TEXT,
                session_id TEXT DEFAULT '',
                source_file TEXT DEFAULT '',
                output_format TEXT DEFAULT 'pdf',
                template_id TEXT DEFAULT 'modern_tech',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def create_task(self, task_id: str, session_id: str = "", source_file: str = "") -> dict:
        await self._conn.execute(
            "INSERT INTO tasks (task_id, session_id, source_file) VALUES (?, ?, ?)",
            (task_id, session_id, source_file),
        )
        await self._conn.commit()
        return await self.get_task(task_id)

    async def get_task(self, task_id: str) -> Optional[dict]:
        cursor = await self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)

    async def update_task(self, task_id: str, **kwargs):
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [task_id]
        await self._conn.execute(
            f"UPDATE tasks SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
            values,
        )
        await self._conn.commit()

    async def list_tasks(self, session_id: str = "", limit: int = 50) -> list[dict]:
        if session_id:
            cursor = await self._conn.execute(
                "SELECT * FROM tasks WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def delete_old_tasks(self, days: int = 7) -> int:
        cursor = await self._conn.execute(
            "DELETE FROM tasks WHERE updated_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        await self._conn.commit()
        return cursor.rowcount

    async def delete_task(self, task_id: str) -> bool:
        cursor = await self._conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        await self._conn.commit()
        return cursor.rowcount > 0


task_db = TaskDB()