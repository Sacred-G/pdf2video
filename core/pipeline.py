"""
PDF2Video Pipeline — End-to-end orchestrator.
Coordinates PDF extraction → AI scripting → voiceover → video composition.
"""

import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from .config import Config
from .content_input import (
    ContentInput,
    content_from_pdf,
    content_from_text_and_images,
)
from .image_classifier import ImageClassifier
from .pdf_extractor import PDFExtractor, PDFContent
from .ai_services import AIServices, VideoScript
from .video_composer import VideoComposer

console = Console()


class PDF2VideoPipeline:
    """Complete content-to-cinematic-video pipeline."""

    def __init__(self):
        Config.validate()
        self.extractor = PDFExtractor(dpi=300)
        self.classifier = ImageClassifier()
        self.ai = AIServices()
        self.composer = VideoComposer()

    # ── Public Entry Points ──────────────────────────────────

    def run(
        self,
        pdf_path: str | Path,
        output_path: str | Path | None = None,
        background_music: str | Path | None = None,
        voice: str | None = None,
        generate_backgrounds: bool = True,
        progress_callback=None,
    ) -> Path:
        """
        Run the full pipeline: PDF → Video.

        Args:
            pdf_path: Path to input PDF
            output_path: Path for output video (auto-generated if None)
            background_music: Optional path to background music file
            voice: OpenAI TTS voice override (alloy, echo, fable, onyx, nova, shimmer)
            generate_backgrounds: Whether to generate AI backgrounds for scenes
            progress_callback: Optional callable(step: str, progress: float)

        Returns:
            Path to the generated video file
        """
        pdf_path = Path(pdf_path)

        if output_path is None:
            output_path = Config.OUTPUT_DIR / f"{pdf_path.stem}_video.mp4"
        else:
            output_path = Path(output_path)

        def _progress(step: str, pct: float):
            if progress_callback:
                progress_callback(step, pct)

        # Step 1: Extract PDF and convert to unified ContentInput
        _progress("Extracting PDF content...", 0.05)
        pdf_content = self.extractor.extract(pdf_path)
        if not pdf_content.pages:
            raise ValueError("PDF has no extractable pages!")

        content = content_from_pdf(pdf_content)

        # Delegate to the unified pipeline
        return self._run_pipeline(
            content=content,
            output_path=output_path,
            background_music=background_music,
            voice=voice,
            generate_backgrounds=generate_backgrounds,
            progress_callback=progress_callback,
            progress_offset=0.05,
        )

    def run_from_content(
        self,
        content: ContentInput,
        output_path: str | Path | None = None,
        background_music: str | Path | None = None,
        voice: str | None = None,
        generate_backgrounds: bool = True,
        progress_callback=None,
    ) -> Path:
        """
        Run the full pipeline from text + images (no PDF).

        Args:
            content: Unified ContentInput (from text+images or any source)
            output_path: Path for output video (auto-generated if None)
            background_music: Optional path to background music file
            voice: OpenAI TTS voice override
            generate_backgrounds: Whether to generate AI backgrounds for gaps
            progress_callback: Optional callable(step: str, progress: float)

        Returns:
            Path to the generated video file
        """
        if output_path is None:
            safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in content.title)
            output_path = Config.OUTPUT_DIR / f"{safe_title.strip()[:60] or 'video'}_video.mp4"
        else:
            output_path = Path(output_path)

        return self._run_pipeline(
            content=content,
            output_path=output_path,
            background_music=background_music,
            voice=voice,
            generate_backgrounds=generate_backgrounds,
            progress_callback=progress_callback,
            progress_offset=0.0,
        )

    # ── Unified Pipeline Core ────────────────────────────────

    def _run_pipeline(
        self,
        content: ContentInput,
        output_path: Path,
        background_music: str | Path | None,
        voice: str | None,
        generate_backgrounds: bool,
        progress_callback,
        progress_offset: float = 0.0,
    ) -> Path:
        """Core pipeline shared by both PDF and text+images entry points."""
        start_time = time.time()
        output_path = Path(output_path)

        console.print(Panel(
            f"[bold]PDF2Video Pipeline[/]\n"
            f"Source: {content.source_type} — {content.title}\n"
            f"Sections: {content.total_sections} | Images: {content.image_count}\n"
            f"Output: {output_path}",
            title="🎬 Starting",
            border_style="blue",
        ))

        def _progress(step: str, pct: float):
            if progress_callback:
                progress_callback(step, max(pct, progress_offset))

        # ── Step 1: Classify Images (GPT-5.2 vision) ─────────
        if content.has_images and Config.IMAGE_CLASSIFICATION_ENABLED:
            _progress("Classifying images with AI vision...", 0.08)
            classifications = self.classifier.classify_images(content.all_images)
            for ci, cls_result in zip(content.all_images, classifications):
                ci.classification = cls_result.classification
                ci.description = cls_result.description
                ci.has_data = cls_result.has_data
                ci.is_comparison = cls_result.is_comparison
                ci.visual_complexity = cls_result.visual_complexity
                ci.suggested_hold_seconds = cls_result.suggested_hold_seconds

        # ── Step 2: Generate AI Script (vision-powered) ──────
        _progress("Generating AI script...", 0.15)
        script = self.ai.generate_script_from_content(content)

        console.print(f"\n[bold]Script Overview:[/]")
        console.print(f"  Title: {script.title}")
        console.print(f"  Scenes: {len(script.scenes)}")
        console.print(f"  Mood: {script.overall_mood}")
        for s in script.scenes:
            img_info = f" [📷 {len(s.use_uploaded_images)} images]" if s.use_uploaded_images else ""
            bg_info = " [🎨 AI bg]" if s.generate_background else ""
            layout_info = f" [🖼️ {s.layout_mode}]" if s.layout_mode != "single" else ""
            console.print(f"  Scene {s.scene_number}: {s.narration[:50]}...{img_info}{bg_info}{layout_info}")

        # ── Step 3: Generate Voiceover ──────────────────────
        _progress("Generating AI voiceover...", 0.35)
        audio_paths = self.ai.generate_voiceover(script, Config.TEMP_DIR, voice=voice)

        # ── Step 4: Generate AI Backgrounds (only for gaps) ──
        ai_backgrounds = {}
        if generate_backgrounds:
            _progress("Generating AI backgrounds...", 0.50)
            ai_backgrounds = self.ai.generate_scene_backgrounds(script, Config.TEMP_DIR)

        # ── Step 5: Compose Video ───────────────────────────
        _progress("Composing video...", 0.65)
        bg_music_path = Path(background_music) if background_music else None

        result = self.composer.compose(
            script=script,
            content=content,
            audio_paths=audio_paths,
            ai_backgrounds=ai_backgrounds,
            output_path=output_path,
            background_music_path=bg_music_path,
        )

        # ── Done ────────────────────────────────────────────
        elapsed = time.time() - start_time
        _progress("Complete!", 1.0)

        console.print(Panel(
            f"[bold green]✓ Video generated successfully![/]\n\n"
            f"📁 Output: {result}\n"
            f"⏱️  Time: {elapsed:.1f}s\n"
            f"🎬 Scenes: {len(script.scenes)}",
            title="🎉 Complete",
            border_style="green",
        ))

        return result


# ── CLI Entry Point ─────────────────────────────────────

def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDF to cinematic video")
    parser.add_argument("pdf", help="Path to input PDF file")
    parser.add_argument("-o", "--output", help="Output video path")
    parser.add_argument("-m", "--music", help="Background music file path")
    parser.add_argument(
        "-v", "--voice",
        choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        default="onyx",
        help="TTS voice (default: onyx)",
    )
    parser.add_argument(
        "--no-backgrounds",
        action="store_true",
        help="Skip AI background generation (faster, cheaper)",
    )

    args = parser.parse_args()

    pipeline = PDF2VideoPipeline()
    pipeline.run(
        pdf_path=args.pdf,
        output_path=args.output,
        background_music=args.music,
        voice=args.voice,
        generate_backgrounds=not args.no_backgrounds,
    )


if __name__ == "__main__":
    main()
