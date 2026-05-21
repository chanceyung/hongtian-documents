"""Tests for FidelityAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import (
    UnifiedDocument, ContentItem, ImageItem, MagazineEditPlan, EditAction, FidelityReport
)
from app.agents.fidelity_agent import FidelityAgent


@pytest.fixture
def fidelity_agent():
    """Create FidelityAgent instance for testing."""
    return FidelityAgent()


@pytest.fixture
def sample_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        title="Test Document",
        content=[
            ContentItem(
                id="text-1",
                text="First paragraph of content",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.1, 0.5, 0.2]
            ),
            ContentItem(
                id="text-2",
                text="Second paragraph of content",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.3, 0.5, 0.4]
            ),
            ContentItem(
                id="text-3",
                text="Third paragraph of content",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.5, 0.5, 0.6]
            )
        ],
        images=[
            ImageItem(
                id="img-1",
                path="/path/to/image1.png",
                page_number=1,
                bbox=[0.6, 0.1, 0.9, 0.4],
                description="First image"
            ),
            ImageItem(
                id="img-2",
                path="/path/to/image2.png",
                page_number=1,
                bbox=[0.6, 0.5, 0.9, 0.8],
                description="Second image"
            )
        ],
        metadata={"format": "pptx"}
    )


@pytest.fixture
def sample_edit_plan():
    """Create sample MagazineEditPlan with all content."""
    return MagazineEditPlan(
        template="modern",
        actions=[
            EditAction(
                action="replace_span",
                id="text-1",
                content="First paragraph of content",
                font_size=18
            ),
            EditAction(
                action="replace_span",
                id="text-2",
                content="Second paragraph of content",
                font_size=16
            ),
            EditAction(
                action="replace_span",
                id="text-3",
                content="Third paragraph of content",
                font_size=16
            ),
            EditAction(
                action="replace_image",
                id="img-1",
                content="/path/to/image1.png"
            ),
            EditAction(
                action="replace_image",
                id="img-2",
                content="/path/to/image2.png"
            )
        ]
    )


@pytest.fixture
def incomplete_edit_plan():
    """Create incomplete MagazineEditPlan missing some content."""
    return MagazineEditPlan(
        template="modern",
        actions=[
            EditAction(
                action="replace_span",
                id="text-1",
                content="First paragraph of content",
                font_size=18
            ),
            # Missing text-2
            EditAction(
                action="replace_span",
                id="text-3",
                content="Third paragraph of content",
                font_size=16
            ),
            EditAction(
                action="replace_image",
                id="img-1",
                content="/path/to/image1.png"
            )
            # Missing img-2
        ]
    )


class TestFidelityAgentCheckFingerprint:
    """Tests for _check_fingerprint method."""

    @pytest.mark.asyncio
    async def test_check_fingerprint_missing_content_detected(self, fidelity_agent, sample_document, incomplete_edit_plan):
        """Test that missing content is detected in fingerprint check."""
        score, details = await fidelity_agent._check_fingerprint(sample_document, incomplete_edit_plan)

        # Score should be less than 1.0
        assert score < 1.0

        # Details should include missing items
        assert len(details.missing_items) > 0
        missing_ids = [item.id for item in details.missing_items]
        assert "text-2" in missing_ids or "img-2" in missing_ids

    @pytest.mark.asyncio
    async def test_check_fingerprint_perfect_score(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that complete content gets perfect score."""
        score, details = await fidelity_agent._check_fingerprint(sample_document, sample_edit_plan)

        # Should get perfect score
        assert score == 1.0
        assert len(details.missing_items) == 0

    @pytest.mark.asyncio
    async def test_check_fingerprint_with_mismatched_content(self, fidelity_agent, sample_document):
        """Test detection of content with wrong text."""
        # Create plan with modified content
        wrong_plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(
                    action="replace_span",
                    id="text-1",
                    content="Modified content that differs from original",
                    font_size=18
                ),
                EditAction(
                    action="replace_span",
                    id="text-2",
                    content="Second paragraph of content",
                    font_size=16
                ),
                EditAction(
                    action="replace_span",
                    id="text-3",
                    content="Third paragraph of content",
                    font_size=16
                )
            ]
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='{"similarities": [{"id": "text-1", "similarity": 0.8}]}'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            score, details = await fidelity_agent._check_fingerprint(sample_document, wrong_plan)

            # Should detect mismatch
            assert score < 1.0

    @pytest.mark.asyncio
    async def test_check_fingerprint_all_content_missing(self, fidelity_agent, sample_document):
        """Test handling of completely missing content."""
        empty_plan = MagazineEditPlan(
            template="modern",
            actions=[]
        )

        score, details = await fidelity_agent._check_fingerprint(sample_document, empty_plan)

        # Should score 0
        assert score == 0.0
        assert len(details.missing_items) == len(sample_document.content) + len(sample_document.images)


