"""
AI Services — OpenAI integration for script writing, voiceover, and image generation.
Uses the Responses API with structured output and gpt-image-1.
"""

import base64
import io
import json
import time
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from PIL import Image
from rich.console import Console

from .config import Config
from .content_input import ContentInput, ContentImage
from .pdf_extractor import PDFContent
from .utils import retry_api as _retry, image_to_data_url

console = Console()


# ── JSON Schema for Structured Output ────────────────────

VIDEO_SCRIPT_SCHEMA = {
    "type": "json_schema",
    "name": "video_script",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "overall_mood": {"type": "string"},
            "intro_text": {"type": "string"},
            "outro_text": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "narration": {"type": "string"},
                        "visual_description": {"type": "string"},
                        "mood": {"type": "string"},
                        "source_pages": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "duration_hint": {"type": "number"},
                        "generate_background": {"type": "boolean"},
                        "background_prompt": {"type": "string"},
                        "use_uploaded_images": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "0-based indices of uploaded images to use in this scene",
                        },
                        "layout_mode": {
                            "type": "string",
                            "enum": ["single", "carousel", "split_screen", "picture_in_picture"],
                            "description": "How to compose visuals: single (one image), carousel (cycle through multiple), split_screen (side-by-side comparison), picture_in_picture (AI bg full-frame with figure inset)",
                        },
                    },
                    "required": [
                        "scene_number", "narration", "visual_description",
                        "mood", "source_pages", "duration_hint",
                        "generate_background", "background_prompt",
                        "use_uploaded_images", "layout_mode",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "overall_mood", "intro_text", "outro_text", "scenes"],
        "additionalProperties": False,
    },
}


@dataclass
class SceneScript:
    """Script for a single video scene."""
    scene_number: int
    narration: str
    visual_description: str
    mood: str  # e.g., "professional", "inspiring", "dramatic"
    source_pages: list[int] = field(default_factory=list)
    duration_hint: float = 8.0  # suggested duration in seconds
    generate_background: bool = False  # whether to AI-generate a background
    background_prompt: str = ""
    use_uploaded_images: list[int] = field(default_factory=list)  # indices into ContentInput.all_images
    layout_mode: str = "single"  # single, carousel, split_screen, picture_in_picture


@dataclass
class VideoScript:
    """Complete video script with all scenes."""
    title: str
    scenes: list[SceneScript]
    total_narration: str = ""  # combined narration for single TTS pass
    intro_text: str = ""
    outro_text: str = ""
    overall_mood: str = "professional"


