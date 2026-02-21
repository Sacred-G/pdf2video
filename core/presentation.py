"""
Presentation Generator — AI-powered slide deck creation.
Takes text/PDF content → plans slides with AI → generates professional slide images
via gpt-image-1 → outputs both a downloadable PDF deck and an MP4 video with voiceover.

Like NotebookLM's presentation feature: professional, clean, graphic-rich slides.
"""

import base64
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI
from PIL import Image
from rich.console import Console

from .config import Config
from .content_input import ContentInput, content_from_pdf
from .pdf_extractor import PDFExtractor
from .utils import retry_api as _retry, image_to_data_url

console = Console()


# ── Data Models ──────────────────────────────────────────

PRESENTATION_SCRIPT_SCHEMA = {
    "type": "json_schema",
    "name": "presentation_script",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "subtitle": {"type": "string"},
            "theme": {
                "type": "string",
                "description": "Visual theme: corporate-white (recommended — white bg with navy/red/green accents, NotebookLM style), modern-light, corporate-blue",
            },
            "slides": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "slide_number": {"type": "integer"},
                        "slide_type": {
                            "type": "string",
                            "enum": ["title", "content", "two_column", "key_point", "quote", "data", "section_break", "closing"],
                        },
                        "headline": {"type": "string"},
                        "body_text": {"type": "string"},
                        "bullet_points": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "narration": {"type": "string"},
                        "visual_description": {
                            "type": "string",
                            "description": "Detailed description of graphics, icons, illustrations to include on this slide",
                        },
                        "color_accent": {
                            "type": "string",
                            "description": "Hex color for accent elements on this slide",
                        },
                    },
                    "required": [
                        "slide_number", "slide_type", "headline", "body_text",
                        "bullet_points", "narration", "visual_description", "color_accent",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "subtitle", "theme", "slides"],
        "additionalProperties": False,
    },
}


@dataclass
class SlideScript:
    """Script for a single presentation slide."""
    slide_number: int
    slide_type: str  # title, content, two_column, key_point, quote, data, section_break, closing
    headline: str
    body_text: str
    bullet_points: list[str] = field(default_factory=list)
    narration: str = ""
    visual_description: str = ""
    color_accent: str = "#2563EB"


@dataclass
class PresentationScript:
    """Complete presentation script with all slides."""
    title: str
    subtitle: str
    theme: str
    slides: list[SlideScript]


@dataclass
class PresentationResult:
    """Output of the presentation pipeline."""
    slide_images: list[Path]  # individual slide PNGs
    pdf_path: Path | None  # assembled PDF deck
    video_path: Path | None  # MP4 with voiceover
    audio_paths: list[Path]  # individual voiceover clips
    script: PresentationScript
    timings: dict[str, float]


# ── Presentation Generator ───────────────────────────────

