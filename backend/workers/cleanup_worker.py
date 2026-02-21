"""
Periodic cleanup worker — removes old temp files and expired job artifacts.
Can be run as a cron job or scheduled task.
"""

import logging
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from backend.config import settings

logger = logging.getLogger(__name__)

# Temp files older than this are cleaned up
TEMP_MAX_AGE_HOURS = 24
# Failed/cancelled jobs older than this have their temp files removed
STALE_JOB_MAX_AGE_DAYS = 7


def cleanup_temp_files() -> int:
    """Remove temp directories older than TEMP_MAX_AGE_HOURS. Returns count removed."""
    temp_dir = settings.STORAGE_LOCAL_PATH / "temp"
    if not temp_dir.exists():
        return 0

    cutoff = time.time() - (TEMP_MAX_AGE_HOURS * 3600)
    removed = 0

    for item in temp_dir.iterdir():
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(item)
                    removed += 1
                    logger.info("Cleaned up temp dir: %s", item.name)
            except Exception as e:
                logger.warning("Failed to clean %s: %s", item, e)

    return removed


async def cleanup_stale_jobs() -> int:
    """Mark stale running jobs as failed and clean up their temp files."""
    from backend.db.session import async_session_factory
    from backend.models.job import Job

    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_JOB_MAX_AGE_DAYS)
    cleaned = 0

    async with async_session_factory() as session:
        # Find jobs stuck in processing states for too long
        result = await session.execute(
            select(Job).where(
                Job.status.in_(["pending", "classifying", "scripting", "voiceover", "backgrounds", "composing", "exporting"]),
                Job.created_at < cutoff,
            )
        )
        for job in result.scalars():
            job.status = "failed"
            job.error_message = "Job timed out after 7 days"
            job.completed_at = datetime.now(timezone.utc)
            cleaned += 1
            logger.info("Marked stale job %s as failed", job.id)

            # Clean up temp directory
            temp_path = settings.STORAGE_LOCAL_PATH / "temp" / str(job.id)
            if temp_path.exists():
                shutil.rmtree(temp_path, ignore_errors=True)

        await session.commit()

    return cleaned


def run_cleanup():
    """Synchronous entry point for running all cleanup tasks."""
    import asyncio

    logger.info("Starting cleanup...")
    temp_count = cleanup_temp_files()
    stale_count = asyncio.run(cleanup_stale_jobs())
    logger.info("Cleanup complete: %d temp dirs removed, %d stale jobs cleaned", temp_count, stale_count)
    return temp_count, stale_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cleanup()
