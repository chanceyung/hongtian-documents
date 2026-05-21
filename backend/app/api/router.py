"""API Key 安全管理 - 临时存储在 Redis 会话中，不持久化"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from cryptography.fernet import Fernet
import hashlib
import httpx

from app.core.redis import redis_client
from app.core.config import settings

router = APIRouter(prefix="/api-keys", tags=["API Key 管理"])

# 会话级加密
_fernet = Fernet(Fernet.generate_key())


class ApiKeyConfig(BaseModel):
    session_id: str
    zhipu_api_key: Optional[str] = None
    zhipu_model: str = "glm-5-pro"  # glm-5-air, glm-5-pro, glm-5-ultra
    zhipu_vision_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    flux_key: Optional[str] = None
    flux_api_url: Optional[str] = None


class ApiKeyTestResult(BaseModel):
    valid: bool
    message: str
    details: Optional[str] = None


def _encrypt_key(key: str) -> str:
    return _fernet.encrypt(key.encode()).decode()


def _decrypt_key(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8]


@router.post("/save")
async def save_api_keys(config: ApiKeyConfig):
    """保存 API Key 到 Redis 会话，设置 24 小时过期"""
    redis = redis_client.client
    key = f"api_keys:{config.session_id}"

    data = {}
    if config.zhipu_api_key:
        data["zhipu_key"] = _encrypt_key(config.zhipu_api_key)
        data["zhipu_model"] = config.zhipu_model
    if config.zhipu_vision_key:
        data["zhipu_vision_key"] = _encrypt_key(config.zhipu_vision_key)
    if config.serpapi_key:
        data["serpapi_key"] = _encrypt_key(config.serpapi_key)
    if config.flux_key:
        data["flux_key"] = _encrypt_key(config.flux_key)
        data["flux_api_url"] = config.flux_api_url or ""

    if not data:
        raise HTTPException(400, "至少需要配置一个 API Key")

    await redis.hset(key, mapping=data)
    await redis.expire(key, 86400)  # 24 小时过期

    return {"status": "saved", "ttl": 86400}


@router.get("/status/{session_id}")
async def get_key_status(session_id: str):
    """检查 API Key 配置状态（不返回密钥本身）"""
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


@router.post("/test/zhipu")
async def test_zhipu_key(session_id: str):
    """测试智谱 API Key 是否有效"""
    redis = redis_client.client
    key = f"api_keys:{session_id}"
    encrypted = await redis.hget(key, "zhipu_key")
    if not encrypted:
        raise HTTPException(400, "未配置智谱 API Key")

    api_key = _decrypt_key(encrypted)
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


@router.delete("/{session_id}")
async def delete_api_keys(session_id: str):
    """删除会话 API Key"""
    redis = redis_client.client
    await redis.delete(f"api_keys:{session_id}")
    return {"status": "deleted"}
