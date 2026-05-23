"""技能注册表 — 管理所有可用技能"""
from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger
from app.skills.types import SkillDefinition
from app.skills.loader import SkillLoader

logger = get_logger(__name__)


class SkillRegistry:

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}
        self._default: SkillDefinition | None = None

    def register(self, skill: SkillDefinition) -> None:
        self._skills[skill.name] = skill
        if skill.is_default:
            self._default = skill

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def get_default(self) -> SkillDefinition:
        if self._default:
            return self._default
        if self._skills:
            return next(iter(self._skills.values()))
        return SkillDefinition(
            name="standard",
            display_name="标准杂志",
            description="默认杂志风格，均衡图文排版",
            is_default=True,
        )

    def list_all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def load_builtin_skills(self, skills_dir: Path | None = None) -> int:
        if skills_dir is None:
            skills_dir = Path(__file__).parent / "builtin"

        skills = SkillLoader.load_from_directory(skills_dir)
        count = 0
        for skill in skills:
            self.register(skill)
            count += 1

        logger.info("Loaded builtin skills", count=count, dir=str(skills_dir))
        return count


skill_registry = SkillRegistry()
