import uuid
import json
import re
import shutil
import asyncio
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import task_db
from app.core.task_tracker import start_task, end_task

router = APIRouter(prefix="/magazine", tags=["Magazine"])

MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    ".pptx": [b"PK\x03\x04"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
    ".pdf": [b"%PDF"],
}

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
_MAX_ERROR_MESSAGE_LENGTH = 500


def _validate_task_id(task_id: str) -> None:
    """Validate task_id is safe (no path traversal)."""
    if not task_id or len(task_id) > 64:
        raise HTTPException(400, "Invalid task ID")
    # Block path traversal attempts
    if "/" in task_id or "\\" in task_id or ".." in task_id:
        raise HTTPException(400, "Invalid task ID")


class GenerateRequest(BaseModel):
    task_id: str = Field(description="任务 ID")
    session_id: str = Field(default="", description="会话 ID")
    output_format: str = Field(default="pdf", description="输出格式：pdf 或 pptx")
    template_id: str = Field(default="modern_tech", description="模板 ID")
    skill: str = Field(default="", description="技能名称，如 standard/data-focus/briefing/academic")


class TaskStatus(BaseModel):
    task_id: str = Field(description="任务 ID")
    status: str = Field(description="任务状态")
    progress: float = Field(description="进度百分比")
    message: str = Field(default="", description="状态消息")
    fidelity_score: float | None = Field(default=None, description="保真得分")
    output_path: str | None = Field(default=None, description="输出文件路径")


def _get_task_dir(task_id: str) -> Path:
    return Path(settings.OUTPUT_DIR) / task_id


def _sanitize_filename(name: str) -> str:
    """Remove path traversal and dangerous characters from filename."""
    name = Path(name).name  # strip any path components
    name = re.sub(r'[^\w.\-]', '_', name)
    if len(name) > 200:
        stem = Path(name).stem[:180]
        suffix = Path(name).suffix
        name = stem + suffix
    return name


