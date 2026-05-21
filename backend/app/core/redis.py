"""Redis 客户端 - 用于会话级 API Key 临时存储"""
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._available = False

    async def initialize(self):
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._client.ping()
            self._available = True
            logger.info("Redis 连接成功: %s", settings.REDIS_URL)
        except Exception as e:
            self._available = False
            logger.warning("Redis 不可用 (%s)，部分功能受限", e)

    async def close(self):
        if self._client:
            await self._client.close()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def client(self) -> aioredis.Redis:
        if not self._client or not self._available:
            raise RuntimeError("Redis 不可用")
        return self._client


redis_client = RedisClient()
