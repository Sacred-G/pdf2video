"""
Video Composer — Assembles scenes into a cinematic video.
Handles scene rendering, audio synchronization, transitions, and
GPU-accelerated export via NVENC on RTX 5090.
"""

import random
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    concatenate_videoclips,
    vfx,
)
from rich.console import Console
from tqdm import tqdm

from .ai_services import SceneScript, VideoScript
from .config import Config
from .content_input import ContentImage, ContentInput
from .effects import (
    apply_vignette,
    black_frame,
    color_grade,
    crossfade,
    fit_image_to_frame,
    ken_burns_frame,
    render_callout_overlay,
    render_logo_watermark,
    render_picture_in_picture,
    render_split_screen,
    render_table_card,
    render_text_overlay,
    text_opacity_at_time,
)

console = Console()


class VideoComposer:
    """Composes cinematic video from script, visuals, and audio."""

    def __init__(self):
        Config.ensure_dirs()
        self.fps = Config.VIDEO_FPS
        self.size = Config.VIDEO_SIZE
        self.transition_dur = Config.TRANSITION_DURATION

    # ── Main Composition Pipeline ───────────────────────────

    def compose(
        self,
        script: VideoScript,
        content: ContentInput,
        audio_paths: list[Path],
        ai_backgrounds: dict[int, Path],
        output_path: Path,
        background_music_path: Path | None = None,
    ) -> Path:
        """Full video composition pipeline."""
        console.print("\n[bold blue]🎬 Composing video...[/]")
        scene_clips: list[VideoClip] = []
        final_video: VideoClip | None = None

        try:
            # Gather logo images once for watermark use across all scenes
            logo_images = self._gather_logo_images(content)
            if logo_images:
                console.print(f"  🏷️  {len(logo_images)} logo(s) will be used as watermarks")

            # 1. Build scene clips
            for i, scene in enumerate(script.scenes):
                layout_tag = f" [{scene.layout_mode}]" if scene.layout_mode != "single" else ""
                console.print(f"  Rendering scene {scene.scene_number}/{len(script.scenes)}{layout_tag}...")
                audio_path = audio_paths[i] if i < len(audio_paths) else None
                clip = self._build_scene_clip(
                    scene=scene,
                    content=content,
                    audio_path=audio_path,
                    ai_background=ai_backgrounds.get(scene.scene_number),
                    logo_images=logo_images,
                )
                scene_clips.append(clip)

            # 2. Add intro
            intro_clip = self._build_title_card(
                script.intro_text or script.title,
                duration=3.5,
                is_intro=True,
            )
            scene_clips.insert(0, intro_clip)

            # 3. Add outro
            outro_clip = self._build_title_card(
                script.outro_text or "Thank you for watching",
                duration=3.0,
                is_intro=False,
            )
            scene_clips.append(outro_clip)

            # 4. Apply crossfade transitions between all clips
            console.print("  Applying transitions...")
            final_clips = self._apply_transitions(scene_clips)

            # 5. Concatenate
            console.print("  Concatenating clips...")
            final_video = concatenate_videoclips(final_clips, method="compose")

            # 6. Add background music if provided
            if background_music_path and background_music_path.exists():
                final_video = self._add_background_music(final_video, background_music_path)

            # 7. Export with GPU acceleration
            console.print("[bold blue]📹 Exporting video (GPU-accelerated)...[/]")
            self._export_gpu(final_video, output_path)

            console.print(f"[bold green]✓ Video saved:[/] {output_path}")
            return output_path
        finally:
            for clip in scene_clips:
                try:
                    clip.close()
                except Exception:
                    pass
            if final_video is not None:
                try:
                    final_video.close()
                except Exception:
                    pass

    # ── Scene Clip Builder ──────────────────────────────────

    def _build_scene_clip(
        self,
        scene: SceneScript,
        content: ContentInput,
        audio_path: Path | None,
        ai_background: Path | None,
        logo_images: list[ContentImage] | None = None,
    ) -> VideoClip:
        """Build a complete scene clip with classification-aware composition.
        Routes through layout modes: single, carousel, split_screen, picture_in_picture.
        Applies classification-specific rendering (table cards, chart callouts, logo watermarks)."""

        # Determine scene duration from audio
        duration = scene.duration_hint
        audio_clip = None
        if audio_path and audio_path.exists():
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration + 0.5  # small padding
            duration = max(duration, Config.MIN_SCENE_DURATION)

        # Gather visual assets for this scene (as ContentImage with classification)
        visuals = self._gather_scene_visuals(scene, content, ai_background)

        if not visuals:
            visuals = [ContentImage(
                image=Image.new("RGB", self.size, (20, 20, 30)),
                classification="decorative",
            )]

        # Separate visuals by classification for smart composition
        tables = [v for v in visuals if v.classification == "table"]
        charts_diagrams = [v for v in visuals if v.classification in ("chart", "diagram")]
        photos = [v for v in visuals if v.is_full_bleed]
        data_visuals = [v for v in visuals if v.is_data_visual]

        # Determine effective layout mode
        layout = scene.layout_mode
        # Auto-correct layout if visuals don't support it
        if layout == "split_screen" and len(visuals) < 2:
            layout = "single"
        if layout == "carousel" and len(visuals) < 2:
            layout = "single"

        # Prepare images for Ken Burns (non-table, non-logo visuals)
        kb_visuals = [v for v in visuals if v.classification != "table"]
        if not kb_visuals:
            kb_visuals = visuals  # fallback

        kb_images = [fit_image_to_frame(v.image, self.size, overscan=1.35) for v in kb_visuals]
        num_visuals = len(kb_images)

        # Generate unique Ken Burns params per visual
        kb_params = []
        for v in kb_visuals:
            if v.is_data_visual:
                # Charts/diagrams: slow zoom in, minimal pan (focus on content)
                kb_params.append({
                    "zoom_start": 1.0,
                    "zoom_end": 1.12,
                    "pan_x": random.uniform(-0.02, 0.02),
                    "pan_y": random.uniform(-0.02, 0.02),
                })
            else:
                # Photos/decorative: standard cinematic Ken Burns
                zs = random.uniform(1.0, 1.1)
                ze = random.uniform(1.15, 1.3)
                if random.random() > 0.5:
                    zs, ze = ze, zs
                kb_params.append({
                    "zoom_start": zs,
                    "zoom_end": ze,
                    "pan_x": random.uniform(-Config.KB_PAN_MAX, Config.KB_PAN_MAX),
                    "pan_y": random.uniform(-Config.KB_PAN_MAX, Config.KB_PAN_MAX),
                })

        # Build frame generator based on layout mode
        narration_text = scene.narration
        scene_dur = duration
        xfade = min(Config.CAROUSEL_CROSSFADE_DURATION,
                     scene_dur / (num_visuals * 4)) if num_visuals > 1 else 0
        logo_list = logo_images or []

        # For PiP: identify the background and inset
        pip_bg_idx = 0
        pip_inset_ci = None
        if layout == "picture_in_picture" and len(visuals) >= 1:
            # Background = AI-generated or first photo; inset = first chart/diagram/figure
            bg_candidates = [i for i, v in enumerate(kb_visuals) if v.source == "ai_generated" or v.is_full_bleed]
            inset_candidates = [v for v in visuals if v.is_data_visual]
            if bg_candidates:
                pip_bg_idx = bg_candidates[0]
            if inset_candidates:
                pip_inset_ci = inset_candidates[0]
            elif visuals:
                # Fallback: use first non-background visual as inset
                non_bg = [v for v in visuals if v.source != "ai_generated"]
                if non_bg:
                    pip_inset_ci = non_bg[0]

        # For split-screen: identify left and right
        split_left_idx = 0
        split_right_idx = min(1, num_visuals - 1)

        def make_frame(t):
            progress = t / scene_dur if scene_dur > 0 else 0

            # ── Layout: Single ──────────────────────────────
            if layout == "single":
                # Check if the primary visual is a table → render as card
                if tables and kb_visuals[0].classification == "table":
                    frame = render_table_card(tables[0].image, self.size)
                else:
                    p = kb_params[0]
                    frame = ken_burns_frame(
                        kb_images[0], progress, self.size, **p,
                    )

            # ── Layout: Carousel ────────────────────────────
            elif layout == "carousel":
                segment_dur = scene_dur / num_visuals
                raw_idx = t / segment_dur
                idx_a = int(raw_idx) % num_visuals
                idx_b = (idx_a + 1) % num_visuals
                local_t = raw_idx - int(raw_idx)
                local_progress = local_t

                # Check if current visual is a table
                if kb_visuals[idx_a].classification == "table":
                    frame_a = render_table_card(kb_visuals[idx_a].image, self.size)
                else:
                    frame_a = ken_burns_frame(
                        kb_images[idx_a], local_progress, self.size, **kb_params[idx_a],
                    )

                # Crossfade zone at end of each segment
                xfade_start = 1.0 - (xfade / segment_dur) if segment_dur > 0 else 1.0
                if local_t >= xfade_start and idx_b != idx_a:
                    blend = (local_t - xfade_start) / (1.0 - xfade_start) if xfade_start < 1.0 else 0
                    if kb_visuals[idx_b].classification == "table":
                        frame_b = render_table_card(kb_visuals[idx_b].image, self.size)
                    else:
                        frame_b = ken_burns_frame(
                            kb_images[idx_b], 0.0, self.size, **kb_params[idx_b],
                        )
                    frame = crossfade(frame_a, frame_b, blend)
                else:
                    frame = frame_a

            # ── Layout: Split Screen ────────────────────────
            elif layout == "split_screen":
                p_left = kb_params[split_left_idx]
                p_right = kb_params[split_right_idx]
                frame_left = ken_burns_frame(
                    kb_images[split_left_idx], progress, self.size, **p_left,
                )
                frame_right = ken_burns_frame(
                    kb_images[split_right_idx], progress, self.size, **p_right,
                )
                frame = render_split_screen(frame_left, frame_right, self.size)

            # ── Layout: Picture-in-Picture ──────────────────
            elif layout == "picture_in_picture":
                p = kb_params[pip_bg_idx]
                bg_frame = ken_burns_frame(
                    kb_images[pip_bg_idx], progress, self.size, **p,
                )
                if pip_inset_ci is not None:
                    frame = render_picture_in_picture(
                        bg_frame, pip_inset_ci.image, self.size,
                    )
                else:
                    frame = bg_frame

            else:
                # Fallback to single
                p = kb_params[0]
                frame = ken_burns_frame(
                    kb_images[0], progress, self.size, **p,
                )

            # ── Post-processing (all layouts) ───────────────

            # Color grading
            frame = color_grade(frame, warmth=0.03, contrast=1.08)

            # Vignette
            frame = apply_vignette(frame, intensity=0.35)

            # Logo watermark overlay
            if logo_list:
                frame = render_logo_watermark(frame, logo_list[0].image, self.size)

            # Callout overlay for charts/diagrams (no lower-third text competing)
            if charts_diagrams and layout != "picture_in_picture":
                callout_text = self._extract_key_phrase(narration_text, max_words=8)
                callout_opacity = text_opacity_at_time(
                    t, scene_dur,
                    fade_in=Config.TEXT_FADE_DURATION,
                    fade_out=Config.TEXT_FADE_DURATION,
                )
                if callout_opacity > 0.05 and callout_text:
                    frame = render_callout_overlay(
                        frame, callout_text,
                        position="upper_right",
                        opacity=callout_opacity * 0.85,
                    )
            # Standard text overlay for photos/decorative (skip for charts — they get callouts)
            elif not charts_diagrams or layout == "picture_in_picture":
                text_opacity = text_opacity_at_time(
                    t, scene_dur,
                    fade_in=Config.TEXT_FADE_DURATION,
                    fade_out=Config.TEXT_FADE_DURATION,
                )
                if text_opacity > 0.05 and narration_text:
                    # Photos: no text overlay competing with full-bleed visuals
                    if photos and len(photos) == len(visuals):
                        pass  # pure photo scene — let visuals breathe
                    else:
                        display_text = self._extract_key_phrase(narration_text)
                        frame = render_text_overlay(
                            frame, display_text,
                            position="lower_third",
                            opacity=text_opacity * 0.85,
                            font_size=38,
                        )

            return frame

        video_clip = VideoClip(make_frame, duration=duration).with_fps(self.fps)

        if audio_clip:
            video_clip = video_clip.with_audio(audio_clip)

        return video_clip

    # ── Title Card ──────────────────────────────────────────

    def _build_title_card(
        self, text: str, duration: float = 3.5, is_intro: bool = True
    ) -> VideoClip:
        """Build an animated title/outro card."""

        # Create gradient background
        bg = self._create_gradient_background()
        bg_fitted = fit_image_to_frame(bg, self.size, overscan=1.15)

        def make_frame(t):
            progress = t / duration
            frame = ken_burns_frame(
                bg_fitted, progress, self.size,
                zoom_start=1.0, zoom_end=1.08,
            )
            frame = color_grade(frame, warmth=0.02, contrast=1.05)
            frame = apply_vignette(frame, intensity=0.5)

            # Fade the text
            if is_intro:
                text_opacity = min(1, t / 1.0) * min(1, (duration - t) / 0.5)
            else:
                text_opacity = min(1, t / 0.5) * min(1, (duration - t) / 1.0)

            if text_opacity > 0.05:
                frame = render_text_overlay(
                    frame, text,
                    position="title",
                    opacity=text_opacity,
                    font_size=48,
                )

            return frame

        return VideoClip(make_frame, duration=duration).with_fps(self.fps)

    # ── Transitions ─────────────────────────────────────────

    def _apply_transitions(self, clips: list[VideoClip]) -> list[VideoClip]:
        """Apply crossfade transitions between clips using MoviePy 2.x effects."""
        if len(clips) < 2:
            return clips

        td = self.transition_dur
        result = []
        for i, clip in enumerate(clips):
            if i == 0:
                # First clip: fade in from black at the start
                faded = clip.with_effects([
                    vfx.CrossFadeIn(td),
                ])
            elif i == len(clips) - 1:
                # Last clip: fade out to black at the end
                faded = clip.with_effects([
                    vfx.CrossFadeIn(td),
                    vfx.CrossFadeOut(td),
                ])
            else:
                # Middle clips: crossfade on both edges
                faded = clip.with_effects([
                    vfx.CrossFadeIn(td),
                ])
            result.append(faded)

        return result

    # ── Visual Asset Gathering ──────────────────────────────

    def _gather_scene_visuals(
        self,
        scene: SceneScript,
        content: ContentInput,
        ai_background: Path | None,
    ) -> list[ContentImage]:
        """Gather all visual assets for a scene as ContentImage objects.
        Priority: uploaded images assigned by AI > AI background > section images > gradient.
        Returns ContentImage so classification metadata is available for composition."""
        visuals: list[ContentImage] = []

        # 1. Uploaded images explicitly assigned by the AI script (excluding logos)
        for img_idx in scene.use_uploaded_images:
            if 0 <= img_idx < len(content.all_images):
                ci = content.all_images[img_idx]
                if not ci.is_logo:
                    visuals.append(ci)

        # 2. AI-generated background (only if AI decided this scene needs one)
        if ai_background and ai_background.exists():
            try:
                img = Image.open(ai_background).convert("RGB")
                visuals.append(ContentImage(
                    image=img,
                    label="AI Background",
                    source="ai_generated",
                    classification="photo",
                    description="AI-generated atmospheric background",
                ))
            except Exception:
                pass

        # 3. Section images from source_pages (fallback if nothing assigned)
        if not visuals:
            for section_num in scene.source_pages:
                if 1 <= section_num <= len(content.sections):
                    section = content.sections[section_num - 1]
                    for ci in section.images:
                        if not ci.is_logo:
                            visuals.append(ci)

        # 4. If still nothing, use a gradient
        if not visuals:
            visuals.append(ContentImage(
                image=self._create_gradient_background(),
                label="Gradient",
                source="generated",
                classification="decorative",
                description="Default gradient background",
            ))

        return visuals

    def _gather_logo_images(self, content: ContentInput) -> list[ContentImage]:
        """Collect all logo images from content for watermark use."""
        return [ci for ci in content.all_images if ci.is_logo]

    # ── Helper Methods ──────────────────────────────────────

    def _create_gradient_background(self) -> Image.Image:
        """Create a nice dark gradient background."""
        w, h = self.size[0] + 200, self.size[1] + 200
        img = Image.new("RGB", (w, h))
        pixels = np.zeros((h, w, 3), dtype=np.uint8)

        # Dark blue-to-dark gradient
        for y in range(h):
            ratio = y / h
            r = int(10 + 15 * ratio)
            g = int(15 + 10 * (1 - ratio))
            b = int(30 + 25 * (1 - ratio))
            pixels[y, :] = [r, g, b]

        return Image.fromarray(pixels)

    def _extract_key_phrase(self, text: str, max_words: int = 12) -> str:
        """Extract a short key phrase from narration for display."""
        sentences = text.replace("...", ".").split(".")
        # Pick the first meaningful sentence
        for sent in sentences:
            words = sent.strip().split()
            if len(words) >= 3:
                return " ".join(words[:max_words])
        return " ".join(text.split()[:max_words])

    # ── Background Music ────────────────────────────────────

    def _add_background_music(
        self, video: VideoClip, music_path: Path, volume: float = 0.12
    ) -> VideoClip:
        """Add background music at low volume under narration."""
        try:
            music = AudioFileClip(str(music_path))
            # Loop music if shorter than video
            if music.duration < video.duration:
                loops_needed = int(video.duration / music.duration) + 1
                from moviepy import concatenate_audioclips
                music = concatenate_audioclips([music] * loops_needed)
            music = music.subclipped(0, video.duration).with_volume_scaled(volume)

            if video.audio:
                from moviepy import CompositeAudioClip
                final_audio = CompositeAudioClip([video.audio, music])
                return video.with_audio(final_audio)
            else:
                return video.with_audio(music)
        except Exception as e:
            console.print(f"[yellow]⚠ Background music error: {e}[/]")
            return video

    # ── GPU-Accelerated Export ──────────────────────────────

    def _export_gpu(self, video: VideoClip, output_path: Path):
        """Export video using NVENC GPU encoder for fast, high-quality output."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if NVENC is available
        has_nvenc = self._check_nvenc()

        if has_nvenc:
            console.print("  [green]Using NVIDIA NVENC GPU encoder[/]")
            codec = "h264_nvenc"
            extra_params = [
                "-preset", Config.NVENC_PRESET,
                "-rc", "vbr",
                "-cq", "19",
                "-b:v", Config.VIDEO_BITRATE,
                "-maxrate", "20M",
                "-bufsize", "24M",
                "-profile:v", "high",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ]
        else:
            console.print("  [yellow]NVENC not available, using CPU encoder (libx264)[/]")
            codec = "libx264"
            extra_params = [
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ]

        # Write to a unique temp file first, then use FFmpeg for final encode
        temp_path: Path | None = None
        if has_nvenc:
            with tempfile.NamedTemporaryFile(
                suffix=".mp4",
                dir=Config.TEMP_DIR,
                delete=False,
            ) as tmp:
                temp_path = Path(tmp.name)

        worker_threads = self._resolve_worker_threads(has_nvenc)
        console.print(f"  Using {worker_threads} CPU worker threads for render pass")

        # MoviePy write with FFmpeg params
        video.write_videofile(
            str(temp_path) if has_nvenc and temp_path else str(output_path),
            fps=self.fps,
            codec=codec if not has_nvenc else "libx264",  # MoviePy render pass
            audio_codec="aac",
            audio_bitrate="192k",
            preset="ultrafast" if has_nvenc else "medium",
            threads=worker_threads,
            logger="bar",
        )

        # If NVENC available, do a GPU re-encode pass for max quality
        if has_nvenc and temp_path and temp_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_path),
                "-c:v", codec,
                *extra_params,
                "-c:a", "aac", "-b:a", "192k",
                str(output_path),
            ]
            console.print("  GPU re-encoding for maximum quality...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            temp_path.unlink(missing_ok=True)
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                raise RuntimeError(f"FFmpeg NVENC re-encode failed: {stderr or 'unknown error'}")

    def _check_nvenc(self) -> bool:
        """Check if NVIDIA NVENC encoder is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=5,
            )
            return "h264_nvenc" in result.stdout
        except Exception:
            return False

    def _resolve_worker_threads(self, has_nvenc: bool) -> int:
        """Choose render worker thread count, with optional auto-tuning."""
        manual_threads = max(1, Config.NUM_WORKERS)
        if not Config.AUTO_TUNE_WORKERS:
            return manual_threads

        cpu_count = os.cpu_count() or manual_threads
        if has_nvenc:
            # Leave headroom for ffmpeg/NVENC orchestration and system responsiveness.
            tuned = max(6, cpu_count - (8 if cpu_count >= 24 else 4))
        else:
            # CPU-only encode path benefits from higher thread usage.
            tuned = max(4, cpu_count - 2)

        return max(1, min(manual_threads, tuned))