@router.post("/upload", summary="上传文档", description="上传 PPTX/PDF/DOCX/XLSX/MD/TXT 文件，创建转换任务。文件大小限制 100MB。")
async def upload_document(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
):
    allowed = {".pptx", ".pdf", ".docx", ".xlsx", ".md", ".txt"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"不支持的格式: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"文件超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    _validate_file_signature(content, ext, file.filename or "unknown")

    task_id = str(uuid.uuid4())
    task_dir = _get_task_dir(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    file_path = task_dir / f"source{ext}"
    file_path.write_bytes(content)

    session_id = request.query_params.get("session_id") or request.headers.get("X-Session-ID") or task_id
    skill_name = request.query_params.get("skill", "") or ""

    await task_db.create_task(
        task_id, session_id=session_id, source_file=str(file_path),
    )

    return {"task_id": task_id, "status": "pending", "session_id": session_id}


def _validate_file_signature(content: bytes, ext: str, filename: str) -> None:
    if ext in {".md", ".txt"}:
        return

    signatures = MAGIC_SIGNATURES.get(ext)
    if not signatures:
        return

    header = content[:8]
    if any(header.startswith(sig) for sig in signatures):
        return

    raise HTTPException(400, f"文件内容与扩展名 {ext} 不匹配: {filename}")


@router.get("/status/{task_id}", response_model=TaskStatus, summary="查询任务状态", description="获取指定任务的当前状态、进度和消息。")
async def get_status(task_id: str):
    _validate_task_id(task_id)
    task = await task_db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/tasks", summary="任务列表", description="获取任务列表，支持按 session_id 过滤。")
async def list_tasks(session_id: str = "", limit: int = 50):
    return await task_db.list_tasks(session_id, limit)


@router.get("/events/{task_id}", summary="实时事件流", description="SSE 端点，实时推送任务状态变化。任务完成或失败时自动关闭。")
async def task_events(task_id: str):
    _validate_task_id(task_id)
    task = await task_db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    async def event_stream():
        last_status = None
        last_progress = None
        idle_ticks = 0
        while idle_ticks < 600:
            task = await task_db.get_task(task_id)
            if not task:
                break

            status = task["status"]
            progress = task["progress"]

            if status != last_status or progress != last_progress:
                data = json.dumps({
                    "status": status,
                    "progress": progress,
                    "message": task.get("message", ""),
                    "fidelity_score": task.get("fidelity_score"),
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
                last_status = status
                last_progress = progress
                idle_ticks = 0
            else:
                idle_ticks += 1

            if status in ("completed", "failed"):
                yield f"data: {json.dumps({'status': status, 'progress': progress, 'done': True})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/tasks/{task_id}", summary="删除任务", description="删除指定任务及其关联文件。正在处理的任务无法删除。")
async def delete_task(task_id: str):
    _validate_task_id(task_id)
    task = await task_db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    if task["status"] not in ("completed", "failed", "pending"):
        raise HTTPException(400, "任务正在处理中，无法删除")

    task_dir = _get_task_dir(task_id)
    if task_dir.exists():
        import shutil
        shutil.rmtree(task_dir, ignore_errors=True)

    await task_db.delete_task(task_id)
    return {"status": "deleted", "task_id": task_id}


@router.get("/fidelity/{task_id}", summary="保真报告", description="获取保真校验报告，包含指纹完整性、图文关联和语义保真得分。")
async def get_fidelity_report(task_id: str):
    _validate_task_id(task_id)
    task = await task_db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    task_dir = _get_task_dir(task_id)
    report_path = task_dir / "task_summary.json"
    if not report_path.exists():
        raise HTTPException(404, "保真报告尚未生成")

    report = json.loads(report_path.read_text("utf-8"))
    report["task_status"] = task["status"]
    report["fidelity_score"] = task.get("fidelity_score")
    return report


@router.get("/export/{task_id}", summary="下载结果", description="下载生成的 PDF 或 PPTX 文件。任务必须已完成。")
async def export_file(task_id: str, format: str = "pdf"):
    _validate_task_id(task_id)
    task = await task_db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task["status"] != "completed":
        raise HTTPException(400, f"任务状态为 {task['status']}，文件尚未生成完成")

    # Try to find output from task record first, then fallback to conventional path
    output_path = task.get("output_path", "")
    if output_path:
        candidate = Path(output_path)
        if candidate.exists():
            ext = candidate.suffix.lstrip(".")
            media_type = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            return FileResponse(candidate, media_type=media_type, filename=f"magazine_{task_id[:8]}.{ext}")

    # Fallback to conventional path
    task_dir = _get_task_dir(task_id)
    format = format.lower()
    if format not in ("pdf", "pptx"):
        format = "pdf"
    ext = format
    file_path = task_dir / f"magazine.{ext}"

    if not file_path.exists():
        raise HTTPException(404, "输出文件不存在")

    media_type = "application/pdf" if ext == "pdf" else (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=f"magazine_{task_id[:8]}.{ext}",
    )


@router.post("/generate", summary="重新生成", description="使用不同的模板或格式重新生成杂志。仅对 pending 或 failed 状态的任务有效。")
async def generate_magazine(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    task = await task_db.get_task(req.task_id)
    if not task:
        raise HTTPException(404, "任务不存在，请先上传文件")

    if task["status"] not in ("pending", "failed"):
        raise HTTPException(400, f"任务状态为 {task['status']}，无法重新生成")

    task_dir = _get_task_dir(req.task_id)
    source_files = list(task_dir.glob("source.*"))
    if not source_files:
        raise HTTPException(404, "源文件不存在")

    session_id = req.session_id or req.task_id
    await task_db.update_task(
        req.task_id, status="pending", progress=0.0, message="",
        output_format=req.output_format, template_id=req.template_id,
    )

    background_tasks.add_task(
        _run_pipeline,
        req.task_id,
        source_files[0],
        session_id,
        req.output_format,
        req.template_id,
        skill_name=req.skill,
    )
    return {"task_id": req.task_id, "status": "pending"}


@router.get("/skills", summary="可用技能列表", description="返回所有可用的文档处理技能及其参数配置。")
async def list_skills():
    from app.skills.registry import skill_registry
    return [s.model_dump() for s in skill_registry.list_all()]


@router.post("/cleanup", summary="清理旧任务", description="删除超过指定天数的旧任务及其关联文件。默认 7 天。")
async def cleanup_old_tasks(days: int = 7):
    deleted_count = await task_db.delete_old_tasks(days)
    cleaned_dirs = 0
    output_dir = Path(settings.OUTPUT_DIR)
    if output_dir.exists():
        import time
        cutoff = time.time() - (days * 86400)
        for task_dir in output_dir.iterdir():
            if task_dir.is_dir() and task_dir.stat().st_mtime < cutoff:
                shutil.rmtree(task_dir, ignore_errors=True)
                cleaned_dirs += 1
    return {"deleted_db_tasks": deleted_count, "cleaned_dirs": cleaned_dirs}


async def _run_pipeline(
    task_id: str,
    file_path: Path,
    session_id: str,
    output_format: str = "pdf",
    template_id: str = "modern_tech",
    skill_name: str = "",
):
    if not start_task():
        return

    try:
        from app.workflow.magazine_pipeline import (
            parser_node, analyzer_node, designer_node,
            check_missing_assets_node, supplement_node,
            renderer_node, fidelity_node, repair_node,
            finalize_node, should_repair,
        )
        from app.workflow.magazine_pipeline import _get_api_key
        from app.services.llm_client import LLMClient
        from app.skills.registry import skill_registry

        # 创建统一 LLM 客户端
        api_key = await _get_api_key(session_id)
        llm = LLMClient(
            api_key=api_key,
            base_url=settings.CUSTOM_LLM_URL,
            model=settings.CUSTOM_MODEL,
        )

        # 加载技能
        skill = skill_registry.get(skill_name) if skill_name else None
        if not skill:
            skill = skill_registry.get_default()

        state: dict = {
            "file_path": str(file_path),
            "task_id": task_id,
            "session_id": session_id,
            "output_format": output_format,
            "template_id": template_id,
            "repair_count": 0,
            "llm": llm,
            "skill_name": skill.name,
            "skill": skill,
        }

        # Step 1: Parse
        await task_db.update_task(task_id, status="parsing", progress=0.05)
        state.update(await parser_node(state))

        # Step 2: Analyze
        await task_db.update_task(task_id, status="analyzing", progress=0.20)
        state.update(await analyzer_node(state))

        # Step 3: Design
        await task_db.update_task(task_id, status="designing", progress=0.40)
        state.update(await designer_node(state))

        # Step 4: Supplement (conditional)
        branch = await check_missing_assets_node(state)
        if branch == "supplement":
            await task_db.update_task(task_id, status="supplementing", progress=0.55)
            state.update(await supplement_node(state))

        # Step 5: Render
        await task_db.update_task(task_id, status="rendering", progress=0.65)
        state.update(await renderer_node(state))

        # Step 6: Verify fidelity
        await task_db.update_task(task_id, status="verifying", progress=0.80)
        state.update(await fidelity_node(state))

        # Step 7: Repair loop (max 2)
        for i in range(2):
            action = should_repair(state)
            if action == "finalize":
                break
            state.update(await repair_node(state))
            await task_db.update_task(task_id, status="repairing", progress=0.85 + i * 0.05)
            state.update(await fidelity_node(state))

        # Step 8: Finalize
        await task_db.update_task(task_id, status="finalizing", progress=0.95)
        state.update(await finalize_node(state))

        await task_db.update_task(
            task_id,
            status="completed",
            progress=1.0,
            output_path=state.get("output_path", ""),
            fidelity_score=state.get("fidelity_score", 0),
        )

    except asyncio.TimeoutError:
        await task_db.update_task(
            task_id,
            status="failed",
            message="Pipeline execution timed out (10 min limit)",
        )
    except Exception as e:
        await task_db.update_task(
            task_id,
            status="failed",
            message=str(e)[:_MAX_ERROR_MESSAGE_LENGTH],
        )
    finally:
        end_task()