"""Tests for ValidationGates system."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock the modules that may not be installed
mock_pypdf = MagicMock()
mock_pypdf.PdfReader = MagicMock()

mock_pptx = MagicMock()
mock_pptx.Presentation = MagicMock()

# Apply mocks before importing validation_gates
import sys
sys.modules["pypdf"] = mock_pypdf
sys.modules["pptx"] = mock_pptx

from app.core.validation_gates import ValidationGates, GateResult
from app.models.unified_document import (
    UnifiedDocument,
    TextElement,
    ImageElement,
    TableElement,
    BoundingBox,
    ContentFingerprint,
)
from app.models.edit_actions import (
    MagazineEditPlan,
    SlideEditPlan,
    EditAction,
)


@pytest.fixture
def validation_gates():
    """Create ValidationGates instance for testing."""
    return ValidationGates(text_threshold=0.98)


@pytest.fixture
def sample_unified_document(tmp_path):
    """Create sample UnifiedDocument with text, images, and tables."""
    # Create a dummy image file
    img_path = tmp_path / "test_image.png"
    img_path.write_bytes(b"fake image data")

    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[
            TextElement(
                id="text-1",
                content="First text element",
                page=1,
                bbox=BoundingBox(left=10, top=10, width=50, height=20),
            ),
            TextElement(
                id="text-2",
                content="Second text element",
                page=1,
                bbox=BoundingBox(left=10, top=30, width=50, height=20),
            ),
            TextElement(
                id="text-3",
                content="Third text element on page 2",
                page=2,
                bbox=BoundingBox(left=10, top=10, width=50, height=20),
            ),
        ],
        images=[
            ImageElement(
                id="img-1",
                local_path=str(img_path),
                page=1,
                bbox=BoundingBox(left=60, top=10, width=90, height=40),
                alt_text="Test image",
                hash="abc123",
            ),
        ],
        tables=[
            TableElement(
                id="table-1",
                page=1,
                bbox=BoundingBox(left=10, top=50, width=90, height=30),
                data=[["Header 1", "Header 2"], ["Value 1", "Value 2"]],
                headers=["Header 1", "Header 2"],
            ),
        ],
        total_pages=2,
    )


@pytest.fixture
def sample_fingerprint(sample_unified_document):
    """Create sample ContentFingerprint."""
    return sample_unified_document.compute_fingerprint()


@pytest.fixture
def sample_edit_plan():
    """Create sample MagazineEditPlan covering all elements."""
    return MagazineEditPlan(
        document_id="doc-123",
        template_id="template-modern",
        pages=[
            SlideEditPlan(
                page_number=1,
                template_page="cover",
                actions=[
                    EditAction(
                        type="replace_text",
                        target_selector="title",
                        source_id="text-1",
                        content="First text element",
                    ),
                    EditAction(
                        type="replace_text",
                        target_selector="subtitle",
                        source_id="text-2",
                        content="Second text element",
                    ),
                    EditAction(
                        type="replace_image",
                        target_selector="hero-image",
                        source_id="img-1",
                        content=None,
                    ),
                ],
            ),
            SlideEditPlan(
                page_number=2,
                template_page="content",
                actions=[
                    EditAction(
                        type="replace_text",
                        target_selector="content",
                        source_id="text-3",
                        content="Third text element on page 2",
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "test_output.pdf"
    # Write minimal PDF header
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")
    return pdf_path


@pytest.fixture
def sample_pptx_file(tmp_path):
    """Create a sample PPTX file for testing."""
    pptx_path = tmp_path / "test_output.pptx"
    # Write minimal PPTX file (ZIP header)
    pptx_path.write_bytes(b"PK\x03\x04")
    return pptx_path


class TestGate1ParseCompleteness:
    """Tests for gate_1_parse_completeness."""

    @pytest.mark.asyncio
    async def test_gate_1_passes_with_complete_document(
        self, validation_gates, sample_unified_document
    ):
        """Test that Gate 1 passes with a complete document."""
        result = await validation_gates.gate_1_parse_completeness(sample_unified_document)

        assert result.passed is True
        assert result.score == 1.0
        assert len(result.issues) == 0
        assert result.gate_name == "gate_1_parse_completeness"

    @pytest.mark.asyncio
    async def test_gate_1_fails_with_missing_image(
        self, validation_gates, sample_unified_document
    ):
        """Test that Gate 1 fails when image file is missing."""
        # Modify to use non-existent path
        sample_unified_document.images[0].local_path = "/nonexistent/path.png"

        result = await validation_gates.gate_1_parse_completeness(sample_unified_document)

        assert result.passed is False
        assert result.score < 1.0
        assert any("图片文件不存在" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_1_fails_with_empty_table(
        self, validation_gates, sample_unified_document
    ):
        """Test that Gate 1 fails when table is empty."""
        sample_unified_document.tables[0].data = []

        result = await validation_gates.gate_1_parse_completeness(sample_unified_document)

        assert result.passed is False
        assert result.score < 1.0
        assert any("表格无数据" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_1_warns_about_zero_pages(
        self, validation_gates, sample_unified_document
    ):
        """Test that Gate 1 warns when total_pages is 0."""
        sample_unified_document.total_pages = 0

        result = await validation_gates.gate_1_parse_completeness(sample_unified_document)

        # Should pass but with warning
        assert any("页数为 0" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_gate_1_warns_about_no_content(
        self, validation_gates
    ):
        """Test that Gate 1 warns when document has no content."""
        empty_doc = UnifiedDocument(
            source_file="empty.pptx",
            source_format="pptx",
            title="Empty Document",
            texts=[],
            images=[],
            tables=[],
            total_pages=1,
        )

        result = await validation_gates.gate_1_parse_completeness(empty_doc)

        assert any("未提取到任何内容" in warning for warning in result.warnings)


class TestGate2ContentUnderstanding:
    """Tests for gate_2_content_understanding."""

    @pytest.mark.asyncio
    async def test_gate_2_passes_with_complete_coverage(
        self,
        validation_gates,
        sample_unified_document,
        sample_edit_plan,
        sample_fingerprint,
    ):
        """Test that Gate 2 passes with complete element coverage."""
        result = await validation_gates.gate_2_content_understanding(
            sample_unified_document, sample_edit_plan, sample_fingerprint
        )

        assert result.passed is True
        assert result.score == 1.0
        assert len(result.issues) == 0
        assert result.gate_name == "gate_2_content_understanding"

    @pytest.mark.asyncio
    async def test_gate_2_fails_with_orphaned_texts(
        self,
        validation_gates,
        sample_unified_document,
        sample_edit_plan,
        sample_fingerprint,
    ):
        """Test that Gate 2 fails with orphaned text elements."""
        # Remove one text reference from edit plan
        sample_edit_plan.pages[0].actions = [
            a for a in sample_edit_plan.pages[0].actions if a.source_id != "text-1"
        ]

        result = await validation_gates.gate_2_content_understanding(
            sample_unified_document, sample_edit_plan, sample_fingerprint
        )

        # Should have issues about orphaned texts
        assert any("未被覆盖" in issue and "文本" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_2_fails_with_orphaned_images(
        self,
        validation_gates,
        sample_unified_document,
        sample_edit_plan,
        sample_fingerprint,
    ):
        """Test that Gate 2 fails with orphaned image elements."""
        # Remove image reference from edit plan
        sample_edit_plan.pages[0].actions = [
            a for a in sample_edit_plan.pages[0].actions if a.type != "replace_image"
        ]

        result = await validation_gates.gate_2_content_understanding(
            sample_unified_document, sample_edit_plan, sample_fingerprint
        )

        assert any("未被覆盖" in issue and "图片" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_2_fails_with_page_mismatch(
        self,
        validation_gates,
        sample_unified_document,
        sample_edit_plan,
        sample_fingerprint,
    ):
        """Test that Gate 2 fails when page counts don't match."""
        sample_edit_plan.pages = [sample_edit_plan.pages[0]]  # Only 1 page

        result = await validation_gates.gate_2_content_understanding(
            sample_unified_document, sample_edit_plan, sample_fingerprint
        )

        assert any("页数不匹配" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_2_warns_about_empty_edit_plan(
        self,
        validation_gates,
        sample_unified_document,
        sample_fingerprint,
    ):
        """Test that Gate 2 warns about empty edit plan."""
        empty_plan = MagazineEditPlan(
            document_id="doc-123",
            template_id="template-modern",
            pages=[],
        )

        result = await validation_gates.gate_2_content_understanding(
            sample_unified_document, empty_plan, sample_fingerprint
        )

        assert any("编辑计划为空" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_gate_2_warns_about_empty_pages(
        self,
        validation_gates,
        sample_unified_document,
        sample_edit_plan,
        sample_fingerprint,
    ):
        """Test that Gate 2 warns about pages with no actions."""
        sample_edit_plan.pages[0].actions = []

        result = await validation_gates.gate_2_content_understanding(
            sample_unified_document, sample_edit_plan, sample_fingerprint
        )

        assert any("无编辑动作" in warning for warning in result.warnings)


class TestGate3RenderQuality:
    """Tests for gate_3_render_quality."""

    @pytest.mark.asyncio
    async def test_gate_3_fails_nonexistent_file(self, validation_gates, tmp_path):
        """Test that Gate 3 fails when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.pdf"

        result = await validation_gates.gate_3_render_quality(nonexistent, "pdf")

        assert result.passed is False
        assert result.score == 0.0
        assert any("不存在" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_3_fails_empty_file(self, validation_gates, tmp_path):
        """Test that Gate 3 fails when file size is 0."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")

        result = await validation_gates.gate_3_render_quality(empty_file, "pdf")

        assert result.passed is False
        assert result.score == 0.0
        assert any("大小为 0" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_gate_3_passes_valid_pdf(
        self, validation_gates, sample_pdf_file
    ):
        """Test that Gate 3 passes with valid PDF."""
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock(), MagicMock()]
        mock_pypdf.PdfReader.return_value = mock_reader

        result = await validation_gates.gate_3_render_quality(
            sample_pdf_file, "pdf"
        )

        assert result.passed is True
        assert result.score == 1.0
        assert len(result.issues) == 0

        # Reset the mock
        mock_pypdf.PdfReader.reset_mock()

    @pytest.mark.asyncio
    async def test_gate_3_fails_invalid_pdf(
        self, validation_gates, sample_pdf_file
    ):
        """Test that Gate 3 fails with corrupted PDF."""
        mock_pypdf.PdfReader.side_effect = Exception("Corrupted PDF")

        result = await validation_gates.gate_3_render_quality(
            sample_pdf_file, "pdf"
        )

        assert result.passed is False
        assert result.score == 0.0
        assert any("损坏" in issue for issue in result.issues)

        # Reset the mock
        mock_pypdf.PdfReader.reset_mock()
        mock_pypdf.PdfReader.side_effect = None

    @pytest.mark.asyncio
    async def test_gate_3_passes_valid_pptx(
        self, validation_gates, sample_pptx_file
    ):
        """Test that Gate 3 passes with valid PPTX."""
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock(), MagicMock()]
        mock_pptx.Presentation.return_value = mock_prs

        result = await validation_gates.gate_3_render_quality(
            sample_pptx_file, "pptx"
        )

        assert result.passed is True
        assert result.score == 1.0
        assert len(result.issues) == 0

        # Reset the mock
        mock_pptx.Presentation.reset_mock()

    @pytest.mark.asyncio
    async def test_gate_3_fails_invalid_pptx(
        self, validation_gates, sample_pptx_file
    ):
        """Test that Gate 3 fails with corrupted PPTX."""
        mock_pptx.Presentation.side_effect = Exception("Corrupted PPTX")

        result = await validation_gates.gate_3_render_quality(
            sample_pptx_file, "pptx"
        )

        assert result.passed is False
        assert result.score == 0.0
        assert any("损坏" in issue for issue in result.issues)

        # Reset the mock
        mock_pptx.Presentation.reset_mock()
        mock_pptx.Presentation.side_effect = None

    @pytest.mark.asyncio
    async def test_gate_3_warns_small_file(self, validation_gates, tmp_path):
        """Test that Gate 3 warns about very small files."""
        small_file = tmp_path / "small.pdf"
        small_file.write_bytes(b"%PDF-1.4\n%%EOF")  # Minimal PDF

        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_pypdf.PdfReader.return_value = mock_reader

        result = await validation_gates.gate_3_render_quality(small_file, "pdf")

        assert any("过小" in warning for warning in result.warnings)

        # Reset the mock
        mock_pypdf.PdfReader.reset_mock()

    @pytest.mark.asyncio
    async def test_gate_3_warns_wrong_extension(self, validation_gates, tmp_path):
        """Test that Gate 3 warns about wrong file extension."""
        wrong_ext = tmp_path / "output.txt"
        wrong_ext.write_bytes(b"%PDF-1.4\n%%EOF")

        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_pypdf.PdfReader.return_value = mock_reader

        result = await validation_gates.gate_3_render_quality(wrong_ext, "pdf")

        assert any("扩展名不匹配" in warning for warning in result.warnings)

        # Reset the mock
        mock_pypdf.PdfReader.reset_mock()


