"""Tests for QualityAgent."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.quality_agent import QualityAgent, QualityResult
from app.models.unified_document import UnifiedDocument, TextElement, ImageElement, BoundingBox, ContentAssetLink
from app.models.edit_actions import MagazineEditPlan, SlideEditPlan, EditAction


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat_json = AsyncMock(return_value={
        "comparisons": [
            {"id": "t1", "faithful": True, "reason": "完全一致"},
        ],
        "overall_fidelity": 1.0,
    })
    return llm


@pytest.fixture
def quality_agent(mock_llm):
    return QualityAgent(mock_llm, threshold=0.95)


@pytest.fixture
def sample_doc():
    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        texts=[
            TextElement(id="t1", content="Hello", page=0, fingerprint="abc"),
            TextElement(id="t2", content="World", page=0, fingerprint="def"),
        ],
        images=[
            ImageElement(id="img1", local_path="/tmp/test.png", page=0, hash="h1"),
        ],
        linkage=[
            ContentAssetLink(
                text_id="t1", asset_id="img1", asset_type="image",
                strategy="spatial", confidence=0.8,
            ),
        ],
    )


@pytest.fixture
def complete_plan():
    return MagazineEditPlan(
        document_id="doc1",
        template_id="modern_tech",
        pages=[
            SlideEditPlan(
                page_number=1,
                template_page="content",
                actions=[
                    EditAction(type="replace_text", target_selector=".t1", source_id="t1", content="Hello"),
                    EditAction(type="replace_text", target_selector=".t2", source_id="t2", content="World"),
                    EditAction(type="replace_image", target_selector=".img1", source_id="img1"),
                ],
            ),
        ],
    )


class TestQualityAgentContentFidelity:
    @pytest.mark.asyncio
    async def test_complete_plan_passes_l1(self, quality_agent, sample_doc, complete_plan):
        result = await quality_agent.verify(sample_doc, complete_plan)
        assert result.l1_score == 1.0

    @pytest.mark.asyncio
    async def test_missing_text_fails_l1(self, quality_agent, sample_doc):
        incomplete_plan = MagazineEditPlan(
            document_id="doc1", template_id="t",
            pages=[
                SlideEditPlan(
                    page_number=1, template_page="content",
                    actions=[
                        EditAction(type="replace_text", target_selector=".t1", source_id="t1", content="Hello"),
                    ],
                ),
            ],
        )
        result = await quality_agent.verify(sample_doc, incomplete_plan)
        assert result.content_passed is False
        assert any(i.category == "fingerprint" for i in result.issues)

    @pytest.mark.asyncio
    async def test_linkage_preserved_passes_l2(self, quality_agent, sample_doc, complete_plan):
        result = await quality_agent.verify(sample_doc, complete_plan)
        assert result.l2_score == 1.0

    @pytest.mark.asyncio
    async def test_broken_linkage_warns_l2(self, quality_agent, sample_doc):
        plan = MagazineEditPlan(
            document_id="doc1", template_id="t",
            pages=[
                SlideEditPlan(
                    page_number=1, template_page="content",
                    actions=[
                        EditAction(type="replace_text", target_selector=".t1", source_id="t1", content="Hello"),
                        EditAction(type="replace_text", target_selector=".t2", source_id="t2", content="World"),
                    ],
                ),
            ],
        )
        result = await quality_agent.verify(sample_doc, plan)
        assert result.l2_score < 1.0


class TestQualityAgentSemantic:
    @pytest.mark.asyncio
    async def test_semantic_check_calls_llm(self, quality_agent, sample_doc, complete_plan):
        score, issues = await quality_agent.check_semantic(sample_doc, complete_plan)
        quality_agent.llm.chat_json.assert_called()

    @pytest.mark.asyncio
    async def test_semantic_faithful_passes(self, quality_agent, sample_doc, complete_plan):
        score, issues = await quality_agent.check_semantic(sample_doc, complete_plan)
        assert score == 1.0
        assert len(issues) == 0


class TestQualityAgentVisualQuality:
    @pytest.mark.asyncio
    async def test_no_output_visual_degrades_gracefully(self, quality_agent, sample_doc, complete_plan):
        result = await quality_agent.verify(sample_doc, complete_plan, "")
        assert result.v4_score > 0

    @pytest.mark.asyncio
    async def test_overall_result_structure(self, quality_agent, sample_doc, complete_plan):
        result = await quality_agent.verify(sample_doc, complete_plan)
        assert isinstance(result, QualityResult)
        assert result.l1_score >= 0
        assert result.l2_score >= 0
        assert result.v1_score >= 0
        assert result.v2_score >= 0
        assert isinstance(result.passed, bool)
        assert isinstance(result.content_passed, bool)
        assert isinstance(result.visual_passed, bool)
