"""Tests for RendererAgent."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, MagazineEditPlan, EditAction, SlideEditPlan
from app.agents.renderer_agent import RendererAgent


@pytest.fixture
def renderer_agent():
    """Create RendererAgent instance for testing."""
    return RendererAgent()


@pytest.fixture
def sample_doc():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[
            {"id": "text-1", "content": "Sample text content", "page": 1}
        ],
        images=[
            {
                "id": "img-1",
                "local_path": "/path/to/image.png",
                "page": 1,
                "width": 300,
                "height": 200
            }
        ],
        tables=[],
        linkage=[],
        total_pages=1,
        parse_method="python-pptx",
        parse_warnings=[]
    )


@pytest.fixture
def sample_edit_plan():
    """Create sample MagazineEditPlan for testing."""
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
                        content="Sample text content"
                    ),
                    EditAction(
                        type="replace_image",
                        target_selector="img-1",
                        source_id="img-1",
                        content=""
                    )
                ]
            )
        ],
        design_spec={"color_theme": "dark"},
        original_fingerprint={}
    )


@pytest.fixture
def sample_svg_content():
    """Create sample SVG template content."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
    <text id="text-1" x="100" y="100" font-size="16" fill="#000000">Placeholder text</text>
    <image id="img-1" x="200" y="200" width="300" height="200" href=""/>
