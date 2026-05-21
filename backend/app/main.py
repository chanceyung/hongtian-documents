"""杂志级文档重构智能体 - 后端主入口"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import api_router
from app.core.config import settings
from app.core.redis import redis_client
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.initialize()
    logger.info("服务启动: %s", settings.APP_NAME)
    yield
    await redis_client.close()
    logger.info("服务关闭")


app = FastAPI(
    title="杂志级文档重构智能体",
    description="将客户文档智能重构为杂志级精美的PDF/PPTX",
    version="4.0.0",
    lifespan=lifespan,
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}
