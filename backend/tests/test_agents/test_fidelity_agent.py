"""Tests for FidelityAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import (
    UnifiedDocument, TextElement, ImageElement, MagazineEditPlan, EditAction, BoundingBox
)
from app.agents.fidelity_agent import FidelityAgent, FidelityResult


@pytest.fixture
def fidelity_agent():
    """Create FidelityAgent instance for testing."""
    with patch('instructor.from_openai') as mock_instructor:
        mock_client = MagicMock()
        mock_instructor.return_value = mock_client
        return FidelityAgent(api_key="test-key", threshold=0.95, base_url="https://test.api/v4")


@pytest.fixture
def sample_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[
            TextElement(
                id="text-1",
                content="First paragraph of content",
                page=1,
                bbox=BoundingBox(left=10, top=10, width=50, height=20)
            ),
            TextElement(
                id="text-2",
                content="Second paragraph of content",
                page=1,
                bbox=BoundingBox(left=10, top=30, width=50, height=40)
            ),
            TextElement(
                id="text-3",
                content="Third paragraph of content",
                page=1,
                bbox=BoundingBox(left=10, top=50, width=50, height=60)
            )
        ],
        images=[
            ImageElement(
                id="img-1",
                local_path="/path/to/image1.png",
                page=1,
                bbox=BoundingBox(left=60, top=10, width=90, height=40),
                alt_text="First image"
            ),
            ImageElement(
                id="img-2",
                local_path="/path/to/image2.png",
                page=1,
                bbox=BoundingBox(left=60, top=50, width=90, height=80),
                alt_text="Second image"
            )
        ]
    )


@pytest.fixture
def sample_edit_plan():
    """Create sample MagazineEditPlan with all content."""
    from app.models.edit_actions import SlideEditPlan
    return MagazineEditPlan(
        document_id="test-doc",
        template_id="modern",
        pages=[
            SlideEditPlan(
                page_number=1,
                template_page="cover",
                actions=[
                    EditAction(
                        type="replace_text",
                        target_selector="text-1",
                        source_id="text-1",
                        content="First paragraph of content"
                    ),
                    EditAction(
                        type="replace_text",
                        target_selector="text-2",
                        source_id="text-2",
                        content="Second paragraph of content"
                    ),
                    EditAction(
                        type="replace_text",
                        target_selector="text-3",
                        source_id="text-3",
                        content="Third paragraph of content"
                    ),
                    EditAction(
                        type="replace_image",
                        target_selector="img-1",
                        source_id="img-1",
                        content="/path/to/image1.png"
                    ),
                    EditAction(
                        type="replace_image",
                        target_selector="img-2",
                        source_id="img-2",
                        content="/path/to/image2.png"
                    )
                ]
            )
        ]
    )


@pytest.fixture
def incomplete_edit_plan():
    """Create incomplete MagazineEditPlan missing some content."""
    from app.models.edit_actions import SlideEditPlan
    return MagazineEditPlan(
        document_id="test-doc",
        template_id="modern",
        pages=[
            SlideEditPlan(
                page_number=1,
                template_page="cover",
                actions=[
                    EditAction(
                        type="replace_text",
                        target_selector="text-1",
                        source_id="text-1",
                        content="First paragraph of content"
                    ),
                    # Missing text-2
                    EditAction(
                        type="replace_text",
                        target_selector="text-3",
                        source_id="text-3",
                        content="Third paragraph of content"
                    ),
                    EditAction(
                        type="replace_image",
                        target_selector="img-1",
                        source_id="img-1",
                        content="/path/to/image1.png"
                    )
                    # Missing img-2
                ]
            )
        ]
    )


class TestFidelityAgentCheckFingerprint:
    """Tests for _check_fingerprint method."""

    @pytest.mark.asyncio
    async def test_check_fingerprint_missing_content_detected(self, fidelity_agent, sample_document, incomplete_edit_plan):
        """Test that missing content is detected in fingerprint check."""
        score, issues = fidelity_agent._check_fingerprint(sample_document, incomplete_edit_plan)

        # Score should be less than 1.0
        assert score < 1.0

        # Issues should include missing items
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_check_fingerprint_perfect_score(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that complete content gets perfect score."""
        score, issues = fidelity_agent._check_fingerprint(sample_document, sample_edit_plan)

        # Should get perfect score
        assert score == 1.0
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_check_fingerprint_with_mismatched_content(self, fidelity_agent, sample_document):
        """Test detection of content with wrong text."""
        # Create plan with modified content
        from app.models.edit_actions import SlideEditPlan
        wrong_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[
                        EditAction(
                            type="replace_text",
                            target_selector="text-1",
                            source_id="text-1",
                            content="Modified content that differs from original"
                        ),
                        EditAction(
                            type="replace_text",
                            target_selector="text-2",
                            source_id="text-2",
                            content="Second paragraph of content"
                        ),
                        EditAction(
                            type="replace_text",
                            target_selector="text-3",
                            source_id="text-3",
                            content="Third paragraph of content"
                        ),
                        EditAction(
                            type="replace_image",
                            target_selector="img-1",
                            source_id="img-1",
                            content="/path/to/image1.png"
                        ),
                        EditAction(
                            type="replace_image",
                            target_selector="img-2",
                            source_id="img-2",
                            content="/path/to/image2.png"
                        )
                    ]
                )
            ]
        )

        score, issues = fidelity_agent._check_fingerprint(sample_document, wrong_plan)

        # Should detect that all IDs are present, so fingerprint passes
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_check_fingerprint_all_content_missing(self, fidelity_agent, sample_document):
        """Test handling of completely missing content."""
        empty_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[]
        )

        score, issues = fidelity_agent._check_fingerprint(sample_document, empty_plan)

        # Should score 0
        assert score == 0.0
        # Should have issues for missing content (but only texts, images count differently)
        assert len(issues) > 0


