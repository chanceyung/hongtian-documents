"""Prometheus 指标 — 任务、LLM、Agent 错误率、页处理量"""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ── 任务指标 ──────────────────────────────────────────────────
TASKS_TOTAL = Counter(
    "magazine_tasks_total",
    "任务总数",
    ["status"],
)

TASK_DURATION = Histogram(
    "magazine_task_duration_seconds",
    "任务耗时",
    ["phase"],
    buckets=[5, 15, 30, 60, 120, 300, 600, 1800, 3600],
)

ACTIVE_TASKS = Gauge(
    "magazine_active_tasks",
    "当前活跃任务数",
)

# ── LLM 指标 ──────────────────────────────────────────────────
LLM_TOKENS = Counter(
    "magazine_llm_tokens_total",
    "Token 消耗",
    ["model", "type"],
)

LLM_COST = Counter(
    "magazine_llm_cost_total",
    "API 费用（元）",
    ["model"],
)

LLM_REQUESTS = Counter(
    "magazine_llm_requests_total",
    "API 请求数",
    ["model", "status"],
)

# ── Agent 错误 ────────────────────────────────────────────────
AGENT_ERRORS = Counter(
    "magazine_agent_errors_total",
    "Agent 错误数",
    ["agent", "trigger"],
)

# ── 页面处理 ──────────────────────────────────────────────────
PAGES_PROCESSED = Counter(
    "magazine_pages_processed",
    "已处理页数",
    ["format"],
)

# ── 渲染耗时 ──────────────────────────────────────────────────
RENDER_DURATION = Histogram(
    "magazine_render_duration_seconds",
    "单页渲染耗时",
    buckets=[0.5, 1, 2, 5, 10, 30],
)


def record_task_start() -> None:
    ACTIVE_TASKS.inc()


def record_task_end(status: str = "completed") -> None:
    ACTIVE_TASKS.dec()
    TASKS_TOTAL.labels(status=status).inc()


def record_llm_usage(model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
    LLM_TOKENS.labels(model=model, type="input").inc(input_tokens)
    LLM_TOKENS.labels(model=model, type="output").inc(output_tokens)
    LLM_COST.labels(model=model).inc(cost)


def record_llm_request(model: str, status: str = "success") -> None:
    LLM_REQUESTS.labels(model=model, status=status).inc()


def record_agent_error(agent: str, trigger: str) -> None:
    AGENT_ERRORS.labels(agent=agent, trigger=trigger).inc()


def record_pages(count: int, fmt: str = "pdf") -> None:
    PAGES_PROCESSED.labels(format=fmt).inc(count)


def metrics_response():
    from starlette.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
