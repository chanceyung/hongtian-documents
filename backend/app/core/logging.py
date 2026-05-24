"""统一日志配置 — structlog JSON 格式 + 上下文自动注入"""
import logging
import re
import sys
import time

import structlog

_SENSITIVE_PATTERNS = re.compile(r"(api[_-]?key|token|secret|password)", re.IGNORECASE)


def setup_logging(debug: bool = False) -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _redact_sensitive,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    for noisy in ("httpx", "httpcore", "urllib3", "aiosqlite", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _redact_sensitive(logger, method, event_dict):
    for key in list(event_dict.keys()):
        if _SENSITIVE_PATTERNS.search(key):
            event_dict[key] = "[REDACTED]"
    return event_dict


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_task_context(task_id: str, phase: str = "", agent: str = "") -> None:
    """绑定当前任务的日志上下文，后续所有日志自动携带。"""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(task_id=task_id)
    if phase:
        structlog.contextvars.bind_contextvars(phase=phase)
    if agent:
        structlog.contextvars.bind_contextvars(agent=agent)


def bind_phase(phase: str) -> None:
    structlog.contextvars.bind_contextvars(phase=phase)


class LogTimer:
    """计时上下文管理器，自动记录 elapsed_ms。"""

    def __init__(self, logger_instance: structlog.stdlib.BoundLogger, action: str, **kwargs):
        self._logger = logger_instance
        self._action = action
        self._kwargs = kwargs
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        elapsed_ms = round((time.perf_counter() - self._start) * 1000, 1)
        self._logger.info(self._action, elapsed_ms=elapsed_ms, **self._kwargs)
        return False