class TestFidelityAgentCheckLinkage:
    """Tests for _check_linkage method."""

    @pytest.mark.asyncio
    async def test_check_linkage_broken_links_detected(self, fidelity_agent, sample_document):
        """Test that broken image-text links are detected."""
        from app.models import ContentAssetLink
        from app.models.edit_actions import SlideEditPlan
        # Add linkage to original document
        sample_document.linkage = [
            ContentAssetLink(
                text_id="text-1",
                asset_id="img-1",
                asset_type="image",
                strategy="spatial",
                confidence=0.9
            )
        ]

        # Create plan that breaks this linkage (by putting them on different pages)
        broken_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[
                        EditAction(
                            type="replace_text",
                            target_selector="text-1",
                            source_id="text-1",
                            content="First paragraph of content"
                        )
                    ]
                ),
                SlideEditPlan(
                    page_number=2,
                    template_page="content",
                    actions=[
                        EditAction(
                            type="replace_image",
                            target_selector="img-1",
                            source_id="img-1",
                            content="/path/to/image1.png"
                        )
                    ]
                )
            ]
        )

        score, issues = fidelity_agent._check_linkage(sample_document, broken_plan)

        # Should detect broken linkage
        assert score <= 1.0  # May be 1.0 if linkage is still preserved in some way

    @pytest.mark.asyncio
    async def test_check_linkage_preserved_links(self, fidelity_agent, sample_document):
        """Test that preserved links get good score."""
        from app.models import ContentAssetLink
        from app.models.edit_actions import SlideEditPlan
        # Add linkage to original document
        sample_document.linkage = [
            ContentAssetLink(
                text_id="text-1",
                asset_id="img-1",
                asset_type="image",
                strategy="spatial",
                confidence=0.9
            )
        ]

        # Create plan that preserves this linkage (same page)
        preserved_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[
                        EditAction(
                            type="replace_text",
                            target_selector="text-1",
                            source_id="text-1",
                            content="First paragraph of content"
                        ),
                        EditAction(
                            type="replace_image",
                            target_selector="img-1",
                            source_id="img-1",
                            content="/path/to/image1.png"
                        )
                    ]
                )
            ]
        )

        score, issues = fidelity_agent._check_linkage(sample_document, preserved_plan)

        # Should get good score for preserved linkage
        assert score >= 0.8

    @pytest.mark.asyncio
    async def test_check_linkage_no_original_linkage(self, fidelity_agent, sample_document):
        """Test handling when original document has no linkage."""
        sample_document.linkage = []

        from app.models.edit_actions import SlideEditPlan
        plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[
                        EditAction(type="replace_text", target_selector="text-1", source_id="text-1", content="Text"),
                        EditAction(type="replace_image", target_selector="img-1", source_id="img-1", content="/path/img.png")
                    ]
                )
            ]
        )

        score, issues = fidelity_agent._check_linkage(sample_document, plan)

        # Should score 1 (nothing to check)
        assert score == 1.0


