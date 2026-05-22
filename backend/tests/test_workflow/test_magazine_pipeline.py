"""Tests for Magazine Pipeline workflow."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import UnifiedDocument, TextElement, ImageElement, MagazineEditPlan, SlideEditPlan, EditAction
from app.workflow.magazine_pipeline import (
    build_magazine_pipeline,
    should_repair,
    check_missing_assets_node,
    PipelineState,
)


def _make_state(**overrides) -> dict:
    base = {
        "file_path": "test.pptx",
        "task_id": "test-session",
        "session_id": "test-session",
        "output_format": "pdf",
        "template_id": "modern_tech",
        "repair_count": 0,
    }
    base.update(overrides)
    return base


def _doc_with_images(*paths) -> UnifiedDocument:
    images = [ImageElement(id=f"img-{i}", local_path=p, page=0) for i, p in enumerate(paths)]
    return UnifiedDocument(source_file="test.pptx", source_format="pptx", images=images)


def _plan_with_image_actions(*image_ids) -> MagazineEditPlan:
    actions = [EditAction(type="replace_image", target_selector=f"#{iid}", source_id=iid) for iid in image_ids]
    return MagazineEditPlan(
        document_id="test-doc",
        template_id="modern",
        pages=[SlideEditPlan(page_number=1, template_page="cover", actions=actions)],
    )


class TestBuildMagazinePipeline:
    def test_returns_compiled_graph(self):
        graph = build_magazine_pipeline()
        assert graph is not None
        assert hasattr(graph, "ainvoke")

    def test_graph_has_expected_type(self):
        from langgraph.graph.state import CompiledStateGraph
        graph = build_magazine_pipeline()
        assert isinstance(graph, CompiledStateGraph)


class TestShouldRepair:
    def test_fidelity_not_passed_below_limit(self):
        state = _make_state(fidelity_passed=False, repair_count=0)
        assert should_repair(state) == "repair"

    def test_fidelity_not_passed_at_limit(self):
        state = _make_state(fidelity_passed=False, repair_count=2)
        assert should_repair(state) == "finalize"

    def test_fidelity_passed(self):
        state = _make_state(fidelity_passed=True, repair_count=0)
        assert should_repair(state) == "finalize"

    def test_fidelity_not_passed_one_below_limit(self):
        state = _make_state(fidelity_passed=False, repair_count=1)
        assert should_repair(state) == "repair"


class TestCheckMissingAssetsNode:
    @pytest.mark.asyncio
    async def test_missing_image_routes_to_supplement(self, tmp_path):
        missing = str(tmp_path / "nonexistent.png")
        doc = _doc_with_images(missing)
        plan = _plan_with_image_actions("img-0")
        state = _make_state(document=doc, edit_plan=plan)
        result = await check_missing_assets_node(state)
        assert result == "supplement"

    @pytest.mark.asyncio
    async def test_existing_image_routes_to_render(self, tmp_path):
        existing = tmp_path / "exists.png"
        existing.write_bytes(b"png")
        doc = _doc_with_images(str(existing))
        plan = _plan_with_image_actions("img-0")
        state = _make_state(document=doc, edit_plan=plan)
        result = await check_missing_assets_node(state)
        assert result == "render"

    @pytest.mark.asyncio
    async def test_no_images_routes_to_render(self):
        doc = _doc_with_images()
        plan = _plan_with_image_actions()
        state = _make_state(document=doc, edit_plan=plan)
        result = await check_missing_assets_node(state)
        assert result == "render"

    @pytest.mark.asyncio
    async def test_no_image_actions_routes_to_render(self):
        doc = _doc_with_images("/some/path.png")
        plan = MagazineEditPlan(
            document_id="test-doc",
            template_id="modern",
            pages=[SlideEditPlan(page_number=1, template_page="text_only", actions=[])],
        )
        state = _make_state(document=doc, edit_plan=plan)
        result = await check_missing_assets_node(state)
        assert result == "render"


class TestPipelineState:
    def test_state_has_required_fields(self):
        state = _make_state()
        assert "file_path" in state
        assert "session_id" in state
        assert "output_format" in state

    def test_state_with_results(self):
        state = _make_state(
            fidelity_score=0.97,
            fidelity_passed=True,
            output_path="/output/test.pdf",
        )
        assert state["fidelity_score"] == 0.97
        assert state["fidelity_passed"] is True


class TestPipelineNodes:
    @pytest.mark.asyncio
    async def test_parser_node(self, tmp_path):
        from app.workflow.magazine_pipeline import parser_node

        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello\n\nWorld", encoding="utf-8")
        state = _make_state(file_path=str(test_file), session_id="test")

        result = await parser_node(state)
        assert "document" in result
        assert isinstance(result["document"], UnifiedDocument)
        assert result["document"].source_format == "md"

    @pytest.mark.asyncio
    async def test_finalize_node(self, tmp_path):
        from app.workflow.magazine_pipeline import finalize_node
        from app.core.config import settings

        output_dir = tmp_path / "output" / "test-session"
        output_dir.mkdir(parents=True)

        with patch.object(settings, "OUTPUT_DIR", str(tmp_path / "output")):
            state = _make_state(
                session_id="test-session",
                output_path=str(output_dir / "magazine.pdf"),
                fidelity_score=0.98,
                fidelity_passed=True,
            )
            result = await finalize_node(state)
            assert result == {}