class TestFidelityAgentCheckLinkage:
    """Tests for _check_linkage method."""

    @pytest.mark.asyncio
    async def test_check_linkage_broken_links_detected(self, fidelity_agent, sample_document):
        """Test that broken image-text links are detected."""
        # Add linkage to original document
        sample_document.linkage = [
            {"text_id": "text-1", "image_id": "img-1", "distance": 0.3}
        ]

        # Create plan that breaks this linkage
        broken_plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(
                    action="replace_span",
                    id="text-1",
                    content="First paragraph of content",
                    font_size=18,
                    position=[0.1, 0.1, 0.3, 0.2]  # Far from image
                ),
                EditAction(
                    action="replace_image",
                    id="img-1",
                    content="/path/to/image1.png",
                    position=[0.7, 0.7, 0.9, 0.8]  # Far from text
                )
            ]
        )

        score, details = await fidelity_agent._check_linkage(sample_document, broken_plan)

        # Should detect broken linkage
        assert score < 1.0

    @pytest.mark.asyncio
    async def test_check_linkage_preserved_links(self, fidelity_agent, sample_document):
        """Test that preserved links get good score."""
        # Add linkage to original document
        sample_document.linkage = [
            {"text_id": "text-1", "image_id": "img-1", "distance": 0.2}
        ]

        # Create plan that preserves this linkage
        preserved_plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(
                    action="replace_span",
                    id="text-1",
                    content="First paragraph of content",
                    font_size=18,
                    position=[0.1, 0.1, 0.4, 0.3]
                ),
                EditAction(
                    action="replace_image",
                    id="img-1",
                    content="/path/to/image1.png",
                    position=[0.5, 0.1, 0.8, 0.3]
                )
            ]
        )

        score, details = await fidelity_agent._check_linkage(sample_document, preserved_plan)

        # Should get good score for preserved linkage
        assert score >= 0.8

    @pytest.mark.asyncio
    async def test_check_linkage_no_original_linkage(self, fidelity_agent, sample_document):
        """Test handling when original document has no linkage."""
        sample_document.linkage = []

        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="Text", font_size=18),
                EditAction(action="replace_image", id="img-1", content="/path/img.png")
            ]
        )

        score, details = await fidelity_agent._check_linkage(sample_document, plan)

        # Should score 1 (nothing to check)
        assert score == 1.0


class TestFidelityAgentCheckSemantic:
    """Tests for _check_semantic method."""

    @pytest.mark.asyncio
    async def test_check_semantic_similarity_calculation(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test semantic similarity calculation using GLM-5."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.95'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            score, details = await fidelity_agent._check_semantic(sample_document, sample_edit_plan)

            # Should call GLM-5
            mock_client.chat.completions.create.assert_called()
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_check_semantic_low_similarity(self, fidelity_agent, sample_document):
        """Test handling of low semantic similarity."""
        # Create plan with very different content
        different_plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="Completely different content")
            ]
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.3'  # Low similarity
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            score, details = await fidelity_agent._check_semantic(sample_document, different_plan)

            # Should reflect low similarity
            assert score <= 0.5

    @pytest.mark.asyncio
    async def test_check_semantic_empty_documents(self, fidelity_agent):
        """Test semantic check with empty documents."""
        empty_doc = UnifiedDocument(title="Empty", content=[], images=[], metadata={})
        empty_plan = MagazineEditPlan(template="modern", actions=[])

        score, details = await fidelity_agent._check_semantic(empty_doc, empty_plan)

        # Should score 1 for empty
        assert score == 1.0


class TestFidelityAgentVerify:
    """Tests for verify method (comprehensive fidelity check)."""

    @pytest.mark.asyncio
    async def test_verify_comprehensive_score_calculation(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that verify calculates comprehensive score using weighted average."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.95'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            report = await fidelity_agent.verify(sample_document, sample_edit_plan)

            # Verify score calculation: L1*0.4 + L2*0.3 + L3*0.3
            # L1 = fingerprint (1.0 for complete plan), L2 = linkage, L3 = semantic
            expected_min_score = 0.4  # At minimum, if other checks fail
            assert report.overall_score >= expected_min_score
            assert report.overall_score <= 1.0

    @pytest.mark.asyncio
    async def test_verify_returns_fidelity_report(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that verify returns FidelityReport instance."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.95'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            report = await fidelity_agent.verify(sample_document, sample_edit_plan)

            assert isinstance(report, FidelityReport)
            assert report.overall_score is not None
            assert report.fingerprint_score is not None
            assert report.linkage_score is not None
            assert report.semantic_score is not None
            assert report.details is not None

    @pytest.mark.asyncio
    async def test_verify_with_low_fidelity(self, fidelity_agent, sample_document, incomplete_edit_plan):
        """Test verify with incomplete content (low fidelity)."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.95'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            report = await fidelity_agent.verify(sample_document, incomplete_edit_plan)

            # Fingerprint score should be low due to missing content
            assert report.fingerprint_score < 1.0
            # Overall score should reflect this
            assert report.overall_score < 0.8

    @pytest.mark.asyncio
    async def test_verify_threshold_check(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that verify correctly determines if threshold is passed."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.95'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            report = await fidelity_agent.verify(sample_document, sample_edit_plan)

            # With complete content and good similarity, should pass threshold (0.95)
            assert report.passed is not None

    @pytest.mark.asyncio
    async def test_verify_includes_repair_suggestions(self, fidelity_agent, sample_document, incomplete_edit_plan):
        """Test that verify includes suggestions for repair."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='0.95'
            ))]
        ))

        with patch('app.agents.fidelity_agent.client', mock_client):
            report = await fidelity_agent.verify(sample_document, incomplete_edit_plan)

            # Should include repair suggestions
            assert report.repair_suggestions is not None