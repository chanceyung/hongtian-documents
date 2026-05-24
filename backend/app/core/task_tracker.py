"""任务追踪器 — 线程安全关闭 + 阶段幂等性保证。

两部分功能：
1. 线程安全的任务计数（用于优雅关闭）
2. Redis 支持的阶段状态追踪（用于幂等重试）
"""
from __future__ import annotations

import threading
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── 线程安全关闭 ──────────────────────────────────────────────

_lock = threading.Lock()
_active_tasks: int = 0
_shutting_down: bool = False


def is_shutting_down() -> bool:
    return _shutting_down


def start_task() -> bool:
    global _active_tasks, _shutting_down
    with _lock:
        if _shutting_down:
            return False
        _active_tasks += 1
    return True


def end_task():
    global _active_tasks
    with _lock:
        _active_tasks -= 1


def get_active_count() -> int:
    with _lock:
        return _active_tasks


def set_shutting_down():
    global _shutting_down
    with _lock:
        _shutting_down = True


# ── 阶段幂等追踪 ──────────────────────────────────────────────

EXPIRE_SECONDS = 86400  # 24h


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


PHASE_ORDER = [
    "plan", "parse", "analyze", "design",
    "supplement", "render", "verify", "finalize",
]


class TaskTracker:
    """基于 Redis 的任务阶段追踪，支持幂等重试。"""

    def _key(self, task_id: str) -> str:
        return f"task_phases:{task_id}"

    async def _get_all(self, task_id: str) -> dict[str, str]:
        from app.core.redis import redis_client

        redis = redis_client.client
        data = await redis.hgetall(self._key(task_id))
        return {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in data.items()
        }

    async def get_phase(self, task_id: str, phase: str) -> PhaseStatus:
        all_phases = await self._get_all(task_id)
        raw = all_phases.get(phase, PhaseStatus.PENDING)
        try:
            return PhaseStatus(raw)
        except ValueError:
            return PhaseStatus.PENDING

    async def set_phase(self, task_id: str, phase: str, status: PhaseStatus, error: str = "") -> None:
        from app.core.redis import redis_client

        redis = redis_client.client
        key = self._key(task_id)
        await redis.hset(key, phase, status.value)
        if error:
            await redis.hset(key, f"{phase}:error", error[:500])
        await redis.expire(key, EXPIRE_SECONDS)

    async def mark_running(self, task_id: str, phase: str) -> None:
        await self.set_phase(task_id, phase, PhaseStatus.RUNNING)

    async def mark_completed(self, task_id: str, phase: str) -> None:
        await self.set_phase(task_id, phase, PhaseStatus.COMPLETED)

    async def mark_failed(self, task_id: str, phase: str, error: str = "") -> None:
        await self.set_phase(task_id, phase, PhaseStatus.FAILED, error=error)

    async def is_completed(self, task_id: str, phase: str) -> bool:
        return await self.get_phase(task_id, phase) == PhaseStatus.COMPLETED

    async def should_run(self, task_id: str, phase: str) -> bool:
        status = await self.get_phase(task_id, phase)
        return status in (PhaseStatus.PENDING, PhaseStatus.FAILED)

    async def get_resume_phase(self, task_id: str) -> str | None:
        """返回第一个未完成的阶段名，用于恢复执行。"""
        all_phases = await self._get_all(task_id)
        for phase in PHASE_ORDER:
            raw = all_phases.get(phase, PhaseStatus.PENDING)
            try:
                status = PhaseStatus(raw)
            except ValueError:
                status = PhaseStatus.PENDING
            if status != PhaseStatus.COMPLETED:
                return phase
        return None

    async def reset_from(self, task_id: str, phase: str) -> None:
        """将指定阶段及之后的所有阶段重置为 pending。"""
        idx = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else 0
        from app.core.redis import redis_client

        redis = redis_client.client
        key = self._key(task_id)
        for p in PHASE_ORDER[idx:]:
            await redis.hset(key, p, PhaseStatus.PENDING.value)
            await redis.hdel(key, f"{p}:error")
        await redis.expire(key, EXPIRE_SECONDS)

    async def delete(self, task_id: str) -> None:
        from app.core.redis import redis_client

        redis = redis_client.client
        await redis.delete(self._key(task_id))


_tracker: TaskTracker | None = None


def get_task_tracker() -> TaskTracker:
    global _tracker
    if _tracker is None:
        _tracker = TaskTracker()
    return _tracker
