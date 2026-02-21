"""
Video Composer — Assembles scenes into a cinematic video.
Handles scene rendering, audio synchronization, transitions, and
GPU-accelerated export via NVENC on RTX 5090.
"""

import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip,
    VideoClip,
    concatenate_videoclips,
    vfx,
)
from rich.console import Console

from .ai_services import SceneScript, VideoScript
from .config import Config
from .content_input import ContentImage, ContentInput

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
            # 1. Build scene clips (exact PDF slides, static)
            for i, scene in enumerate(script.scenes):
                console.print(f"  Rendering scene {scene.scene_number}/{len(script.scenes)}...")
                audio_path = audio_paths[i] if i < len(audio_paths) else None
                clip = self._build_scene_clip(
                    scene=scene,
                    content=content,
                    audio_path=audio_path,
                    ai_background=None,
                    logo_images=None,
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
        """Build a scene clip showing the exact PDF slide image, static, with audio."""

        # Determine scene duration from audio
        duration = scene.duration_hint
        audio_clip = None
        if audio_path and audio_path.exists():
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration + 0.5
            duration = max(duration, Config.MIN_SCENE_DURATION)

        # Get the first uploaded image for this scene (the PDF slide)
        slide_image = None
        for img_idx in scene.use_uploaded_images:
            if 0 <= img_idx < len(content.all_images):
                slide_image = content.all_images[img_idx].image
                break

        # Fallback: try section images from source pages
        if slide_image is None:
            for section_num in scene.source_pages:
                if 1 <= section_num <= len(content.sections):
                    section = content.sections[section_num - 1]
                    if section.images:
                        slide_image = section.images[0].image
                        break

        # Final fallback: dark background
        if slide_image is None:
            slide_image = Image.new("RGB", self.size, (20, 20, 30))

        # Fit the slide to the frame (no overscan — exact fit)
        fw, fh = self.size
        img = slide_image.copy()
        img_ratio = img.width / img.height
        frame_ratio = fw / fh

        if img_ratio > frame_ratio:
            new_w = fw
            new_h = int(fw / img_ratio)
        else:
            new_h = fh
            new_w = int(fh * img_ratio)

        img = img.resize((new_w, new_h), Image.LANCZOS)

        # Center on black background
        bg = Image.new("RGB", (fw, fh), (0, 0, 0))
        x_offset = (fw - new_w) // 2
        y_offset = (fh - new_h) // 2
        bg.paste(img, (x_offset, y_offset))

        # Convert to numpy array once (static frame)
        static_frame = np.array(bg)

        def make_frame(t):
            return static_frame

        video_clip = VideoClip(make_frame, duration=duration).with_fps(self.fps)

        if audio_clip:
            video_clip = video_clip.with_audio(audio_clip)

        return video_clip

    # ── Title Card ──────────────────────────────────────────

    def _build_title_card(
        self, text: str, duration: float = 3.5, is_intro: bool = True
    ) -> VideoClip:
        """Build a simple title/outro card — dark background with centered text."""
        fw, fh = self.size

        # Render text onto a dark background using PIL
        bg = Image.new("RGB", (fw, fh), (20, 20, 30))
        draw = ImageDraw.Draw(bg)

        # Try to load a nice font, fall back to default
        font_size = 42
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        # Word-wrap text to fit frame width
        max_chars = max(20, fw // (font_size // 2))
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if len(test) <= max_chars:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Draw centered text
        line_height = font_size + 10
        total_height = len(lines) * line_height
        y_start = (fh - total_height) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (fw - tw) // 2
            y = y_start + i * line_height
            draw.text((x, y), line, fill=(255, 255, 255), font=font)

        static_frame = np.array(bg)

        def make_frame(t):
            return static_frame

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

    # ── Video Export ────────────────────────────────────────

    def _export_gpu(self, video: VideoClip, output_path: Path):
        """
        Export video using MoviePy's write_videofile with NVENC or libx264.
        MoviePy handles FFmpeg I/O internally — no raw-frame pipe needed.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        has_nvenc = self._check_nvenc()

        if has_nvenc:
            console.print("  [green]Encoding: HEVC NVENC (GPU)[/]")
            video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="hevc_nvenc",
                audio_codec="aac",
                audio_bitrate="128k",
                preset=Config.NVENC_PRESET,
                bitrate=Config.VIDEO_BITRATE,
                ffmpeg_params=[
                    "-rc", "vbr",
                    "-cq", "28",
                    "-maxrate", "4M",
                    "-bufsize", "8M",
                    "-tag:v", "hvc1",
                    "-movflags", "+faststart",
                ],
                threads=self._resolve_render_workers(),
                logger="bar",
            )
        else:
            console.print("  [yellow]Encoding: libx265 (CPU)[/]")
            video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx265",
                audio_codec="aac",
                audio_bitrate="128k",
                preset="medium",
                ffmpeg_params=[
                    "-crf", "28",
                    "-tag:v", "hvc1",
                    "-movflags", "+faststart",
                ],
                threads=self._resolve_render_workers(),
                logger="bar",
            )

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

    def _resolve_render_workers(self) -> int:
        """Choose parallel render worker count based on available CPU cores."""
        cpu_count = os.cpu_count() or 4
        if not Config.AUTO_TUNE_WORKERS:
            return max(1, Config.NUM_WORKERS)

        # Leave 2 cores for ffmpeg encoder + OS; use the rest for rendering
        workers = max(2, cpu_count - 2)
        return min(workers, Config.NUM_WORKERS) if Config.NUM_WORKERS > 0 else workers
