"""Tests for ParserAgent."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, TextElement, ImageElement, BoundingBox
from app.agents.parser_agent import ParserAgent


@pytest.fixture
def parser_agent():
    """Create ParserAgent instance for testing."""
    return ParserAgent()


@pytest.fixture
def sample_unified_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[
            TextElement(
                id="text-1",
                content="Sample text content",
                page=1,
                bbox=BoundingBox(left=10, top=10, width=50, height=30)
            )
        ],
        images=[
            ImageElement(
                id="img-1",
                local_path="/path/to/image.png",
                page=1,
                bbox=BoundingBox(left=60, top=10, width=90, height=40),
                alt_text="Test image"
            )
        ]
    )


class TestParserAgentParse:
    """Tests for parse method."""

    @pytest.mark.asyncio
    async def test_parse_pptx_routes_to_pptx_parser(self, parser_agent):
        """Test that .pptx files are routed to pptx parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            title="PPTX Doc",
            texts=[],
            images=[]
        ))

        with patch('app.parsers.pptx_parser.PptxParser', return_value=mock_parser):
            result = await parser_agent.parse(Path("test.pptx"), "session-1")

            assert result.source_format == "pptx"

    @pytest.mark.asyncio
    async def test_parse_pdf_routes_to_pdf_parser(self, parser_agent):
        """Test that .pdf files are routed to pdf parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            source_file="test.pdf",
            source_format="pdf",
            title="PDF Doc",
            texts=[],
            images=[]
        ))

        with patch('app.parsers.pdf_parser.PdfParser', return_value=mock_parser):
            result = await parser_agent.parse(Path("test.pdf"), "session-1")

            assert result.source_format == "pdf"

    @pytest.mark.asyncio
    async def test_parse_docx_routes_to_docx_parser(self, parser_agent):
        """Test that .docx files are routed to docx parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            source_file="test.docx",
            source_format="docx",
            title="DOCX Doc",
            texts=[],
            images=[]
        ))

        with patch('app.parsers.docx_parser.DocxParser', return_value=mock_parser):
            result = await parser_agent.parse(Path("test.docx"), "session-1")

            assert result.source_format == "docx"

    @pytest.mark.asyncio
    async def test_parse_xlsx_routes_to_xlsx_parser(self, parser_agent):
        """Test that .xlsx files are routed to xlsx parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            source_file="test.xlsx",
            source_format="xlsx",
            title="XLSX Doc",
            texts=[],
            images=[]
        ))

        with patch('app.parsers.xlsx_parser.XlsxParser', return_value=mock_parser):
            result = await parser_agent.parse(Path("test.xlsx"), "session-1")

            assert result.source_format == "xlsx"

    @pytest.mark.asyncio
    async def test_parse_md_routes_to_md_parser(self, parser_agent):
        """Test that .md files are routed to markdown parser."""
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            source_file="test.md",
            source_format="md",
            title="MD Doc",
            texts=[],
            images=[]
        ))

        with patch('app.parsers.md_parser.MdParser', return_value=mock_parser):
            result = await parser_agent.parse(Path("test.md"), "session-1")

            assert result.source_format == "md"

    @pytest.mark.asyncio
    async def test_parse_unsupported_format_raises_error(self, parser_agent):
        """Test that unsupported formats raise ValueError."""
        with pytest.raises(ValueError, match="不支持的格式"):
            await parser_agent.parse(Path("test.unknown"), "session-1")


class TestParserAgentLinkage:
    """Tests for _build_linkage method."""

    def test_build_linkage_with_spatial_distance(self, parser_agent, sample_unified_document):
        """Test linkage generation using spatial distance."""
        # Text at [10, 10, 50, 30], Image at [60, 10, 90, 40]
        # Distance should be calculated between centroids
        linkage = parser_agent._build_linkage(sample_unified_document)

        assert len(linkage) > 0
        assert any(l.text_id == "text-1" and l.asset_id == "img-1" for l in linkage)

    def test_build_linkage_with_structure_keywords(self, parser_agent):
        """Test linkage generation using structure keywords."""
        doc = UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            title="Test",
            texts=[
                TextElement(id="text-1", content="图表显示增长趋势", page=1, bbox=BoundingBox(left=10, top=10, width=50, height=30)),
                TextElement(id="text-2", content="增长数据", page=1, bbox=BoundingBox(left=10, top=40, width=50, height=60))
            ],
            images=[
                ImageElement(id="img-1", local_path="/chart.png", page=1, bbox=BoundingBox(left=60, top=10, width=90, height=40), alt_text="Growth chart")
            ]
        )

        linkage = parser_agent._build_linkage(doc)

        # Should find linkage between text containing "图表" and the image
        assert len(linkage) > 0

    def test_build_linkage_no_duplicate_links(self, parser_agent, sample_unified_document):
        """Test that duplicate links are not created."""
        linkage = parser_agent._build_linkage(sample_unified_document)

        # Check no duplicate (text_id, asset_id) pairs
        pairs = [(l.text_id, l.asset_id) for l in linkage]
        assert len(pairs) == len(set(pairs))


class TestParserAgentBboxDistance:
    """Tests for _bbox_distance method."""

    def test_bbox_distance_same_box(self, parser_agent):
        """Test distance between identical bounding boxes is zero."""
        bbox1 = BoundingBox(left=0, top=0, width=100, height=100)
        bbox2 = BoundingBox(left=0, top=0, width=100, height=100)

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        assert distance == 0.0

    def test_bbox_distance_far_apart(self, parser_agent):
        """Test distance between far apart bounding boxes."""
        bbox1 = BoundingBox(left=0, top=0, width=100, height=100)
        bbox2 = BoundingBox(left=900, top=900, width=100, height=100)

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        assert distance > 1000

    def test_bbox_distance_adjacent_boxes(self, parser_agent):
        """Test distance between adjacent boxes."""
        bbox1 = BoundingBox(left=0, top=0, width=500, height=500)
        bbox2 = BoundingBox(left=500, top=0, width=500, height=500)

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        # Should be small (adjacent) - centroids are at (250, 250) and (750, 250)
        # Distance = 500
        assert 400 < distance < 600

    def test_bbox_distance_centroid_calculation(self, parser_agent):
        """Test that centroid is calculated correctly."""
        # Box 1 centroid at (250, 250)
        bbox1 = BoundingBox(left=0, top=0, width=500, height=500)
        # Box 2 centroid at (750, 750)
        bbox2 = BoundingBox(left=500, top=500, width=500, height=500)

        distance = parser_agent._bbox_distance(bbox1, bbox2)
        # Distance = sqrt((750-250)^2 + (750-250)^2) = sqrt(500000) ≈ 707.1
        assert abs(distance - 707.1) < 1.0