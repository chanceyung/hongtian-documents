"""Tests for DesignerAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import (
    UnifiedDocument, ContentItem, ImageItem, MagazineEditPlan, EditAction,
    ContentGroup, DesignSpec
)
from app.agents.designer_agent import DesignerAgent


@pytest.fixture
def designer_agent():
    """Create DesignerAgent instance for testing."""
    return DesignerAgent()


@pytest.fixture
def sample_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        title="Test Document",
        content=[
            ContentItem(
                id="text-1",
                text="Introduction text that will be styled",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.1, 0.5, 0.2]
            ),
            ContentItem(
                id="text-2",
                text="Main content with details",
                type="paragraph",
                page_number=1,
                bbox=[0.1, 0.3, 0.5, 0.5]
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


@pytest.fixture
def sample_analysis_result():
    """Create sample analysis result for testing."""
    from app.models import AnalysisResult

    return AnalysisResult(
        content_groups=[
            ContentGroup(id="group-1", title="Introduction", content_ids=["text-1"])
        ],
        layout_patterns=["top-bottom"],
        semantic_links=[]
    )


class TestDesignerAgentDesign:
    """Tests for design method."""

    @pytest.mark.asyncio
    async def test_design_returns_magazine_edit_plan(self, designer_agent, sample_document, sample_analysis_result):
        """Test that design returns MagazineEditPlan."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"action": "replace_span", "id": "text-1", "font_size": 18, "color": "#333333"}]'
            ))]
        ))

        with patch('app.agents.designer_agent.client', mock_client):
            result = await designer_agent.design(sample_document, sample_analysis_result)

            assert isinstance(result, MagazineEditPlan)
            assert len(result.actions) > 0
            assert result.template is not None

    @pytest.mark.asyncio
    async def test_design_with_empty_document(self, designer_agent):
        """Test designing an empty document."""
        empty_doc = UnifiedDocument(
            title="Empty",
            content=[],
            images=[],
            metadata={}
        )

        from app.models import AnalysisResult
        empty_analysis = AnalysisResult(
            content_groups=[],
            layout_patterns=[],
            semantic_links=[]
        )

        result = await designer_agent.design(empty_doc, empty_analysis)

        assert isinstance(result, MagazineEditPlan)
        assert result.actions == []

    @pytest.mark.asyncio
    async def test_design_includes_all_content(self, designer_agent, sample_document, sample_analysis_result):
        """Test that all content items are included in the plan."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='''[
                    {"action": "replace_span", "id": "text-1", "font_size": 18, "color": "#333333"},
                    {"action": "replace_span", "id": "text-2", "font_size": 16, "color": "#666666"}
                ]'''
            ))]
        ))

        with patch('app.agents.designer_agent.client', mock_client):
            result = await designer_agent.design(sample_document, sample_analysis_result)

            # All content IDs should appear in the actions
            action_ids = {action.id for action in result.actions}
            assert "text-1" in action_ids
            assert "text-2" in action_ids


class TestDesignerAgentValidateCompleteness:
    """Tests for _validate_completeness method."""

    @pytest.mark.asyncio
    async def test_validate_completeness_appends_missing_content(self, designer_agent, sample_document):
        """Test that missing content is automatically appended."""
        # Create a plan that only includes text-1
        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(
                    action="replace_span",
                    id="text-1",
                    content="Introduction text that will be styled",
                    font_size=18
                )
            ]
        )

        # Validate should detect text-2 is missing and append it
        validated_plan = await designer_agent._validate_completeness(plan, sample_document)

        action_ids = {action.id for action in validated_plan.actions}
        assert "text-1" in action_ids
        assert "text-2" in action_ids

    @pytest.mark.asyncio
    async def test_validate_completeness_with_complete_plan(self, designer_agent, sample_document):
        """Test validation with already complete plan."""
        # Create a plan that includes all content
        plan = MagazineEditPlan(
            template="modern",
            actions=[
                EditAction(
                    action="replace_span",
                    id="text-1",
                    content="Introduction text that will be styled",
                    font_size=18
                ),
                EditAction(
                    action="replace_span",
                    id="text-2",
                    content="Main content with details",
                    font_size=16
                )
            ]
        )

        validated_plan = await designer_agent._validate_completeness(plan, sample_document)

        # Should remain the same
        assert len(validated_plan.actions) == len(plan.actions)


class TestDesignerAgentEditActions:
    """Tests for edit action generation."""

    @pytest.mark.asyncio
    async def test_edit_actions_content_is_original_text(self, designer_agent, sample_document, sample_analysis_result):
        """Test that edit action content field contains original text, not LLM rewritten text."""
        original_text = "Introduction text that will be styled"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"action": "replace_span", "id": "text-1", "font_size": 18, "color": "#333333"}]'
            ))]
        ))

        with patch('app.agents.designer_agent.client', mock_client):
            result = await designer_agent.design(sample_document, sample_analysis_result)

            # Find action for text-1
            text1_action = next((a for a in result.actions if a.id == "text-1"), None)
            assert text1_action is not None
            assert text1_action.content == original_text
            assert text1_action.content != " rewritten version"  # Not modified by LLM

    @pytest.mark.asyncio
    async def test_edit_actions_include_styles(self, designer_agent, sample_document, sample_analysis_result):
        """Test that edit actions include style properties."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[{"action": "replace_span", "id": "text-1", "font_size": 24, "font_family": "Arial", "color": "#1a1a2e", "alignment": "center"}]'
            ))]
        ))

        with patch('app.agents.designer_agent.client', mock_client):
            result = await designer_agent.design(sample_document, sample_analysis_result)

            action = result.actions[0]
            assert action.font_size == 24
            assert action.font_family == "Arial"
            assert action.color == "#1a1a2e"
            assert action.alignment == "center"


class TestDesignerAgentTemplateSelection:
    """Tests for template selection logic."""

    @pytest.mark.asyncio
    async def test_template_selection_based_on_layout_pattern(self, designer_agent, sample_document):
        """Test that template is selected based on layout pattern."""
        from app.models import AnalysisResult

        # Analysis suggests a top-bottom layout
        analysis = AnalysisResult(
            content_groups=[],
            layout_patterns=["top-bottom"],
            semantic_links=[]
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        with patch('app.agents.designer_agent.client', mock_client):
            result = await designer_agent.design(sample_document, analysis)

            # Template should be appropriate for top-bottom layout
            assert result.template in ["modern", "classic", "minimal"]

    @pytest.mark.asyncio
    async def test_template_selection_with_images(self, designer_agent, sample_document):
        """Test template selection when document has images."""
        from app.models import AnalysisResult

        analysis = AnalysisResult(
            content_groups=[],
            layout_patterns=["image-heavy"],
            semantic_links=[]
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='[]'
            ))]
        ))

        with patch('app.agents.designer_agent.client', mock_client):
            result = await designer_agent.design(sample_document, analysis)

            # Template should support images
            assert result.template is not None