class AIServices:
    """OpenAI-powered AI services for video generation pipeline."""

    def __init__(self):
        Config.validate()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    # ── Script Generation ───────────────────────────────────

    def generate_script(self, pdf_content: PDFContent) -> VideoScript:
        """Generate a cinematic video script from PDF content using Responses API."""
        console.print("[bold blue]🎬 Generating video script with AI...[/]")

        # Build content summary for the AI
        pages_summary = []
        for page in pdf_content.pages:
            page_info = {
                "page": page.page_number,
                "text": page.text[:2000],  # cap per page
                "has_images": page.has_significant_images,
                "has_text": page.has_significant_text,
            }
            pages_summary.append(page_info)

        prompt = f"""You are a professional video scriptwriter. Convert this PDF content into a 
cinematic video script. The video should feel like a polished documentary or explainer video — 
NOT a slideshow or presentation.

PDF Title: {pdf_content.title}
Total Pages: {pdf_content.total_pages}

Page Contents:
{json.dumps(pages_summary, indent=2)}

Create a video script as JSON with this exact structure:
{{
    "title": "compelling video title",
    "overall_mood": "professional|inspiring|dramatic|educational|storytelling",
    "intro_text": "short intro overlay text (5-8 words)",
    "outro_text": "short outro overlay text (5-8 words)", 
    "scenes": [
        {{
            "scene_number": 1,
            "narration": "what the narrator says (conversational, engaging, 2-4 sentences)",
            "visual_description": "what the viewer sees described cinematically",
            "mood": "mood for this scene",
            "source_pages": [1, 2],
            "duration_hint": 8.0,
            "generate_background": true,
            "background_prompt": "a DALL-E prompt for an atmospheric background image",
            "use_uploaded_images": [],
            "layout_mode": "single"
        }}
    ]
}}

layout_mode options:
- "single" — one primary image with Ken Burns (default for most scenes)
- "carousel" — cycle through multiple page images with crossfades (when a scene covers 3+ pages with images)
- "split_screen" — side-by-side comparison (for before/after or two related charts)
- "picture_in_picture" — AI background full-frame with a PDF figure inset in a corner card

Guidelines:
- Combine related pages into single scenes (aim for 4-10 scenes total)
- Write narration that's conversational and engaging, not just reading the PDF
- Each narration should be 2-4 sentences that tell a story
- For pages with strong images/graphics, suggest shorter narration and let visuals breathe
- Mark generate_background=true for scenes that need more visual interest
- Background prompts should describe abstract, atmospheric visuals (not text-heavy)
- Duration hints: 5-8s for simple scenes, 8-15s for complex ones
- For scenes spanning multiple pages with images, use "carousel" layout
- For comparison pages, use "split_screen" layout
- For data-heavy pages with charts, consider "picture_in_picture" with an AI background
- use_uploaded_images should be an empty array for PDF scenes (page images are auto-gathered)
- The video should have narrative flow — it should feel like one cohesive story

Return ONLY valid JSON, no markdown formatting."""

        response = _retry(lambda: self.client.responses.create(
            model=Config.OPENAI_CHAT_MODEL,
            input=[{"role": "user", "content": prompt}],
            text={"format": VIDEO_SCRIPT_SCHEMA},
            temperature=0.7,
        ))

        # Structured output guarantees valid JSON matching our schema
        script_data = json.loads(response.output_text)

        scenes = []
        for s in script_data["scenes"]:
            scenes.append(SceneScript(
                scene_number=s["scene_number"],
                narration=s["narration"],
                visual_description=s["visual_description"],
                mood=s.get("mood", "professional"),
                source_pages=s.get("source_pages", []),
                duration_hint=s.get("duration_hint", 8.0),
                generate_background=s.get("generate_background", False),
                background_prompt=s.get("background_prompt", ""),
                use_uploaded_images=s.get("use_uploaded_images", []),
                layout_mode=s.get("layout_mode", "single"),
            ))

        # Build total narration with natural pauses
        total_narration = " ... ".join(s.narration for s in scenes)

        video_script = VideoScript(
            title=script_data.get("title", pdf_content.title),
            scenes=scenes,
            total_narration=total_narration,
            intro_text=script_data.get("intro_text", pdf_content.title),
            outro_text=script_data.get("outro_text", "Thank you for watching"),
            overall_mood=script_data.get("overall_mood", "professional"),
        )

        console.print(f"[bold green]✓[/] Generated {len(scenes)} scenes")
        return video_script

    # ── Script Generation (Unified — vision-powered) ───────

    def generate_script_from_content(self, content: ContentInput) -> VideoScript:
        """
        Generate a video script from unified ContentInput.
        Sends image thumbnails to GPT-5.2 vision so the AI can see uploaded
        images and decide which to feature, which scenes need more visuals,
        and where to generate AI backgrounds to fill gaps.
        """
        console.print("[bold blue]🎬 Generating video script with AI vision...[/]")

        # Build section summaries
        sections_summary = []
        for section in content.sections:
            sections_summary.append({
                "section": section.section_number,
                "text": section.text[:2000],
                "has_images": section.has_significant_images,
                "image_count": len(section.images),
                "has_text": section.has_significant_text,
            })

        # Build image inventory for the prompt (now includes classification)
        image_inventory = []
        for i, ci in enumerate(content.all_images):
            entry = {
                "index": i,
                "label": ci.label,
                "source": ci.source,
                "size": f"{ci.width}x{ci.height}",
            }
            if ci.is_classified:
                entry["classification"] = ci.classification
                entry["description"] = ci.description
                entry["has_data"] = ci.has_data
                entry["is_comparison"] = ci.is_comparison
                entry["visual_complexity"] = ci.visual_complexity
                entry["suggested_hold_seconds"] = ci.suggested_hold_seconds
            image_inventory.append(entry)

        prompt_text = f"""You are a professional video scriptwriter. Convert this content into a 
cinematic video script. The video should feel like a polished documentary or explainer video.

Title: {content.title}
Source type: {content.source_type}
Total sections: {content.total_sections}
Total images available: {content.image_count}

Section Contents:
{json.dumps(sections_summary, indent=2)}

Available Images (by index, with AI classification):
{json.dumps(image_inventory, indent=2)}

I am also sending you thumbnail previews of each available image so you can SEE what they contain.

Create a video script as JSON. For each scene:
- **use_uploaded_images**: list the 0-based indices of images that should appear in that scene.
  Use EVERY uploaded image at least once (EXCEPT logos — logos are used as watermarks, not scene visuals).
  Assign images to the scenes where they are most relevant.
- **generate_background**: set true ONLY for scenes that have NO suitable uploaded images.
  If a scene already has good uploaded images, set this to false.
  Also set true for picture_in_picture scenes (the AI background is the full-frame backdrop).
- **source_pages**: section numbers this scene draws content from.
- **layout_mode**: choose the best visual composition for each scene:
  - "single" — one primary image with Ken Burns (best for photos, simple scenes)
  - "carousel" — cycle through multiple images with crossfades (best when a scene references 3+ images)
  - "split_screen" — side-by-side comparison layout (best for before/after, two charts, comparison images)
  - "picture_in_picture" — AI background full-frame with a figure/chart inset in a rounded corner card (best when you have a data visual like a chart or diagram AND want an atmospheric backdrop)

Layout selection rules:
- If a scene has only 1 non-logo image → "single"
- If a scene has 2 comparison images (is_comparison=true) → "split_screen"
- If a scene has 3+ images → "carousel"
- If a scene has a chart/diagram AND generate_background=true → "picture_in_picture"
- Photos classified as "photo" look best as "single" with full-bleed Ken Burns
- Tables classified as "table" are rendered as styled cards automatically regardless of layout
- Images classified as "logo" should NOT be in use_uploaded_images — they are auto-applied as watermarks

Guidelines:
- Combine related sections into single scenes (aim for 4-10 scenes total)
- Write narration that's conversational and engaging, 2-4 sentences per scene
- Reference the images in your narration when relevant (e.g., "As we can see here...")
- For scenes with strong uploaded images, let the visuals breathe — shorter narration
- Charts/diagrams need longer duration (use suggested_hold_seconds from classification)
- Only generate_background=true when a scene truly lacks visual content OR uses picture_in_picture
- Duration hints: 5-8s for simple scenes, 8-15s for complex or multi-image scenes
- The video should have narrative flow — one cohesive story

Return ONLY valid JSON, no markdown formatting."""

        # Build the multimodal input: text prompt + image thumbnails
        input_content = [{"type": "input_text", "text": prompt_text}]

        # Attach image thumbnails (resized to save tokens)
        for i, ci in enumerate(content.all_images):
            try:
                data_url = self._image_to_data_url(ci.image, max_size=512)
                input_content.append({
                    "type": "input_image",
                    "image_url": data_url,
                })
            except Exception as e:
                console.print(f"  [yellow]⚠ Could not encode image {i}: {e}[/]")

        response = _retry(lambda: self.client.responses.create(
            model=Config.OPENAI_CHAT_MODEL,
            input=[{"role": "user", "content": input_content}],
            text={"format": VIDEO_SCRIPT_SCHEMA},
            temperature=0.7,
        ))

        script_data = json.loads(response.output_text)

        scenes = []
        for s in script_data["scenes"]:
            scenes.append(SceneScript(
                scene_number=s["scene_number"],
                narration=s["narration"],
                visual_description=s["visual_description"],
                mood=s.get("mood", "professional"),
                source_pages=s.get("source_pages", []),
                duration_hint=s.get("duration_hint", 8.0),
                generate_background=s.get("generate_background", False),
                background_prompt=s.get("background_prompt", ""),
                use_uploaded_images=s.get("use_uploaded_images", []),
                layout_mode=s.get("layout_mode", "single"),
            ))

        total_narration = " ... ".join(s.narration for s in scenes)

        video_script = VideoScript(
            title=script_data.get("title", content.title),
            scenes=scenes,
            total_narration=total_narration,
            intro_text=script_data.get("intro_text", content.title),
            outro_text=script_data.get("outro_text", "Thank you for watching"),
            overall_mood=script_data.get("overall_mood", "professional"),
        )

        # Log image usage and layout modes
        used_indices = set()
        layout_counts = {}
        for s in scenes:
            used_indices.update(s.use_uploaded_images)
            layout_counts[s.layout_mode] = layout_counts.get(s.layout_mode, 0) + 1
        unused = set(range(content.image_count)) - used_indices
        bg_count = sum(1 for s in scenes if s.generate_background)

        console.print(f"[bold green]✓[/] Generated {len(scenes)} scenes")
        console.print(f"  📷 {len(used_indices)}/{content.image_count} uploaded images assigned")
        layouts_str = ", ".join(f"{k}: {v}" for k, v in sorted(layout_counts.items()))
        console.print(f"  🖼️  Layouts: {layouts_str}")
        if unused:
            console.print(f"  [yellow]⚠ {len(unused)} images not assigned by AI — will distribute to nearest scenes[/]")
        console.print(f"  🎨 {bg_count} scenes will get AI-generated backgrounds")

        return video_script

    # ── Image Encoding Helper ────────────────────────────────

    @staticmethod
    def _image_to_data_url(img: Image.Image, max_size: int = 512) -> str:
        """Resize an image and encode as a data URL for the Responses API vision input."""
        return image_to_data_url(img, max_size)

    # ── Voice Generation ────────────────────────────────────

    def generate_voiceover(
        self,
        script: VideoScript,
        output_dir: Path,
        voice: str | None = None,
    ) -> list[Path]:
        """Generate individual voiceover clips for each scene."""
        console.print("[bold blue]🎙️  Generating AI voiceover...[/]")
        audio_paths = []
        selected_voice = voice or Config.OPENAI_TTS_VOICE

        for scene in script.scenes:
            audio_path = output_dir / f"scene_{scene.scene_number:03d}_voice.mp3"
            console.print(f"  Scene {scene.scene_number}: generating audio...")

            response = _retry(lambda scene=scene: self.client.audio.speech.create(
                model=Config.OPENAI_TTS_MODEL,
                voice=selected_voice,
                input=scene.narration,
                response_format="mp3",
                speed=0.95,  # slightly slower for documentary feel
            ))

            response.stream_to_file(str(audio_path))
            audio_paths.append(audio_path)

        console.print(f"[bold green]✓[/] Generated {len(audio_paths)} audio clips")
        return audio_paths

    # ── Background Image Generation ─────────────────────────

    def generate_background_image(self, prompt: str, output_path: Path) -> Path:
        """Generate a cinematic background image using gpt-image-1."""
        console.print(f"  🎨 Generating background: {prompt[:60]}...")

        enhanced_prompt = (
            f"Cinematic, high-quality, 16:9 aspect ratio, atmospheric background. "
            f"No text or words in the image. Subtle depth of field. "
            f"{prompt}"
        )

        response = _retry(lambda: self.client.images.generate(
            model=Config.OPENAI_IMAGE_MODEL,
            prompt=enhanced_prompt,
            size="1536x1024",
            quality="high",
            n=1,
        ))

        # gpt-image-1 returns base64 data directly
        img_b64 = response.data[0].b64_json
        output_path.write_bytes(base64.b64decode(img_b64))

        return output_path

    def generate_scene_backgrounds(
        self, script: VideoScript, output_dir: Path
    ) -> dict[int, Path]:
        """Generate AI backgrounds for scenes that need them."""
        console.print("[bold blue]🎨 Generating AI backgrounds...[/]")
        backgrounds = {}

        for scene in script.scenes:
            if scene.generate_background and scene.background_prompt:
                bg_path = output_dir / f"scene_{scene.scene_number:03d}_bg.png"
                try:
                    self.generate_background_image(scene.background_prompt, bg_path)
                    backgrounds[scene.scene_number] = bg_path
                except Exception as e:
                    console.print(f"  [yellow]⚠ Background gen failed for scene {scene.scene_number}: {e}[/]")

        console.print(f"[bold green]✓[/] Generated {len(backgrounds)} backgrounds")
        return backgrounds

    # ── Narration Timing Analysis ───────────────────────────

    def estimate_narration_duration(self, text: str) -> float:
        """Estimate how long narration will take at natural speaking pace."""
        words = len(text.split())
        # Average speaking rate: ~145 words per minute for documentary style
        return max(Config.MIN_SCENE_DURATION, (words / 145) * 60 + 1.0)
