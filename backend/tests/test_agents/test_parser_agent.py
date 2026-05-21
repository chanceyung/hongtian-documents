"""Tests for ParserAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, ContentItem, ImageItem
from app.agents.parser_agent import ParserAgent


@pytest.fixture
def parser_agent():
    """Create ParserAgent instance for testing."""
    return ParserAgent()


@pytest.fixture
def sample_unified_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        title="Test Document",
        content=[
            ContentItem(
                id="text-1",
                text="Sample text content",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.1, 0.5, 0.3]
            )
        ],
        images=[
            ImageItem(
                id="img-1",
                path="/path/to/image.png",
                page_number=1,
                bbox=[0.6, 0.1, 0.9, 0.4],
                description="Test image"
            )
        ],
        metadata={"format": "pptx"}
    )


class TestParserAgentParse:
    """Tests for parse method."""

    @pytest.mark.asyncio
    async def test_parse_pptx_routes_to_pptx_parser(self, parser_agent):
        """Test that .pptx files are routed to pptx parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            title="PPTX Doc",
            content=[],
            images=[],
            metadata={"format": "pptx"}
        ))

        with patch('app.agents.parser_agent.PPTXParser', return_value=mock_parser):
            result = await parser_agent.parse("test.pptx")

            mock_parser.assert_called_once()
            assert result.metadata["format"] == "pptx"

    @pytest.mark.asyncio
    async def test_parse_pdf_routes_to_pdf_parser(self, parser_agent):
        """Test that .pdf files are routed to pdf parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            title="PDF Doc",
            content=[],
            images=[],
            metadata={"format": "pdf"}
        ))

        with patch('app.agents.parser_agent.PDFParser', return_value=mock_parser):
            result = await parser_agent.parse("test.pdf")

            mock_parser.assert_called_once()
            assert result.metadata["format"] == "pdf"

    @pytest.mark.asyncio
    async def test_parse_docx_routes_to_docx_parser(self, parser_agent):
        """Test that .docx files are routed to docx parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            title="DOCX Doc",
            content=[],
            images=[],
            metadata={"format": "docx"}
        ))

        with patch('app.agents.parser_agent.DOCXParser', return_value=mock_parser):
            result = await parser_agent.parse("test.docx")

            mock_parser.assert_called_once()
            assert result.metadata["format"] == "docx"

    @pytest.mark.asyncio
    async def test_parse_xlsx_routes_to_xlsx_parser(self, parser_agent):
        """Test that .xlsx files are routed to xlsx parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            title="XLSX Doc",
            content=[],
            images=[],
            metadata={"format": "xlsx"}
        ))

        with patch('app.agents.parser_agent.XLSXParser', return_value=mock_parser):
            result = await parser_agent.parse("test.xlsx")

            mock_parser.assert_called_once()
            assert result.metadata["format"] == "xlsx"

    @pytest.mark.asyncio
    async def test_parse_md_routes_to_md_parser(self, parser_agent):
        """Test that .md files are routed to markdown parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            title="MD Doc",
            content=[],
            images=[],
            metadata={"format": "md"}
        ))

        with patch('app.agents.parser_agent.MDParser', return_value=mock_parser):
            result = await parser_agent.parse("test.md")

            mock_parser.assert_called_once()
            assert result.metadata["format"] == "md"

    @pytest.mark.asyncio
    async def test_parse_unsupported_format_raises_error(self, parser_agent):
        """Test that unsupported formats raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            await parser_agent.parse("test.unknown")


class TestParserAgentLinkage:
    """Tests for _build_linkage method."""

    def test_build_linkage_with_spatial_distance(self, parser_agent, sample_unified_document):
        """Test linkage generation using spatial distance."""
        # Text at [0.1, 0.1, 0.5, 0.3], Image at [0.6, 0.1, 0.9, 0.4]
        # Distance should be calculated between centroids
        linkage = parser_agent._build_linkage(sample_unified_document)

        assert len(linkage) > 0
        assert any(l.text_id == "text-1" and l.image_id == "img-1" for l in linkage)

    def test_build_linkage_with_structure_keywords(self, parser_agent):
        """Test linkage generation using structure keywords."""
        doc = UnifiedDocument(
            title="Test",
            content=[
                ContentItem(id="text-1", text="图表显示增长趋势", type="paragraph", page_number=1, bbox=[0.1, 0.1, 0.5, 0.3]),
                ContentItem(id="text-2", text="增长数据", type="paragraph", page_number=1, bbox=[0.1, 0.4, 0.5, 0.6])
            ],
            images=[
                ImageItem(id="img-1", path="/chart.png", page_number=1, bbox=[0.6, 0.1, 0.9, 0.4], description="Growth chart")
            ],
            metadata={}
        )

        linkage = parser_agent._build_linkage(doc)

        # Should find linkage between text containing "图表" and the image
        assert len(linkage) > 0

    def test_build_linkage_no_duplicate_links(self, parser_agent, sample_unified_document):
        """Test that duplicate links are not created."""
        linkage = parser_agent._build_linkage(sample_unified_document)

        # Check no duplicate (text_id, image_id) pairs
        pairs = [(l.text_id, l.image_id) for l in linkage]
        assert len(pairs) == len(set(pairs))


class TestParserAgentBboxDistance:
    """Tests for _bbox_distance method."""

    def test_bbox_distance_same_box(self, parser_agent):
        """Test distance between identical bounding boxes is zero."""
        bbox1 = [0.1, 0.1, 0.3, 0.3]
        bbox2 = [0.1, 0.1, 0.3, 0.3]

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        assert distance == 0.0

    def test_bbox_distance_far_apart(self, parser_agent):
        """Test distance between far apart bounding boxes."""
        bbox1 = [0.0, 0.0, 0.1, 0.1]
        bbox2 = [0.9, 0.9, 1.0, 1.0]

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        assert distance > 0.5

    def test_bbox_distance_adjacent_boxes(self, parser_agent):
        """Test distance between adjacent boxes."""
        bbox1 = [0.0, 0.0, 0.5, 0.5]
        bbox2 = [0.5, 0.0, 1.0, 0.5]

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        # Should be small (adjacent)
        assert 0.0 < distance < 1.0

    def test_bbox_distance_centroid_calculation(self, parser_agent):
        """Test that centroid is calculated correctly."""
        # Box 1 centroid at (0.25, 0.25)
        bbox1 = [0.0, 0.0, 0.5, 0.5]
        # Box 2 centroid at (0.75, 0.75)
        bbox2 = [0.5, 0.5, 1.0, 1.0]

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        # Distance = sqrt((0.75-0.25)^2 + (0.75-0.25)^2) = sqrt(0.5) ≈ 0.707
        assert abs(distance - 0.707) < 0.01