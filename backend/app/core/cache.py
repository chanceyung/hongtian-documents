"""解析结果缓存 — Redis 不可用时自动跳过"""
import hashlib
import json
from pathlib import Path

from app.core.redis import redis_client
from app.models.unified_document import UnifiedDocument


class ParseCache:
    TTL = 3600
    PREFIX = "parse_cache:"

    @staticmethod
    def _cache_key(file_path: Path) -> str:
        content_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
        stat = file_path.stat()
        return f"{ParseCache.PREFIX}{content_hash}_{stat.st_size}_{int(stat.st_mtime)}"

    @staticmethod
    async def get(file_path: Path) -> UnifiedDocument | None:
        if not redis_client.available:
            return None
        try:
            redis = redis_client.client
            key = ParseCache._cache_key(file_path)
            cached = await redis.get(key)
            if not cached:
                return None
            return UnifiedDocument.model_validate(json.loads(cached))
        except Exception:
            return None

    @staticmethod
    async def set(file_path: Path, doc: UnifiedDocument) -> None:
        if not redis_client.available:
            return
        try:
            redis = redis_client.client
            key = ParseCache._cache_key(file_path)
            await redis.set(key, doc.model_dump_json(), ex=ParseCache.TTL)
        except Exception:
            pass

    @staticmethod
    async def invalidate(file_path: Path) -> None:
        if not redis_client.available:
            return
        try:
            redis = redis_client.client
            key = ParseCache._cache_key(file_path)
            await redis.delete(key)
        except Exception:
            pass
