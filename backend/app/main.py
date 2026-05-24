"""杂志级文档重构智能体 - 后端主入口"""
import asyncio
import os
import shutil
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.database import task_db
from app.core.logging import setup_logging, get_logger
from app.core.redis import redis_client, DESKTOP_MODE
from app.core.task_tracker import get_active_count, set_shutting_down
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware

setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await task_db.initialize()
    await redis_client.initialize()

    # 加载内置技能
    from app.skills.registry import skill_registry
    skill_registry.load_builtin_skills()
    if DESKTOP_MODE:
        logger.info("service.desktop_mode", storage="SQLite KV Store")
    else:
        logger.info("service.server_mode", storage="Redis")
    logger.info("service.started", app_name=settings.APP_NAME)
    yield
    set_shutting_down()
    logger.info("service.shutting_down", active_tasks=get_active_count())
    for _ in range(30):
        if get_active_count() == 0:
            break
        await asyncio.sleep(1)
    await task_db.close()
    await redis_client.close()
    logger.info("service.stopped")


app = FastAPI(
    title="弘天文档 API",
    summary="杂志级文档重构智能体",
    description="将 PPTX/PDF/Word/Excel/Markdown 文档智能重构为杂志级精美的 PDF 或 PPTX。\n\n"
               "## 工作流程\n"
               "1. **上传文件** — `POST /magazine/upload`\n"
               "2. **实时进度** — `GET /magazine/events/{task_id}` (SSE)\n"
               "3. **查询状态** — `GET /magazine/status/{task_id}`\n"
               "4. **下载结果** — `GET /magazine/export/{task_id}`\n"
               "5. **保真报告** — `GET /magazine/fidelity/{task_id}`\n\n"
               "## 前置条件\n"
               "使用前请先在设置页面配置智谱 API Key。",
    version="4.0.0",
    lifespan=lifespan,
    contact={"name": "弘天 AI"},
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


# ─── 桌面模式：托管前端静态文件（仅 PyInstaller 打包模式） ────────────────
if DESKTOP_MODE:
    import sys
    _static_dir = None
    if getattr(sys, 'frozen', False):
        _static_dir = Path(sys._MEIPASS) / "app" / "static"

    if _static_dir and _static_dir.exists() and (_static_dir / "index.html").exists():
        from fastapi.staticfiles import StaticFiles as _StaticFiles

        _next_dir = _static_dir / "_next"
        if _next_dir.exists():
            app.mount("/_next", _StaticFiles(directory=_next_dir), name="static-assets")
        for subdir in ["logo"]:
            sub_path = _static_dir / subdir
            if sub_path.exists():
                app.mount(f"/{subdir}", _StaticFiles(directory=sub_path), name=f"static-{subdir}")

        @app.get("/{page:path}")
        async def serve_frontend(page: str = ""):
            if not page or page == "/":
                html_path = _static_dir / "index.html"
            else:
                html_path = _static_dir / f"{page}.html"
                if not html_path.exists():
                    html_path = _static_dir / page / "index.html"
                if not html_path.exists():
                    html_path = _static_dir / "index.html"
            if html_path.exists():
                from fastapi.responses import FileResponse
                return FileResponse(html_path, media_type="text/html")
            from fastapi.responses import Response
            return Response(status_code=404)

        import threading
        def _open_browser():
            import time
            time.sleep(2)
            import webbrowser as _wb
            _wb.open(f"http://127.0.0.1:{settings.PORT}")
        threading.Thread(target=_open_browser, daemon=True).start()


@app.get("/health")
async def health():
    checks = {}

    if redis_client.available:
        checks["redis"] = {"status": "ok"}
    else:
        checks["redis"] = {"status": "unavailable"}

    try:
        await task_db.get_task("__health_check__")
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)[:100]}

    output_dir = Path(settings.OUTPUT_DIR)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
        checks["output_dir"] = {"status": "ok", "path": str(output_dir)}
    except Exception as e:
        checks["output_dir"] = {"status": "error", "detail": str(e)[:100]}

    try:
        disk_usage = shutil.disk_usage(str(output_dir))
        free_gb = disk_usage.free / (1024 ** 3)
        checks["disk"] = {
            "status": "ok" if free_gb > 1 else "warning",
            "free_gb": round(free_gb, 2),
            "total_gb": round(disk_usage.total / (1024 ** 3), 2),
        }
    except Exception as e:
        checks["disk"] = {"status": "error", "detail": str(e)[:100]}

    try:
        from app.services.llm_client import LLMClient
        llm = LLMClient(api_key="health-check", base_url="https://open.bigmodel.cn/api/paas/v4")
        checks["llm"] = {"status": "configured", "model": llm.model}
    except Exception as e:
        checks["llm"] = {"status": "error", "detail": str(e)[:100]}

    checks["active_tasks"] = get_active_count()

    all_ok = all(c.get("status") in ("ok", "unavailable", "configured") for c in checks.values() if isinstance(c, dict))
    has_degraded = any(isinstance(c, dict) and c.get("status") == "unavailable" for c in checks.values())

    if all_ok and not has_degraded:
        status = "ok"
    elif all_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return {"status": status, "version": "4.0.0", "checks": checks}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    from app.core.metrics import metrics_response
    return metrics_response()


# ─── 桌面打包模式入口 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    print("=" * 50)
    print("  弘天文档 v4.0 — 杂志级文档重构智能体")
    print("=" * 50)
    print(f"  后端地址: http://127.0.0.1:{port}")
    print(f"  按 Ctrl+C 退出")
    print("=" * 50)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )
