"""技能系统 — 可插拔的文档处理模式"""
from app.skills.types import SkillDefinition
from app.skills.loader import SkillLoader
from app.skills.registry import skill_registry

__all__ = ["SkillDefinition", "SkillLoader", "skill_registry"]
