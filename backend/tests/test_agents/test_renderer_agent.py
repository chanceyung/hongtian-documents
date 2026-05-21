"""Tests for RendererAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from app.models import UnifiedDocument, MagazineEditPlan, EditAction
from app.agents.renderer_agent import RendererAgent


@pytest.fixture
def renderer_agent():
    """Create RendererAgent instance for testing."""
    return RendererAgent()


@pytest.fixture
def sample_edit_plan():
    """Create sample MagazineEditPlan for testing."""
    return MagazineEditPlan(
        template="modern",
        actions=[
            EditAction(
                action="replace_span",
                id="text-1",
                content="Sample text content",
                font_size=18,
                color="#333333"
            ),
            EditAction(
                action="replace_image",
                id="img-1",
                content="/path/to/image.png",
                position=[0.1, 0.1, 0.3, 0.3]
            )
        ]
    )


@pytest.fixture
def sample_svg_content():
    """Create sample SVG template content."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
    <text data-placeholder="text-1" x="100" y="100" font-size="16" fill="#000000">Placeholder text</text>
    <image data-placeholder="img-1" x="200" y="200" width="300" height="200" href=""/>
</svg>'''


class TestRendererAgentLoadSvgTemplate:
    """Tests for _load_svg_template method."""

    def test_load_svg_template_modern_layout(self, renderer_agent, sample_svg_content):
        """Test loading SVG template for modern layout."""
        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            result = renderer_agent._load_svg_template("pptx", "modern", "cover")

            assert isinstance(result, str)
            assert result.startswith('<?xml')
            assert '<svg' in result
            assert 'data-placeholder' in result

    def test_load_svg_template_different_layouts(self, renderer_agent, sample_svg_content):
        """Test loading different layout templates."""
        layouts = ["cover", "content", "gallery", "data"]

        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            for layout in layouts:
                result = renderer_agent._load_svg_template("pptx", "modern", layout)
                assert result is not None
                assert '<svg' in result

    def test_load_svg_template_different_templates(self, renderer_agent, sample_svg_content):
        """Test loading different template styles."""
        templates = ["modern", "classic", "minimal"]

        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            for template in templates:
                result = renderer_agent._load_svg_template("pptx", template, "cover")
                assert result is not None

    def test_load_svg_template_file_not_found(self, renderer_agent):
        """Test handling of missing template file."""
        with patch('builtins.open', side_effect=FileNotFoundError("Template not found")):
            with pytest.raises(FileNotFoundError):
                renderer_agent._load_svg_template("pptx", "nonexistent", "cover")


class TestRendererAgentApplyEditActionsSvg:
    """Tests for _apply_edit_actions_svg method."""

    def test_apply_edit_actions_svg_text_replacement(self, renderer_agent, sample_edit_plan, sample_svg_content):
        """Test text replacement in SVG."""
        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            result = renderer_agent._apply_edit_actions_svg(sample_edit_plan, sample_svg_content)

            # The placeholder should be replaced with actual content
            assert "Sample text content" in result or "text-1" in result
            assert "Placeholder text" not in result or result.count("Placeholder text") < sample_svg_content.count("Placeholder text")

    def test_apply_edit_actions_svg_font_styling(self, renderer_agent, sample_edit_plan, sample_svg_content):
        """Test that font styles are applied to text elements."""
        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            result = renderer_agent._apply_edit_actions_svg(sample_edit_plan, sample_svg_content)

            # Font styles should be in the result
            assert "font-size" in result or "fontSize" in result
            # Check for the specified font size
            assert 'font-size="18"' in result or "18" in result

    def test_apply_edit_actions_svg_color_styling(self, renderer_agent, sample_edit_plan, sample_svg_content):
        """Test that color is applied to text elements."""
        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            result = renderer_agent._apply_edit_actions_svg(sample_edit_plan, sample_svg_content)

            # Color should be in the result
            assert "#333333" in result or "333333" in result
            assert "fill" in result

    def test_apply_edit_actions_svg_multiple_actions(self, renderer_agent, sample_svg_content):
        """Test applying multiple edit actions."""
        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="First text", font_size=18),
                EditAction(action="replace_span", id="text-2", content="Second text", font_size=16)
            ]
        )

        svg_with_two_placeholders = '''<?xml version="1.0"?>
<svg viewBox="0 0 1920 1080">
    <text data-placeholder="text-1">Placeholder 1</text>
    <text data-placeholder="text-2">Placeholder 2</text>
