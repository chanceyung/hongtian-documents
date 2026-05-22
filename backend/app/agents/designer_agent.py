"""Designer Agent — PPTAgent 风格的排版规划：选择模板 + 生成编辑动作"""
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan, SlideEditPlan, EditAction
from app.models.design_spec import DesignSpec, ColorScheme, Typography
from app.core.retry import llm_retry
from app.core.logging import get_logger

logger = get_logger(__name__)


class DesignSpecResult(BaseModel):
    style: str
    color_primary: str
    color_secondary: str
    color_accent: str
    color_background: str
    suggested_pages: int


class PageMappingResult(BaseModel):
    pages: list[dict]


class DesignerAgent:

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4", model: str = "glm-4-flash"):
        self._model = model
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )

    async def design(
        self,
        doc: UnifiedDocument,
        analysis: dict,
        template_id: str,
    ) -> MagazineEditPlan:
        design_spec = await self._determine_design_spec(doc, analysis)
        page_mapping = await self._map_content_to_pages(doc, analysis, design_spec)
        edit_plan = await self._generate_edit_actions(doc, page_mapping, design_spec)
        edit_plan = self._validate_completeness(doc, edit_plan)
        return edit_plan

    @llm_retry
    async def _determine_design_spec(self, doc: UnifiedDocument, analysis: dict) -> DesignSpec:
        result = await self.client.chat.completions.create(
            model=self._model,
            response_model=DesignSpecResult,
            messages=[
                {"role": "system", "content": "根据文档类型推荐设计规范。"},
                {"role": "user", "content": f"文档类型: {analysis.get('document_type')}\n目标受众: {analysis.get('target_audience')}"},
            ],
        )

        return DesignSpec(
            colors=ColorScheme(
                primary=result.color_primary,
                secondary=result.color_secondary,
                accent=result.color_accent,
                background=result.color_background,
            ),
            target_pages=result.suggested_pages,
            style=result.style,
        )

    @llm_retry
    async def _map_content_to_pages(
        self, doc: UnifiedDocument, analysis: dict, spec: DesignSpec
    ) -> list[dict]:
        groups = analysis.get("content_groups", [])
        if not groups:
            groups = [{"group_id": f"g{i}", "theme": t.content[:50],
                       "text_ids": [t.id], "image_ids": [],
                       "table_ids": [], "suggested_layout": "text_only"}
                      for i, t in enumerate(doc.texts[:spec.target_pages])]

        result = await self.client.chat.completions.create(
            model=self._model,
            response_model=PageMappingResult,
            messages=[
                {"role": "system", "content": """将内容分组映射到页面。
布局类型: cover | text_only | text_image | data_card | two_column
输出: pages 数组，每项含 page_number, layout_type, text_ids, image_ids, table_ids"""},
                {"role": "user", "content": f"内容分组: {groups}\n目标页数: {spec.target_pages}"},
            ],
            temperature=0.1,
        )
        return result.pages

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
        self, doc: UnifiedDocument, plan: MagazineEditPlan
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
