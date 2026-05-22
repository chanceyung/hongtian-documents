"""Analyzer Agent — PPTAgent 风格的文档分析：聚类 + 模式提取 + 语义关联"""
import asyncio

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.models.unified_document import UnifiedDocument
from app.core.retry import llm_retry
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContentGroup(BaseModel):
    group_id: str
    theme: str
    text_ids: list[str]
    image_ids: list[str]
    table_ids: list[str]
    suggested_layout: str


class ClusteringResult(BaseModel):
    groups: list[ContentGroup]


class PatternResult(BaseModel):
    document_type: str
    target_audience: str
    key_sections: list[dict]
    highlights: list[str]
    suggested_pages: int
    suggested_style: str


class SemanticLink(BaseModel):
    text_id: str
    image_id: str
    reason: str
    confidence: float


class SemanticLinkResult(BaseModel):
    links: list[SemanticLink]


class AnalyzerAgent:

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4", model: str = "glm-4-flash"):
        self._model = model
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )

    async def analyze(self, doc: UnifiedDocument) -> dict:
        groups_task = self._cluster_content(doc)
        patterns_task = self._extract_patterns(doc)
        linkage_task = self._semantic_linkage(doc)

        groups, patterns, semantic_links = await asyncio.gather(
            groups_task, patterns_task, linkage_task,
        )

        return {
            "content_groups": groups,
            "layout_patterns": patterns,
            "semantic_links": semantic_links,
            "document_type": patterns.get("document_type", "general"),
            "suggested_pages": patterns.get("suggested_pages", 10),
        }

    @llm_retry
    async def _cluster_content(self, doc: UnifiedDocument) -> list[dict]:
        content_summary = [
            {"id": t.id, "page": t.page, "preview": t.content[:100], "level": t.level}
            for t in doc.texts[:50]
        ]

        result = await self.client.chat.completions.create(
            model=self._model,
            response_model=ClusteringResult,
            messages=[
                {"role": "system", "content": "你是文档结构分析专家。将文档内容按主题分组。"},
                {"role": "user", "content": f"分析以下文档内容结构:\n{content_summary}"},
            ],
            temperature=0.1,
        )
        return [g.model_dump() for g in result.groups]

    @llm_retry
    async def _extract_patterns(self, doc: UnifiedDocument) -> dict:
        text_for_analysis = "\n".join(t.content for t in doc.texts[:100])[:8000]

        result = await self.client.chat.completions.create(
            model=self._model,
            response_model=PatternResult,
            messages=[
                {"role": "system", "content": "分析文档内容，识别文档类型和结构。只基于提供的文本，不添加信息。"},
                {"role": "user", "content": text_for_analysis},
            ],
            temperature=0.1,
        )
        return result.model_dump()

    @llm_retry
    async def _semantic_linkage(self, doc: UnifiedDocument) -> list[dict]:
        linked_text_ids = {l.text_id for l in doc.linkage}
        unlinked_texts = [t for t in doc.texts if t.id not in linked_text_ids]

        if not unlinked_texts or not doc.images:
            return []

        text_summaries = [
            {"id": t.id, "content": t.content[:200], "page": t.page}
            for t in unlinked_texts[:20]
        ]
        image_summaries = [
            {"id": img.id, "page": img.page, "alt": img.alt_text}
            for img in doc.images
        ]

        result = await self.client.chat.completions.create(
            model=self._model,
            response_model=SemanticLinkResult,
            messages=[
                {"role": "system", "content": "根据文字内容和图片位置，判断哪些文字和哪些图片有关联。只匹配同页的元素。"},
                {"role": "user", "content": f"文字: {text_summaries}\n图片: {image_summaries}"},
            ],
            temperature=0.1,
        )
        return [l.model_dump() for l in result.links]