</svg>'''


class TestLoadSvgTemplate:
    """Tests for _load_svg_template method."""

    def test_load_svg_template_existing_file(self, renderer_agent):
        """Test loading SVG template when file exists."""
        template_root = Path("/templates/modern")
        layout_type = "cover"
        expected_content = "<svg>test content</svg>"

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value=expected_content):
                result = renderer_agent._load_svg_template(template_root, layout_type)
                assert result == expected_content

    def test_load_svg_template_non_existing_file(self, renderer_agent):
        """Test loading SVG template when file does not exist."""
        template_root = Path("/templates/modern")
        layout_type = "cover"

        with patch.object(Path, 'exists', return_value=False):
            result = renderer_agent._load_svg_template(template_root, layout_type)
            assert result is None

    def test_load_svg_template_layout_mapping(self, renderer_agent):
        """Test that layout types map to correct filenames."""
        template_root = Path("/templates/modern")
        expected_content = "<svg>content</svg>"

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value=expected_content):
                for layout_type, expected_filename in [
                    ("cover", "cover.svg"),
                    ("text_only", "content_text.svg"),
                    ("text_image", "content_image_text.svg"),
                    ("data_card", "data_card.svg"),
                ]:
                    result = renderer_agent._load_svg_template(template_root, layout_type)
                    assert result == expected_content


class TestApplyEditActionsSvg:
    """Tests for _apply_edit_actions_svg method."""

    def test_apply_edit_actions_svg_text_replacement(self, renderer_agent, sample_svg_content):
        """Test text replacement in SVG."""
        page = SlideEditPlan(
            page_number=1,
            template_page="cover",
            actions=[
                EditAction(
                    type="replace_text",
                    target_selector="#text-1",
                    source_id="text-1",
                    content="New content"
                )
            ]
        )

        mock_doc = MagicMock()
        result = renderer_agent._apply_edit_actions_svg(sample_svg_content, page, mock_doc)

        assert "New content" in result
        assert "Placeholder text" not in result

    def test_apply_edit_actions_svg_image_replacement(self, renderer_agent, sample_svg_content, sample_doc):
        """Test image replacement in SVG with base64 encoding."""
        page = SlideEditPlan(
            page_number=1,
            template_page="cover",
            actions=[
                EditAction(
                    type="replace_image",
                    target_selector="#img-1",
                    source_id="img-1",
                    content=""
                )
            ]
        )

        mock_doc = MagicMock()
        mock_doc.find_image.return_value = sample_doc.images[0]

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_bytes', return_value=b"fake_image_data"):
                result = renderer_agent._apply_edit_actions_svg(sample_svg_content, page, mock_doc)

                assert "data:image/png;base64" in result
                assert "fake_image_data" in result or "ZmFrZV9pbWFnZV9kYXRh" in result

    def test_apply_edit_actions_svg_multiple_actions(self, renderer_agent):
        """Test applying multiple edit actions."""
        svg = '''<svg><text id="t1">A</text><text id="t2">B</text></svg>'''
        page = SlideEditPlan(
            page_number=1,
            template_page="cover",
            actions=[
                EditAction(type="replace_text", target_selector="#t1", source_id="t1", content="X"),
                EditAction(type="replace_text", target_selector="#t2", source_id="t2", content="Y")
            ]
        )

        mock_doc = MagicMock()
        result = renderer_agent._apply_edit_actions_svg(svg, page, mock_doc)

        assert "X" in result
        assert "Y" in result
        assert "A" not in result
        assert "B" not in result


class TestCreateFallbackSvg:
    """Tests for _create_fallback_svg method."""

    def test_create_fallback_svg_with_content(self, renderer_agent, sample_edit_plan):
        """Test fallback SVG generation with content."""
        mock_doc = MagicMock()
        result = renderer_agent._create_fallback_svg(sample_edit_plan, mock_doc)

        assert '<svg' in result
        assert '</svg>' in result
        assert 'viewBox="0 0 1920 1080"' in result
        assert "Sample text content" in result
        assert 'xmlns="http://www.w3.org/2000/svg"' in result

    def test_create_fallback_svg_empty_plan(self, renderer_agent):
        """Test fallback SVG generation with empty plan."""
        empty_plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[],
            design_spec={},
            original_fingerprint={}
        )

        mock_doc = MagicMock()
        result = renderer_agent._create_fallback_svg(empty_plan, mock_doc)

        assert '<svg' in result
        assert '</svg>' in result
        assert 'viewBox="0 0 1920 1080"' in result
        assert 'xmlns="http://www.w3.org/2000/svg"' in result

    def test_create_fallback_svg_text_positioning(self, renderer_agent):
        """Test that fallback SVG positions text elements correctly."""
        plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[
                SlideEditPlan(
                    page_number=1,
                    template_page="cover",
                    actions=[
                        EditAction(type="replace_text", target_selector="t1", source_id="t1", content="First"),
                        EditAction(type="replace_text", target_selector="t2", source_id="t2", content="Second")
                    ]
                )
            ],
            design_spec={},
            original_fingerprint={}
        )

        mock_doc = MagicMock()
        result = renderer_agent._create_fallback_svg(plan, mock_doc)

        assert 'y="120"' in result
        assert 'y="160"' in result


class TestRenderMethods:
    """Tests for render_pptx and render_pdf methods."""

    @pytest.mark.asyncio
    async def test_render_pptx(self, renderer_agent, sample_edit_plan, sample_doc):
        """Test PPTX rendering with mocked converter."""
        template_dir = Path("/templates")
        output_path = Path("/output/test.pptx")

        mock_converter = MagicMock()
        mock_finalizer = MagicMock()
        mock_finalizer.finalize.return_value = "<svg>finalized</svg>"

        with patch("app.exporters.ppt_master.svg_to_pptx.SvgToPptxConverter", return_value=mock_converter):
            with patch("app.exporters.ppt_master.finalize_svg.SvgFinalizer", return_value=mock_finalizer):
                with patch.object(Path, "exists", return_value=False):
                    result = await renderer_agent.render_pptx(sample_edit_plan, sample_doc, template_dir, output_path)

                    assert result == output_path
                    mock_converter.convert.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_pdf(self, renderer_agent, sample_edit_plan, sample_doc):
        """Test PDF rendering with mocked renderer."""
        template_dir = Path("/templates")
        output_path = Path("/output/test.pdf")

        mock_renderer = AsyncMock()
        mock_renderer.render.return_value = output_path

        with patch("app.exporters.pdf_renderer.HybridPdfRenderer", return_value=mock_renderer):
            result = await renderer_agent.render_pdf(sample_edit_plan, sample_doc, template_dir, output_path)

            assert result == output_path
            mock_renderer.render.assert_called_once_with(sample_edit_plan, sample_doc, template_dir, output_path)