class PresentationGenerator:
    """Generates professional AI slide decks from text/PDF content."""

    def __init__(self):
        Config.validate()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    # ── Slide Planning (AI Script) ───────────────────────

    def plan_slides(
        self, content: ContentInput, logo_image: Image.Image | None = None,
    ) -> PresentationScript:
        """Use AI to plan the slide deck structure and content.
        If a logo_image is provided, it's sent to the AI so it can theme the design around it."""
        console.print("[bold blue]📋 Planning presentation slides with AI...[/]")

        # Build content summary
        sections_text = []
        for section in content.sections:
            sections_text.append({
                "section": section.section_number,
                "text": section.text[:3000],
                "has_images": section.has_significant_images,
                "image_count": len(section.images),
            })

        prompt = f"""You are a world-class presentation designer creating slides in the style of 
Google NotebookLM / corporate training decks. The slides must look like professional infographics 
with a CLEAN WHITE BACKGROUND, bold dark navy headlines, structured card layouts, flat vector 
icons, and color-coded sections.

REFERENCE STYLE (match this exactly):
- WHITE or very light gray background — NOT dark themes
- Bold dark navy (#1B2A4A) headlines in large sans-serif font
- Smaller red (#C41E3A) section labels/pillar headers above the main headline
- Content organized in CARD LAYOUTS: rounded-corner cards with thin borders arranged in rows
- Each card has: a flat vector ICON at top, a navy header bar with white text, body text below
- Color-coded accents: green (#2E7D32) for positive/required, red (#C41E3A) for warnings/prohibited
- Checkmark (✓) and X (✗) icons for do/don't lists
- Process flows shown as horizontal card sequences with arrow connections
- Two-column comparison layouts with green "Must Have" vs red "Prohibited" headers
- Flat vector silhouette icons (people, objects, symbols) — NOT photos, NOT 3D
- Clean sans-serif typography (like Inter, Helvetica, or Segoe UI)
- Generous whitespace, never overcrowded
- Subtle drop shadows on cards for depth

Title: {content.title}
Source: {content.source_type}

Content:
{json.dumps(sections_text, indent=2)}

Create a presentation script as JSON. Design 7-12 slides that tell a compelling story.

Slide types and when to use them:
- "title" — opening slide with title + subtitle on white background with a subtle accent graphic
- "content" — standard content slide with headline and bullet points in card layout
- "two_column" — side-by-side comparison cards (e.g., "Must Have" vs "Prohibited", "Before" vs "After")
- "key_point" — large bold statement centered, with a supporting icon or graphic
- "quote" — featured quote or important policy callout in a styled card
- "data" — process flow, timeline, or metrics displayed as connected cards with icons
- "section_break" — pillar/section transition with section number and title
- "closing" — final slide with summary checklist or call to action

For each slide:
- headline: concise, impactful (3-8 words)
- body_text: supporting text (1-2 sentences, can be empty)
- bullet_points: key points as SHORT phrases (3-5 max, can be empty)
- narration: what a presenter would say (2-4 sentences, conversational)
- visual_description: EXTREMELY DETAILED layout description for the image generator.
  Describe the EXACT layout: how many cards, what icons, what colors, what text goes where.
  Examples:
  - "White background. Three rounded-corner cards arranged horizontally. Each card has a flat 
    vector icon at top (calendar icon, warning triangle icon, medical cross icon), a dark navy 
    header bar with white text, and body text below. Cards connected by subtle arrow lines."
  - "White background. Two-column layout. Left column has green header bar reading 'Must Have' 
    with checkmark icons and bullet points. Right column has red header bar reading 'Prohibited' 
    with X icons and bullet points. Flat vector silhouette illustrations in each column."
  - "White background. Large bold headline at top. Below: four metric cards in a row, each 
    showing a large number, a label, and a small icon. Color-coded borders."
- color_accent: hex color for this slide's accent (navy #1B2A4A, red #C41E3A, green #2E7D32, blue #1565C0)

Theme: always use "corporate-white" — white backgrounds with navy/red/green accents.
If a company logo image is provided below, study its colors, style, and branding to:
- Extract the brand's primary and accent colors and use them throughout the slides
- Include the logo on the TITLE slide (first slide) prominently
- Use the logo as a small watermark in the corner of every other slide
- Match the overall color scheme to the brand identity

Guidelines:
- Every slide MUST have an extremely detailed visual_description with specific layout instructions
- Think Google NotebookLM slides or corporate training decks — NOT dark tech themes
- Bullet points should be SHORT phrases, not sentences
- Vary slide types for visual rhythm
- Use process flows (horizontal card sequences) for procedures and timelines
- Use two-column comparisons for do/don't, before/after, required/prohibited
- Use icon+card layouts for categorized information
- The narration should flow naturally as a spoken presentation

Return ONLY valid JSON."""

        # Build multimodal input with image thumbnails if available
        input_content = [{"type": "input_text", "text": prompt}]

        # Send logo image first so AI can theme around it
        if logo_image is not None:
            try:
                logo_url = image_to_data_url(logo_image, max_size=512)
                input_content.append({
                    "type": "input_text",
                    "text": "COMPANY LOGO — use this to theme the entire presentation. Extract brand colors and include this logo on the title slide and as a watermark on other slides:",
                })
                input_content.append({
                    "type": "input_image",
                    "image_url": logo_url,
                })
            except Exception as e:
                console.print(f"  [yellow]⚠ Could not encode logo: {e}[/]")

        for i, ci in enumerate(content.all_images[:10]):  # cap at 10 images
            try:
                data_url = image_to_data_url(ci.image, max_size=512)
                input_content.append({
                    "type": "input_image",
                    "image_url": data_url,
                })
            except Exception:
                pass

        response = _retry(lambda: self.client.responses.create(
            model=Config.OPENAI_CHAT_MODEL,
            input=[{"role": "user", "content": input_content}],
            text={"format": PRESENTATION_SCRIPT_SCHEMA},
            temperature=0.7,
        ))

        data = json.loads(response.output_text)

        slides = []
        for s in data["slides"]:
            slides.append(SlideScript(
                slide_number=s["slide_number"],
                slide_type=s["slide_type"],
                headline=s["headline"],
                body_text=s.get("body_text", ""),
                bullet_points=s.get("bullet_points", []),
                narration=s.get("narration", ""),
                visual_description=s.get("visual_description", ""),
                color_accent=s.get("color_accent", "#2563EB"),
            ))

        script = PresentationScript(
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            theme=data.get("theme", "corporate-white"),
            slides=slides,
        )

        console.print(f"[bold green]✓[/] Planned {len(slides)} slides (theme: {script.theme})")
        for s in slides:
            console.print(f"  Slide {s.slide_number} [{s.slide_type}]: {s.headline}")

        return script

    # ── Slide Image Generation (gpt-image-1) ─────────────

    def generate_slide_image(
        self, slide: SlideScript, theme: str, title: str, output_path: Path,
        logo_data_url: str | None = None,
    ) -> Path:
        """Generate a single professional slide image using gpt-image-1."""

        # Build a detailed prompt for the image generator
        bullet_text = ""
        if slide.bullet_points:
            bullet_text = "\nBullet points displayed on the slide:\n" + "\n".join(
                f"• {bp}" for bp in slide.bullet_points
            )

        body_section = ""
        if slide.body_text:
            body_section = f"\nBody text on the slide: {slide.body_text}"

        prompt = f"""Create a professional presentation slide image in the style of Google NotebookLM 
or a corporate training deck. This must look like a real, polished infographic slide.

EXACT STYLE TO MATCH:
- CLEAN WHITE or very light gray (#F8F9FA) background — NOT dark
- Bold dark navy (#1B2A4A) headline text, large sans-serif font at the top
- If there's a section label, it goes ABOVE the headline in smaller red (#C41E3A) text
- Content organized in ROUNDED-CORNER CARDS with thin gray borders and subtle drop shadows
- Cards have: colored header bars (navy, green, or red) with white text, then body content below
- FLAT VECTOR ICONS — simple, clean silhouette-style (NOT 3D, NOT photographic)
- Color coding: green (#2E7D32) = positive/required, red (#C41E3A) = warning/prohibited, 
  navy (#1B2A4A) = neutral/informational, blue (#1565C0) = highlights
- Checkmark icons (✓) in green circles for positive items
- X icons (✗) in red for prohibited items  
- Clean sans-serif typography throughout (like Inter, Helvetica, or Segoe UI)
- Generous whitespace between elements
- Professional, corporate, training-deck aesthetic

SLIDE CONTENT:
- Presentation: {title}
- Slide type: {slide.slide_type}
- Headline: {slide.headline}{body_section}{bullet_text}
- Accent color: {slide.color_accent}

LAYOUT & VISUAL ELEMENTS:
{slide.visual_description}

CRITICAL REQUIREMENTS:
- 16:9 landscape aspect ratio (1920x1080)
- WHITE background — this is non-negotiable
- All text on the slide must be READABLE and properly rendered
- Include the headline, body text, and bullet points as actual text on the slide
- Use flat vector icons and illustrations, NOT photographs
- Cards should have rounded corners, thin borders, subtle shadows
- The slide must look like it came from a professional corporate presentation
- NO watermarks, NO placeholder text, NO lorem ipsum
- Match the clean, structured, infographic style of Google NotebookLM slides"""

        # For title slides with a logo, include the logo as a reference image
        if logo_data_url and slide.slide_type == "title":
            prompt += "\n\nIMPORTANT: Include the company logo (shown in the reference image) prominently on this title slide. Place it centered or top-center, with the title text below it."
            response = _retry(lambda: self.client.images.edit(
                model=Config.OPENAI_IMAGE_MODEL,
                image=self._data_url_to_png_bytes(logo_data_url),
                prompt=prompt,
                size="1536x1024",
            ))
        elif logo_data_url and slide.slide_type != "title":
            prompt += "\n\nInclude a small company logo watermark in the top-right corner of the slide (subtle, semi-transparent). The logo is shown in the reference image."
            response = _retry(lambda: self.client.images.edit(
                model=Config.OPENAI_IMAGE_MODEL,
                image=self._data_url_to_png_bytes(logo_data_url),
                prompt=prompt,
                size="1536x1024",
            ))
        else:
            response = _retry(lambda: self.client.images.generate(
                model=Config.OPENAI_IMAGE_MODEL,
                prompt=prompt,
                size="1536x1024",
                quality="high",
                n=1,
            ))

        img_b64 = response.data[0].b64_json
        img_bytes = base64.b64decode(img_b64)

        # Save and resize to exact 1920x1080
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = img.resize((1920, 1080), Image.LANCZOS)
        img.save(str(output_path), quality=95)

        return output_path

    @staticmethod
    def _data_url_to_png_bytes(data_url: str) -> bytes:
        """Convert a data URL to raw PNG bytes for the images.edit API."""
        # Strip the data:image/...;base64, prefix
        if "," in data_url:
            b64_data = data_url.split(",", 1)[1]
        else:
            b64_data = data_url
        img_bytes = base64.b64decode(b64_data)
        # Ensure it's PNG format
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate_all_slides(
        self, script: PresentationScript, output_dir: Path,
        logo_data_url: str | None = None,
    ) -> list[Path]:
        """Generate all slide images in parallel."""
        console.print(f"[bold blue]🎨 Generating {len(script.slides)} slide images (parallel)...[/]")
        slide_paths: list[Path | None] = [None] * len(script.slides)

        def _gen_one(idx: int, slide: SlideScript) -> tuple[int, Path]:
            path = output_dir / f"slide_{slide.slide_number:03d}.png"
            self.generate_slide_image(slide, script.theme, script.title, path, logo_data_url)
            return idx, path

        max_workers = min(4, len(script.slides))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_gen_one, i, slide): i
                for i, slide in enumerate(script.slides)
            }
            for future in as_completed(futures):
                idx, path = future.result()
                slide_paths[idx] = path
                console.print(f"  Slide {idx + 1}: image ready")

        console.print(f"[bold green]✓[/] Generated {len(slide_paths)} slide images")
        return slide_paths

    # ── Voiceover Generation ─────────────────────────────

    def generate_voiceover(
        self, script: PresentationScript, output_dir: Path, voice: str | None = None
    ) -> list[Path]:
        """Generate voiceover for each slide in parallel."""
        console.print("[bold blue]🎙️  Generating voiceover (parallel)...[/]")
        selected_voice = voice or Config.OPENAI_TTS_VOICE
        audio_paths: list[Path | None] = [None] * len(script.slides)

        def _gen_one(idx: int, slide: SlideScript) -> tuple[int, Path]:
            audio_path = output_dir / f"slide_{slide.slide_number:03d}_voice.mp3"
            response = _retry(lambda: self.client.audio.speech.create(
                model=Config.OPENAI_TTS_MODEL,
                voice=selected_voice,
                input=slide.narration,
                response_format="mp3",
                speed=0.95,
            ))
            response.stream_to_file(str(audio_path))
            return idx, audio_path

        max_workers = min(8, len(script.slides))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_gen_one, i, slide): i
                for i, slide in enumerate(script.slides)
            }
            for future in as_completed(futures):
                idx, path = future.result()
                audio_paths[idx] = path
                console.print(f"  Slide {idx + 1}: audio ready")

        console.print(f"[bold green]✓[/] Generated {len(audio_paths)} audio clips")
        return audio_paths

    # ── PDF Deck Export ──────────────────────────────────

    def export_pdf(self, slide_images: list[Path], output_path: Path) -> Path:
        """Assemble slide images into a downloadable PDF deck."""
        console.print("[bold blue]📄 Assembling PDF deck...[/]")

        images = []
        for p in slide_images:
            img = Image.open(p).convert("RGB")
            images.append(img)

        if not images:
            raise ValueError("No slide images to assemble")

        # Save as multi-page PDF
        first = images[0]
        rest = images[1:] if len(images) > 1 else []
        first.save(
            str(output_path),
            save_all=True,
            append_images=rest,
            resolution=150,
        )

        console.print(f"[bold green]✓[/] PDF deck saved: {output_path} ({len(images)} slides)")
        return output_path

    # ── Video Export (slides + transitions + voiceover) ───

    def export_video(
        self,
        slide_images: list[Path],
        audio_paths: list[Path],
        output_path: Path,
        transition_duration: float = 0.8,
    ) -> Path:
        """
        Export slides as an MP4 video with simple crossfade transitions
        and voiceover. No Ken Burns, no vignette, no color grading —
        just clean slide transitions like a real presentation.
        """
        import subprocess
        import tempfile
        from moviepy import (
            AudioFileClip,
            ImageClip,
            VideoClip,
            concatenate_videoclips,
            vfx,
        )

        console.print("[bold blue]🎬 Composing presentation video...[/]")

        fps = Config.VIDEO_FPS
        size = (1920, 1080)
        scene_clips = []

        try:
            for i, (img_path, audio_path) in enumerate(zip(slide_images, audio_paths)):
                # Load slide image
                img = Image.open(img_path).convert("RGB").resize(size, Image.LANCZOS)
                img_array = __import__("numpy").array(img)

                # Determine duration from audio
                audio_clip = AudioFileClip(str(audio_path))
                duration = audio_clip.duration + 1.0  # 1s padding after narration
                duration = max(duration, 3.0)  # minimum 3s per slide

                # Create static image clip (no effects — just the slide)
                clip = ImageClip(img_array, duration=duration).with_fps(fps)
                clip = clip.with_audio(audio_clip)
                scene_clips.append(clip)

            # Apply simple crossfade transitions
            td = transition_duration
            transitioned = []
            for i, clip in enumerate(scene_clips):
                if i == 0:
                    faded = clip.with_effects([vfx.CrossFadeIn(td)])
                elif i == len(scene_clips) - 1:
                    faded = clip.with_effects([
                        vfx.CrossFadeIn(td),
                        vfx.CrossFadeOut(td),
                    ])
                else:
                    faded = clip.with_effects([vfx.CrossFadeIn(td)])
                transitioned.append(faded)

            # Concatenate
            final = concatenate_videoclips(transitioned, method="compose")

            # Export — use the same parallel pipe approach
            console.print("[bold blue]📹 Exporting video...[/]")
            self._export_video_pipe(final, output_path, fps, size)

            console.print(f"[bold green]✓[/] Video saved: {output_path}")
            return output_path

        finally:
            for clip in scene_clips:
                try:
                    clip.close()
                except Exception:
                    pass

    def _export_video_pipe(self, video, output_path: Path, fps: int, size: tuple):
        """Export video by piping frames to ffmpeg (NVENC or libx264)."""
        import subprocess
        import tempfile
        import numpy as np
        from tqdm import tqdm

        w, h = size
        total_frames = int(video.duration * fps)

        # Write audio
        audio_tmp = None
        if video.audio is not None:
            audio_tmp = tempfile.NamedTemporaryFile(
                suffix=".aac", dir=Config.TEMP_DIR, delete=False
            )
            audio_tmp.close()
            video.audio.write_audiofile(
                audio_tmp.name, fps=44100, codec="aac",
                bitrate="192k", logger=None,
            )

        # Check for NVENC
        has_nvenc = False
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=5,
            )
            has_nvenc = "h264_nvenc" in result.stdout
        except Exception:
            pass

        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{w}x{h}", "-pix_fmt", "rgb24",
            "-r", str(fps), "-i", "pipe:0",
        ]

        if audio_tmp:
            cmd.extend(["-i", audio_tmp.name, "-c:a", "aac", "-b:a", "192k"])

        if has_nvenc:
            console.print("  [green]Encoding: NVIDIA NVENC (GPU)[/]")
            cmd.extend([
                "-c:v", "h264_nvenc", "-preset", Config.NVENC_PRESET,
                "-rc", "vbr", "-cq", "19",
                "-b:v", Config.VIDEO_BITRATE,
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output_path),
            ])
        else:
            console.print("  [yellow]Encoding: libx264 (CPU)[/]")
            cmd.extend([
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output_path),
            ])

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            # Parallel frame rendering for static slides is simpler —
            # but since slides are static images, frame rendering is fast already.
            # Just pipe frames directly.
            for frame_idx in tqdm(range(total_frames), desc="  Rendering frames", unit="f"):
                t = frame_idx / fps
                frame = video.get_frame(t)
                if frame.dtype != np.uint8:
                    frame = np.clip(frame, 0, 255).astype(np.uint8)
                proc.stdin.write(frame.tobytes())

            proc.stdin.close()
            proc.wait()

            if proc.returncode != 0:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                raise RuntimeError(f"FFmpeg failed (rc={proc.returncode}): {stderr[:500]}")
        except Exception:
            proc.kill()
            raise
        finally:
            if audio_tmp:
                Path(audio_tmp.name).unlink(missing_ok=True)


