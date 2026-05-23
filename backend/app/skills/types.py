"""技能数据模型"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    name: str = Field(description="技能唯一标识")
    display_name: str = Field(description="显示名称")
    description: str = Field(description="技能描述")
    version: str = "1.0"
    tags: list[str] = []

    # 设计参数覆盖
    style_override: str | None = None
    color_scheme_override: dict | None = None
    target_pages_override: int | None = None
    layout_preferences: dict | None = None

    # Agent 行为调整
    analyzer_instructions: str | None = None
    designer_instructions: str | None = None
    fidelity_threshold: float | None = None

    # 元信息
    is_default: bool = False
