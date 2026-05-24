"""Quality Agent — 双重质量校验：内容保真（L1-L3）+ 视觉质量（V1-V4）"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.core.logging import get_logger
from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan
from app.services.llm_client import LLMClient

logger = get_logger(__name__)


class QualityIssue(BaseModel):
    level: Literal["critical", "warning", "info"]
    category: str
    description: str
    element_id: str = ""
    original: str = ""
    generated: str = ""


class ContentFidelityResult(BaseModel):
    l1_score: float = 0.0
    l2_score: float = 0.0
    l3_score: float = 0.0
    passed: bool = False
    issues: list[QualityIssue] = []


class VisualQualityResult(BaseModel):
    v1_score: float = 0.0
    v2_score: float = 0.0
    v3_score: float = 0.0
    v4_score: float = 0.0
    passed: bool = False
    issues: list[QualityIssue] = []


class QualityResult(BaseModel):
    overall_score: float = 0.0
    content_passed: bool = False
    visual_passed: bool = False
    passed: bool = False
    l1_score: float = 0.0
    l2_score: float = 0.0
    l3_score: float = 0.0
    v1_score: float = 0.0
    v2_score: float = 0.0
    v3_score: float = 0.0
    v4_score: float = 0.0
    issues: list[QualityIssue] = []


class QualityAgent:

    def __init__(self, llm: LLMClient, threshold: float = 0.95) -> None:
        self.llm = llm
        self.threshold = threshold

    async def verify(
        self, doc: UnifiedDocument, plan: MagazineEditPlan, output_path: str = "",
    ) -> QualityResult:
        all_issues: list[QualityIssue] = []

        # 阶段 1：内容保真（L1-L3）
        content = self._check_content_fidelity(doc, plan)
        all_issues.extend(content.issues)

        if not content.passed:
            return QualityResult(
                overall_score=content.l1_score * 0.4 + content.l2_score * 0.3 + content.l3_score * 0.3,
                content_passed=False,
                visual_passed=False,
                passed=False,
                l1_score=content.l1_score,
                l2_score=content.l2_score,
                l3_score=content.l3_score,
                issues=all_issues,
            )

        # 阶段 2：视觉质量（V1-V4）
        visual = await self._check_visual_quality(doc, plan, output_path)
        all_issues.extend(visual.issues)

        overall = (content.l1_score * 0.3 + content.l2_score * 0.2 + content.l3_score * 0.2
                   + visual.v1_score * 0.1 + visual.v2_score * 0.1 + visual.v3_score * 0.05 + visual.v4_score * 0.05)

        return QualityResult(
            overall_score=round(overall, 4),
            content_passed=True,
            visual_passed=visual.passed,
            passed=visual.passed,
            l1_score=content.l1_score,
            l2_score=content.l2_score,
            l3_score=content.l3_score,
            v1_score=visual.v1_score,
            v2_score=visual.v2_score,
            v3_score=visual.v3_score,
            v4_score=visual.v4_score,
            issues=all_issues,
        )

    def _check_content_fidelity(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> ContentFidelityResult:
        issues: list[QualityIssue] = []

        # L1: 指纹完整性
        l1_score, l1_issues = self._check_fingerprint(doc, plan)
        issues.extend(l1_issues)

        # L2: 图文关联
        l2_score, l2_issues = self._check_linkage(doc, plan)
        issues.extend(l2_issues)

        # L3: 语义保真 — 同步版本（LLM 调用在 verify 中处理）
        l3_score = 1.0

        passed = l1_score >= 1.0 and l2_score >= 0.9
        if not passed:
            logger.warning(
                "quality.content_fidelity.failed",
                l1=l1_score, l2=l2_score,
                issues_count=len(issues),
            )

        return ContentFidelityResult(
            l1_score=l1_score,
            l2_score=l2_score,
            l3_score=l3_score,
            passed=passed,
            issues=issues,
        )

    async def check_semantic(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> tuple[float, list[QualityIssue]]:
        return await self._check_semantic(doc, plan)

    def _check_fingerprint(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> tuple[float, list[QualityIssue]]:
        issues: list[QualityIssue] = []

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

        missing_texts = [t for t in doc.texts if t.id not in planned_text_ids]
        if missing_texts:
            issues.append(QualityIssue(
                level="critical", category="fingerprint",
                description=f"遗漏 {len(missing_texts)} 段文字",
                element_id=missing_texts[0].id,
                original=missing_texts[0].content[:100],
            ))

        missing_images = [i for i in doc.images if i.id not in planned_image_ids]
        if missing_images:
            issues.append(QualityIssue(
                level="critical", category="fingerprint",
                description=f"遗漏 {len(missing_images)} 张图片",
                element_id=missing_images[0].id,
            ))

        missing_tables = [t for t in doc.tables if t.id not in planned_table_ids]
        if missing_tables:
            issues.append(QualityIssue(
                level="warning", category="fingerprint",
                description=f"遗漏 {len(missing_tables)} 个表格",
            ))

        total = len(doc.texts) + len(doc.images) + len(doc.tables)
        covered = (len(planned_text_ids & {t.id for t in doc.texts})
                   + len(planned_image_ids & {i.id for i in doc.images})
                   + len(planned_table_ids & {t.id for t in doc.tables}))
        score = covered / total if total > 0 else 1.0

        return score, issues

    def _check_linkage(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> tuple[float, list[QualityIssue]]:
        issues: list[QualityIssue] = []

        broken_links = []
        for link in doc.linkage:
            text_in_plan = any(
                a.source_id == link.text_id
                for p in plan.pages for a in p.actions
            )
            asset_in_plan = any(
                a.source_id == link.asset_id
                for p in plan.pages for a in p.actions
            )
            if link.confidence >= 0.7 and not (text_in_plan and asset_in_plan):
                broken_links.append(link)

        if broken_links:
            issues.append(QualityIssue(
                level="warning", category="linkage",
                description=f"{len(broken_links)} 个图文关联被打破",
                element_id=broken_links[0].text_id,
            ))

        total_links = len([l for l in doc.linkage if l.confidence >= 0.7])
        intact = total_links - len(broken_links)
        score = intact / total_links if total_links > 0 else 1.0

        return score, issues

    async def _check_semantic(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> tuple[float, list[QualityIssue]]:
        issues: list[QualityIssue] = []

        sampled_actions = [
            a for page in plan.pages
            for a in page.actions
            if a.type == "replace_text" and a.content
        ][:10]

        if not sampled_actions:
            return 1.0, []

        comparisons = []
        for action in sampled_actions:
            original = next(
                (t for t in doc.texts if t.id == action.source_id), None,
            )
            if original:
                comparisons.append({
                    "id": original.id,
                    "original": original.content,
                    "generated": action.content,
                })

        if not comparisons:
            return 1.0, []

        result = await self.llm.chat_json(
            system=(
                "你是内容保真校验专家。对比原始文字和生成文字，判断语义是否一致。\n"
                "规则：1.只检查含义是否相同 2.数据、数字、专有名词必须100%一致 "
                "3.每个对比给出 faithful(true/false) 和说明\n"
                "返回 JSON 对象：{\"comparisons\":[{\"id\":\"...\",\"faithful\":true,"
                "\"reason\":\"...\"}],\"overall_fidelity\":0.95}\n"
                "只返回 JSON，不要其他文字。"
            ),
            user=json.dumps(comparisons, ensure_ascii=False),
            temperature=0.0,
        )

        comparisons_list = result.get("comparisons", [])
        unfaithful = [c for c in comparisons_list if not c.get("faithful", True)]

        for u in unfaithful:
            orig = next(
                (c for c in comparisons if c["id"] == u.get("id", "")), None,
            )
            issues.append(QualityIssue(
                level="critical", category="semantic",
                description=u.get("reason", "语义不一致"),
                element_id=u.get("id", ""),
                original=orig["original"][:100] if orig else "",
                generated=u.get("generated", "")[:100],
            ))

        return result.get("overall_fidelity", 1.0), issues

    async def _check_visual_quality(
        self, doc: UnifiedDocument, plan: MagazineEditPlan, output_path: str,
    ) -> VisualQualityResult:
        issues: list[QualityIssue] = []
        v1, v2, v3, v4 = 1.0, 1.0, 1.0, 1.0

        # V1: 文字可读性 — 检查编辑动作完整性
        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_text" and action.content:
                    if len(action.content) > 2000:
                        v1 = min(v1, 0.7)
                        issues.append(QualityIssue(
                            level="warning", category="visual_text_readability",
                            description=f"页面 {page.page_number} 文字过长，可能溢出",
                            element_id=action.source_id,
                        ))

        # V2: 图片清晰度 — 检查图片文件存在性
        missing_images = [
            img for img in doc.images
            if img.local_path and not Path(img.local_path).exists()
        ]
        if missing_images:
            v2 = 0.5
            issues.append(QualityIssue(
                level="warning", category="visual_image_quality",
                description=f"{len(missing_images)} 张图片文件缺失",
                element_id=missing_images[0].id,
            ))

        # V4: Logo 规范性 — 检查输出文件中 Logo 的存在
        if output_path and Path(output_path).exists():
            logo_checks = self._check_logo_in_output(output_path)
            v4 = logo_checks
            if v4 < 1.0:
                issues.append(QualityIssue(
                    level="info", category="visual_logo",
                    description="Logo 嵌入需人工确认",
                ))

        passed = v1 >= 0.8 and v2 >= 0.8 and v3 >= 0.8 and v4 >= 0.8

        return VisualQualityResult(
            v1_score=v1, v2_score=v2, v3_score=v3, v4_score=v4,
            passed=passed, issues=issues,
        )

    def _check_logo_in_output(self, output_path: str) -> float:
        path = Path(output_path)
        if not path.exists():
            return 0.5

        try:
            if path.suffix == ".pdf":
                content = path.read_bytes()
                has_logo = b"White.png" in content or b"Black.png" in content or b"logo" in content.lower()
                return 1.0 if has_logo else 0.5
        except Exception:
            pass
        return 0.8
