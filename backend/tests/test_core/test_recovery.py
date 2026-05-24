"""Tests for RecoveryManager and error classification."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.recovery import (
    RecoveryAction,
    RecoveryResult,
    RecoveryManager,
    FallbackStrategy,
    AGENT_STRATEGIES,
    classify_error,
)


class TestClassifyError:
    def test_parser_docling_error(self):
        err = RuntimeError("docling process OOM memory error")
        assert classify_error("parser", err) == "docling_memory_error"

    def test_parser_image_error(self):
        err = ValueError("image extraction failed")
        assert classify_error("parser", err) == "image_extract_failed"

    def test_parser_structure_error(self):
        err = RuntimeError("PDF structure too complex")
        assert classify_error("parser", err) == "pdf_structure_complex"

    def test_parser_generic(self):
        err = RuntimeError("something went wrong")
        assert classify_error("parser", err) == "parse_generic_error"

    def test_analyzer_timeout(self):
        err = TimeoutError("request timed out after 30s")
        assert classify_error("analyzer", err) == "glm5_timeout"

    def test_analyzer_rate_limit(self):
        err = Exception("HTTP 429 rate limit exceeded")
        assert classify_error("analyzer", err) == "glm5_timeout"

    def test_analyzer_generic(self):
        err = RuntimeError("unexpected failure")
        assert classify_error("analyzer", err) == "all_retries_failed"

    def test_designer_template_error(self):
        err = ValueError("template mismatch for layout")
        assert classify_error("designer", err) == "template_mismatch"

    def test_designer_generic(self):
        err = RuntimeError("glm5 api error")
        assert classify_error("designer", err) == "glm5_error"

    def test_supplement_pexels(self):
        err = ConnectionError("pexels API unreachable")
        assert classify_error("supplement", err) == "pexels_failed"

    def test_supplement_generic(self):
        err = Exception("all sources unavailable")
        assert classify_error("supplement", err) == "all_sources_failed"

    def test_renderer_page_error(self):
        err = RuntimeError("page 3 render failed")
        assert classify_error("renderer", err) == "single_page_fail"

    def test_renderer_playwright_timeout(self):
        err = TimeoutError("playwright timeout 60s")
        assert classify_error("renderer", err) == "playwright_timeout"

    def test_renderer_generic(self):
        err = RuntimeError("unknown render issue")
        assert classify_error("renderer", err) == "render_generic_error"

    def test_quality_generic(self):
        err = Exception("visual check discrepancy")
        assert classify_error("quality", err) == "visual_check_failed"

    def test_unknown_agent(self):
        err = Exception("something")
        assert classify_error("unknown_agent", err) == "unknown_error"


class TestRecoveryManagerAttempts:
    def test_initial_attempts_zero(self):
        mgr = RecoveryManager()
        assert mgr.get_attempts("parser", "task1") == 0

    def test_increment_attempts(self):
        mgr = RecoveryManager()
        assert mgr.increment_attempts("parser", "task1") == 1
        assert mgr.increment_attempts("parser", "task1") == 2
        assert mgr.get_attempts("parser", "task1") == 2

    def test_reset_attempts(self):
        mgr = RecoveryManager()
        mgr.increment_attempts("parser", "task1")
        mgr.increment_attempts("parser", "task1")
        mgr.reset_attempts("parser", "task1")
        assert mgr.get_attempts("parser", "task1") == 0

    def test_different_tasks_independent(self):
        mgr = RecoveryManager()
        mgr.increment_attempts("parser", "task1")
        assert mgr.get_attempts("parser", "task2") == 0


class TestRecoveryManagerRecover:
    @pytest.mark.asyncio
    async def test_level1_retry_on_first_failure(self):
        mgr = RecoveryManager(max_retries=3)
        err = RuntimeError("docling memory error")
        result = await mgr.recover("parser", err, "task1")
        assert result.action == RecoveryAction.RETRY
        assert result.success is False
        assert "1" in result.message
        assert mgr.get_attempts("parser", "task1") == 1

    @pytest.mark.asyncio
    async def test_level1_retry_up_to_max(self):
        mgr = RecoveryManager(max_retries=3)
        err = RuntimeError("docling memory error")
        for i in range(3):
            result = await mgr.recover("parser", err, "task1")
            assert result.action == RecoveryAction.RETRY
        assert mgr.get_attempts("parser", "task1") == 3

    @pytest.mark.asyncio
    async def test_level2_degrade_with_fallback(self):
        mgr = RecoveryManager(max_retries=2)
        err = RuntimeError("docling memory error")
        # Exhaust retries
        await mgr.recover("parser", err, "task1")
        await mgr.recover("parser", err, "task1")

        fallback_fn = AsyncMock(return_value={"status": "ok", "parser": "pymupdf"})
        result = await mgr.recover("parser", err, "task1", fallback_fn=fallback_fn)

        assert result.action == RecoveryAction.DEGRADE
        assert result.success is True
        assert result.degraded is True
        assert result.fallback_used == "pymupdf"
        fallback_fn.assert_called_once_with("pymupdf")

    @pytest.mark.asyncio
    async def test_level2_fallback_failure_falls_to_notify(self):
        mgr = RecoveryManager(max_retries=1)
        err = RuntimeError("docling memory error")
        await mgr.recover("parser", err, "task1")

        fallback_fn = AsyncMock(side_effect=Exception("fallback also failed"))
        result = await mgr.recover("parser", err, "task1", fallback_fn=fallback_fn)

        assert result.action == RecoveryAction.NOTIFY_USER
        assert result.success is False

    @pytest.mark.asyncio
    async def test_level3_notify_user_when_no_strategy(self):
        mgr = RecoveryManager(max_retries=1)
        err = RuntimeError("unknown issue")
        await mgr.recover("unknown_agent", err, "task1")

        result = await mgr.recover("unknown_agent", err, "task1")
        assert result.action == RecoveryAction.NOTIFY_USER
        assert "unknown_agent" in result.message
        assert "unknown_error" in result.message

    @pytest.mark.asyncio
    async def test_level3_notify_user_when_no_fallback_fn(self):
        mgr = RecoveryManager(max_retries=1)
        err = RuntimeError("docling memory error")
        await mgr.recover("parser", err, "task1")

        result = await mgr.recover("parser", err, "task1")
        assert result.action == RecoveryAction.NOTIFY_USER
        assert result.success is False

    @pytest.mark.asyncio
    async def test_attempts_reset_after_successful_degrade(self):
        mgr = RecoveryManager(max_retries=2)
        err = RuntimeError("timeout")
        await mgr.recover("analyzer", err, "task1")
        await mgr.recover("analyzer", err, "task1")

        fallback_fn = AsyncMock(return_value={"analysis": "rule_based"})
        await mgr.recover("analyzer", err, "task1", fallback_fn=fallback_fn)

        assert mgr.get_attempts("analyzer", "task1") == 0


class TestAgentStrategies:
    def test_all_agents_have_strategies(self):
        expected = {"parser", "analyzer", "designer", "supplement", "renderer", "quality"}
        assert set(AGENT_STRATEGIES.keys()) == expected

    def test_parser_has_docling_fallback(self):
        strategies = AGENT_STRATEGIES["parser"]
        triggers = [s.trigger for s in strategies]
        assert "docling_memory_error" in triggers
        docling = next(s for s in strategies if s.trigger == "docling_memory_error")
        assert docling.fallback == "pymupdf"

    def test_supplement_has_pexels_and_unsplash(self):
        strategies = AGENT_STRATEGIES["supplement"]
        triggers = [s.trigger for s in strategies]
        assert "pexels_failed" in triggers
        assert "all_sources_failed" in triggers

    def test_renderer_has_playwright_fallback(self):
        strategies = AGENT_STRATEGIES["renderer"]
        triggers = [s.trigger for s in strategies]
        assert "playwright_timeout" in triggers
        pw = next(s for s in strategies if s.trigger == "playwright_timeout")
        assert pw.fallback == "weasyprint_fallback"


class TestFallbackStrategyModel:
    def test_fallback_strategy_fields(self):
        s = FallbackStrategy(
            trigger="test_trigger",
            fallback="test_fallback",
            description="test description",
        )
        assert s.trigger == "test_trigger"
        assert s.fallback == "test_fallback"
        assert s.description == "test description"

    def test_fallback_strategy_optional_description(self):
        s = FallbackStrategy(trigger="t", fallback="f")
        assert s.description == ""


class TestRecoveryResultModel:
    def test_default_values(self):
        r = RecoveryResult(action=RecoveryAction.RETRY)
        assert r.success is False
        assert r.message == ""
        assert r.degraded is False
        assert r.fallback_used == ""

    def test_degrade_result(self):
        r = RecoveryResult(
            action=RecoveryAction.DEGRADE,
            success=True,
            degraded=True,
            fallback_used="pymupdf",
            message="降级到 PyMuPDF",
        )
        assert r.action == RecoveryAction.DEGRADE
        assert r.degraded is True
