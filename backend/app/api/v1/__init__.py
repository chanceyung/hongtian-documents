import uuid
import json
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/magazine", tags=["Magazine"])

MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    ".pptx": [b"PK\x03\x04"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
    ".pdf": [b"%PDF"],
}

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
_MAX_ERROR_MESSAGE_LENGTH = 500


class GenerateRequest(BaseModel):
    task_id: str
    session_id: str = ""
    output_format: str = "pdf"
    template_id: str = "modern_tech"


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str = ""
    fidelity_score: float | None = None
    output_path: str | None = None


_tasks: dict[str, TaskStatus] = {}


def _get_task_dir(task_id: str) -> Path:
    return Path(settings.OUTPUT_DIR) / task_id


@router.post("/upload")
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

    _tasks[task_id] = TaskStatus(
        task_id=task_id, status="pending", progress=0.0,
    )

    background_tasks.add_task(_run_pipeline, task_id, file_path, session_id)
    return {"task_id": task_id, "status": "pending", "session_id": session_id}


def _validate_file_signature(content: bytes, ext: str, filename: str) -> None:
    """深度验证文件类型（检查魔数签名，防止扩展名伪造）"""
    if ext in {".md", ".txt"}:
        return

    signatures = MAGIC_SIGNATURES.get(ext)
    if not signatures:
        return

    header = content[:8]
    for sig in signatures:
        if header.startswith(sig):
            return

    if ext in {".pptx", ".docx", ".xlsx"} and header.startswith(b"PK\x03\x04"):
        return

    raise HTTPException(400, f"文件内容与扩展名 {ext} 不匹配: {filename}")


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/fidelity/{task_id}")
async def get_fidelity_report(task_id: str):
    task_dir = _get_task_dir(task_id)
    report_path = task_dir / "task_summary.json"
    if not report_path.exists():
        raise HTTPException(404, "保真报告尚未生成")
    return json.loads(report_path.read_text("utf-8"))


@router.get("/export/{task_id}")
async def export_file(task_id: str, format: str = "pdf"):
    task = _tasks.get(task_id)
    if not task or task.status != "completed":
        raise HTTPException(400, "文件尚未生成完成")

    task_dir = _get_task_dir(task_id)
    ext = "pdf" if format == "pdf" else "pptx"
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


@router.post("/generate")
async def generate_magazine(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    task = _tasks.get(req.task_id)
    if not task:
        raise HTTPException(404, "任务不存在，请先上传文件")

    if task.status not in ("pending", "failed"):
        raise HTTPException(400, f"任务状态为 {task.status}，无法重新生成")

    task_dir = _get_task_dir(req.task_id)
    source_files = list(task_dir.glob("source.*"))
    if not source_files:
        raise HTTPException(404, "源文件不存在")

    session_id = req.session_id or req.task_id
    task.status = "pending"
    task.progress = 0.0
    task.message = ""

    background_tasks.add_task(
        _run_pipeline,
        req.task_id,
        source_files[0],
        session_id,
        req.output_format,
        req.template_id,
    )
    return {"task_id": req.task_id, "status": "pending"}


async def _run_pipeline(
    task_id: str,
    file_path: Path,
    session_id: str,
    output_format: str = "pdf",
    template_id: str = "modern_tech",
):
    from app.workflow.magazine_pipeline import build_magazine_pipeline

    task = _tasks[task_id]

    try:
        pipeline = build_magazine_pipeline()
        task.status = "parsing"
        task.progress = 0.1

        result = await pipeline.ainvoke({
            "file_path": str(file_path),
            "session_id": session_id,
            "output_format": output_format,
            "template_id": template_id,
            "repair_count": 0,
        })

        task.status = "completed"
        task.progress = 1.0
        task.output_path = result.get("output_path", "")
        task.fidelity_score = result.get("fidelity_score", 0)

    except Exception as e:
        task.status = "failed"
        task.message = str(e)[:_MAX_ERROR_MESSAGE_LENGTH]
