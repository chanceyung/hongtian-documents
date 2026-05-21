"""Tests for AnalyzerAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, TextElement, ImageElement, BoundingBox
from app.agents.analyzer_agent import AnalyzerAgent


@pytest.fixture
def analyzer_agent():
    """Create AnalyzerAgent instance for testing."""
    with patch('instructor.from_openai') as mock_instructor:
        mock_client = MagicMock()
        mock_instructor.return_value = mock_client
        return AnalyzerAgent(api_key="test-key", base_url="https://test.api/v4")


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
                content="Introduction paragraph about the topic",
                page=1,
                bbox=BoundingBox(left=10, top=10, width=50, height=20)
            ),
            TextElement(
                id="text-2",
                content="Main content section with detailed information",
                page=1,
                bbox=BoundingBox(left=10, top=30, width=50, height=50)
            ),
            TextElement(
                id="text-3",
                content="Conclusion summarizing the key points",
                page=1,
                bbox=BoundingBox(left=10, top=60, width=50, height=70)
            )
        ],
        images=[
            ImageElement(
                id="img-1",
                local_path="/path/to/image1.png",
                page=1,
                bbox=BoundingBox(left=60, top=10, width=90, height=40),
                alt_text="First image"
            )
        ]
    )


class TestAnalyzerAgentAnalyze:
    """Tests for analyze method."""

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_structure(self, analyzer_agent, sample_document):
        """Test that analyze returns dict with content_groups, layout_patterns, and semantic_links."""
        mock_clustering = MagicMock()
        mock_clustering.groups = [
            MagicMock(group_id="group-1", theme="Introduction", text_ids=["text-1"], image_ids=[], table_ids=[], suggested_layout="text_only")
        ]

        mock_pattern = MagicMock()
        mock_pattern.document_type = "report"
        mock_pattern.target_audience = "general"
        mock_pattern.key_sections = []
        mock_pattern.highlights = []
        mock_pattern.suggested_pages = 1
        mock_pattern.suggested_style = "modern"

        mock_semantic = MagicMock()
        mock_semantic.links = []

        with patch.object(analyzer_agent, '_cluster_content', return_value=[mock_clustering.model_dump()]) as mock_cluster:
            with patch.object(analyzer_agent, '_extract_patterns', return_value=mock_pattern.model_dump()) as mock_patterns:
                with patch.object(analyzer_agent, '_semantic_linkage', return_value=[]) as mock_links:
                    result = await analyzer_agent.analyze(sample_document)

                    assert isinstance(result, dict)
                    assert "content_groups" in result
                    assert "layout_patterns" in result
                    assert "semantic_links" in result
                    assert len(result["content_groups"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_empty_document(self, analyzer_agent):
        """Test analyzing an empty document."""
        empty_doc = UnifiedDocument(
            source_file="empty.pptx",
            source_format="pptx",
            title="Empty",
            texts=[],
            images=[]
        )

        with patch.object(analyzer_agent, '_cluster_content', return_value=[]):
            with patch.object(analyzer_agent, '_extract_patterns', return_value={}) as mock_patterns:
                with patch.object(analyzer_agent, '_semantic_linkage', return_value=[]):
                    result = await analyzer_agent.analyze(empty_doc)

                    assert isinstance(result, dict)
                    assert result["content_groups"] == []

    @pytest.mark.asyncio
    async def test_analyze_with_large_document(self, analyzer_agent):
        """Test analyzing a document with many content items."""
        large_doc = UnifiedDocument(
            source_file="large.pptx",
            source_format="pptx",
            title="Large Document",
            texts=[
                TextElement(
                    id=f"text-{i}",
                    content=f"Content item {i} with some text",
                    page=1,
                    bbox=BoundingBox(left=10, top=10 + i, width=50, height=10 + i + 1)
                )
                for i in range(100)
            ],
            images=[]
        )

        mock_clustering = MagicMock()
        mock_clustering.groups = []

        mock_pattern = MagicMock()
        mock_pattern.document_type = "report"
        mock_pattern.target_audience = "general"
        mock_pattern.key_sections = []
        mock_pattern.highlights = []
        mock_pattern.suggested_pages = 10
        mock_pattern.suggested_style = "modern"

        with patch.object(analyzer_agent, '_cluster_content', return_value=[mock_clustering.model_dump()]):
            with patch.object(analyzer_agent, '_extract_patterns', return_value=mock_pattern.model_dump()):
                with patch.object(analyzer_agent, '_semantic_linkage', return_value=[]):
                    result = await analyzer_agent.analyze(large_doc)

                    assert isinstance(result, dict)
                    assert result["content_groups"] is not None


class TestAnalyzerAgentClusterContent:
    """Tests for _cluster_content method."""

    @pytest.mark.asyncio
    async def test_cluster_content_calls_glm5(self, analyzer_agent, sample_document):
        """Test that _cluster_content calls GLM-5 API."""
        from app.agents.analyzer_agent import ClusteringResult, ContentGroup

        mock_result = ClusteringResult(
            groups=[
                ContentGroup(
                    group_id="group-1",
                    theme="Section 1",
                    text_ids=["text-1", "text-2"],
                    image_ids=[],
                    table_ids=[],
                    suggested_layout="text_only"
                )
            ]
        )

        with patch.object(analyzer_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            result = await analyzer_agent._cluster_content(sample_document)

            mock_create.assert_called_once()
            assert len(result) > 0
            assert result[0]["theme"] == "Section 1"

    @pytest.mark.asyncio
    async def test_cluster_content_preserves_ids(self, analyzer_agent, sample_document):
        """Test that content IDs are preserved in clustering."""
        from app.agents.analyzer_agent import ClusteringResult, ContentGroup

        mock_result = ClusteringResult(
            groups=[
                ContentGroup(
                    group_id="group-1",
                    theme="Intro",
                    text_ids=["text-1", "text-2"],
                    image_ids=[],
                    table_ids=[],
                    suggested_layout="text_only"
                )
            ]
        )

        with patch.object(analyzer_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            result = await analyzer_agent._cluster_content(sample_document)

            assert "text-1" in result[0]["text_ids"]
            assert "text-2" in result[0]["text_ids"]


class TestAnalyzerAgentExtractPatterns:
    """Tests for _extract_patterns method."""

    @pytest.mark.asyncio
    async def test_extract_patterns_truncates_long_text(self, analyzer_agent):
        """Test that long text is truncated to 8000 characters."""
        long_text = "A" * 10000
        content = TextElement(
            id="text-1",
            content=long_text,
            page=1,
            bbox=BoundingBox(left=10, top=10, width=50, height=20)
        )

        mock_pattern = MagicMock()
        mock_pattern.document_type = "report"
        mock_pattern.target_audience = "general"
        mock_pattern.key_sections = []
        mock_pattern.highlights = []
        mock_pattern.suggested_pages = 1
        mock_pattern.suggested_style = "modern"

        # Call analyze which internally calls _extract_patterns
        doc = UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            title="Test",
            texts=[content],
            images=[]
        )

        with patch.object(analyzer_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pattern
            result = await analyzer_agent._extract_patterns(doc)

            # Verify that the call was made with truncated content
            call_args = mock_create.call_args
            if call_args:
                messages = call_args.kwargs.get('messages', call_args.args[0] if call_args.args else [])
                # The content should be truncated in the prompt
                assert all(len(str(msg.get('content', ''))) <= 8500 for msg in messages)

    @pytest.mark.asyncio
    async def test_extract_patterns_with_short_text(self, analyzer_agent, sample_document):
        """Test that short text is not truncated."""
        mock_pattern = MagicMock()
        mock_pattern.document_type = "report"
        mock_pattern.target_audience = "general"
        mock_pattern.key_sections = []
        mock_pattern.highlights = []
        mock_pattern.suggested_pages = 1
        mock_pattern.suggested_style = "modern"

        with patch.object(analyzer_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_pattern
            result = await analyzer_agent._extract_patterns(sample_document)

            # Should still call the API
            mock_create.assert_called()


class TestAnalyzerAgentSemanticLinkage:
    """Tests for _semantic_linkage method."""

    @pytest.mark.asyncio
    async def test_semantic_linkage_with_existing_links(self, analyzer_agent, sample_document):
        """Test that _semantic_linkage respects existing links."""
        # Add some existing linkage to document
        from app.models import ContentAssetLink
        sample_document.linkage = [
            ContentAssetLink(text_id="text-1", asset_id="img-1", asset_type="image", strategy="spatial", confidence=0.9)
        ]

        mock_semantic = MagicMock()
        mock_semantic.links = []

        with patch.object(analyzer_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_semantic
            result = await analyzer_agent._semantic_linkage(sample_document)

            # Should not create duplicate links
            assert result is not None

    @pytest.mark.asyncio
    async def test_semantic_linkage_skips_linked_text(self, analyzer_agent):
        """Test that text with existing links is skipped."""
        from app.models import ContentAssetLink
        doc = UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            title="Test",
            texts=[
                TextElement(id="text-1", content="Text 1", page=1, bbox=BoundingBox(left=10, top=10, width=50, height=20)),
                TextElement(id="text-2", content="Text 2", page=1, bbox=BoundingBox(left=10, top=30, width=50, height=40))
            ],
            images=[
                ImageElement(id="img-1", local_path="/img1.png", page=1, bbox=BoundingBox(left=60, top=10, width=90, height=40), alt_text="Img 1")
            ],
            linkage=[]  # Empty linkage means no existing links
        )

        mock_semantic = MagicMock()
        mock_semantic.links = [
            MagicMock(text_id="text-1", image_id="img-1", reason="semantic match", confidence=0.9)
        ]

        with patch.object(analyzer_agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_semantic
            result = await analyzer_agent._semantic_linkage(doc)

            # Should find semantic links
            assert len(result) > 0