class TestRunAllGates:
    """Tests for run_all_gates method."""

    @pytest.mark.asyncio
    async def test_run_all_gates_success(
        self,
        validation_gates,
        sample_unified_document,
        sample_edit_plan,
        sample_fingerprint,
        sample_pdf_file,
    ):
        """Test running all gates successfully."""
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock(), MagicMock()]
        mock_pypdf.PdfReader.return_value = mock_reader

        results = await validation_gates.run_all_gates(
            sample_unified_document,
            sample_edit_plan,
            sample_fingerprint,
            sample_pdf_file,
            "pdf",
        )

        assert "gate_1" in results
        assert "gate_2" in results
        assert "gate_3" in results
        assert all(r.passed for r in results.values())

        # Reset the mock
        mock_pypdf.PdfReader.reset_mock()

    @pytest.mark.asyncio
    async def test_run_all_gates_partial_failure(
        self,
        validation_gates,
        sample_unified_document,
        sample_fingerprint,
        tmp_path,
    ):
        """Test running all gates with partial failures."""
        # Create an invalid edit plan
        bad_plan = MagazineEditPlan(
            document_id="doc-123",
            template_id="template-modern",
            pages=[],
        )

        # Create a valid PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF")

        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_pypdf.PdfReader.return_value = mock_reader

        results = await validation_gates.run_all_gates(
            sample_unified_document,
            bad_plan,
            sample_fingerprint,
            pdf_path,
            "pdf",
        )

        # Gate 1 and 3 should pass, Gate 2 should fail
        assert results["gate_1"].passed is True
        assert results["gate_2"].passed is False
        assert results["gate_3"].passed is True

        # Reset the mock
        mock_pypdf.PdfReader.reset_mock()

    @pytest.mark.asyncio
    async def test_gate_result_serializable(
        self, validation_gates, sample_unified_document
    ):
        """Test that GateResult can be serialized."""
        result = await validation_gates.gate_1_parse_completeness(
            sample_unified_document
        )

        # Should be able to convert to dict without errors
        result_dict = result.model_dump()
        assert result_dict["gate_name"] == "gate_1_parse_completeness"
        assert "passed" in result_dict
        assert "score" in result_dict
        assert "issues" in result_dict