"""杂志级文档重构 Pipeline — LangGraph 工作流编排

集成 LLMClient 统一调用 + 技能系统参数覆盖。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.core.recovery import RecoveryManager
from app.core.task_tracker import get_task_tracker, start_task, end_task, is_shutting_down
from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan, EditAction, SlideEditPlan
from app.models.design_spec import DesignSpec
from app.models.execution_plan import ExecutionPlan
from app.services.llm_client import LLMClient
from app.skills.types import SkillDefinition

logger = get_logger(__name__)


class PipelineState(TypedDict, total=False):
    file_path: str
    session_id: str
    task_id: str
    output_format: str
    template_id: str
    execution_plan: ExecutionPlan
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
    recovery_messages: list[str]
    # LLM + 技能（运行时注入）
    llm: LLMClient
    skill_name: str
    skill: SkillDefinition


async def _run_with_recovery(
    agent_name: str,
    state: PipelineState,
    primary_fn: object,
    fallback_fn: object | None = None,
    **kwargs: object,
) -> dict:
    """包裹 agent 调用，失败时走 RecoveryManager 三级恢复。"""
    from app.core.recovery import RecoveryManager, RecoveryAction

    task_id = state.get("task_id", "unknown")
    mgr = _recovery_mgr

    try:
        return await primary_fn(state, **kwargs)
    except Exception as e:
        result = await mgr.recover(agent_name, e, task_id, fallback_fn=fallback_fn)

        if result.action == RecoveryAction.RETRY:
            raise
        if result.action == RecoveryAction.DEGRADE and result.success:
            msgs = list(state.get("recovery_messages", []))
            msgs.append(result.message)
            return {"recovery_messages": msgs}
        raise


_recovery_mgr = RecoveryManager()


def _track_phase(phase_name: str):
    """装饰器：为 pipeline node 添加阶段状态追踪，实现幂等跳过。"""
    def decorator(fn):
        async def wrapper(state: PipelineState) -> dict:
            task_id = state.get("task_id", "")
            if not task_id:
                return await fn(state)

            tracker = get_task_tracker()
            if await tracker.is_completed(task_id, phase_name):
                logger.info("pipeline.phase.skip", phase=phase_name, task_id=task_id, reason="already completed")
                return {}

            await tracker.mark_running(task_id, phase_name)
            try:
                result = await fn(state)
                await tracker.mark_completed(task_id, phase_name)
                return result
            except Exception:
                await tracker.mark_failed(task_id, phase_name)
                raise
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


async def _get_api_key(session_id: str) -> str:
    import os
    from app.api.router import decrypt_key, encrypt_key
    from app.core.redis import redis_client

    redis = redis_client.client

    # 1. Try KV store (fast path — from sync or cache)
    encrypted = await redis.hget(f"api_keys:{session_id}", "zhipu_key")
    if encrypted:
        return decrypt_key(encrypted)

    # 2. Fallback: query Node.js server for API key
    node_port = os.environ.get("NODE_SERVER_PORT")
    if node_port:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"http://127.0.0.1:{node_port}/api/internal/settings")
                if resp.status_code == 200:
                    data = resp.json()
                    api_key = data.get("apiKey", "")
                    if api_key:
                        model = data.get("model", "glm-4-flash")
                        await redis.hset(f"api_keys:{session_id}", mapping={
                            "zhipu_key": encrypt_key(api_key),
                            "zhipu_model": model,
                        })
                        await redis.expire(f"api_keys:{session_id}", 86400)
                        logger.info("api_key.synced_from_node", session_id=session_id)
                        return api_key
        except Exception as e:
            logger.warning("api_key.node_fallback_failed", error=str(e)[:200])

    logger.warning("api_key.not_found", session_id=session_id)
    raise ValueError("未配置智谱 API Key，请先在设置中配置")


def _skill_overrides(skill: SkillDefinition | None) -> dict:
    if not skill:
        return {}
    overrides: dict = {}
    if skill.style_override:
        overrides["style_override"] = skill.style_override
    if skill.color_scheme_override:
        overrides["color_scheme_override"] = skill.color_scheme_override
    if skill.target_pages_override:
        overrides["target_pages_override"] = skill.target_pages_override
    if skill.layout_preferences:
        overrides["layout_preferences"] = skill.layout_preferences
    return overrides


@_track_phase("plan")
async def planner_node(state: PipelineState) -> dict:
    from app.agents.planner_agent import PlannerAgent

    logger.info("pipeline.plan.start", session_id=state["session_id"], file_path=state["file_path"])
    agent = PlannerAgent()
    plan = await agent.plan(Path(state["file_path"]))
    logger.info(
        "pipeline.plan.done",
        session_id=state["session_id"],
        score=plan.complexity_score,
        path=plan.processing_path,
        est_time=plan.estimated_time_seconds,
    )
    return {"execution_plan": plan}


def should_skip_analyzer(state: PipelineState) -> str:
    plan: ExecutionPlan | None = state.get("execution_plan")
    if plan and plan.skip_analyzer:
        return "skip_to_design"
    return "analyze"


@_track_phase("parse")
async def parser_node(state: PipelineState) -> dict:
    from app.agents.parser_agent import ParserAgent
    from app.core.recovery import RecoveryAction

    logger.info("pipeline.parse.start", session_id=state["session_id"], file_path=state["file_path"])
    agent = ParserAgent()
    try:
        doc = await agent.parse(Path(state["file_path"]), state["session_id"])
        return {"document": doc, "parse_warnings": doc.parse_warnings}
    except Exception as e:
        result = await _recovery_mgr.recover("parser", e, state.get("task_id", ""))
        if result.action == RecoveryAction.RETRY:
            raise
        if result.action == RecoveryAction.DEGRADE and result.success:
            logger.warning("pipeline.parse.degraded", fallback=result.fallback_used)
            doc = await agent.parse(Path(state["file_path"]), state["session_id"])
            msgs = list(state.get("recovery_messages", []))
            msgs.append(result.message)
            return {"document": doc, "parse_warnings": doc.parse_warnings, "recovery_messages": msgs}
        raise


@_track_phase("analyze")
async def analyzer_node(state: PipelineState) -> dict:
    from app.agents.analyzer_agent import AnalyzerAgent
    from app.core.recovery import RecoveryAction

    logger.info("pipeline.analyze.start", session_id=state["session_id"])
    llm: LLMClient = state["llm"]
    skill: SkillDefinition | None = state.get("skill")

    agent = AnalyzerAgent(llm)

    try:
        # 技能附加指令
        if skill and skill.analyzer_instructions:
            doc = state["document"]
            extra_analysis = await llm.chat_json(
                system=f"对文档进行补充分析。{skill.analyzer_instructions}\n返回 JSON 对象。",
                user="\n".join(t.content[:200] for t in doc.texts[:20])[:4000],
            )
            analysis = await agent.analyze(state["document"])
            analysis["skill_analysis"] = extra_analysis
            return {"analysis": analysis}

        analysis = await agent.analyze(state["document"])
        return {"analysis": analysis}
    except Exception as e:
        result = await _recovery_mgr.recover("analyzer", e, state.get("task_id", ""))
        if result.action == RecoveryAction.RETRY:
            raise
        if result.action == RecoveryAction.DEGRADE and result.success:
            logger.warning("pipeline.analyze.degraded", fallback=result.fallback_used)
            return {"analysis": {"mode": "minimal", "degraded": True}}
        raise


@_track_phase("design")
async def designer_node(state: PipelineState) -> dict:
    from app.agents.designer_agent import DesignerAgent
    from app.core.recovery import RecoveryAction

    logger.info("pipeline.design.start", session_id=state["session_id"], template_id=state["template_id"])
    llm: LLMClient = state["llm"]
    skill: SkillDefinition | None = state.get("skill")

    agent = DesignerAgent(llm)
    overrides = _skill_overrides(skill)

    try:
        plan = await agent.design(
            state["document"],
            state["analysis"],
            state["template_id"],
            skill_overrides=overrides if overrides else None,
        )
        return {"edit_plan": plan, "design_spec": plan.design_spec}
    except Exception as e:
        result = await _recovery_mgr.recover("designer", e, state.get("task_id", ""))
        if result.action == RecoveryAction.RETRY:
            raise
        if result.action == RecoveryAction.DEGRADE and result.success:
            logger.warning("pipeline.design.degraded", fallback=result.fallback_used)
            plan = await agent.design(
                state["document"],
                state["analysis"],
                state["template_id"],
                skill_overrides=overrides if overrides else None,
            )
            msgs = list(state.get("recovery_messages", []))
            msgs.append(result.message)
            return {"edit_plan": plan, "design_spec": plan.design_spec, "recovery_messages": msgs}
        raise


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


@_track_phase("supplement")
async def supplement_node(state: PipelineState) -> dict:
    from app.agents.supplement_agent import SupplementAgent

    doc = state["document"]
    llm: LLMClient = state["llm"]

    missing = [
        img for img in doc.images
        if not img.local_path or not Path(img.local_path).exists()
    ]
    if not missing:
        return {"supplemented": False}

    agent = SupplementAgent(llm, state["session_id"])
    # supplement_node can run before designer; create a minimal plan for missing images
    from app.models.edit_actions import MagazineEditPlan, SlideEditPlan, EditAction
    actions = []
    for img in missing:
        actions.append(EditAction(
            type="replace_image",
            target_selector=f".{img.id}",
            source_id=img.id,
        ))
    mini_plan = MagazineEditPlan(
        document_id="supplement_prep",
        template_id="",
        pages=[SlideEditPlan(page_number=img.page + 1, template_page="content", actions=[a]) for a, img in zip(actions, missing)],
    )
    await agent.supplement(doc, mini_plan)
    return {"supplemented": True}


@_track_phase("render")
async def renderer_node(state: PipelineState) -> dict:
    from app.agents.renderer_agent import RendererAgent
    from app.core.config import settings
    from app.core.recovery import RecoveryAction

    logger.info("pipeline.render.start", session_id=state["session_id"], output_format=state["output_format"])
    agent = RendererAgent()
    template_dir = Path(settings.MAGAZINE_TEMPLATES_DIR)
    output_dir = Path(settings.OUTPUT_DIR) / state["task_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
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
    except Exception as e:
        result = await _recovery_mgr.recover("renderer", e, state.get("task_id", ""))
        if result.action == RecoveryAction.RETRY:
            raise
        if result.action == RecoveryAction.DEGRADE and result.success:
            logger.warning("pipeline.render.degraded", fallback=result.fallback_used)
            msgs = list(state.get("recovery_messages", []))
            msgs.append(result.message)
            return {"output_path": "", "recovery_messages": msgs}
        raise


@_track_phase("verify")
async def fidelity_node(state: PipelineState) -> dict:
    from app.agents.quality_agent import QualityAgent
    from app.core.config import settings

    logger.info("pipeline.quality.start", session_id=state["session_id"])
    llm: LLMClient = state["llm"]
    skill: SkillDefinition | None = state.get("skill")

    threshold = settings.FIDELITY_THRESHOLD
    if skill and skill.fidelity_threshold is not None:
        threshold = skill.fidelity_threshold

    agent = QualityAgent(llm, threshold=threshold)
    result = await agent.verify(
        state["document"], state["edit_plan"],
        state.get("output_path", ""),
    )
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


@_track_phase("finalize")
async def finalize_node(state: PipelineState) -> dict:
    from app.core.config import settings

    llm: LLMClient = state["llm"]

    summary = {
        "output_path": state.get("output_path", ""),
        "fidelity_score": state.get("fidelity_score", 0),
        "fidelity_passed": state.get("fidelity_passed", False),
        "repair_count": state.get("repair_count", 0),
        "supplemented": state.get("supplemented", False),
        "skill": state.get("skill_name", "standard"),
        "usage": llm.get_usage_summary(),
    }

    output_dir = Path(settings.OUTPUT_DIR) / state["task_id"]
    summary_path = output_dir / "task_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    try:
        from app.core.metrics import record_pages, record_task_end
        doc = state.get("document")
        if doc:
            record_pages(doc.total_pages, state.get("output_format", "pdf"))
        record_task_end("completed")
    except Exception:
        pass

    return {}


def should_repair(state: PipelineState) -> str:
    if not state.get("fidelity_passed", False) and state.get("repair_count", 0) < 2:
        return "repair"
    return "finalize"


def _needs_supplement(state: PipelineState) -> str:
    """analyze 后决定是否启动 supplement 分支。"""
    doc = state.get("document")
    if not doc:
        return "design_only"
    missing = [
        img for img in doc.images
        if not img.local_path or not Path(img.local_path).exists()
    ]
    return "parallel" if missing else "design_only"


async def merge_node(state: PipelineState) -> dict:
    """合并 design 和 supplement 的结果，将补充素材合并到 edit_plan。"""
    doc = state["document"]
    plan = state.get("edit_plan")
    if not plan:
        return {}

    for img in doc.images:
        if img.local_path and Path(img.local_path).exists():
            continue
        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_image" and action.source_id == img.id:
                    if img.local_path and Path(img.local_path).exists():
                        break

    return {}


def build_magazine_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("plan", planner_node)
    graph.add_node("parse", parser_node)
    graph.add_node("analyze", analyzer_node)
    graph.add_node("design", designer_node)
    graph.add_node("supplement", supplement_node)
    graph.add_node("merge", merge_node)
    graph.add_node("render", renderer_node)
    graph.add_node("verify", fidelity_node)
    graph.add_node("repair", repair_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "parse")

    graph.add_conditional_edges(
        "parse",
        should_skip_analyzer,
        {"analyze": "analyze", "skip_to_design": "design"},
    )

    graph.add_conditional_edges(
        "analyze",
        _needs_supplement,
        {
            "parallel": "supplement",
            "design_only": "design",
        },
    )

    graph.add_edge("analyze", "design")
    graph.add_edge("supplement", "merge")
    graph.add_edge("design", "merge")
    graph.add_edge("merge", "render")
    graph.add_edge("render", "verify")

    graph.add_conditional_edges(
        "verify",
        should_repair,
        {"repair": "repair", "finalize": "finalize"},
    )

    graph.add_edge("repair", "verify")
    graph.add_edge("finalize", END)

    return graph.compile()