# ── Presentation Pipeline ────────────────────────────────

class PresentationPipeline:
    """End-to-end orchestrator for presentation generation."""

    def __init__(self):
        Config.validate()
        self.generator = PresentationGenerator()
        self.extractor = PDFExtractor(dpi=300)

    def run(
        self,
        pdf_path: str | Path | None = None,
        text_content: str | None = None,
        title: str = "Presentation",
        output_dir: str | Path | None = None,
        voice: str | None = None,
        generate_video: bool = True,
        generate_pdf: bool = True,
        progress_callback=None,
        images: list[Image.Image] | None = None,
        image_labels: list[str] | None = None,
    ) -> PresentationResult:
        """
        Run the full presentation pipeline.

        Args:
            pdf_path: Path to input PDF (optional)
            text_content: Raw text content (optional, used if no PDF)
            title: Presentation title
            output_dir: Directory for outputs
            voice: TTS voice override
            generate_video: Whether to generate MP4
            generate_pdf: Whether to generate PDF deck
            progress_callback: Optional callable(step: str, progress: float)
            images: Optional list of PIL images (first one treated as logo)
            image_labels: Optional labels for the images

        Returns:
            PresentationResult with paths to all outputs
        """
        start_time = time.time()
        timings: dict[str, float] = {}

        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        work_dir = Config.TEMP_DIR / "presentation"
        work_dir.mkdir(parents=True, exist_ok=True)

        def _progress(step: str, pct: float):
            if progress_callback:
                progress_callback(step, pct)

        # ── Step 1: Build ContentInput ────────────────────
        _progress("Preparing content...", 0.05)
        if pdf_path:
            pdf_content = self.extractor.extract(Path(pdf_path))
            content = content_from_pdf(pdf_content)
            title = content.title or title
        else:
            from .content_input import content_from_text_and_images
            content = content_from_text_and_images(
                title=title,
                text=text_content or "",
                images=[],
                image_labels=[],
            )

        # Extract logo from uploaded images (first image is treated as logo)
        logo_image = None
        logo_data_url = None
        if images and len(images) > 0:
            logo_image = images[0]
            try:
                logo_data_url = image_to_data_url(logo_image, max_size=1024)
                logo_label = (image_labels[0] if image_labels else "logo")
                console.print(f"  🏷️  Logo detected: {logo_label}")
            except Exception as e:
                console.print(f"  [yellow]⚠ Could not process logo: {e}[/]")
                logo_image = None
                logo_data_url = None

        console.print(f"[bold]Content: {content.title}[/]")
        console.print(f"  Sections: {content.total_sections} | Images: {content.image_count}")

        # ── Step 2: Plan Slides with AI ───────────────────
        _progress("Planning slides with AI...", 0.10)
        t0 = time.time()
        script = self.generator.plan_slides(content, logo_image=logo_image)
        timings["Slide planning"] = time.time() - t0
        console.print(f"  ⏱️  Slide planning: {timings['Slide planning']:.1f}s")

        # ── Step 3: Generate Slides + Voiceover (concurrent) ──
        _progress("Generating slides + voiceover...", 0.20)

        slide_paths = []
        audio_paths = []

        with ThreadPoolExecutor(max_workers=2) as stage_pool:
            # Slide images and voiceover are independent — run concurrently
            slides_future = stage_pool.submit(
                self.generator.generate_all_slides, script, work_dir, logo_data_url,
            )
            voice_future = stage_pool.submit(
                self.generator.generate_voiceover, script, work_dir, voice,
            )

            t1 = time.time()
            slide_paths = slides_future.result()
            timings["Slide image generation"] = time.time() - t1

            t2 = time.time()
            audio_paths = voice_future.result()
            timings["Voiceover generation"] = time.time() - t2

        wall_time = time.time() - t1
        console.print(f"  ⏱️  Slides + Voiceover wall time: {wall_time:.1f}s (concurrent)")

        # ── Step 4: Export PDF Deck ───────────────────────
        pdf_path_out = None
        if generate_pdf:
            _progress("Assembling PDF deck...", 0.70)
            t3 = time.time()
            safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
            pdf_path_out = output_dir / f"{safe_title.strip()[:60] or 'presentation'}_deck.pdf"
            self.generator.export_pdf(slide_paths, pdf_path_out)
            timings["PDF export"] = time.time() - t3

        # ── Step 5: Export Video ──────────────────────────
        video_path_out = None
        if generate_video:
            _progress("Composing presentation video...", 0.75)
            t4 = time.time()
            safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
            video_path_out = output_dir / f"{safe_title.strip()[:60] or 'presentation'}_video.mp4"
            self.generator.export_video(slide_paths, audio_paths, video_path_out)
            timings["Video export"] = time.time() - t4

        # ── Done ──────────────────────────────────────────
        elapsed = time.time() - start_time
        _progress("Complete!", 1.0)

        timing_lines = "\n".join(f"  {k}: {v:.1f}s" for k, v in timings.items())
        from rich.panel import Panel
        console.print(Panel(
            f"[bold green]✓ Presentation generated![/]\n\n"
            f"📊 Slides: {len(slide_paths)}\n"
            f"📄 PDF: {pdf_path_out or 'skipped'}\n"
            f"🎬 Video: {video_path_out or 'skipped'}\n"
            f"⏱️  Total: {elapsed:.1f}s\n\n"
            f"[bold]Timing Breakdown:[/]\n{timing_lines}",
            title="🎉 Presentation Complete",
            border_style="green",
        ))

        return PresentationResult(
            slide_images=slide_paths,
            pdf_path=pdf_path_out,
            video_path=video_path_out,
            audio_paths=audio_paths,
            script=script,
            timings=timings,
        )
