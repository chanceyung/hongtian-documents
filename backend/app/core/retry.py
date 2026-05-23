"""增强重试策略 — 指数退避 + 抖动 + 错误分类

参考 hongtian-ai-new/backend/intelligence/llm/retry.py 简化版
替换原 tenacity 方案，保持 @llm_retry 装饰器接口兼容
"""
from __future__ import annotations

import asyncio
import functools
import random
from typing import Any, Callable, TypeVar

from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# 可重试的 HTTP 状态码
_RETRYABLE_STATUS = {429, 500, 502, 503, 504, 529}

# 模型降级链
FALLBACK_CHAIN: dict[str, str] = {
    "glm-4-plus": "glm-4",
    "glm-4": "glm-4-flash",
    "glm-4-flash": "glm-4-long",
    "glm-4-long": "glm-4-long",
}

# 连续失败阈值 — 触发模型降级
_FALLBACK_THRESHOLD = 3


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True
    status = getattr(exc, "status_code", None)
    if status is not None and status in _RETRYABLE_STATUS:
        return True
    msg = str(exc).lower()
    if any(k in msg for k in ("rate_limit", "overload", "capacity", "too many requests")):
        return True
    return False


def _get_retry_after(exc: Exception) -> float | None:
    retry_after = getattr(exc, "headers", {}).get("retry-after")
    if retry_after:
        try:
            return float(retry_after)
        except (ValueError, TypeError):
            pass
    return None


def llm_retry(func: F) -> F:
    """LLM 调用重试装饰器 — 指数退避 + 抖动 + 错误分类

    与旧版 @llm_retry (tenacity) 接口兼容，无需改动调用方。
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        max_attempts = 3
        base_delay = 1.0
        max_delay = 30.0

        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc

                if not _is_retryable(exc):
                    raise

                if attempt >= max_attempts - 1:
                    raise

                # 计算 delay: 指数退避 + 随机抖动
                delay = base_delay * (2 ** attempt)
                jitter = random.random() * 0.25 * delay
                delay = min(delay + jitter, max_delay)

                # 如果有 Retry-After header，取较大值
                retry_after = _get_retry_after(exc)
                if retry_after:
                    delay = max(delay, retry_after)

                logger.warning(
                    "LLM call failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    delay=f"{delay:.1f}s",
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:200],
                )
                await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]

    return wrapper  # type: ignore[return-value]


def llm_retry_with_fallback(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Callable:
    """带模型降级的重试装饰器

    连续失败 _FALLBACK_THRESHOLD 次后自动降级到 fallback 模型。
    需要被装饰函数接受 `model` 关键字参数。
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            consecutive_failures = 0
            current_model = kwargs.get("model", "glm-4-flash")
            last_exc: Exception | None = None

            for attempt in range(max_attempts):
                kwargs["model"] = current_model
                try:
                    result = await func(*args, **kwargs)
                    consecutive_failures = 0
                    return result
                except Exception as exc:
                    last_exc = exc
                    consecutive_failures += 1

                    if not _is_retryable(exc):
                        raise

                    # 检查是否需要降级
                    if consecutive_failures >= _FALLBACK_THRESHOLD:
                        fallback = FALLBACK_CHAIN.get(current_model)
                        if fallback and fallback != current_model:
                            logger.warning(
                                "Model fallback triggered",
                                from_model=current_model,
                                to_model=fallback,
                                consecutive_failures=consecutive_failures,
                            )
                            current_model = fallback
                            consecutive_failures = 0

                    if attempt >= max_attempts - 1:
                        raise

                    delay = min(base_delay * (2 ** attempt) + random.random() * 0.25, max_delay)
                    retry_after = _get_retry_after(exc)
                    if retry_after:
                        delay = max(delay, retry_after)

                    logger.warning(
                        "LLM call failed, retrying",
                        attempt=attempt + 1,
                        model=current_model,
                        delay=f"{delay:.1f}s",
                    )
                    await asyncio.sleep(delay)

            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
