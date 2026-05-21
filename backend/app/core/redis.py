"""Redis 客户端 - 用于会话级 API Key 临时存储"""
import redis.asyncio as redis
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self._client: redis.Redis | None = None

    async def initialize(self):
        self._client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

    async def close(self):
        if self._client:
            await self._client.close()

    @property
    def client(self) -> redis.Redis:
        assert self._client is not None, "Redis not initialized"
        return self._client


redis_client = RedisClient()
