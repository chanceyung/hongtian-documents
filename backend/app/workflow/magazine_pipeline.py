import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan, EditAction, SlideEditPlan
from app.models.design_spec import DesignSpec

logger = get_logger(__name__)


class PipelineState(TypedDict, total=False):
    file_path: str
    session_id: str
    output_format: str
    template_id: str
    document: UnifiedDocument
    parse_warnings: list[str]
    analysis: dict
    edit_plan: MagazineEditPlan
    design_spec: dict
    supplemented: bool
    output_path: str
    fidelity_score: float
    fidelity_passed: bool
    fidelity_issues: list[dict]
    repair_count: int


async def _get_api_key(session_id: str) -> str:
    from app.api.router import decrypt_key
    from app.core.redis import redis_client

    redis = redis_client.client
    encrypted = await redis.hget(f"api_keys:{session_id}", "zhipu_key")
    if not encrypted:
        logger.warning("未配置智谱 API Key", session_id=session_id)
        raise ValueError("未配置智谱 API Key，请先在设置中配置")
    return decrypt_key(encrypted)


async def parser_node(state: PipelineState) -> dict:
    from app.agents.parser_agent import ParserAgent

    logger.info("pipeline.parse.start", session_id=state["session_id"], file_path=state["file_path"])
    agent = ParserAgent()
    doc = await agent.parse(Path(state["file_path"]), state["session_id"])
    return {"document": doc, "parse_warnings": doc.parse_warnings}


async def analyzer_node(state: PipelineState) -> dict:
    from app.agents.analyzer_agent import AnalyzerAgent
    from app.core.config import settings

    logger.info("pipeline.analyze.start", session_id=state["session_id"])
    api_key = await _get_api_key(state["session_id"])
    agent = AnalyzerAgent(api_key, model=settings.CUSTOM_MODEL)
    analysis = await agent.analyze(state["document"])
    return {"analysis": analysis}


async def designer_node(state: PipelineState) -> dict:
    from app.agents.designer_agent import DesignerAgent
    from app.core.config import settings

    logger.info("pipeline.design.start", session_id=state["session_id"], template_id=state["template_id"])
    api_key = await _get_api_key(state["session_id"])
    agent = DesignerAgent(api_key, model=settings.CUSTOM_MODEL)
    plan = await agent.design(
        state["document"],
        state["analysis"],
        state["template_id"],
    )
    return {"edit_plan": plan, "design_spec": plan.design_spec}


async def check_missing_assets_node(state: PipelineState) -> str:
    plan = state["edit_plan"]
    doc = state["document"]

    for page in plan.pages:
        for action in page.actions:
            if action.type == "replace_image":
                img = next(
                    (i for i in doc.images if i.id == action.source_id), None,
                )
                if not img or not Path(img.local_path).exists():
                    return "supplement"
    return "render"


async def supplement_node(state: PipelineState) -> dict:
    from app.agents.supplement_agent import SupplementAgent

    agent = SupplementAgent(state["session_id"])
    await agent.supplement(state["document"], state["edit_plan"])
    return {"supplemented": True}


async def renderer_node(state: PipelineState) -> dict:
    from app.agents.renderer_agent import RendererAgent
    from app.core.config import settings

    logger.info("pipeline.render.start", session_id=state["session_id"], output_format=state["output_format"])
    agent = RendererAgent()
    template_dir = Path(settings.MAGAZINE_TEMPLATES_DIR)
    output_dir = Path(settings.OUTPUT_DIR) / state["task_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    if state["output_format"] == "pdf":
        output_path = output_dir / "magazine.pdf"
        path = await agent.render_pdf(
            state["edit_plan"], state["document"],
            template_dir / "pdf", output_path,
        )
    else:
        output_path = output_dir / "magazine.pptx"
        path = await agent.render_pptx(
            state["edit_plan"], state["document"],
            template_dir / "pptx", output_path,
        )

    return {"output_path": str(path)}


async def fidelity_node(state: PipelineState) -> dict:
    from app.agents.fidelity_agent import FidelityAgent
    from app.core.config import settings

    logger.info("pipeline.fidelity.start", session_id=state["session_id"])
    api_key = await _get_api_key(state["session_id"])
    agent = FidelityAgent(api_key, threshold=settings.FIDELITY_THRESHOLD, model=settings.CUSTOM_MODEL)
    result = await agent.verify(state["document"], state["edit_plan"])
    return {
        "fidelity_score": result.overall_score,
        "fidelity_passed": result.passed,
        "fidelity_issues": [i.model_dump() for i in result.issues],
    }


async def repair_node(state: PipelineState) -> dict:
    repair_count = state.get("repair_count", 0) + 1
    plan = state["edit_plan"]
    doc = state["document"]

    logger.warning("pipeline.repair", session_id=state["session_id"], repair_count=repair_count)
    for issue in state.get("fidelity_issues", []):
        if issue.get("category") != "fingerprint":
            continue

        if "遗漏" in issue.get("description", ""):
            element_id = issue.get("element_id", "")
            text = next((t for t in doc.texts if t.id == element_id), None)
            if text:
                if plan.pages:
                    target_page = plan.pages[-1]
                else:
                    target_page = SlideEditPlan(page_number=1, template_page="text_only")
                    plan.pages.append(target_page)

                target_page.actions.append(EditAction(
                    type="replace_text",
                    target_selector=f".repaired-{len(target_page.actions)}",
                    source_id=text.id,
                    content=text.content,
                ))

    return {"edit_plan": plan, "repair_count": repair_count}


async def finalize_node(state: PipelineState) -> dict:
    from app.core.config import settings

    summary = {
        "output_path": state.get("output_path", ""),
        "fidelity_score": state.get("fidelity_score", 0),
        "fidelity_passed": state.get("fidelity_passed", False),
        "repair_count": state.get("repair_count", 0),
        "supplemented": state.get("supplemented", False),
    }

    output_dir = Path(settings.OUTPUT_DIR) / state["task_id"]
    summary_path = output_dir / "task_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return {}


def should_repair(state: PipelineState) -> str:
    if not state.get("fidelity_passed", False) and state.get("repair_count", 0) < 2:
        return "repair"
    return "finalize"


def build_magazine_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("parse", parser_node)
    graph.add_node("analyze", analyzer_node)
    graph.add_node("design", designer_node)
    graph.add_node("supplement", supplement_node)
    graph.add_node("render", renderer_node)
    graph.add_node("verify", fidelity_node)
    graph.add_node("repair", repair_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "analyze")
    graph.add_edge("analyze", "design")

    graph.add_conditional_edges(
        "design",
        check_missing_assets_node,
        {"supplement": "supplement", "render": "render"},
    )

    graph.add_edge("supplement", "render")
    graph.add_edge("render", "verify")

    graph.add_conditional_edges(
        "verify",
        should_repair,
        {"repair": "repair", "finalize": "finalize"},
    )

    graph.add_edge("repair", "verify")
    graph.add_edge("finalize", END)

    return graph.compile()
