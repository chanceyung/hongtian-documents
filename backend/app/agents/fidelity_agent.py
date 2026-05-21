"""Fidelity Agent — 四层保真校验：指纹 → 关联 → 语义 → 人工"""
import hashlib
from typing import Literal

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.models.unified_document import UnifiedDocument, ContentFingerprint
from app.models.edit_actions import MagazineEditPlan


class FidelityIssue(BaseModel):
    level: Literal["critical", "warning", "info"]
    category: str
    description: str
    element_id: str = ""
    original: str = ""
    generated: str = ""


class FidelityResult(BaseModel):
    overall_score: float
    passed: bool
    l1_score: float = 0.0
    l2_score: float = 0.0
    l3_score: float = 0.0
    l4_required: bool = False
    issues: list[FidelityIssue] = []


class SemanticCheckResult(BaseModel):
    comparisons: list[dict]
    overall_fidelity: float


class FidelityAgent:

    def __init__(
        self,
        api_key: str,
        threshold: float = 0.95,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    ):
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )
        self.threshold = threshold

    async def verify(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> FidelityResult:
        issues: list[FidelityIssue] = []

        l1_score, l1_issues = self._check_fingerprint(doc, plan)
        issues.extend(l1_issues)

        l2_score, l2_issues = self._check_linkage(doc, plan)
        issues.extend(l2_issues)

        l3_score, l3_issues = await self._check_semantic(doc, plan)
        issues.extend(l3_issues)

        l4_required = (
            l1_score < 1.0
            or l2_score < 0.9
            or l3_score < 0.9
            or any(i.level == "critical" for i in issues)
        )

        overall = l1_score * 0.4 + l2_score * 0.3 + l3_score * 0.3

        return FidelityResult(
            overall_score=round(overall, 4),
            passed=overall >= self.threshold and not l4_required,
            l1_score=l1_score,
            l2_score=l2_score,
            l3_score=l3_score,
            l4_required=l4_required,
            issues=issues,
        )

    def _check_fingerprint(
        self, doc: UnifiedDocument, plan: MagazineEditPlan,
    ) -> tuple[float, list[FidelityIssue]]:
        issues: list[FidelityIssue] = []

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
            issues.append(FidelityIssue(
                level="critical", category="fingerprint",
                description=f"遗漏 {len(missing_texts)} 段文字",
                element_id=missing_texts[0].id,
                original=missing_texts[0].content[:100],
            ))

        missing_images = [i for i in doc.images if i.id not in planned_image_ids]
        if missing_images:
            issues.append(FidelityIssue(
                level="critical", category="fingerprint",
                description=f"遗漏 {len(missing_images)} 张图片",
                element_id=missing_images[0].id,
            ))

        missing_tables = [t for t in doc.tables if t.id not in planned_table_ids]
        if missing_tables:
            issues.append(FidelityIssue(
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
    ) -> tuple[float, list[FidelityIssue]]:
        issues: list[FidelityIssue] = []

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
            issues.append(FidelityIssue(
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
    ) -> tuple[float, list[FidelityIssue]]:
        issues: list[FidelityIssue] = []

        sampled_actions = []
        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_text" and action.content:
                    sampled_actions.append(action)
        sampled_actions = sampled_actions[:10]

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

        result = await self.client.chat.completions.create(
            model="glm-5-pro",
            response_model=SemanticCheckResult,
            messages=[
                {
                    "role": "system",
                    "content": "你是内容保真校验专家。对比原始文字和生成文字，判断语义是否一致。"
                               "规则：1.只检查含义是否相同 2.数据、数字、专有名词必须100%一致 "
                               "3.每个对比给出 faithful(true/false) 和说明 "
                               "4.overall_fidelity = faithful数量/总数量",
                },
                {"role": "user", "content": str(comparisons)},
            ],
            temperature=0.0,
        )

        unfaithful = [c for c in result.comparisons if not c.get("faithful", True)]

        for u in unfaithful:
            orig = next(
                (c for c in comparisons if c["id"] == u.get("id", "")), None,
            )
            issues.append(FidelityIssue(
                level="critical", category="semantic",
                description=u.get("reason", "语义不一致"),
                element_id=u.get("id", ""),
                original=orig["original"][:100] if orig else "",
                generated=u.get("generated", "")[:100],
            ))

        return result.overall_fidelity, issues
