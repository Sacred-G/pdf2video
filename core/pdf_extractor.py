"""
PDF Extractor — pulls text, images, and full-page renders from PDFs.
Uses PyMuPDF for high-fidelity extraction with GPU-friendly image sizing.
"""

import io
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from rich.console import Console

from .config import Config

console = Console()


@dataclass
class PageContent:
    """Content extracted from a single PDF page."""
    page_number: int
    text: str
    images: list[Image.Image] = field(default_factory=list)
    page_render: Optional[Image.Image] = None  # full page as high-res image
    has_significant_text: bool = False
    has_significant_images: bool = False


@dataclass
class PDFContent:
    """Complete extracted PDF content."""
    pages: list[PageContent]
    title: str = ""
    total_pages: int = 0
    metadata: dict = field(default_factory=dict)


class PDFExtractor:
    """Extracts rich content from PDF files for video generation."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.zoom = dpi / 72.0  # PDF base is 72 DPI

    def extract(self, pdf_path: str | Path) -> PDFContent:
        """Extract all content from a PDF file."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        console.print(f"[bold blue]📄 Opening PDF:[/] {pdf_path.name}")
        doc = fitz.open(str(pdf_path))
        try:
            content = PDFContent(
                pages=[],
                title=doc.metadata.get("title", pdf_path.stem) or pdf_path.stem,
                total_pages=len(doc),
                metadata=dict(doc.metadata),
            )

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_content = self._extract_page(page, page_num + 1)
                content.pages.append(page_content)
                console.print(
                    f"  Page {page_num + 1}/{len(doc)}: "
                    f"{len(page_content.text)} chars, "
                    f"{len(page_content.images)} images"
                )
        finally:
            doc.close()

        console.print(f"[bold green]✓[/] Extracted {len(content.pages)} pages")
        return content

    def _extract_page(self, page: fitz.Page, page_number: int) -> PageContent:
        """Extract content from a single page."""
        # Extract text
        text = page.get_text("text").strip()

        # Extract embedded images
        images = self._extract_images(page)

        # Render full page as high-res image (for visual elements, diagrams, etc.)
        page_render = self._render_page(page)

        # Determine content significance
        has_text = len(text) > 20
        has_images = len(images) > 0 or self._page_has_visual_elements(page)

        return PageContent(
            page_number=page_number,
            text=text,
            images=images,
            page_render=page_render,
            has_significant_text=has_text,
            has_significant_images=has_images,
        )

    def _extract_images(self, page: fitz.Page) -> list[Image.Image]:
        """Extract embedded images from a page."""
        images = []
        image_list = page.get_images(full=True)

        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = page.parent.extract_image(xref)
                if base_image:
                    img_data = base_image["image"]
                    img = Image.open(io.BytesIO(img_data)).convert("RGBA")

                    # Only keep images of reasonable size (skip tiny icons)
                    if img.width >= 50 and img.height >= 50:
                        # Scale up small images to at least 720p width
                        if img.width < 1280:
                            scale = 1280 / img.width
                            new_size = (int(img.width * scale), int(img.height * scale))
                            img = img.resize(new_size, Image.LANCZOS)
                        images.append(img)
            except Exception as e:
                console.print(f"  [yellow]⚠ Could not extract image xref={xref}: {e}[/]")
                continue

        return images

    def _render_page(self, page: fitz.Page) -> Image.Image:
        """Render the full page as a high-resolution image."""
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    def _page_has_visual_elements(self, page: fitz.Page) -> bool:
        """Check if page has drawings, charts, or other visual elements."""
        # Check for vector drawings
        drawings = page.get_drawings()
        if len(drawings) > 5:  # More than just basic lines/borders
            return True

        # Check for significant non-text content by comparing text area to page area
        text_blocks = page.get_text("blocks")
        if text_blocks:
            text_area = sum(
                (b[2] - b[0]) * (b[3] - b[1])
                for b in text_blocks
                if b[6] == 0  # text blocks only
            )
            page_area = page.rect.width * page.rect.height
            # If text covers less than 40% of page, there are visual elements
            if text_area / page_area < 0.4:
                return True

        return False
