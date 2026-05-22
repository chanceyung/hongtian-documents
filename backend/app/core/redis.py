"""Redis 兼容层 — 桌面版用本地 KV 存储，服务器版用真实 Redis。

通过 DESKTOP_MODE 环境变量切换：
- True (默认): 使用 LocalKVStore (SQLite)，零外部依赖
- False: 使用真实 Redis 连接
"""
import os
from app.core.logging import get_logger

logger = get_logger(__name__)

DESKTOP_MODE = os.getenv("DESKTOP_MODE", "true").lower() in ("true", "1", "yes")


class _RedisCompat:
    """兼容 Redis 客户端接口的本地 KV 包装。"""

    def __init__(self):
        from app.core.kv_store import kv_store
        self._store = kv_store

    async def initialize(self):
        await self._store.initialize()

    async def close(self):
        await self._store.close()

    @property
    def available(self) -> bool:
        return True

    @property
    def client(self):
        return self._store


class _RedisReal:
    """真实 Redis 客户端（服务器部署用）。"""

    def __init__(self):
        import redis.asyncio as aioredis
        from app.core.config import settings
        self._client = None
        self._available = False
        self._url = settings.REDIS_URL

    async def initialize(self):
        import redis.asyncio as aioredis
        try:
            self._client = aioredis.from_url(
                self._url, decode_responses=True, socket_connect_timeout=5,
            )
            await self._client.ping()
            self._available = True
            logger.info("Redis connected", redis_url=self._url)
        except Exception as e:
            self._available = False
            logger.warning("Redis unavailable", error=str(e))

    async def close(self):
        if self._client:
            await self._client.close()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def client(self):
        if not self._client or not self._available:
            raise RuntimeError("Redis not available")
        return self._client


if DESKTOP_MODE:
    redis_client = _RedisCompat()
    logger.info("Desktop mode: using local KV store")
else:
    redis_client = _RedisReal()
    logger.info("Server mode: using Redis")