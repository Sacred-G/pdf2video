"""
Progress tracking for video generation jobs.

Uses Redis pub/sub when available for scalable multi-worker broadcasting.
Falls back to an in-process asyncio Event mechanism when Redis is unavailable.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


# ── Redis-backed implementation ──────────────────────────────────────

class RedisProgressManager:
    """
    Progress tracker backed by Redis pub/sub + hash storage.
    Supports multiple workers and multiple SSE subscribers.
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def _channel(self, job_id: uuid.UUID) -> str:
        return f"job:{job_id}:progress"

    def _hash_key(self, job_id: uuid.UUID) -> str:
        return f"job:{job_id}:state"

    def register(self, job_id: uuid.UUID) -> None:
        # No-op for Redis — state is created on first update
        pass

    def update(self, job_id: uuid.UUID, status: str, step: str, progress: float) -> None:
        """
        Synchronous update — safe to call from worker threads.
        Uses a sync Redis client to publish + store state.
        """
        import redis as sync_redis
        r = sync_redis.from_url(self._redis_url, decode_responses=True)
        data = {"status": status, "step": step, "progress": progress}
        r.hset(self._hash_key(job_id), mapping=data)
        r.publish(self._channel(job_id), json.dumps(data))
        # Auto-expire state hash after 1 hour
        r.expire(self._hash_key(job_id), 3600)
        r.close()

    def get_sync(self, job_id: uuid.UUID) -> dict | None:
        import redis as sync_redis
        r = sync_redis.from_url(self._redis_url, decode_responses=True)
        data = r.hgetall(self._hash_key(job_id))
        r.close()
        if not data:
            return None
        return {
            "status": data.get("status", "unknown"),
            "step": data.get("step", ""),
            "progress": float(data.get("progress", 0)),
        }

    def remove(self, job_id: uuid.UUID) -> None:
        import redis as sync_redis
        r = sync_redis.from_url(self._redis_url, decode_responses=True)
        r.delete(self._hash_key(job_id))
        r.close()

    async def subscribe(self, job_id: uuid.UUID) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted progress events via Redis pub/sub."""
        r = await self._get_redis()

        # Yield current state from hash immediately
        state = await r.hgetall(self._hash_key(job_id))
        if state:
            yield self._format_event("progress", {
                "status": state.get("status", "unknown"),
                "step": state.get("step", ""),
                "progress": float(state.get("progress", 0)),
            })
            if state.get("status") in ("completed", "failed", "cancelled"):
                return
        else:
            yield self._format_event("progress", {"status": "pending", "step": "Queued", "progress": 0})

        # Subscribe to channel for live updates
        pubsub = r.pubsub()
        await pubsub.subscribe(self._channel(job_id))

        try:
            while True:
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=30.0,
                )
                if msg is None:
                    # Keepalive
                    yield ": keepalive\n\n"
                    continue

                if msg["type"] == "message":
                    data = json.loads(msg["data"])
                    yield self._format_event("progress", data)
                    if data.get("status") in ("completed", "failed", "cancelled"):
                        break
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"
        finally:
            await pubsub.unsubscribe(self._channel(job_id))
            await pubsub.aclose()

    @staticmethod
    def _format_event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# ── In-memory fallback ───────────────────────────────────────────────

@dataclass
class JobProgressState:
    status: str = "pending"
    step: str = "Queued"
    progress: float = 0.0
    event: asyncio.Event = field(default_factory=asyncio.Event)


class InMemoryProgressManager:
    """In-memory progress tracker — single-process fallback."""

    def __init__(self):
        self._jobs: dict[uuid.UUID, JobProgressState] = {}

    def register(self, job_id: uuid.UUID) -> None:
        self._jobs[job_id] = JobProgressState()

    def update(self, job_id: uuid.UUID, status: str, step: str, progress: float) -> None:
        state = self._jobs.get(job_id)
        if state is None:
            state = JobProgressState()
            self._jobs[job_id] = state
        state.status = status
        state.step = step
        state.progress = progress
        state.event.set()

    def get(self, job_id: uuid.UUID) -> JobProgressState | None:
        return self._jobs.get(job_id)

    def remove(self, job_id: uuid.UUID) -> None:
        self._jobs.pop(job_id, None)

    async def subscribe(self, job_id: uuid.UUID) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted progress events until job completes/fails."""
        state = self._jobs.get(job_id)
        if state is None:
            yield self._format_event("progress", {"status": "unknown", "step": "Not found", "progress": 0})
            return

        yield self._format_event("progress", {
            "status": state.status,
            "step": state.step,
            "progress": state.progress,
        })

        while True:
            state.event.clear()
            try:
                await asyncio.wait_for(state.event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue

            yield self._format_event("progress", {
                "status": state.status,
                "step": state.step,
                "progress": state.progress,
            })

            if state.status in ("completed", "failed", "cancelled"):
                break

    @staticmethod
    def _format_event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# ── Singleton factory ────────────────────────────────────────────────

def _create_progress_manager() -> RedisProgressManager | InMemoryProgressManager:
    """Try Redis first; fall back to in-memory if unavailable."""
    from backend.config import settings

    if settings.REDIS_URL:
        try:
            import redis as sync_redis
            r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            r.ping()
            r.close()
            logger.info("Progress manager: using Redis at %s", settings.REDIS_URL)
            return RedisProgressManager(settings.REDIS_URL)
        except Exception as e:
            logger.warning("Redis unavailable (%s), falling back to in-memory progress", e)

    logger.info("Progress manager: using in-memory fallback")
    return InMemoryProgressManager()


progress_manager = _create_progress_manager()
