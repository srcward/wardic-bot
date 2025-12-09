import asyncio
import time
from typing import Any, Optional, Dict
from collections import OrderedDict


class CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class Cache:
    MEMORY = "memory"

    def __init__(
        self, cache_type: str, namespace: str, ttl: int = 300, maxsize: int = 1000
    ):
        self.cache_type = cache_type
        self.namespace = namespace
        self.ttl = ttl
        self.maxsize = maxsize
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            expire_time = time.time() + (ttl if ttl is not None else self.ttl)

            if key in self._cache:
                del self._cache[key]

            self._cache[key] = CacheEntry(value, expire_time)

            while len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return default

            if entry.is_expired():
                del self._cache[key]
                return default

            self._cache.move_to_end(key)
            return entry.value

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from the cache."""
        async with self._lock:
            self._cache.clear()

    async def exists(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return False

            if entry.is_expired():
                del self._cache[key]
                return False

            return True

    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)

    async def cleanup_expired(self) -> int:
        async with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    async def get_all(self) -> Dict[str, Any]:
        async with self._lock:
            result = {}
            expired_keys = []

            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    result[key] = entry.value

            for key in expired_keys:
                del self._cache[key]

            return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def get_many(self, keys: list[str], default: Any = None) -> Dict[str, Any]:
        result = {}
        for key in keys:
            result[key] = await self.get(key, default)
        return result

    async def delete_pattern(self, pattern: str) -> int:
        async with self._lock:
            matching_keys = [k for k in self._cache.keys() if pattern in k]

            for key in matching_keys:
                del self._cache[key]

            return len(matching_keys)
