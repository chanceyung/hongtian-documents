"""ExecutionPlan — Planner Agent 输出的执行计划模型"""
from __future__ import annotations

from pydantic import BaseModel


class ComplexityMetrics(BaseModel):
    page_count: int = 0
    image_count: int = 0
    table_count: int = 0
    total_chars: int = 0
    text_density: float = 0.0
    image_ratio: float = 0.0
    layout_diversity: int = 0


class ExecutionPlan(BaseModel):
    complexity_score: float = 50.0
    complexity_metrics: ComplexityMetrics = ComplexityMetrics()
    processing_path: str = "standard"
    estimated_time_seconds: int = 180
    estimated_api_calls: int = 5
    estimated_cost_cny: float = 0.05
    skip_analyzer: bool = False
    skip_supplement: bool = False
    page_parallel: bool = False
    max_render_concurrency: int = 1
    checkpoint_list: list[str] = ["cp0", "cp1", "cp2", "cp3", "cp4"]
    risk_alerts: list[str] = []
