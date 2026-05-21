"""Unit tests for PPTX parser."""

from pathlib import Path
from typing import Dict, List

import pytest
from pptx import Presentation
from pptx.util import Inches, Pt

from app.parsers.pptx_parser import PPTXParser
from app.models.unified_document import UnifiedDocument


class TestPPTXParser:
    """Test suite for PPTX parser."""

    @pytest.fixture
    def sample_pptx_with_content(self, tmp_path: Path) -> Path:
        """Create a sample PPTX file with text box and table."""
        prs = Presentation()

        # Add a slide
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # Blank layout

        # Add text box
        text_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        text_frame = text_box.text_frame
        text_frame.text = "Sample Title"
        p = text_frame.add_paragraph()
        p.text = "Sample paragraph content"
        p.font.size = Pt(18)

        # Add table
        table = slide.shapes.add_table(
            rows=3,
            cols=2,
            left=Inches(1),
            top=Inches(2.5),
            width=Inches(4),
            height=Inches(1.5)
        )
        table.columns[0].width = Inches(2)
        table.columns[1].width = Inches(2)

        # Populate table
        cell = table.cell(0, 0)
        cell.text = "Header 1"
        cell = table.cell(0, 1)
        cell.text = "Header 2"

        cell = table.cell(1, 0)
        cell.text = "Row 1 Col 1"
        cell = table.cell(1, 1)
        cell.text = "Row 1 Col 2"

        cell = table.cell(2, 0)
        cell.text = "Row 2 Col 1"
        cell = table.cell(2, 1)
        cell.text = "Row 2 Col 2"

        # Save file
        file_path = tmp_path / "sample.pptx"
        prs.save(file_path)
        return file_path

    @pytest.fixture
    def empty_pptx(self, tmp_path: Path) -> Path:
        """Create an empty PPTX file with blank slides."""
        prs = Presentation()
        prs.slides.add_slide(prs.slide_layouts[5])  # Blank slide

        file_path = tmp_path / "empty.pptx"
        prs.save(file_path)
        return file_path

    @pytest.mark.asyncio
    async def test_parser_pptx_with_textbox_and_table_returns_unified_document(
        self,
        sample_pptx_with_content: Path
    ) -> None:
        """Test parsing PPTX with text box and table returns UnifiedDocument."""
        parser = PPTXParser()
        result: UnifiedDocument = await parser.parse(sample_pptx_with_content)

        # Verify type
        assert isinstance(result, UnifiedDocument)

        # Verify texts extracted
        assert len(result.texts) > 0, "Should extract text from text box"

        # Verify tables extracted
        assert len(result.tables) > 0, "Should extract table"

        # Verify fingerprint generated
        assert result.fingerprint != "", "Should generate fingerprint"

        # Verify parse method
        assert result.parse_method == "python-pptx", "Should use python-pptx parser"

    @pytest.mark.asyncio
    async def test_parser_pptx_textbox_content_correct(self, sample_pptx_with_content: Path) -> None:
        """Test that text box content is correctly extracted."""
        parser = PPTXParser()
        result: UnifiedDocument = await parser.parse(sample_pptx_with_content)

        # Check for expected text content
        text_content = " ".join([t.content for t in result.texts])
        assert "Sample Title" in text_content, "Should extract title"
        assert "Sample paragraph content" in text_content, "Should extract paragraph"

    @pytest.mark.asyncio
    async def test_parser_pptx_table_structure_correct(self, sample_pptx_with_content: Path) -> None:
        """Test that table structure is correctly extracted."""
        parser = PPTXParser()
        result: UnifiedDocument = await parser.parse(sample_pptx_with_content)

        assert len(result.tables) == 1, "Should extract exactly one table"

        table = result.tables[0]
        assert len(table.headers) == 2, "Table should have 2 headers"
        assert len(table.rows) == 2, "Table should have 2 data rows"

        # Verify header content
        header_texts = [h.content for h in table.headers]
        assert "Header 1" in header_texts, "Should extract first header"
        assert "Header 2" in header_texts, "Should extract second header"

    @pytest.mark.asyncio
    async def test_parser_pptx_empty_document(self, empty_pptx: Path) -> None:
        """Test parsing empty PPTX (no shapes)."""
        parser = PPTXParser()
        result: UnifiedDocument = await parser.parse(empty_pptx)

        assert isinstance(result, UnifiedDocument)
        assert result.fingerprint != "", "Should still generate fingerprint for empty file"
        assert result.parse_method == "python-pptx"
        # Empty document should have no texts or tables
        assert len(result.texts) == 0, "Empty PPTX should have no texts"
        assert len(result.tables) == 0, "Empty PPTX should have no tables"

    @pytest.mark.asyncio
    async def test_parser_pptx_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parsing non-existent PPTX file raises appropriate error."""
        parser = PPTXParser()
        nonexistent_file = tmp_path / "nonexistent.pptx"

        with pytest.raises(FileNotFoundError):
            await parser.parse(nonexistent_file)

    @pytest.mark.asyncio
    async def test_parser_pptx_multiple_slides(self, tmp_path: Path) -> None:
        """Test parsing PPTX with multiple slides."""
        prs = Presentation()

        # First slide with text
        slide1 = prs.slides.add_slide(prs.slide_layouts[5])
        text_box1 = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        text_box1.text_frame.text = "First Slide"

        # Second slide with text
        slide2 = prs.slides.add_slide(prs.slide_layouts[5])
        text_box2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        text_box2.text_frame.text = "Second Slide"

        file_path = tmp_path / "multiple_slides.pptx"
        prs.save(file_path)

        parser = PPTXParser()
        result: UnifiedDocument = await parser.parse(file_path)

        # Should extract texts from both slides
        text_content = " ".join([t.content for t in result.texts])
        assert "First Slide" in text_content, "Should extract first slide text"
        assert "Second Slide" in text_content, "Should extract second slide text"

    @pytest.mark.asyncio
    async def test_parser_pptx_fingerprint_uniqueness(self, sample_pptx_with_content: Path) -> None:
        """Test that fingerprint is unique and consistent for same file."""
        parser = PPTXParser()

        # Parse same file twice
        result1: UnifiedDocument = await parser.parse(sample_pptx_with_content)
        result2: UnifiedDocument = await parser.parse(sample_pptx_with_content)

        # Fingerprints should be identical for same file
        assert result1.fingerprint == result2.fingerprint, "Fingerprint should be consistent"

        # Fingerprint should not be empty
        assert len(result1.fingerprint) > 0, "Fingerprint should not be empty"