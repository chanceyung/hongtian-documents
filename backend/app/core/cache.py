"""解析结果缓存 — 避免重复解析同一文件"""
import hashlib
import json
from pathlib import Path

from app.core.redis import redis_client
from app.models.unified_document import UnifiedDocument


class ParseCache:
    """基于 Redis 的解析结果缓存，TTL 1 小时"""

    TTL = 3600
    PREFIX = "parse_cache:"

    @staticmethod
    def _cache_key(file_path: Path) -> str:
        content_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
        stat = file_path.stat()
        return f"{ParseCache.PREFIX}{content_hash}_{stat.st_size}_{int(stat.st_mtime)}"

    @staticmethod
    async def get(file_path: Path) -> UnifiedDocument | None:
        redis = redis_client.client
        key = ParseCache._cache_key(file_path)
        cached = await redis.get(key)
        if not cached:
            return None

        data = json.loads(cached)
        return UnifiedDocument.model_validate(data)

    @staticmethod
    async def set(file_path: Path, doc: UnifiedDocument) -> None:
        redis = redis_client.client
        key = ParseCache._cache_key(file_path)
        await redis.set(key, doc.model_dump_json(), ex=ParseCache.TTL)

    @staticmethod
    async def invalidate(file_path: Path) -> None:
        redis = redis_client.client
        key = ParseCache._cache_key(file_path)
        await redis.delete(key)
