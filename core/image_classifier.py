"""
Image Classifier — GPT-5.2 vision-powered image analysis.
Classifies each extracted/uploaded image as: chart, photo, diagram, table, logo, decorative.
Classification drives composition decisions (layout, timing, overlays).
"""

import base64
import io
import json
import time
from dataclasses import dataclass
from PIL import Image
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from rich.console import Console

from .config import Config
from .utils import retry_api, image_to_data_url

console = Console()

# ── Classification Schema ────────────────────────────────

IMAGE_CLASSIFICATION_SCHEMA = {
    "type": "json_schema",
    "name": "image_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["chart", "photo", "diagram", "table", "logo", "decorative"],
                "description": "Primary type of this image",
            },
            "description": {
                "type": "string",
                "description": "Brief description of what the image shows (1-2 sentences)",
            },
            "has_data": {
                "type": "boolean",
                "description": "Whether the image contains quantitative data or metrics",
            },
            "is_comparison": {
                "type": "boolean",
                "description": "Whether the image shows a before/after or side-by-side comparison",
            },
            "visual_complexity": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How visually complex/detailed the image is",
            },
            "suggested_hold_seconds": {
                "type": "number",
                "description": "How long this image should be shown (3-10 seconds based on complexity)",
            },
        },
        "required": [
            "classification", "description", "has_data",
            "is_comparison", "visual_complexity", "suggested_hold_seconds",
        ],
        "additionalProperties": False,
    },
}

BATCH_CLASSIFICATION_SCHEMA = {
    "type": "json_schema",
    "name": "batch_image_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "classification": {
                            "type": "string",
                            "enum": ["chart", "photo", "diagram", "table", "logo", "decorative"],
                        },
                        "description": {"type": "string"},
                        "has_data": {"type": "boolean"},
                        "is_comparison": {"type": "boolean"},
                        "visual_complexity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "suggested_hold_seconds": {"type": "number"},
                    },
                    "required": [
                        "index", "classification", "description",
                        "has_data", "is_comparison", "visual_complexity",
                        "suggested_hold_seconds",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["classifications"],
        "additionalProperties": False,
    },
}


# ── Classification Result ────────────────────────────────

@dataclass
class ImageClassification:
    """Result of classifying a single image."""
    classification: str  # chart, photo, diagram, table, logo, decorative
    description: str
    has_data: bool = False
    is_comparison: bool = False
    visual_complexity: str = "medium"  # low, medium, high
    suggested_hold_seconds: float = 5.0


class ImageClassifier:
    """Classifies images using GPT-5.2 vision to drive smart composition."""

    def __init__(self):
        Config.validate()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def classify_images(self, images: list) -> list[ImageClassification]:
        """
        Classify a list of ContentImage objects using GPT-5.2 vision.
        Sends images in batches to minimize API calls.
        Returns list of ImageClassification in same order as input.
        """
        if not Config.IMAGE_CLASSIFICATION_ENABLED or not images:
            return [ImageClassification(
                classification="photo",
                description="Unclassified image",
            ) for _ in images]

        console.print(f"[bold blue]🔍 Classifying {len(images)} images with AI vision...[/]")

        # Process in batches of up to 8 images per API call
        batch_size = 8
        all_results: list[ImageClassification] = []

        for batch_start in range(0, len(images), batch_size):
            batch = images[batch_start:batch_start + batch_size]
            batch_results = self._classify_batch(batch, batch_start)
            all_results.extend(batch_results)

        # Log classification summary
        counts = {}
        for r in all_results:
            counts[r.classification] = counts.get(r.classification, 0) + 1
        summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        console.print(f"[bold green]✓[/] Classified {len(all_results)} images — {summary}")

        return all_results

    def _classify_batch(
        self, images: list, offset: int
    ) -> list[ImageClassification]:
        """Classify a batch of images in a single API call."""
        input_content = [{
            "type": "input_text",
            "text": (
                f"Classify each of the following {len(images)} images. "
                f"For each image (numbered starting from index {offset}), determine:\n"
                f"- **classification**: chart, photo, diagram, table, logo, or decorative\n"
                f"- **description**: brief 1-2 sentence description\n"
                f"- **has_data**: does it contain quantitative data/metrics?\n"
                f"- **is_comparison**: does it show before/after or side-by-side comparison?\n"
                f"- **visual_complexity**: low/medium/high\n"
                f"- **suggested_hold_seconds**: how long to display (3-10s based on complexity)\n\n"
                f"Classification guide:\n"
                f"- **chart**: bar charts, line graphs, pie charts, scatter plots, any data visualization\n"
                f"- **photo**: photographs, real-world images, screenshots of real scenes\n"
                f"- **diagram**: flowcharts, architecture diagrams, process flows, mind maps, technical drawings\n"
                f"- **table**: tabular data, spreadsheet-like grids, comparison matrices\n"
                f"- **logo**: company logos, brand marks, icons, small symbolic graphics\n"
                f"- **decorative**: backgrounds, textures, abstract art, dividers, ornamental graphics\n\n"
                f"Return JSON with a 'classifications' array containing one entry per image."
            ),
        }]

        # Attach image thumbnails
        for i, ci in enumerate(images):
            try:
                img = ci.image if hasattr(ci, 'image') else ci
                data_url = self._image_to_data_url(img, max_size=512)
                input_content.append({
                    "type": "input_image",
                    "image_url": data_url,
                })
            except Exception as e:
                console.print(f"  [yellow]⚠ Could not encode image {offset + i}: {e}[/]")

        try:
            response = retry_api(lambda: self.client.responses.create(
                model=Config.OPENAI_CHAT_MODEL,
                input=[{"role": "user", "content": input_content}],
                text={"format": BATCH_CLASSIFICATION_SCHEMA},
                temperature=0.3,
            ))

            data = json.loads(response.output_text)
            results = []

            # Build a lookup by index for safety
            classified = {c["index"]: c for c in data["classifications"]}

            for i in range(len(images)):
                idx = offset + i
                if idx in classified:
                    c = classified[idx]
                    results.append(ImageClassification(
                        classification=c["classification"],
                        description=c["description"],
                        has_data=c.get("has_data", False),
                        is_comparison=c.get("is_comparison", False),
                        visual_complexity=c.get("visual_complexity", "medium"),
                        suggested_hold_seconds=c.get("suggested_hold_seconds", 5.0),
                    ))
                else:
                    results.append(ImageClassification(
                        classification="photo",
                        description="Classification unavailable",
                    ))

                cls_label = results[-1].classification
                console.print(
                    f"  Image {idx}: [cyan]{cls_label}[/] — {results[-1].description[:60]}"
                )

            return results

        except Exception as e:
            console.print(f"  [yellow]⚠ Batch classification failed: {e}[/]")
            return [ImageClassification(
                classification="photo",
                description="Classification failed — defaulting to photo",
            ) for _ in images]

    @staticmethod
    def _image_to_data_url(img: Image.Image, max_size: int = 512) -> str:
        """Resize an image and encode as a data URL for the Responses API vision input."""
        return image_to_data_url(img, max_size)
