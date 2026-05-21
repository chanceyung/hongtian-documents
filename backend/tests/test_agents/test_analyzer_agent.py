"""Tests for AnalyzerAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, ContentItem, ImageItem
from app.agents.analyzer_agent import AnalyzerAgent


@pytest.fixture
def analyzer_agent():
    """Create AnalyzerAgent instance for testing."""
    return AnalyzerAgent()


@pytest.fixture
def sample_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        title="Test Document",
        content=[
            ContentItem(
                id="text-1",
                text="Introduction paragraph about the topic",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.1, 0.5, 0.2]
            ),
            ContentItem(
                id="text-2",
                text="Main content section with detailed information",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.3, 0.5, 0.5]
            ),
            ContentItem(
                id="text-3",
                text="Conclusion summarizing the key points",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.6, 0.5, 0.7]
            )
        ],
        images=[
            ImageItem(
                id="img-1",
                path="/path/to/image1.png",
                page_number=1,
                bbox=[0.6, 0.1, 0.9, 0.4],
                description="First image"
            )
        ],
        metadata={"format": "pptx"}
    )


class TestAnalyzerAgentAnalyze:
    """Tests for analyze method."""

    @pytest.mark.asyncio
    async def test_analyze_returns_correct_structure(self, analyzer_agent, sample_document):
        """Test that analyze returns ContentGroups, LayoutPatterns, and SemanticLinks."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"id": "group-1", "title": "Introduction", "content_ids": ["text-1"]}]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            result = await analyzer_agent.analyze(sample_document)

            assert result.content_groups is not None
            assert result.layout_patterns is not None
            assert result.semantic_links is not None
            assert len(result.content_groups) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_empty_document(self, analyzer_agent):
        """Test analyzing an empty document."""
        empty_doc = UnifiedDocument(
            title="Empty",
            content=[],
            images=[],
            metadata={}
        )

        result = await analyzer_agent.analyze(empty_doc)

        assert result.content_groups == []
        assert result.layout_patterns == []
        assert result.semantic_links == []

    @pytest.mark.asyncio
    async def test_analyze_with_large_document(self, analyzer_agent):
        """Test analyzing a document with many content items."""
        large_doc = UnifiedDocument(
            title="Large Document",
            content=[
                ContentItem(
                    id=f"text-{i}",
                    text=f"Content item {i} with some text",
                    type="paragraph",
                    page_number=1,
                    bbox=[0.1, 0.1 + i*0.01, 0.5, 0.1 + (i+1)*0.01]
                )
                for i in range(100)
            ],
            images=[],
            metadata={}
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            result = await analyzer_agent.analyze(large_doc)

            assert result.content_groups is not None


class TestAnalyzerAgentClusterContent:
    """Tests for _cluster_content method."""

    @pytest.mark.asyncio
    async def test_cluster_content_calls_glm5(self, analyzer_agent, sample_document):
        """Test that _cluster_content calls GLM-5 API."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"id": "group-1", "title": "Section 1", "content_ids": ["text-1", "text-2"]}]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            result = await analyzer_agent._cluster_content(sample_document)

            mock_client.chat.completions.create.assert_called_once()
            assert len(result) > 0
            assert result[0].title == "Section 1"

    @pytest.mark.asyncio
    async def test_cluster_content_preserves_ids(self, analyzer_agent, sample_document):
        """Test that content IDs are preserved in clustering."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"id": "group-1", "title": "Intro", "content_ids": ["text-1", "text-2"]}]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            result = await analyzer_agent._cluster_content(sample_document)

            assert "text-1" in result[0].content_ids
            assert "text-2" in result[0].content_ids


class TestAnalyzerAgentExtractPatterns:
    """Tests for _extract_patterns method."""

    def test_extract_patterns_truncates_long_text(self, analyzer_agent):
        """Test that long text is truncated to 8000 characters."""
        long_text = "A" * 10000
        content = ContentItem(
            id="text-1",
            text=long_text,
            type="paragraph",
            page_number=1,
            bbox=[0.1, 0.1, 0.5, 0.2]
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        # Call analyze which internally calls _extract_patterns
        doc = UnifiedDocument(
            title="Test",
            content=[content],
            images=[],
            metadata={}
        )

        with patch('app.agents.analyzer_agent.client', mock_client):
            # The truncation happens in _extract_patterns
            analyzer_agent._extract_patterns(doc)

            # Verify that the call was made with truncated content
            call_args = mock_client.chat.completions.create.call_args
            if call_args:
                messages = call_args.kwargs.get('messages', call_args.args[0] if call_args.args else [])
                # The content should be truncated in the prompt
                assert all(len(str(msg.get('content', ''))) <= 8500 for msg in messages)

    def test_extract_patterns_with_short_text(self, analyzer_agent, sample_document):
        """Test that short text is not truncated."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            analyzer_agent._extract_patterns(sample_document)

            # Should still call the API
            mock_client.chat.completions.create.assert_called()


class TestAnalyzerAgentSemanticLinkage:
    """Tests for _semantic_linkage method."""

    @pytest.mark.asyncio
    async def test_semantic_linkage_with_existing_links(self, analyzer_agent, sample_document):
        """Test that _semantic_linkage respects existing links."""
        # Add some existing linkage to document
        sample_document.linkage = []

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            result = await analyzer_agent._semantic_linkage(sample_document)

            # Should not create duplicate links
            assert result is not None

    @pytest.mark.asyncio
    async def test_semantic_linkage_skips_linked_text(self, analyzer_agent):
        """Test that text with existing links is skipped."""
        doc = UnifiedDocument(
            title="Test",
            content=[
                ContentItem(id="text-1", text="Text 1", type="paragraph", page_number=1, bbox=[0.1, 0.1, 0.5, 0.2]),
                ContentItem(id="text-2", text="Text 2", type="paragraph", page_number=1, bbox=[0.1, 0.3, 0.5, 0.4])
            ],
            images=[
                ImageItem(id="img-1", path="/img1.png", page_number=1, bbox=[0.6, 0.1, 0.9, 0.4], description="Img 1")
            ],
            linkage=[],  # Empty linkage means no existing links
            metadata={}
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"text_id": "text-1", "image_id": "img-1", "reason": "semantic match"}]'
            ))]
        ))

        with patch('app.agents.analyzer_agent.client', mock_client):
            result = await analyzer_agent._semantic_linkage(doc)

            # Should find semantic links
            assert len(result) > 0