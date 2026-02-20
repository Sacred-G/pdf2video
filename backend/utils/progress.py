"""
In-process progress tracking for video generation jobs.
Uses an asyncio-safe dict + Event mechanism for SSE broadcasting.
When Redis is available, this can be swapped for Redis pub/sub.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class JobProgressState:
    status: str = "pending"
    step: str = "Queued"
    progress: float = 0.0
    event: asyncio.Event = field(default_factory=asyncio.Event)


class ProgressManager:
    """In-memory progress tracker. One instance shared across the app."""

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
            # Job not actively tracked — yield current DB state and stop
            yield self._format_event("progress", {"status": "unknown", "step": "Not found", "progress": 0})
            return

        # Yield current state immediately
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
                # Send keepalive
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


# Singleton
progress_manager = ProgressManager()
