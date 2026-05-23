"""Designer Agent — 排版规划：选择模板 + 生成编辑动作

使用统一 LLMClient 进行 LLM 调用。
"""
from __future__ import annotations

import json

from app.core.logging import get_logger
from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan, SlideEditPlan, EditAction
from app.models.design_spec import DesignSpec, ColorScheme
from app.services.llm_client import LLMClient

logger = get_logger(__name__)


class DesignerAgent:

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def design(
        self,
        doc: UnifiedDocument,
        analysis: dict,
        template_id: str,
        skill_overrides: dict | None = None,
    ) -> MagazineEditPlan:
        design_spec = await self._determine_design_spec(doc, analysis, skill_overrides)
        page_mapping = await self._map_content_to_pages(doc, analysis, design_spec)
        edit_plan = await self._generate_edit_actions(doc, page_mapping, design_spec)
        edit_plan = self._validate_completeness(doc, edit_plan)
        return edit_plan

    async def _determine_design_spec(
        self,
        doc: UnifiedDocument,
        analysis: dict,
        skill_overrides: dict | None = None,
    ) -> DesignSpec:
        result = await self.llm.chat_json(
            system=(
                "根据文档类型推荐设计规范。\n"
                "返回 JSON 对象：{\"style\":\"...\",\"color_primary\":\"#...\",\"color_secondary\":\"#...\","
                "\"color_accent\":\"#...\",\"color_background\":\"#...\",\"suggested_pages\":10}\n"
                "只返回 JSON，不要其他文字。"
            ),
            user=f"文档类型: {analysis.get('document_type')}\n目标受众: {analysis.get('target_audience')}",
            temperature=0.1,
        )

        # 技能覆盖
        if skill_overrides:
            if skill_overrides.get("style_override"):
                result["style"] = skill_overrides["style_override"]
            if skill_overrides.get("color_scheme_override"):
                cs = skill_overrides["color_scheme_override"]
                result.setdefault("color_primary", cs.get("primary", "#1a1a2e"))
                result.setdefault("color_secondary", cs.get("secondary", "#16213e"))
                result.setdefault("color_accent", cs.get("accent", "#0f3460"))
                result.setdefault("color_background", cs.get("background", "#ffffff"))
            if skill_overrides.get("target_pages_override"):
                result["suggested_pages"] = skill_overrides["target_pages_override"]

        return DesignSpec(
            colors=ColorScheme(
                primary=result.get("color_primary", "#1a1a2e"),
                secondary=result.get("color_secondary", "#16213e"),
                accent=result.get("color_accent", "#0f3460"),
                background=result.get("color_background", "#ffffff"),
            ),
            target_pages=result.get("suggested_pages", 10),
            style=result.get("style", "modern_tech"),
        )

    async def _map_content_to_pages(
        self, doc: UnifiedDocument, analysis: dict, spec: DesignSpec,
    ) -> list[dict]:
        groups = analysis.get("content_groups", [])
        if not groups:
            groups = [{"group_id": f"g{i}", "theme": t.content[:50],
                       "text_ids": [t.id], "image_ids": [],
                       "table_ids": [], "suggested_layout": "text_only"}
                      for i, t in enumerate(doc.texts[:spec.target_pages])]

        result = await self.llm.chat_json(
            system=(
                "将内容分组映射到页面。\n"
                "布局类型: cover | text_only | text_image | data_card | two_column\n"
                "返回 JSON 对象：{\"pages\":[{\"page_number\":1,\"layout_type\":\"text_only\","
                "\"text_ids\":[\"id1\"],\"image_ids\":[],\"table_ids\":[]}]}\n"
                "只返回 JSON，不要其他文字。"
            ),
            user=f"内容分组: {json.dumps(groups, ensure_ascii=False)}\n目标页数: {spec.target_pages}",
            temperature=0.1,
        )
        return result.get("pages", [])

    async def _generate_edit_actions(
        self,
        doc: UnifiedDocument,
        page_mapping: list[dict],
        spec: DesignSpec,
    ) -> MagazineEditPlan:
        pages: list[SlideEditPlan] = []

        for page_info in page_mapping:
            page_texts = [t for t in doc.texts if t.id in page_info.get("text_ids", [])]
            page_images = [i for i in doc.images if i.id in page_info.get("image_ids", [])]
            page_tables = [t for t in doc.tables if t.id in page_info.get("table_ids", [])]

            actions: list[EditAction] = []

            for text in page_texts:
                actions.append(EditAction(
                    type="replace_text",
                    target_selector=f"[data-placeholder='{self._text_placeholder(text)}']",
                    source_id=text.id,
                    content=text.content,
                    confidence=1.0,
                ))

            for img in page_images:
                actions.append(EditAction(
                    type="replace_image",
                    target_selector=f"[data-placeholder='image']",
                    source_id=img.id,
                    confidence=1.0,
                ))

            for tbl in page_tables:
                actions.append(EditAction(
                    type="replace_table_data",
                    target_selector=f"[data-placeholder='table']",
                    source_id=tbl.id,
                    confidence=1.0,
                ))

            pages.append(SlideEditPlan(
                page_number=page_info.get("page_number", len(pages) + 1),
                template_page=page_info.get("layout_type", "text_only"),
                actions=actions,
            ))

        return MagazineEditPlan(
            document_id=doc.source_file,
            template_id=spec.style,
            pages=pages,
            design_spec=spec.model_dump(),
            original_fingerprint=doc.compute_fingerprint().model_dump(),
        )

    def _text_placeholder(self, text) -> str:
        if text.level == 1:
            return "title" if text.page == 0 else "heading"
        if text.level >= 2:
            return "subtitle"
        return "body"

    def _validate_completeness(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> MagazineEditPlan:
        planned_text_ids: set[str] = set()
        planned_image_ids: set[str] = set()
        planned_table_ids: set[str] = set()

        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_text":
                    planned_text_ids.add(action.source_id)
                elif action.type == "replace_image":
                    planned_image_ids.add(action.source_id)
                elif action.type == "replace_table_data":
                    planned_table_ids.add(action.source_id)

        missing_texts = [t.id for t in doc.texts if t.id not in planned_text_ids]
        missing_images = [i.id for i in doc.images if i.id not in planned_image_ids]

        if missing_texts or missing_images:
            last_page = plan.pages[-1] if plan.pages else SlideEditPlan(
                page_number=len(plan.pages) + 1, template_page="text_only",
            )
            if not plan.pages:
                plan.pages.append(last_page)

            for text_id in missing_texts:
                text = next(t for t in doc.texts if t.id == text_id)
                last_page.actions.append(EditAction(
                    type="replace_text",
                    target_selector=f".extra-text-{len(last_page.actions)}",
                    source_id=text_id,
                    content=text.content,
                ))

            for img_id in missing_images:
                last_page.actions.append(EditAction(
                    type="replace_image",
                    target_selector=f".extra-image-{len(last_page.actions)}",
                    source_id=img_id,
                ))

        return plan
