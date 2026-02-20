"""
Centralized configuration for PDF2Video.
Loads from .env and provides defaults optimized for RTX 5090 + Ryzen 9 9950X3D.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # ── OpenAI ──────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.2")
    OPENAI_TTS_MODEL: str = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    OPENAI_TTS_VOICE: str = os.getenv("OPENAI_TTS_VOICE", "onyx")
    OPENAI_IMAGE_MODEL: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

    # ── Video Output ────────────────────────────────────────
    VIDEO_WIDTH: int = int(os.getenv("VIDEO_WIDTH", "1920"))
    VIDEO_HEIGHT: int = int(os.getenv("VIDEO_HEIGHT", "1080"))
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", "30"))
    VIDEO_CODEC: str = os.getenv("VIDEO_CODEC", "h264_nvenc")
    VIDEO_BITRATE: str = os.getenv("VIDEO_BITRATE", "12M")
    VIDEO_SIZE: tuple = (VIDEO_WIDTH, VIDEO_HEIGHT)

    # ── Scene Timing (seconds) ──────────────────────────────
    MIN_SCENE_DURATION: float = 4.0
    MAX_SCENE_DURATION: float = 15.0
    TRANSITION_DURATION: float = 1.0
    TEXT_FADE_DURATION: float = 0.8

    # ── Ken Burns Effect ────────────────────────────────────
    KB_ZOOM_RANGE: tuple = (1.0, 1.25)  # start/end zoom
    KB_PAN_MAX: float = 0.08  # max pan as fraction of frame

    # ── Image Classification ─────────────────────────────────
    IMAGE_CLASSIFICATION_ENABLED: bool = True
    IMAGE_CLASSES: tuple = ("chart", "photo", "diagram", "table", "logo", "decorative")

    # ── Multi-Visual Composition ─────────────────────────────
    # Layout modes: carousel, split_screen, picture_in_picture, single
    CAROUSEL_CROSSFADE_DURATION: float = 0.6  # seconds for crossfade between carousel images
    PIP_SCALE: float = 0.30  # PiP inset size as fraction of frame width
    PIP_PADDING: int = 40  # pixels from corner for PiP inset
    PIP_CORNER_RADIUS: int = 16  # rounded corner radius for PiP card
    PIP_SHADOW_OFFSET: int = 6  # drop shadow offset in pixels
    SPLIT_SCREEN_GAP: int = 8  # pixel gap between split-screen panels
    CALLOUT_HOLD_EXTRA: float = 2.0  # extra seconds to hold on charts/diagrams
    TABLE_CARD_PADDING: int = 32  # padding inside table card
    LOGO_WATERMARK_SCALE: float = 0.10  # logo watermark size as fraction of frame width
    LOGO_WATERMARK_OPACITY: float = 0.35  # logo watermark opacity

    # ── Directories ─────────────────────────────────────────
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./output"))
    TEMP_DIR: Path = Path("./temp")

    # ── GPU / Performance ───────────────────────────────────
    # NVENC presets: p1(fastest) → p7(slowest/best quality)
    NVENC_PRESET: str = "p5"
    AUTO_TUNE_WORKERS: bool = _env_bool("AUTO_TUNE_WORKERS", True)
    # Number of threads for CPU-heavy render work.
    # Override with NUM_WORKERS env var when needed.
    NUM_WORKERS: int = int(os.getenv("NUM_WORKERS", str(min(24, os.cpu_count() or 8))))

    @classmethod
    def ensure_dirs(cls):
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not set. Copy .env.example to .env and add your key."
            )
        cls.ensure_dirs()
