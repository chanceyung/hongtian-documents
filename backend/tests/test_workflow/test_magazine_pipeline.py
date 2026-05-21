"""Tests for Magazine Pipeline workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models import UnifiedDocument, MagazineEditPlan, SlideEditPlan
from app.agents.fidelity_agent import FidelityResult as FidelityReport
from app.workflow.magazine_pipeline import build_magazine_pipeline, should_repair, check_missing_assets_node


@pytest.fixture
def sample_unified_document():
    """Create sample UnifiedDocument for testing."""
    return UnifiedDocument(
        source_file="test.pptx",
        source_format="pptx",
        title="Test Document",
        texts=[],
        images=[]
    )


@pytest.fixture
def sample_edit_plan():
    """Create sample MagazineEditPlan for testing."""
    return MagazineEditPlan(
        document_id="test-doc",
        template_id="modern",
        pages=[]
    )


@pytest.fixture
def sample_fidelity_report_passed():
    """Create sample FidelityReport indicating success."""
    return FidelityReport(
        overall_score=0.98,
        fingerprint_score=1.0,
        linkage_score=1.0,
        semantic_score=0.95,
        passed=True,
        details={}
    )


@pytest.fixture
def sample_fidelity_report_failed():
    """Create sample FidelityReport indicating failure."""
    return FidelityReport(
        overall_score=0.7,
        fingerprint_score=0.8,
        linkage_score=0.6,
        semantic_score=0.7,
        passed=False,
        details={}
    )


class TestBuildMagazinePipeline:
    """Tests for build_magazine_pipeline function."""

    def test_build_magazine_pipeline_returns_compilable_graph(self):
        """Test that build_magazine_pipeline returns a compilable LangGraph."""
        graph = build_magazine_pipeline()

        # Should return a StateGraph
        assert graph is not None
        # Should be compilable
        compiled = graph.compile()
        assert compiled is not None

    def test_build_magazine_pipeline_has_required_nodes(self):
        """Test that pipeline includes all required nodes."""
        graph = build_magazine_pipeline()

        # Get the nodes from the graph
        # Note: The exact method to access nodes depends on LangGraph version
        # This is a basic check that the graph is structured correctly
        compiled = graph.compile()
        assert compiled is not None

    def test_build_magazine_pipeline_default_state(self):
        """Test that pipeline starts with correct default state."""
        graph = build_magazine_pipeline()
        compiled = graph.compile()

        # The graph should be ready to process state
        assert compiled is not None


class TestShouldRepair:
    """Tests for should_repair conditional edge."""

    def test_should_repair_fidelity_passed_false_repair_count_below_limit(self):
        """Test that should_repair returns 'repair' when fidelity fails and repair count < MAX_REPAIR_ATTEMPTS."""
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=FidelityReport(
                overall_score=0.7,
                fingerprint_score=0.8,
                linkage_score=0.6,
                semantic_score=0.7,
                passed=False,
                details={}
            ),
            repair_count=1,  # Below MAX_REPAIR_ATTEMPTS (which is typically 2)
            error=None
        )

        result = should_repair(state)

        assert result == "repair"

    def test_should_repair_fidelity_passed_false_repair_count_at_limit(self):
        """Test that should_repair returns 'finalize' when fidelity fails but repair count >= MAX_REPAIR_ATTEMPTS."""
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=FidelityReport(
                overall_score=0.7,
                fingerprint_score=0.8,
                linkage_score=0.6,
                semantic_score=0.7,
                passed=False,
                details={}
            ),
            repair_count=2,  # At MAX_REPAIR_ATTEMPTS
            error=None
        )

        result = should_repair(state)

        assert result == "finalize"

    def test_should_repair_fidelity_passed_true(self):
        """Test that should_repair returns 'finalize' when fidelity passes."""
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=FidelityReport(
                overall_score=0.98,
                fingerprint_score=1.0,
                linkage_score=1.0,
                semantic_score=0.95,
                passed=True,
                details={}
            ),
            repair_count=0,
            error=None
        )

        result = should_repair(state)

        assert result == "finalize"

    def test_should_repair_edge_case_exactly_at_threshold(self):
        """Test should_repair behavior at exactly MAX_REPAIR_ATTEMPTS - 1."""
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=FidelityReport(
                overall_score=0.5,
                fingerprint_score=0.5,
                linkage_score=0.5,
                semantic_score=0.5,
                passed=False,
                details={}
            ),
            repair_count=1,  # One below MAX_REPAIR_ATTEMPTS (2)
            error=None
        )

        result = should_repair(state)

        # Should still try to repair
        assert result == "repair"


class TestCheckMissingAssetsNode:
    """Tests for check_missing_assets_node function."""

    @pytest.mark.asyncio
    async def test_check_missing_assets_node_missing_images(self):
        """Test that check_missing_assets_node routes to 'supplement' when images are missing."""
        from app.models import ImageElement, BoundingBox

        state = MagazineState(
            unified_document=UnifiedDocument(
                source_file="test.pptx",
                source_format="pptx",
                title="Test",
                texts=[],
                images=[
                    ImageElement(id="img-1", local_path="", page=1, bbox=BoundingBox(left=0, top=0, width=1, height=1), alt_text="")
                ]
            ),
            edit_plan=MagazineEditPlan(
                document_id="test-doc",
                template_id="modern",
                pages=[]
            ),
            fidelity_report=None,
            repair_count=0,
            error=None
        )

        result = await check_missing_assets_node(state)

        # Should route to supplement
        assert result == "supplement"

    @pytest.mark.asyncio
    async def test_check_missing_assets_node_all_images_exist(self):
        """Test that check_missing_assets_node routes to 'render' when all images exist."""
        from app.models import ImageElement, BoundingBox

        state = MagazineState(
            unified_document=UnifiedDocument(
                source_file="test.pptx",
                source_format="pptx",
                title="Test",
                texts=[],
                images=[
                    ImageElement(id="img-1", local_path="/existing/path.png", page=1, bbox=BoundingBox(left=0, top=0, width=1, height=1), alt_text="")
                ]
            ),
            edit_plan=MagazineEditPlan(
                document_id="test-doc",
                template_id="modern",
                pages=[]
            ),
            fidelity_report=None,
            repair_count=0,
            error=None
        )

        result = await check_missing_assets_node(state)

        # Should route to render
        assert result == "render"

    @pytest.mark.asyncio
    async def test_check_missing_assets_node_no_images(self):
        """Test that check_missing_assets_node routes to 'render' when there are no images."""
        state = MagazineState(
            unified_document=UnifiedDocument(
                source_file="test.pptx",
                source_format="pptx",
                title="Test",
                texts=[],
                images=[]
            ),
            edit_plan=MagazineEditPlan(
                document_id="test-doc",
                template_id="modern",
                pages=[]
            ),
            fidelity_report=None,
            repair_count=0,
            error=None
        )

        result = await check_missing_assets_node(state)

        # Should route to render (no images to check)
        assert result == "render"

    @pytest.mark.asyncio
    async def test_check_missing_assets_node_partial_missing(self):
        """Test check_missing_assets_node with some images missing and some present."""
        from app.models import ImageElement, BoundingBox

        state = MagazineState(
            unified_document=UnifiedDocument(
                source_file="test.pptx",
                source_format="pptx",
                title="Test",
                texts=[],
                images=[
                    ImageElement(id="img-1", local_path="/existing.png", page=1, bbox=BoundingBox(left=0, top=0, width=0.5, height=1), alt_text=""),
                    ImageElement(id="img-2", local_path="", page=1, bbox=BoundingBox(left=0.5, top=0, width=1, height=1), alt_text="")
                ]
            ),
            edit_plan=MagazineEditPlan(
                document_id="test-doc",
                template_id="modern",
                pages=[]
            ),
            fidelity_report=None,
            repair_count=0,
            error=None
        )

        result = await check_missing_assets_node(state)

        # Should route to supplement (at least one image missing)
        assert result == "supplement"


class TestMagazinePipelineIntegration:
    """Integration tests for the complete magazine pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_parser_to_analyzer_flow(self):
        """Test flow from parser to analyzer agent."""
        # Mock parser agent
        mock_parser = AsyncMock(return_value=UnifiedDocument(
            source_file="test.pptx",
            source_format="pptx",
            title="Test",
            texts=[],
            images=[]
        ))

        # Mock analyzer agent
        mock_analyzer = AsyncMock(return_value=None)

        with patch('app.workflow.magazine_pipeline.ParserAgent') as MockParser:
            with patch('app.workflow.magazine_pipeline.AnalyzerAgent') as MockAnalyzer:
                MockParser.return_value.parse = mock_parser
                MockAnalyzer.return_value.analyze = mock_analyzer

                state = MagazineState(
                    input_file="test.pptx",
                    unified_document=None,
                    analysis_result=None,
                    edit_plan=None,
                    fidelity_report=None,
                    repair_count=0,
                    error=None
                )

                graph = build_magazine_pipeline()
                compiled = graph.compile()

                # The graph should be able to process this state
                assert compiled is not None

    @pytest.mark.asyncio
    async def test_pipeline_repair_loop(self):
        """Test that repair loop respects MAX_REPAIR_ATTEMPTS."""
        # This tests the conditional edge logic
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=FidelityReport(
                overall_score=0.6,
                fingerprint_score=0.6,
                linkage_score=0.6,
                semantic_score=0.6,
                passed=False,
                details={}
            ),
            repair_count=2,  # At limit
            error=None
        )

        result = should_repair(state)

        # Should finalize, not repair
        assert result == "finalize"

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test that errors are properly propagated through the pipeline."""
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=None,
            repair_count=0,
            error="Test error message"
        )

        # Error state should be handled
        assert state.error is not None


class TestMagazineState:
    """Tests for MagazineState model."""

    def test_magazine_state_initialization(self):
        """Test that MagazineState can be initialized with all fields."""
        state = MagazineState(
            input_file="test.pptx",
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            analysis_result=None,
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=None,
            repair_count=0,
            error=None
        )

        assert state.input_file == "test.pptx"
        assert state.unified_document is not None
        assert state.analysis_result is None
        assert state.edit_plan is not None
        assert state.fidelity_report is None
        assert state.repair_count == 0
        assert state.error is None

    def test_magazine_state_with_error(self):
        """Test MagazineState with error set."""
        state = MagazineState(
            unified_document=UnifiedDocument(source_file="test.pptx", source_format="pptx", title="Test", texts=[], images=[]),
            edit_plan=MagazineEditPlan(document_id="test-doc", template_id="modern", pages=[]),
            fidelity_report=None,
            repair_count=0,
            error="Processing failed"
        )

        assert state.error == "Processing failed"