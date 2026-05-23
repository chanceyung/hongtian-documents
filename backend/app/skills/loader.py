"""技能加载器 — 从 Markdown YAML frontmatter 加载技能定义"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from app.core.logging import get_logger
from app.skills.types import SkillDefinition

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class SkillLoader:

    @staticmethod
    def load_from_directory(directory: Path) -> list[SkillDefinition]:
        if not directory.exists():
            return []

        skills: list[SkillDefinition] = []
        for md_file in sorted(directory.glob("*.md")):
            skill = SkillLoader.load_from_file(md_file)
            if skill:
                skills.append(skill)
        return skills

    @staticmethod
    def load_from_file(file_path: Path) -> SkillDefinition | None:
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("Cannot read skill file", path=str(file_path))
            return None

        match = _FRONTMATTER_RE.match(text)
        if not match:
            logger.warning("No YAML frontmatter in skill file", path=str(file_path))
            return None

        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            logger.warning("Invalid YAML in skill file", path=str(file_path))
            return None

        if not isinstance(data, dict) or "name" not in data:
            logger.warning("Missing 'name' in skill frontmatter", path=str(file_path))
            return None

        data.setdefault("display_name", data.get("name", ""))
        data.setdefault("description", "")

        try:
            return SkillDefinition.model_validate(data)
        except Exception as exc:
            logger.warning("Invalid skill definition", path=str(file_path), error=str(exc))
            return None
