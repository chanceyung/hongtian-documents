"""LLM 调用成本追踪 — token 用量 + 模型定价 + 成本汇总

提取自 hongtian-ai-new/backend/intelligence/llm/costs.py 简化版
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class ModelCost:
    input_token_rate: float   # per 1000 tokens
    output_token_rate: float  # per 1000 tokens


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)


class CostTracker:

    MODEL_PRICING: Dict[str, ModelCost] = {
        "glm-4-plus": ModelCost(0.05, 0.05),
        "glm-4": ModelCost(0.1, 0.1),
        "glm-4-flash": ModelCost(0.01, 0.01),
        "glm-4-long": ModelCost(0.001, 0.001),
    }

    def __init__(self) -> None:
        self.usage_by_model: Dict[str, List[TokenUsage]] = {}
        self.total_cost = 0.0
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def track(self, model: str, usage: Dict) -> None:
        if not usage:
            return

        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        if input_tokens == 0 and output_tokens == 0:
            return

        self.usage_by_model.setdefault(model, []).append(
            TokenUsage(input_tokens, output_tokens)
        )
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens

        if model in self.MODEL_PRICING:
            self.total_cost += self._calculate_cost(model, input_tokens, output_tokens)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.MODEL_PRICING.get(model)
        if not pricing:
            return 0.0
        return (input_tokens / 1000) * pricing.input_token_rate + \
               (output_tokens / 1000) * pricing.output_token_rate

    def get_summary(self) -> Dict:
        summary: Dict = {
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "requests_count": sum(len(u) for u in self.usage_by_model.values()),
            "model_breakdown": {},
        }

        for model, usages in self.usage_by_model.items():
            in_t = sum(u.input_tokens for u in usages)
            out_t = sum(u.output_tokens for u in usages)
            summary["model_breakdown"][model] = {
                "input_tokens": in_t,
                "output_tokens": out_t,
                "total_tokens": in_t + out_t,
                "cost": round(self._calculate_cost(model, in_t, out_t), 6),
                "requests": len(usages),
            }

        return summary
