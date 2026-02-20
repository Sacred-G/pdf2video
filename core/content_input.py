"""
Content Input — Unified data model for all input types (PDF, text+images).
Both PDF extraction and manual text+images feed into this common structure
so the rest of the pipeline (AI scripting, video composition) works identically.
"""

from PIL import Image
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentImage:
    """A single uploaded or extracted image with metadata."""
    image: Image.Image
    label: str = ""  # user-provided or auto-detected label
    source: str = ""  # "uploaded", "pdf_page_3", "pdf_extracted", "ai_generated"
    classification: str = ""  # filled by vision: "photo", "chart", "diagram", "logo", etc.
    description: str = ""  # filled by vision: what the image shows
    has_data: bool = False  # contains quantitative data/metrics
    is_comparison: bool = False  # shows before/after or side-by-side
    visual_complexity: str = "medium"  # low, medium, high
    suggested_hold_seconds: float = 5.0  # how long to display
    width: int = 0
    height: int = 0

    def __post_init__(self):
        if self.width == 0:
            self.width = self.image.width
        if self.height == 0:
            self.height = self.image.height

    @property
    def is_classified(self) -> bool:
        return self.classification != ""

    @property
    def is_data_visual(self) -> bool:
        """Charts, diagrams, and tables that benefit from zoom + hold."""
        return self.classification in ("chart", "diagram", "table")

    @property
    def is_full_bleed(self) -> bool:
        """Photos that look best full-frame with Ken Burns."""
        return self.classification in ("photo", "decorative")

    @property
    def is_logo(self) -> bool:
        return self.classification == "logo"


@dataclass
class ContentSection:
    """A logical section of content (maps to one or more video scenes)."""
    section_number: int
    text: str
    images: list[ContentImage] = field(default_factory=list)
    has_significant_text: bool = False
    has_significant_images: bool = False


@dataclass
class ContentInput:
    """
    Unified content input for the video pipeline.
    Created from either PDF extraction or manual text+images upload.
    """
    title: str
    sections: list[ContentSection]
    all_images: list[ContentImage] = field(default_factory=list)
    total_sections: int = 0
    source_type: str = ""  # "pdf" or "text_images"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.total_sections == 0:
            self.total_sections = len(self.sections)

    @property
    def has_images(self) -> bool:
        return len(self.all_images) > 0

    @property
    def image_count(self) -> int:
        return len(self.all_images)


def content_from_pdf(pdf_content) -> ContentInput:
    """Convert PDFContent into the unified ContentInput format."""
    from .pdf_extractor import PDFContent

    sections = []
    all_images = []

    for page in pdf_content.pages:
        section_images = []

        # Wrap extracted images
        for i, img in enumerate(page.images):
            ci = ContentImage(
                image=img.convert("RGB"),
                label=f"Page {page.page_number} image {i + 1}",
                source=f"pdf_extracted_page_{page.page_number}",
            )
            section_images.append(ci)
            all_images.append(ci)

        # Wrap page render
        if page.page_render:
            ci = ContentImage(
                image=page.page_render.convert("RGB"),
                label=f"Page {page.page_number} render",
                source=f"pdf_page_{page.page_number}",
            )
            section_images.append(ci)
            all_images.append(ci)

        sections.append(ContentSection(
            section_number=page.page_number,
            text=page.text,
            images=section_images,
            has_significant_text=page.has_significant_text,
            has_significant_images=page.has_significant_images,
        ))

    return ContentInput(
        title=pdf_content.title,
        sections=sections,
        all_images=all_images,
        total_sections=len(sections),
        source_type="pdf",
        metadata=pdf_content.metadata,
    )


def content_from_text_and_images(
    title: str,
    text: str,
    images: list[Image.Image],
    image_labels: list[str] | None = None,
) -> ContentInput:
    """
    Create ContentInput from raw text and uploaded images.
    Text is split into paragraphs to form sections.
    Images are distributed across sections or kept as a global pool.
    """
    if image_labels is None:
        image_labels = [f"Image {i + 1}" for i in range(len(images))]

    # Wrap all uploaded images
    all_images = []
    for i, img in enumerate(images):
        label = image_labels[i] if i < len(image_labels) else f"Image {i + 1}"
        ci = ContentImage(
            image=img.convert("RGB"),
            label=label,
            source="uploaded",
        )
        all_images.append(ci)

    # Split text into sections by double-newline paragraphs
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Merge very short paragraphs together (< 50 chars)
    paragraphs = []
    buffer = ""
    for p in raw_paragraphs:
        if len(buffer) + len(p) < 50:
            buffer = f"{buffer}\n\n{p}".strip() if buffer else p
        else:
            if buffer:
                paragraphs.append(buffer)
            buffer = p
    if buffer:
        paragraphs.append(buffer)

    # If no paragraphs, treat entire text as one section
    if not paragraphs:
        paragraphs = [text] if text.strip() else [""]

    # Distribute images across sections as evenly as possible
    sections = []
    images_per_section = max(1, len(all_images) // max(1, len(paragraphs)))

    img_idx = 0
    for i, para in enumerate(paragraphs):
        # Assign a slice of images to this section
        section_images = []
        end_idx = img_idx + images_per_section
        # Last section gets all remaining images
        if i == len(paragraphs) - 1:
            end_idx = len(all_images)
        for ci in all_images[img_idx:end_idx]:
            section_images.append(ci)
        img_idx = end_idx

        sections.append(ContentSection(
            section_number=i + 1,
            text=para,
            images=section_images,
            has_significant_text=len(para) > 20,
            has_significant_images=len(section_images) > 0,
        ))

    return ContentInput(
        title=title or "Untitled Video",
        sections=sections,
        all_images=all_images,
        total_sections=len(sections),
        source_type="text_images",
        metadata={},
    )
