"""Mission queue with shared-state leasing — in-memory or Redis-backed.

Distributed workers need a shared queue so many workers can drive missions
without two of them running the same one. This provides that with a small
interface: `enqueue` (deduplicated), `claim` (pop + lease so it's in-flight for
exactly one worker), `complete` (drop the lease), and `release` (return it for
retry). `InMemoryQueue` is the default (CI-safe, single-process); `RedisQueue`
uses Redis sets/lists for cross-process coordination. `build_queue` picks Redis
when a URL is configured and the client is importable, else in-memory.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import deque


class MissionQueue(ABC):
    @abstractmethod
    async def enqueue(self, mission_id: int) -> None: ...
    @abstractmethod
    async def claim(self) -> int | None: ...
    @abstractmethod
    async def complete(self, mission_id: int) -> None: ...
    @abstractmethod
    async def release(self, mission_id: int) -> None: ...
    @abstractmethod
    async def size(self) -> int: ...
    @abstractmethod
    async def in_flight(self) -> int: ...


class InMemoryQueue(MissionQueue):
    def __init__(self) -> None:
        self._queue: deque[int] = deque()
        self._queued: set[int] = set()      # dedup: currently waiting
        self._inflight: set[int] = set()     # leased to a worker
        self._lock = asyncio.Lock()

    async def enqueue(self, mission_id: int) -> None:
        async with self._lock:
            if mission_id not in self._queued and mission_id not in self._inflight:
                self._queue.append(mission_id)
                self._queued.add(mission_id)

    async def claim(self) -> int | None:
        async with self._lock:
            if not self._queue:
                return None
            mid = self._queue.popleft()
            self._queued.discard(mid)
            self._inflight.add(mid)
            return mid

    async def complete(self, mission_id: int) -> None:
        async with self._lock:
            self._inflight.discard(mission_id)

    async def release(self, mission_id: int) -> None:
        async with self._lock:
            self._inflight.discard(mission_id)
            if mission_id not in self._queued:
                self._queue.append(mission_id)
                self._queued.add(mission_id)

    async def size(self) -> int:
        return len(self._queue)

    async def in_flight(self) -> int:
        return len(self._inflight)


class RedisQueue(MissionQueue):
    """Redis-backed queue: a list for order + sets for dedup/lease coordination."""

    def __init__(self, redis, key: str = "missions") -> None:
        self._r = redis
        self._list = key
        self._queued = f"{key}:queued"
        self._inflight = f"{key}:inflight"

    async def enqueue(self, mission_id: int) -> None:
        if await self._r.sismember(self._inflight, mission_id):
            return  # already leased to a worker -> don't double-queue
        if await self._r.sadd(self._queued, mission_id):  # newly added -> push
            await self._r.lpush(self._list, mission_id)

    async def claim(self) -> int | None:
        raw = await self._r.rpop(self._list)
        if raw is None:
            return None
        mid = int(raw)
        await self._r.srem(self._queued, mid)
        await self._r.sadd(self._inflight, mid)
        return mid

    async def complete(self, mission_id: int) -> None:
        await self._r.srem(self._inflight, mission_id)

    async def release(self, mission_id: int) -> None:
        await self._r.srem(self._inflight, mission_id)
        if await self._r.sadd(self._queued, mission_id):
            await self._r.lpush(self._list, mission_id)

    async def size(self) -> int:
        return int(await self._r.llen(self._list))

    async def in_flight(self) -> int:
        return int(await self._r.scard(self._inflight))


def build_queue(redis_url: str = "") -> MissionQueue:
    """Redis queue when a URL is set and the client imports; else in-memory."""
    if redis_url:
        try:
            import redis.asyncio as aioredis
            return RedisQueue(aioredis.from_url(redis_url))
        except Exception:
            pass
    return InMemoryQueue()