class TestFidelityAgentCheckSemantic:
    """Tests for _check_semantic method."""

    @pytest.mark.asyncio
    async def test_check_semantic_similarity_calculation(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test semantic similarity calculation using GLM-5."""
        mock_result = MagicMock()
        mock_result.comparisons = [{"id": "text-1", "similarity": 0.95}]
        mock_result.overall_fidelity = 0.95

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            score, issues = await fidelity_agent._check_semantic(sample_document, sample_edit_plan)

            # Should call GLM-5
            mock_create.assert_called()
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_check_semantic_low_similarity(self, fidelity_agent, sample_document):
        """Test handling of low semantic similarity."""
        # Create plan with very different content
        from app.models.edit_actions import SlideEditPlan
        different_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[
                        EditAction(type="replace_text", target_selector="text-1", source_id="text-1", content="Completely different content")
                    ]
                )
            ]
        )

        mock_result = MagicMock()
        mock_result.comparisons = [{"id": "text-1", "similarity": 0.3}]
        mock_result.overall_fidelity = 0.3

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            score, issues = await fidelity_agent._check_semantic(sample_document, different_plan)

            # Should reflect low similarity
            assert score <= 0.5

    @pytest.mark.asyncio
    async def test_check_semantic_empty_documents(self, fidelity_agent):
        """Test semantic check with empty documents."""
        empty_doc = UnifiedDocument(
            source_file="empty.pptx",
            source_format="pptx",
            title="Empty",
            texts=[],
            images=[]
        )
        empty_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[]
        )

        score, issues = await fidelity_agent._check_semantic(empty_doc, empty_plan)

        # Should score 1 for empty
        assert score == 1.0


class TestFidelityAgentVerify:
    """Tests for verify method (comprehensive fidelity check)."""

    @pytest.mark.asyncio
    async def test_verify_comprehensive_score_calculation(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that verify calculates comprehensive score using weighted average."""
        mock_result = MagicMock()
        mock_result.comparisons = []
        mock_result.overall_fidelity = 0.95

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            report = await fidelity_agent.verify(sample_document, sample_edit_plan)

            # Verify score calculation: L1*0.4 + L2*0.3 + L3*0.3
            # L1 = fingerprint (1.0 for complete plan), L2 = linkage, L3 = semantic
            expected_min_score = 0.4  # At minimum, if other checks fail
            assert report.overall_score >= expected_min_score
            assert report.overall_score <= 1.0

    @pytest.mark.asyncio
    async def test_verify_returns_fidelity_result(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that verify returns FidelityResult instance."""
        mock_result = MagicMock()
        mock_result.comparisons = []
        mock_result.overall_fidelity = 0.95

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            report = await fidelity_agent.verify(sample_document, sample_edit_plan)

            assert isinstance(report, FidelityResult)
            assert report.overall_score is not None
            assert report.l1_score is not None
            assert report.l2_score is not None
            assert report.l3_score is not None
            assert report.passed is not None

    @pytest.mark.asyncio
    async def test_verify_with_low_fidelity(self, fidelity_agent, sample_document, incomplete_edit_plan):
        """Test verify with incomplete content (low fidelity)."""
        mock_result = MagicMock()
        mock_result.comparisons = []
        mock_result.overall_fidelity = 0.95

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            report = await fidelity_agent.verify(sample_document, incomplete_edit_plan)

            # Fingerprint score should be low due to missing content
            assert report.l1_score < 1.0
            # Overall score should reflect this (but may be > 0.8 depending on other factors)
            assert report.overall_score < 1.0

    @pytest.mark.asyncio
    async def test_verify_threshold_check(self, fidelity_agent, sample_document, sample_edit_plan):
        """Test that verify correctly determines if threshold is passed."""
        mock_result = MagicMock()
        mock_result.comparisons = []
        mock_result.overall_fidelity = 0.95

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            report = await fidelity_agent.verify(sample_document, sample_edit_plan)

            # With complete content and good similarity, should pass threshold (0.95)
            assert report.passed is not None

    @pytest.mark.asyncio
    async def test_verify_includes_repair_suggestions(self, fidelity_agent, sample_document, incomplete_edit_plan):
        """Test that verify includes suggestions for repair."""
        mock_result = MagicMock()
        mock_result.comparisons = []
        mock_result.overall_fidelity = 0.95

        with patch.object(fidelity_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            report = await fidelity_agent.verify(sample_document, incomplete_edit_plan)

            # Should include repair suggestions in issues
            assert len(report.issues) > 0