"""Analyzer Agent — 文档分析：聚类 + 模式提取 + 语义关联

使用统一 LLMClient 进行 LLM 调用。
"""
from __future__ import annotations

import asyncio
import json

from app.core.logging import get_logger
from app.models.unified_document import UnifiedDocument
from app.services.llm_client import LLMClient

logger = get_logger(__name__)


class AnalyzerAgent:

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

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

    async def _cluster_content(self, doc: UnifiedDocument) -> list[dict]:
        content_summary = [
            {"id": t.id, "page": t.page, "preview": t.content[:100], "level": t.level}
            for t in doc.texts[:50]
        ]

        result = await self.llm.chat_json_list(
            system=(
                "你是文档结构分析专家。将文档内容按主题分组。\n"
                "返回 JSON 数组，每个元素：{\"group_id\":\"g1\",\"theme\":\"主题\","
                "\"text_ids\":[\"id1\"],\"image_ids\":[],\"table_ids\":[],\"suggested_layout\":\"text_only\"}\n"
                "只返回 JSON 数组，不要其他文字。"
            ),
            user=f"分析以下文档内容结构:\n{json.dumps(content_summary, ensure_ascii=False)}",
            temperature=0.1,
        )
        return result

    async def _extract_patterns(self, doc: UnifiedDocument) -> dict:
        text_for_analysis = "\n".join(t.content for t in doc.texts[:100])[:8000]

        return await self.llm.chat_json(
            system=(
                "分析文档内容，识别文档类型和结构。只基于提供的文本，不添加信息。\n"
                "返回 JSON 对象：{\"document_type\":\"...\",\"target_audience\":\"...\","
                "\"key_sections\":[{\"title\":\"...\"}],\"highlights\":[\"...\"],"
                "\"suggested_pages\":10,\"suggested_style\":\"modern\"}\n"
                "只返回 JSON，不要其他文字。"
            ),
            user=text_for_analysis,
            temperature=0.1,
        )

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

        return await self.llm.chat_json_list(
            system=(
                "根据文字内容和图片位置，判断哪些文字和哪些图片有关联。只匹配同页的元素。\n"
                "返回 JSON 数组，每个元素：{\"text_id\":\"...\",\"image_id\":\"...\","
                "\"reason\":\"...\",\"confidence\":0.8}\n"
                "只返回 JSON 数组，不要其他文字。"
            ),
            user=f"文字: {json.dumps(text_summaries, ensure_ascii=False)}\n图片: {json.dumps(image_summaries, ensure_ascii=False)}",
            temperature=0.1,
        )