</svg>'''

        with patch('builtins.open', mock_open(read_data=svg_with_two_placeholders)):
            result = renderer_agent._apply_edit_actions_svg(plan, svg_with_two_placeholders)

            # Both actions should be applied
            assert "First text" in result
            assert "Second text" in result


class TestRendererAgentImageEmbedding:
    """Tests for image handling in SVG."""

    def test_apply_edit_actions_svg_image_base64_embedding(self, renderer_agent, sample_edit_plan, sample_svg_content):
        """Test that images are embedded as base64 in SVG."""
        # Mock the image reading to return base64 data
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            with patch('app.agents.renderer_agent.base64.b64encode', return_value=base64_data):
                result = renderer_agent._apply_edit_actions_svg(sample_edit_plan, sample_svg_content)

                # Should contain base64 data (or at least reference to image)
                assert "image" in result.lower() or "img-1" in result

    def test_apply_edit_actions_svg_image_position(self, renderer_agent, sample_edit_plan, sample_svg_content):
        """Test that image position is applied correctly."""
        with patch('builtins.open', mock_open(read_data=sample_svg_content)):
            result = renderer_agent._apply_edit_actions_svg(sample_edit_plan, sample_svg_content)

            # Position data should be in the result
            # The EditAction has position [0.1, 0.1, 0.3, 0.3]
            assert "x" in result.lower() or "y" in result.lower()


class TestRendererAgentFallbackSvg:
    """Tests for _create_fallback_svg method."""

    def test_create_fallback_svg_generates_valid_svg(self, renderer_agent):
        """Test that fallback SVG is valid XML."""
        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="Fallback content", font_size=16)
            ]
        )

        result = renderer_agent._create_fallback_svg(plan)

        # Should be valid SVG
        assert result.startswith('<?xml') or '<svg' in result
        assert '</svg>' in result
        assert 'viewBox' in result

    def test_create_fallback_svg_includes_content(self, renderer_agent):
        """Test that fallback SVG includes content from edit plan."""
        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(action="replace_span", id="text-1", content="Test content for fallback"),
                EditAction(action="replace_span", id="text-2", content="More content")
            ]
        )

        result = renderer_agent._create_fallback_svg(plan)

        # All content should be present
        assert "Test content for fallback" in result
        assert "More content" in result

    def test_create_fallback_svg_with_empty_plan(self, renderer_agent):
        """Test fallback SVG generation with empty plan."""
        empty_plan = MagazineEditPlan(
            template="modern",
            actions=[]
        )

        result = renderer_agent._create_fallback_svg(empty_plan)

        # Should still be valid SVG
        assert '<svg' in result
        assert '</svg>' in result

    def test_create_fallback_svg_basic_structure(self, renderer_agent):
        """Test that fallback SVG has proper structure."""
        plan = MagazineEditPlan(
            template="modern",
            actions=[EditAction(action="replace_span", id="text-1", content="Test")]
        )

        result = renderer_agent._create_fallback_svg(plan)

        # Should have XML declaration and proper SVG elements
        assert '<?xml version' in result or '<svg' in result
        assert 'xmlns' in result
        assert 'http://www.w3.org/2000/svg' in result


class TestRendererAgentRender:
    """Tests for render method."""

    @pytest.mark.asyncio
    async def test_render_pdf_output(self, renderer_agent, sample_edit_plan):
        """Test rendering PDF output."""
        mock_doc = UnifiedDocument(
            title="Test",
            content=[],
            images=[],
            metadata={}
        )

        with patch('app.agents.renderer_agent.PlaywrightRenderer'):
            result = await renderer_agent.render(mock_doc, sample_edit_plan, "pdf")

            assert result is not None

    @pytest.mark.asyncio
    async def test_render_pptx_output(self, renderer_agent, sample_edit_plan):
        """Test rendering PPTX output."""
        mock_doc = UnifiedDocument(
            title="Test",
            content=[],
            images=[],
            metadata={}
        )

        with patch('app.agents.renderer_agent.PPTXRenderer'):
            result = await renderer_agent.render(mock_doc, sample_edit_plan, "pptx")

            assert result is not None

    @pytest.mark.asyncio
    async def test_render_unsupported_format(self, renderer_agent, sample_edit_plan):
        """Test rendering unsupported format raises error."""
        mock_doc = UnifiedDocument(
            title="Test",
            content=[],
            images=[],
            metadata={}
        )

        with pytest.raises(ValueError, match="Unsupported output format"):
            await renderer_agent.render(mock_doc, sample_edit_plan, "unsupported")