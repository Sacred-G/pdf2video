"""
Video generation worker — wraps core/ pipeline with progress callbacks.
Runs in a ThreadPoolExecutor to avoid blocking the async event loop.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from rich.console import Console

from backend.config import settings
from backend.utils.progress import progress_manager
from backend.utils.storage import LocalStorage

console = Console()

# Shared thread pool for CPU-bound pipeline work
_executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)


def _run_pipeline_sync(
    job_id: uuid.UUID,
    source_type: str,
    title: str,
    job_settings: dict,
    pdf_path: Path | None,
    image_paths: list[Path],
    image_labels: list[str],
    music_path: Path | None,
    text_content: str | None,
    output_dir: Path,
) -> Path:
    """
    Synchronous pipeline execution — called inside a thread.
    Imports core/ modules here to keep them isolated from async context.
    """
    from core.config import Config

    # Apply per-job settings to core Config
    voice = job_settings.get("voice", "onyx")
    resolution = job_settings.get("resolution", "1920x1080")
    fps = job_settings.get("fps", 30)
    generate_backgrounds = job_settings.get("generate_backgrounds", True)
    output_mode = job_settings.get("output_mode", "video")

    w, h = (int(x) for x in resolution.split("x"))
    Config.VIDEO_WIDTH = w
    Config.VIDEO_HEIGHT = h
    Config.VIDEO_SIZE = (w, h)
    Config.VIDEO_FPS = fps
    Config.ensure_dirs()

    # Map pipeline status strings to frontend-compatible status codes
    step_to_status = {
        "Classifying images": "classifying",
        "Generating AI script": "scripting",
        "Generating AI voiceover": "voiceover",
        "Generating AI backgrounds": "backgrounds",
        "Composing video": "composing",
        "Exporting video": "exporting",
        "Planning slides": "scripting",
        "Generating slides": "composing",
        "Assembling PDF": "exporting",
        "Composing presentation": "composing",
    }

    def on_progress(step: str, pct: float):
        status = "composing"
        for keyword, s in step_to_status.items():
            if keyword.lower() in step.lower():
                status = s
                break
        progress_manager.update(job_id, status, step, pct)

    # ── Presentation Mode ─────────────────────────────────
    if output_mode in ("presentation", "both"):
        from core.presentation import PresentationPipeline

        pres_pipeline = PresentationPipeline()
        result = pres_pipeline.run(
            pdf_path=pdf_path,
            text_content=text_content,
            title=title,
            output_dir=output_dir,
            voice=voice,
            generate_video=True,
            generate_pdf=True,
            progress_callback=on_progress,
        )
        # Return the video path (PDF is also saved in output_dir)
        return result.video_path or result.pdf_path

    # ── Standard Video Mode ───────────────────────────────
    from core.content_input import content_from_pdf, content_from_text_and_images
    from core.pipeline import PDF2VideoPipeline

    pipeline = PDF2VideoPipeline()
    output_path = output_dir / f"{job_id}.mp4"

    if source_type == "pdf" and pdf_path:
        result = pipeline.run(
            pdf_path=pdf_path,
            output_path=output_path,
            background_music=str(music_path) if music_path else None,
            voice=voice,
            generate_backgrounds=generate_backgrounds,
            progress_callback=on_progress,
        )
    else:
        # Text + images workflow
        pil_images = []
        for p in image_paths:
            try:
                pil_images.append(Image.open(p).convert("RGB"))
            except Exception:
                pass

        content = content_from_text_and_images(
            title=title,
            text=text_content or "",
            images=pil_images,
            image_labels=image_labels,
        )

        result = pipeline.run_from_content(
            content=content,
            output_path=output_path,
            background_music=str(music_path) if music_path else None,
            voice=voice,
            generate_backgrounds=generate_backgrounds,
            progress_callback=on_progress,
        )

    return Path(result)


async def run_video_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    source_type: str,
    title: str,
    job_settings: dict,
    pdf_path: Path | None,
    image_paths: list[Path],
    image_labels: list[str],
    music_path: Path | None,
    text_content: str | None,
) -> Path:
    """
    Async entry point — dispatches the sync pipeline to a thread pool
    and updates progress/DB when done.
    """
    storage = LocalStorage()
    output_dir = settings.STORAGE_LOCAL_PATH / "temp" / str(job_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    progress_manager.register(job_id)
    progress_manager.update(job_id, "pending", "Starting...", 0.0)

    loop = asyncio.get_event_loop()

    try:
        result_path = await loop.run_in_executor(
            _executor,
            _run_pipeline_sync,
            job_id,
            source_type,
            title,
            job_settings,
            pdf_path,
            image_paths,
            image_labels,
            music_path,
            text_content,
            output_dir,
        )
        progress_manager.update(job_id, "completed", "Complete!", 1.0)
        return result_path

    except Exception as e:
        progress_manager.update(job_id, "failed", f"Error: {e}", 0.0)
        raise
