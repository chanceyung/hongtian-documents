"""Unit tests for PDF parser."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import fitz  # PyMuPDF

from app.parsers.pdf_parser import PdfParser
from app.models.unified_document import UnifiedDocument


class TestPdfParser:
    """Test suite for PDF parser."""

    @pytest.fixture
    def sample_pdf_with_text(self, tmp_path: Path) -> Path:
        """Create a sample PDF file with text using PyMuPDF."""
        doc = fitz.open()

        # Add a page
        page = doc.new_page()

        # Insert text
        text = "Sample PDF Document\n\nThis is a test paragraph.\n\nSecond paragraph here."
        page.insert_text(
            (50, 72),
            text,
            fontsize=12,
            fontname="helv"
        )

        file_path = tmp_path / "sample.pdf"
        doc.save(file_path)
        doc.close()

        return file_path

    @pytest.fixture
    def empty_pdf(self, tmp_path: Path) -> Path:
        """Create an empty PDF file with blank page."""
        doc = fitz.open()
        doc.new_page()

        file_path = tmp_path / "empty.pdf"
        doc.save(file_path)
        doc.close()

        return file_path

    @pytest.mark.asyncio
    async def test_parser_pdf_pymupdf_fallback_returns_unified_document(
        self,
        sample_pdf_with_text: Path
    ) -> None:
        """Test parsing PDF with PyMuPDF fallback returns UnifiedDocument."""
        # Mock Docling to fail so it falls back to PyMuPDF
        parser = PdfParser()

        with patch.object(parser, '_parse_with_docling', side_effect=Exception("Docling not available")):
            result: UnifiedDocument = await parser.parse(sample_pdf_with_text, "session-test")

        # Verify type
        assert isinstance(result, UnifiedDocument)

        # Verify texts extracted
        assert len(result.texts) > 0, "Should extract text from PDF"

        # Verify parse method indicates PyMuPDF
        assert "pymupdf" in result.parse_method.lower(), "Should use PyMuPDF parser"

    @pytest.mark.asyncio
    async def test_parser_pdf_text_content_correct(self, sample_pdf_with_text: Path) -> None:
        """Test that text content is correctly extracted."""
        # Mock Docling to fail so it falls back to PyMuPDF
        parser = PdfParser()

        with patch.object(parser, '_parse_with_docling', side_effect=Exception("Docling not available")):
            result: UnifiedDocument = await parser.parse(sample_pdf_with_text, "session-test")

        # Check for expected text content
        text_content = " ".join([t.content for t in result.texts])
        assert "Sample PDF Document" in text_content, "Should extract title"
        assert "test paragraph" in text_content, "Should extract paragraph"
        assert "Second paragraph" in text_content, "Should extract second paragraph"

    @pytest.mark.asyncio
    async def test_parser_pdf_empty_document(self, empty_pdf: Path) -> None:
        """Test parsing empty PDF (blank page)."""
        # Mock Docling to fail so it falls back to PyMuPDF
        parser = PdfParser()

        with patch.object(parser, '_parse_with_docling', side_effect=Exception("Docling not available")):
            result: UnifiedDocument = await parser.parse(empty_pdf, "session-test")

        assert isinstance(result, UnifiedDocument)
        assert "pymupdf" in result.parse_method.lower()
        # Empty document should have no texts
        assert len(result.texts) == 0, "Empty PDF should have no texts"

    @pytest.mark.asyncio
    async def test_parser_pdf_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parsing non-existent PDF file raises appropriate error."""
        parser = PdfParser()
        nonexistent_file = tmp_path / "nonexistent.pdf"

        with pytest.raises(Exception):
            await parser.parse(nonexistent_file, "session-test")

    @pytest.mark.asyncio
    async def test_parser_pdf_docling_path_mock(self, tmp_path: Path) -> None:
        """Test Docling parsing path using mock (no actual Docling call)."""
        # Create a PDF file
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Test Document", fontsize=12)
        file_path = tmp_path / "test_docling.pdf"
        doc.save(file_path)
        doc.close()

        parser = PdfParser()

        # Create a proper mock UnifiedDocument
        from app.models.unified_document import TextElement, BoundingBox

        mock_doc = UnifiedDocument(
            source_file=str(file_path),
            source_format="pdf",
            parse_method="docling",
            parse_warnings=[],
            total_pages=1,
            texts=[
                TextElement(
                    id="test_1",
                    content="Test Document",
                    page=1,
                    level=0,
                    fingerprint="test",
                    bbox=BoundingBox(left=0, top=0, width=0, height=0)
                )
            ],
            tables=[],
            images=[]
        )

        with patch.object(parser, '_parse_with_docling', return_value=mock_doc):
            result: UnifiedDocument = await parser.parse(file_path, "session-test")

            # Verify result
            assert isinstance(result, UnifiedDocument)
            # Should indicate docling in parse method
            assert "docling" in result.parse_method.lower()

    @pytest.mark.asyncio
    async def test_parser_pdf_multiple_pages(self, tmp_path: Path) -> None:
        """Test parsing PDF with multiple pages."""
        # Mock Docling to fail so it falls back to PyMuPDF
        doc = fitz.open()

        # First page
        page1 = doc.new_page()
        page1.insert_text((50, 72), "First Page Content", fontsize=12)

        # Second page
        page2 = doc.new_page()
        page2.insert_text((50, 72), "Second Page Content", fontsize=12)

        file_path = tmp_path / "multiple_pages.pdf"
        doc.save(file_path)
        doc.close()

        parser = PdfParser()

        with patch.object(parser, '_parse_with_docling', side_effect=Exception("Docling not available")):
            result: UnifiedDocument = await parser.parse(file_path, "session-test")

        # Should extract texts from both pages
        text_content = " ".join([t.content for t in result.texts])
        assert "First Page Content" in text_content, "Should extract first page text"
        assert "Second Page Content" in text_content, "Should extract second page text"
        assert result.total_pages == 2, "Should have 2 pages"

    @pytest.mark.asyncio
    async def test_parser_pdf_fingerprint_uniqueness(self, sample_pdf_with_text: Path) -> None:
        """Test that fingerprint is unique and consistent for same file."""
        # Mock Docling to fail so it falls back to PyMuPDF
        parser = PdfParser()

        with patch.object(parser, '_parse_with_docling', side_effect=Exception("Docling not available")):
            # Parse same file twice
            result1: UnifiedDocument = await parser.parse(sample_pdf_with_text, "session-test")
            result2: UnifiedDocument = await parser.parse(sample_pdf_with_text, "session-test")

        # Compute fingerprints using the method
        fp1 = result1.compute_fingerprint()
        fp2 = result2.compute_fingerprint()

        # Fingerprints should be identical for same file
        assert fp1.text_fingerprints == fp2.text_fingerprints, "Fingerprint should be consistent"

        # Fingerprint should not be empty
        assert len(fp1.text_fingerprints) > 0, "Fingerprint should not be empty"

    @pytest.mark.asyncio
    async def test_parser_pdf_corrupted_file(self, tmp_path: Path) -> None:
        """Test parsing corrupted PDF raises appropriate error."""
        # Create a non-PDF file with .pdf extension
        corrupted_file = tmp_path / "corrupted.pdf"
        corrupted_file.write_text("This is not a valid PDF")

        parser = PdfParser()

        with pytest.raises(Exception):  # PyMuPDF will raise an exception
            await parser.parse(corrupted_file, "session-test")

    @pytest.mark.asyncio
    async def test_parser_pdf_docling_subprocess_error(self, tmp_path: Path) -> None:
        """Test Docling subprocess error falls back to PyMuPDF."""
        # Create a PDF file
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Test Document", fontsize=12)
        file_path = tmp_path / "test_error.pdf"
        doc.save(file_path)
        doc.close()

        parser = PdfParser()

        # Mock Docling to fail
        with patch.object(parser, '_parse_with_docling', side_effect=Exception("Docling subprocess failed")):
            # Should not raise exception, but fall back to PyMuPDF
            result: UnifiedDocument = await parser.parse(file_path, "session-test")

            # Verify result (should come from PyMuPDF fallback)
            assert isinstance(result, UnifiedDocument)
            # Should fall back to pymupdf
            assert "pymupdf" in result.parse_method.lower()