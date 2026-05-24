"""Tests for TaskTracker — phase idempotency."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.task_tracker import (
    PhaseStatus,
    PHASE_ORDER,
    TaskTracker,
    get_task_tracker,
    start_task,
    end_task,
    get_active_count,
    is_shutting_down,
    set_shutting_down,
)


class TestThreadSafeShutdown:
    def test_start_task_increments(self):
        count = get_active_count()
        assert start_task() is True
        assert get_active_count() == count + 1
        end_task()

    def test_start_task_blocked_when_shutting_down(self):
        set_shutting_down()
        assert start_task() is False
        assert is_shutting_down() is True


class TestPhaseStatus:
    def test_pending(self):
        assert PhaseStatus.PENDING == "pending"

    def test_running(self):
        assert PhaseStatus.RUNNING == "running"

    def test_completed(self):
        assert PhaseStatus.COMPLETED == "completed"

    def test_failed(self):
        assert PhaseStatus.FAILED == "failed"


class TestPhaseOrder:
    def test_all_phases_present(self):
        assert PHASE_ORDER == [
            "plan", "parse", "analyze", "design",
            "supplement", "render", "verify", "finalize",
        ]


class TestTaskTracker:
    def _make_tracker(self):
        tracker = TaskTracker()
        tracker._get_all = AsyncMock(return_value={})
        return tracker

    @pytest.mark.asyncio
    async def test_get_phase_defaults_to_pending(self):
        tracker = self._make_tracker()
        status = await tracker.get_phase("task1", "plan")
        assert status == PhaseStatus.PENDING

    @pytest.mark.asyncio
    async def test_mark_running_and_read(self):
        tracker = self._make_tracker()
        mock_redis = MagicMock()
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.client = mock_redis
            await tracker.mark_running("task1", "parse")

        mock_redis.hset.assert_any_call("task_phases:task1", "parse", "running")
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_completed(self):
        tracker = self._make_tracker()
        mock_redis = MagicMock()
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.client = mock_redis
            await tracker.mark_completed("task1", "parse")

        mock_redis.hset.assert_any_call("task_phases:task1", "parse", "completed")

    @pytest.mark.asyncio
    async def test_mark_failed_with_error(self):
        tracker = self._make_tracker()
        mock_redis = MagicMock()
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.client = mock_redis
            await tracker.mark_failed("task1", "render", error="OOM")

        mock_redis.hset.assert_any_call("task_phases:task1", "render", "failed")
        mock_redis.hset.assert_any_call("task_phases:task1", "render:error", "OOM")

    @pytest.mark.asyncio
    async def test_is_completed_true(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={"parse": "completed"})
        assert await tracker.is_completed("task1", "parse") is True

    @pytest.mark.asyncio
    async def test_is_completed_false(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={"parse": "running"})
        assert await tracker.is_completed("task1", "parse") is False

    @pytest.mark.asyncio
    async def test_should_run_pending(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={})
        assert await tracker.should_run("task1", "plan") is True

    @pytest.mark.asyncio
    async def test_should_run_failed(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={"render": "failed"})
        assert await tracker.should_run("task1", "render") is True

    @pytest.mark.asyncio
    async def test_should_not_run_completed(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={"parse": "completed"})
        assert await tracker.should_run("task1", "parse") is False

    @pytest.mark.asyncio
    async def test_should_not_run_running(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={"design": "running"})
        assert await tracker.should_run("task1", "design") is False

    @pytest.mark.asyncio
    async def test_get_resume_phase_returns_first_incomplete(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={
            "plan": "completed",
            "parse": "completed",
            "analyze": "failed",
        })
        phase = await tracker.get_resume_phase("task1")
        assert phase == "analyze"

    @pytest.mark.asyncio
    async def test_get_resume_phase_all_completed_returns_none(self):
        tracker = self._make_tracker()
        completed = {p: "completed" for p in PHASE_ORDER}
        tracker._get_all = AsyncMock(return_value=completed)
        phase = await tracker.get_resume_phase("task1")
        assert phase is None

    @pytest.mark.asyncio
    async def test_get_resume_phase_nothing_done_returns_plan(self):
        tracker = self._make_tracker()
        tracker._get_all = AsyncMock(return_value={})
        phase = await tracker.get_resume_phase("task1")
        assert phase == "plan"

    @pytest.mark.asyncio
    async def test_reset_from_phase(self):
        tracker = self._make_tracker()
        mock_redis = MagicMock()
        mock_redis.hset = AsyncMock()
        mock_redis.hdel = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.client = mock_redis
            await tracker.reset_from("task1", "design")

        reset_phases = PHASE_ORDER[PHASE_ORDER.index("design"):]
        for p in reset_phases:
            mock_redis.hset.assert_any_call("task_phases:task1", p, "pending")
            mock_redis.hdel.assert_any_call("task_phases:task1", f"{p}:error")

    @pytest.mark.asyncio
    async def test_delete_task(self):
        tracker = self._make_tracker()
        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock()

        with patch("app.core.redis.redis_client") as mock_client:
            mock_client.client = mock_redis
            await tracker.delete("task1")

        mock_redis.delete.assert_called_once_with("task_phases:task1")


class TestGetTracker:
    def test_returns_singleton(self):
        t1 = get_task_tracker()
        t2 = get_task_tracker()
        assert t1 is t2
