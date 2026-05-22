"""API Key 安全管理 - 临时存储在 Redis 会话中，不持久化"""
import hashlib
import base64

from cryptography.fernet import Fernet
from fastapi import HTTPException
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import httpx

from app.core.config import settings

router = APIRouter(prefix="/api-keys", tags=["API Key 管理"])


def _get_fernet() -> Fernet:
    key_material = settings.API_KEY_ENCRYPTION_KEY.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"hongtian-docs-v4",
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_material))
    return Fernet(key)


class ApiKeyConfig(BaseModel):
    session_id: str = Field(description="会话 ID")
    zhipu_api_key: Optional[str] = Field(default=None, description="智谱 API Key")
    zhipu_model: str = Field(default="glm-4-flash", description="智谱模型名称")
    zhipu_vision_key: Optional[str] = Field(default=None, description="智谱视觉 API Key")
    serpapi_key: Optional[str] = Field(default=None, description="SerpApi Key")
    flux_key: Optional[str] = Field(default=None, description="Flux API Key")
    flux_api_url: Optional[str] = Field(default=None, description="Flux API 地址")


class ApiKeyTestResult(BaseModel):
    valid: bool = Field(description="是否有效")
    message: str = Field(description="结果消息")
    details: Optional[str] = Field(default=None, description="详细信息")


def encrypt_key(key: str) -> str:
    return _get_fernet().encrypt(key.encode()).decode()


def decrypt_key(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


@router.post("/save", summary="保存 API Key", description="加密保存 API Key 到 Redis，24 小时自动过期。")
async def save_api_keys(config: ApiKeyConfig):
    from app.core.redis import redis_client

    if not redis_client.available:
        raise HTTPException(503, "Redis 不可用，无法保存 API Key")

    redis = redis_client.client
    key = f"api_keys:{config.session_id}"

    data = {}
    if config.zhipu_api_key:
        data["zhipu_key"] = encrypt_key(config.zhipu_api_key)
        data["zhipu_model"] = config.zhipu_model
    if config.zhipu_vision_key:
        data["zhipu_vision_key"] = encrypt_key(config.zhipu_vision_key)
    if config.serpapi_key:
        data["serpapi_key"] = encrypt_key(config.serpapi_key)
    if config.flux_key:
        data["flux_key"] = encrypt_key(config.flux_key)
        data["flux_api_url"] = config.flux_api_url or ""

    if not data:
        raise HTTPException(400, "至少需要配置一个 API Key")

    await redis.hset(key, mapping=data)
    await redis.expire(key, 86400)

    return {"status": "saved", "ttl": 86400}


@router.get("/status/{session_id}", summary="查询 Key 状态", description="检查指定会话是否已配置 API Key。")
async def get_key_status(session_id: str):
    from app.core.redis import redis_client

    redis = redis_client.client
    key = f"api_keys:{session_id}"
    exists = await redis.exists(key)
    if not exists:
        return {"configured": False}

    fields = await redis.hgetall(key)
    return {
        "configured": True,
        "has_zhipu": "zhipu_key" in fields,
        "zhipu_model": fields.get("zhipu_model", ""),
        "has_vision": "zhipu_vision_key" in fields,
        "has_serpapi": "serpapi_key" in fields,
        "has_flux": "flux_key" in fields,
        "ttl": await redis.ttl(key),
    }


@router.post("/test/zhipu", summary="测试智谱 Key", description="发送测试请求验证智谱 API Key 是否有效。")
async def test_zhipu_key(session_id: str):
    from app.core.redis import redis_client

    redis = redis_client.client
    key = f"api_keys:{session_id}"
    encrypted = await redis.hget(key, "zhipu_key")
    if not encrypted:
        raise HTTPException(400, "未配置智谱 API Key")

    api_key = decrypt_key(encrypted)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "glm-5-air",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
                timeout=30,
            )
        if resp.status_code == 200:
            return ApiKeyTestResult(valid=True, message="智谱 API Key 有效")
        else:
            return ApiKeyTestResult(
                valid=False,
                message=f"API 返回错误: {resp.status_code}",
                details=resp.text[:200],
            )
    except Exception as e:
        return ApiKeyTestResult(valid=False, message=f"连接失败: {str(e)}")


@router.delete("/{session_id}", summary="删除 Key", description="清除指定会话的所有 API Key。")
async def delete_api_keys(session_id: str):
    from app.core.redis import redis_client

    redis = redis_client.client
    await redis.delete(f"api_keys:{session_id}")
    return {"status": "deleted"}
