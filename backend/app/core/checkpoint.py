"""Pipeline Checkpoint System — 5-level persistent state snapshots"""
from __future__ import annotations

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel
from structlog.stdlib import BoundLogger

from app.core.config import settings
from app.core.logging import get_logger


# Checkpoint level definitions
CheckpointLevel = Literal[0, 1, 2, 3, 4]
CHECKPOINT_PHASES = {
    0: "upload",
    1: "parse",
    2: "analyze",
    3: "design",
    4: "render",
}


class CheckpointInfo(BaseModel):
    """Checkpoint metadata"""
    id: str
    task_id: str
    level: int
    phase_name: str
    created_at: str


class CheckpointDB:
    """Thread-safe SQLite checkpoint storage"""

    def __init__(self):
        self._db_url = settings.DATABASE_URL
        self._conn: aiosqlite.Connection | None = None
        self._logger: BoundLogger = get_logger(__name__)

    async def initialize(self):
        """Initialize checkpoint table"""
        db_path = self._db_url.replace("sqlite:///", "")
        if db_path == ":memory:":
            self._conn = await aiosqlite.connect(":memory:")
        else:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(str(path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                level INTEGER NOT NULL,
                phase_name TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, level)
            )
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_task_id ON checkpoints(task_id)
        """)
        await self._conn.commit()
        self._logger.info("Checkpoint database initialized")

    async def close(self):
        """Close database connection"""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def save_checkpoint(
        self,
        task_id: str,
        level: CheckpointLevel,
        state: dict[str, Any],
    ) -> CheckpointInfo:
        """Save pipeline state at checkpoint level"""
        checkpoint_id = f"{task_id}_cp{level}"
        phase_name = CHECKPOINT_PHASES[level]
        state_json = json.dumps(state, ensure_ascii=False, default=str)

        await self._conn.execute(
            """
            INSERT INTO checkpoints (id, task_id, level, phase_name, state_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(task_id, level) DO UPDATE SET
                phase_name = excluded.phase_name,
                state_json = excluded.state_json,
                created_at = CURRENT_TIMESTAMP
            """,
            (checkpoint_id, task_id, level, phase_name, state_json),
        )
        await self._conn.commit()

        info = CheckpointInfo(
            id=checkpoint_id,
            task_id=task_id,
            level=level,
            phase_name=phase_name,
            created_at=datetime.now().isoformat(),
        )
        self._logger.info(
            "Checkpoint saved",
            task_id=task_id,
            level=level,
            phase=phase_name,
            state_keys=list(state.keys()),
        )
        return info

    async def load_checkpoint(
        self,
        task_id: str,
        level: CheckpointLevel,
    ) -> Optional[dict[str, Any]]:
        """Load pipeline state from checkpoint level"""
        cursor = await self._conn.execute(
            "SELECT state_json FROM checkpoints WHERE task_id = ? AND level = ?",
            (task_id, level),
        )
        row = await cursor.fetchone()
        if not row:
            self._logger.debug(
                "Checkpoint not found",
                task_id=task_id,
                level=level,
            )
            return None

        state = json.loads(row["state_json"])
        self._logger.info(
            "Checkpoint loaded",
            task_id=task_id,
            level=level,
            phase=CHECKPOINT_PHASES[level],
        )
        return state

    async def list_checkpoints(
        self,
        task_id: str,
    ) -> list[CheckpointInfo]:
        """List all checkpoints for a task"""
        cursor = await self._conn.execute(
            """
            SELECT id, task_id, level, phase_name, created_at
            FROM checkpoints WHERE task_id = ?
            ORDER BY level ASC
            """,
            (task_id,),
        )
        rows = await cursor.fetchall()
        return [
            CheckpointInfo(
                id=row["id"],
                task_id=row["task_id"],
                level=row["level"],
                phase_name=row["phase_name"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def delete_task_checkpoints(self, task_id: str) -> int:
        """Delete all checkpoints for a task"""
        cursor = await self._conn.execute(
            "DELETE FROM checkpoints WHERE task_id = ?",
            (task_id,),
        )
        await self._conn.commit()
        count = cursor.rowcount
        self._logger.info(
            "Checkpoints deleted",
            task_id=task_id,
            count=count,
        )
        return count

    async def get_latest_checkpoint(
        self,
        task_id: str,
    ) -> Optional[tuple[int, dict[str, Any]]]:
        """Get the highest level checkpoint for a task"""
        cursor = await self._conn.execute(
            """
            SELECT level, state_json FROM checkpoints
            WHERE task_id = ?
            ORDER BY level DESC
            LIMIT 1
            """,
            (task_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        level = int(row["level"])
        state = json.loads(row["state_json"])
        return (level, state)


# Global checkpoint database instance
checkpoint_db = CheckpointDB()