"""Tests for PlannerAgent."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.planner_agent import PlannerAgent
from app.models.execution_plan import ComplexityMetrics, ExecutionPlan


@pytest.fixture
def planner_agent():
    return PlannerAgent()


class TestPlannerComplexityScore:
    def test_simple_document_low_score(self, planner_agent):
        metrics = ComplexityMetrics(
            page_count=3, image_count=1, table_count=0,
            total_chars=500, text_density=100, image_ratio=0.3,
            layout_diversity=1,
        )
        score = planner_agent._complexity_score(metrics)
        assert score <= 30

    def test_complex_document_high_score(self, planner_agent):
        metrics = ComplexityMetrics(
            page_count=50, image_count=80, table_count=10,
            total_chars=50000, text_density=800, image_ratio=2.0,
            layout_diversity=5,
        )
        score = planner_agent._complexity_score(metrics)
        assert score > 70

    def test_medium_document_middle_score(self, planner_agent):
        metrics = ComplexityMetrics(
            page_count=10, image_count=5, table_count=2,
            total_chars=5000, text_density=300, image_ratio=0.5,
            layout_diversity=2,
        )
        score = planner_agent._complexity_score(metrics)
        assert 31 <= score <= 70


class TestPlannerPathSelection:
    def test_fast_path_for_simple(self, planner_agent):
        path = planner_agent._select_path(25)
        assert path == "fast"

    def test_standard_path_for_medium(self, planner_agent):
        path = planner_agent._select_path(50)
        assert path == "standard"

    def test_deep_path_for_complex(self, planner_agent):
        path = planner_agent._select_path(80)
        assert path == "deep"


class TestPlannerPlanGeneration:
    def test_fast_plan_skips_analyzer(self, planner_agent):
        metrics = ComplexityMetrics(page_count=3, image_count=1)
        plan = planner_agent._generate_plan(metrics, 20, "fast")
        assert plan.processing_path == "fast"
        assert plan.skip_analyzer is True
        assert plan.skip_supplement is True
        assert plan.estimated_time_seconds <= 60

    def test_standard_plan_full_pipeline(self, planner_agent):
        metrics = ComplexityMetrics(page_count=15, image_count=10)
        plan = planner_agent._generate_plan(metrics, 50, "standard")
        assert plan.processing_path == "standard"
        assert plan.skip_analyzer is False
        assert plan.page_parallel is False

    def test_deep_plan_enables_parallel(self, planner_agent):
        metrics = ComplexityMetrics(page_count=50, image_count=80)
        plan = planner_agent._generate_plan(metrics, 85, "deep")
        assert plan.processing_path == "deep"
        assert plan.page_parallel is True
        assert plan.max_render_concurrency == 4

    def test_risk_alerts_for_large_documents(self, planner_agent):
        metrics = ComplexityMetrics(page_count=50, image_ratio=3.0, table_count=10, text_density=900)
        plan = planner_agent._generate_plan(metrics, 90, "deep")
        assert len(plan.risk_alerts) >= 3

    def test_no_risk_alerts_for_simple(self, planner_agent):
        metrics = ComplexityMetrics(page_count=3, image_ratio=0.2, table_count=0, text_density=100)
        plan = planner_agent._generate_plan(metrics, 20, "fast")
        assert len(plan.risk_alerts) == 0


class TestPlannerScanPptx:
    @pytest.mark.asyncio
    async def test_scan_pptx_returns_metrics(self, planner_agent):
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape_text = MagicMock()
        mock_shape_text.shape_type = 1
        mock_shape_text.has_text_frame = True
        mock_shape_text.has_table = False
        mock_para = MagicMock()
        mock_para.text = "Hello World"
        mock_para.level = 0
        mock_shape_text.text_frame.paragraphs = [mock_para]

        mock_slide.shapes = [mock_shape_text]
        mock_prs.slides = [mock_slide]

        with patch("pptx.Presentation", return_value=mock_prs):
            metrics = await planner_agent._scan_pptx(Path("test.pptx"))
            assert metrics.page_count == 1
            assert metrics.total_chars == 11


class TestPlannerFullPlan:
    @pytest.mark.asyncio
    async def test_plan_returns_execution_plan(self, planner_agent):
        mock_metrics = ComplexityMetrics(
            page_count=5, image_count=2, text_density=200,
        )
        with patch.object(planner_agent, "_quick_scan", return_value=mock_metrics):
            plan = await planner_agent.plan(Path("test.pptx"))
            assert isinstance(plan, ExecutionPlan)
            assert plan.processing_path in ("fast", "standard", "deep")
            assert plan.complexity_score >= 0
            assert plan.estimated_time_seconds > 0
