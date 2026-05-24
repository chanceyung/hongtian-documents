"""Agent 级错误恢复策略 — 三级恢复：重试 → 降级 → 用户协商

每个 Agent 有独立的降级策略表，流水线节点通过 RecoveryManager 统一调度。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel

from app.core.logging import get_logger
from app.exceptions import ParseError, RenderError, SupplementError, WorkflowError

logger = get_logger(__name__)


class RecoveryAction(str, Enum):
    RETRY = "retry"
    DEGRADE = "degrade"
    NOTIFY_USER = "notify_user"
    ABORT = "abort"


class RecoveryResult(BaseModel):
    action: RecoveryAction
    success: bool = False
    message: str = ""
    degraded: bool = False
    fallback_used: str = ""


class FallbackStrategy(BaseModel):
    trigger: str
    fallback: str
    description: str = ""


AGENT_STRATEGIES: dict[str, list[FallbackStrategy]] = {
    "parser": [
        FallbackStrategy(
            trigger="docling_memory_error",
            fallback="pymupdf",
            description="Docling 子进程崩溃，降级到 PyMuPDF 解析",
        ),
        FallbackStrategy(
            trigger="image_extract_failed",
            fallback="mark_needs_supplement",
            description="图片提取失败，标记为需要补充",
        ),
        FallbackStrategy(
            trigger="pdf_structure_complex",
            fallback="text_only_mode",
            description="PDF 结构过于复杂，只提取文本",
        ),
    ],
    "analyzer": [
        FallbackStrategy(
            trigger="glm5_timeout",
            fallback="rule_based_analysis",
            description="GLM-5 超时，使用规则引擎降级分析",
        ),
        FallbackStrategy(
            trigger="all_retries_failed",
            fallback="minimal_analysis",
            description="所有重试失败，执行最小化分析",
        ),
    ],
    "designer": [
        FallbackStrategy(
            trigger="template_mismatch",
            fallback="generic_layout",
            description="模板不适配，使用通用布局",
        ),
        FallbackStrategy(
            trigger="glm5_error",
            fallback="rule_based_design",
            description="GLM-5 错误，使用规则引擎设计",
        ),
    ],
    "supplement": [
        FallbackStrategy(
            trigger="pexels_failed",
            fallback="try_unsplash",
            description="Pexels 搜索失败，尝试 Unsplash",
        ),
        FallbackStrategy(
            trigger="all_sources_failed",
            fallback="use_placeholder",
            description="所有素材源失败，使用占位符",
        ),
    ],
    "renderer": [
        FallbackStrategy(
            trigger="single_page_fail",
            fallback="skip_page",
            description="单页渲染失败，跳过该页",
        ),
        FallbackStrategy(
            trigger="playwright_timeout",
            fallback="weasyprint_fallback",
            description="Playwright 超时，降级到 WeasyPrint",
        ),
    ],
    "quality": [
        FallbackStrategy(
            trigger="visual_check_failed",
            fallback="targeted_repair",
            description="视觉质量校验失败，精准修复问题页",
        ),
    ],
}


def classify_error(agent_name: str, error: Exception) -> str:
    """根据异常类型和消息分类错误，返回 trigger 字符串"""
    error_msg = str(error).lower()

    if agent_name == "parser":
        if "docling" in error_msg or "memory" in error_msg:
            return "docling_memory_error"
        if "image" in error_msg:
            return "image_extract_failed"
        if "structure" in error_msg or "complex" in error_msg:
            return "pdf_structure_complex"
        return "parse_generic_error"

    if agent_name == "analyzer":
        if "timeout" in error_msg or "timed out" in error_msg:
            return "glm5_timeout"
        if "rate" in error_msg or "429" in error_msg:
            return "glm5_timeout"
        return "all_retries_failed"

    if agent_name == "designer":
        if "template" in error_msg or "match" in error_msg:
            return "template_mismatch"
        return "glm5_error"

    if agent_name == "supplement":
        if "pexels" in error_msg:
            return "pexels_failed"
        return "all_sources_failed"

    if agent_name == "renderer":
        if "page" in error_msg:
            return "single_page_fail"
        if "playwright" in error_msg or "timeout" in error_msg:
            return "playwright_timeout"
        return "render_generic_error"

    if agent_name == "quality":
        return "visual_check_failed"

    return "unknown_error"


class RecoveryManager:
    """统一错误恢复管理器"""

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self._attempt_counts: dict[str, int] = {}

    def get_attempts(self, agent_name: str, task_id: str) -> int:
        key = f"{task_id}:{agent_name}"
        return self._attempt_counts.get(key, 0)

    def increment_attempts(self, agent_name: str, task_id: str) -> int:
        key = f"{task_id}:{agent_name}"
        self._attempt_counts[key] = self._attempt_counts.get(key, 0) + 1
        return self._attempt_counts[key]

    def reset_attempts(self, agent_name: str, task_id: str) -> None:
        key = f"{task_id}:{agent_name}"
        self._attempt_counts.pop(key, None)

    async def recover(
        self,
        agent_name: str,
        error: Exception,
        task_id: str,
        fallback_fn: Callable[..., Awaitable[Any]] | None = None,
        **kwargs: Any,
    ) -> RecoveryResult:
        """三级恢复：重试 → 降级 → 通知用户"""
        trigger = classify_error(agent_name, error)
        attempts = self.increment_attempts(agent_name, task_id)

        logger.warning(
            "recovery.attempt",
            agent=agent_name,
            trigger=trigger,
            attempt=attempts,
            max_retries=self.max_retries,
            error=str(error)[:200],
        )

        # 级别 1：重试（未超过重试次数）
        if attempts <= self.max_retries:
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                success=False,
                message=f"第 {attempts} 次重试",
            )

        # 级别 2：降级（查找降级策略）
        strategies = AGENT_STRATEGIES.get(agent_name, [])
        matched = next(
            (s for s in strategies if s.trigger == trigger), None,
        )

        if matched and fallback_fn:
            logger.info(
                "recovery.degrade",
                agent=agent_name,
                trigger=trigger,
                fallback=matched.fallback,
            )
            try:
                result = await fallback_fn(matched.fallback, **kwargs)
                self.reset_attempts(agent_name, task_id)
                return RecoveryResult(
                    action=RecoveryAction.DEGRADE,
                    success=True,
                    message=matched.description,
                    degraded=True,
                    fallback_used=matched.fallback,
                )
            except Exception as fallback_error:
                logger.error(
                    "recovery.degrade_failed",
                    agent=agent_name,
                    fallback=matched.fallback,
                    error=str(fallback_error)[:200],
                )

        # 级别 3：通知用户
        logger.error(
            "recovery.notify_user",
            agent=agent_name,
            trigger=trigger,
            attempts=attempts,
        )
        return RecoveryResult(
            action=RecoveryAction.NOTIFY_USER,
            success=False,
            message=f"{agent_name} Agent 失败（{trigger}），已尝试 {attempts} 次。建议回退到上一个检查点。",
        )
