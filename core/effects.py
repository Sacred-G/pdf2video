"""
Visual Effects — Cinematic effects for video scenes.
Ken Burns, crossfades, text animations, vignettes, and color grading.
Optimized for GPU-friendly numpy operations.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional
from .config import Config

# ── Utility ─────────────────────────────────────────────


def fit_image_to_frame(
    img: Image.Image,
    frame_size: tuple[int, int] = None,
    overscan: float = 1.3,
) -> Image.Image:
    """Scale image to fill frame with optional overscan for Ken Burns movement."""
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    fw, fh = frame_size
    target_w = int(fw * overscan)
    target_h = int(fh * overscan)

    img_ratio = img.width / img.height
    frame_ratio = target_w / target_h

    if img_ratio > frame_ratio:
        # Image is wider — fit height
        new_h = target_h
        new_w = int(new_h * img_ratio)
    else:
        # Image is taller — fit width
        new_w = target_w
        new_h = int(new_w / img_ratio)

    return img.resize((new_w, new_h), Image.LANCZOS)


# ── Ken Burns Effect ────────────────────────────────────


def ken_burns_frame(
    img: Image.Image,
    t: float,
    frame_size: tuple[int, int] = None,
    zoom_start: float = 1.0,
    zoom_end: float = 1.2,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
) -> np.ndarray:
    """
    Generate a single Ken Burns frame at time t (0.0 to 1.0).
    Applies smooth zoom and pan to create cinematic motion.
    Returns numpy array (H, W, 3) uint8.
    """
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    fw, fh = frame_size

    # Smooth easing (ease-in-out cubic)
    t_eased = 3 * t**2 - 2 * t**3

    # Interpolate zoom
    zoom = zoom_start + (zoom_end - zoom_start) * t_eased

    # Calculate crop region
    crop_w = int(fw / zoom)
    crop_h = int(fh / zoom)

    # Center point with pan offset
    cx = img.width / 2 + pan_x * img.width * t_eased
    cy = img.height / 2 + pan_y * img.height * t_eased

    # Clamp to valid region
    x1 = max(0, int(cx - crop_w / 2))
    y1 = max(0, int(cy - crop_h / 2))
    x2 = min(img.width, x1 + crop_w)
    y2 = min(img.height, y1 + crop_h)

    # Adjust if clamped
    if x2 - x1 < crop_w:
        x1 = max(0, x2 - crop_w)
    if y2 - y1 < crop_h:
        y1 = max(0, y2 - crop_h)

    cropped = img.crop((x1, y1, x2, y2))
    frame = cropped.resize(frame_size, Image.LANCZOS)

    return np.array(frame)


# ── Crossfade Transition ────────────────────────────────


def crossfade(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
    t: float,
) -> np.ndarray:
    """Smooth crossfade between two frames. t: 0.0 (all A) to 1.0 (all B)."""
    t_smooth = 3 * t**2 - 2 * t**3  # ease-in-out
    blended = (1 - t_smooth) * frame_a.astype(np.float32) + t_smooth * frame_b.astype(np.float32)
    return np.clip(blended, 0, 255).astype(np.uint8)


# ── Vignette Effect ─────────────────────────────────────


def apply_vignette(
    frame: np.ndarray,
    intensity: float = 0.4,
) -> np.ndarray:
    """Apply a cinematic vignette (darkened edges)."""
    h, w = frame.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    # Normalized distance from center
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    # Smooth vignette mask
    vignette = 1 - np.clip((dist - 0.5) * intensity * 2, 0, intensity)
    vignette = vignette[..., np.newaxis]
    result = (frame.astype(np.float32) * vignette).astype(np.uint8)
    return result


# ── Color Grading ───────────────────────────────────────


def color_grade(
    frame: np.ndarray,
    warmth: float = 0.05,
    contrast: float = 1.1,
    brightness: float = 1.0,
) -> np.ndarray:
    """Apply cinematic color grading — warm tones, lifted shadows."""
    f = frame.astype(np.float32)

    # Contrast adjustment (pivot at 128)
    f = (f - 128) * contrast + 128

    # Brightness
    f *= brightness

    # Warmth (add to red/green, reduce blue slightly)
    f[:, :, 0] += warmth * 255  # Red
    f[:, :, 1] += warmth * 128  # Green (less)
    f[:, :, 2] -= warmth * 64   # Blue

    # Lift shadows slightly (prevents pure black)
    f = np.clip(f, 8, 255)

    return f.astype(np.uint8)


# ── Text Overlays ───────────────────────────────────────


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font, falling back gracefully."""
    font_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        # Windows
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        # Linux / fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def render_text_overlay(
    frame: np.ndarray,
    text: str,
    position: str = "lower_third",
    opacity: float = 0.9,
    font_size: int = 42,
    max_width_pct: float = 0.75,
) -> np.ndarray:
    """
    Render styled text overlay on a frame.
    Positions: 'center', 'lower_third', 'upper', 'title'
    """
    h, w = frame.shape[:2]
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    is_title = position == "title"
    font = _get_font(font_size * (2 if is_title else 1), bold=is_title)
    actual_font_size = font_size * (2 if is_title else 1)

    # Word wrap
    max_width = int(w * max_width_pct)
    lines = _word_wrap(draw, text, font, max_width)
    line_height = actual_font_size + 8

    # Calculate total text block height
    block_height = len(lines) * line_height
    pad = 20

    # Position
    if position == "lower_third":
        text_y = int(h * 0.72)
        bg_y1 = text_y - pad
        bg_y2 = text_y + block_height + pad
    elif position == "upper":
        text_y = int(h * 0.08)
        bg_y1 = text_y - pad
        bg_y2 = text_y + block_height + pad
    elif position == "title":
        text_y = (h - block_height) // 2
        bg_y1 = text_y - pad * 2
        bg_y2 = text_y + block_height + pad * 2
    else:  # center
        text_y = (h - block_height) // 2
        bg_y1 = text_y - pad
        bg_y2 = text_y + block_height + pad

    # Draw semi-transparent background bar
    bg_alpha = int(180 * opacity)
    draw.rectangle(
        [(0, bg_y1), (w, bg_y2)],
        fill=(15, 15, 20, bg_alpha),
    )

    # Draw subtle accent line
    accent_color = (0, 150, 255, int(200 * opacity))  # Blue accent
    draw.rectangle(
        [(0, bg_y1), (4, bg_y2)],
        fill=accent_color,
    )

    # Draw text
    text_color = (255, 255, 255, int(255 * opacity))
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        if position == "title":
            tx = (w - tw) // 2
        else:
            tx = int(w * 0.05)
        ty = text_y + i * line_height
        # Drop shadow
        draw.text(
            (tx + 2, ty + 2),
            line,
            fill=(0, 0, 0, int(150 * opacity)),
            font=font,
        )
        draw.text((tx, ty), line, fill=text_color, font=font)

    # Composite
    result = Image.alpha_composite(img, overlay)
    return np.array(result.convert("RGB"))


def _word_wrap(
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines or [""]


# ── Animated Text (fade in/out) ─────────────────────────


def text_opacity_at_time(
    t: float,
    scene_duration: float,
    fade_in: float = 0.8,
    fade_out: float = 0.8,
) -> float:
    """Calculate text opacity at time t within a scene."""
    if t < fade_in:
        return t / fade_in
    elif t > scene_duration - fade_out:
        return max(0, (scene_duration - t) / fade_out)
    else:
        return 1.0


# ── Split-Screen Layout ──────────────────────────────────


def render_split_screen(
    frame_left: np.ndarray,
    frame_right: np.ndarray,
    frame_size: tuple[int, int] = None,
    gap: int = None,
) -> np.ndarray:
    """
    Render two images side-by-side with a subtle divider.
    Both inputs should be full-resolution frames (H, W, 3).
    """
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    if gap is None:
        gap = Config.SPLIT_SCREEN_GAP

    fw, fh = frame_size
    half_w = (fw - gap) // 2

    canvas = np.zeros((fh, fw, 3), dtype=np.uint8)

    # Resize left panel
    left_img = Image.fromarray(frame_left).resize((half_w, fh), Image.LANCZOS)
    canvas[:, :half_w] = np.array(left_img)

    # Subtle divider (dark gray line)
    canvas[:, half_w:half_w + gap] = 40

    # Resize right panel (clamp to canvas width to avoid off-by-one overflow)
    right_img = Image.fromarray(frame_right).resize((half_w, fh), Image.LANCZOS)
    right_start = half_w + gap
    right_end = min(right_start + half_w, fw)
    canvas[:, right_start:right_end] = np.array(right_img)[:, :right_end - right_start]

    return canvas


# ── Picture-in-Picture Layout ────────────────────────────


def render_picture_in_picture(
    background_frame: np.ndarray,
    inset_image: Image.Image,
    frame_size: tuple[int, int] = None,
    pip_scale: float = None,
    padding: int = None,
    corner_radius: int = None,
    shadow_offset: int = None,
    corner: str = "bottom_right",
) -> np.ndarray:
    """
    Render a full-frame background with a rounded-corner inset card + drop shadow.
    corner: 'bottom_right', 'bottom_left', 'top_right', 'top_left'
    """
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    if pip_scale is None:
        pip_scale = Config.PIP_SCALE
    if padding is None:
        padding = Config.PIP_PADDING
    if corner_radius is None:
        corner_radius = Config.PIP_CORNER_RADIUS
    if shadow_offset is None:
        shadow_offset = Config.PIP_SHADOW_OFFSET

    fw, fh = frame_size

    # Size the inset
    inset_w = int(fw * pip_scale)
    inset_h = int(inset_w * inset_image.height / max(inset_image.width, 1))
    inset_h = min(inset_h, int(fh * 0.45))  # cap height

    inset_resized = inset_image.convert("RGB").resize((inset_w, inset_h), Image.LANCZOS)

    # Create rounded-corner mask
    mask = Image.new("L", (inset_w, inset_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (inset_w - 1, inset_h - 1)],
        radius=corner_radius,
        fill=255,
    )

    # Position based on corner
    if corner == "bottom_right":
        ix = fw - inset_w - padding
        iy = fh - inset_h - padding
    elif corner == "bottom_left":
        ix = padding
        iy = fh - inset_h - padding
    elif corner == "top_right":
        ix = fw - inset_w - padding
        iy = padding
    else:  # top_left
        ix = padding
        iy = padding

    # Build composite on PIL for alpha blending
    bg_img = Image.fromarray(background_frame).convert("RGB").resize(frame_size, Image.LANCZOS)

    # Drop shadow
    shadow = Image.new("RGBA", (inset_w, inset_h), (0, 0, 0, 100))
    shadow_mask = mask.copy()
    bg_img.paste(
        Image.new("RGB", (inset_w, inset_h), (0, 0, 0)),
        (ix + shadow_offset, iy + shadow_offset),
        shadow_mask,
    )

    # Paste inset with rounded mask
    bg_img.paste(inset_resized, (ix, iy), mask)

    # Thin border
    overlay = Image.new("RGBA", bg_img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [(ix, iy), (ix + inset_w - 1, iy + inset_h - 1)],
        radius=corner_radius,
        outline=(255, 255, 255, 60),
        width=2,
    )
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")

    return np.array(bg_img)


# ── Table Card Rendering ─────────────────────────────────


def render_table_card(
    table_image: Image.Image,
    frame_size: tuple[int, int] = None,
    padding: int = None,
) -> np.ndarray:
    """
    Render a table image as a clean styled card centered on a dark background
    with highlighted appearance (subtle border, rounded corners, shadow).
    """
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    if padding is None:
        padding = Config.TABLE_CARD_PADDING

    fw, fh = frame_size

    # Scale table to fit within padded area
    max_w = fw - padding * 4
    max_h = fh - padding * 4
    table_img = table_image.convert("RGB")
    table_img.thumbnail((max_w, max_h), Image.LANCZOS)
    tw, th = table_img.size

    # Create dark background
    canvas = Image.new("RGB", (fw, fh), (18, 18, 28))

    # Card background (slightly lighter)
    card_w = tw + padding * 2
    card_h = th + padding * 2
    card_x = (fw - card_w) // 2
    card_y = (fh - card_h) // 2

    card = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card)

    # Drop shadow
    card_draw.rounded_rectangle(
        [(card_x + 4, card_y + 4), (card_x + card_w + 4, card_y + card_h + 4)],
        radius=12,
        fill=(0, 0, 0, 120),
    )

    # Card background
    card_draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_w, card_y + card_h)],
        radius=12,
        fill=(30, 30, 45, 240),
    )

    # Subtle top accent line
    card_draw.rectangle(
        [(card_x + 12, card_y), (card_x + card_w - 12, card_y + 3)],
        fill=(0, 150, 255, 180),
    )

    canvas = Image.alpha_composite(canvas.convert("RGBA"), card).convert("RGB")

    # Paste table image centered in card
    table_x = card_x + padding
    table_y = card_y + padding
    canvas.paste(table_img, (table_x, table_y))

    return np.array(canvas)


# ── Callout Text Overlay ─────────────────────────────────


def render_callout_overlay(
    frame: np.ndarray,
    callout_text: str,
    position: str = "upper_right",
    opacity: float = 0.9,
    font_size: int = 28,
) -> np.ndarray:
    """
    Render a small callout/annotation box on a frame.
    Used for chart/diagram annotations (e.g., 'Revenue grew 45%').
    """
    h, w = frame.shape[:2]
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _get_font(font_size, bold=True)

    # Measure text
    bbox = draw.textbbox((0, 0), callout_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = 16

    # Position the callout box
    if position == "upper_right":
        bx = w - tw - pad * 3
        by = int(h * 0.06)
    elif position == "upper_left":
        bx = pad * 2
        by = int(h * 0.06)
    elif position == "lower_right":
        bx = w - tw - pad * 3
        by = int(h * 0.60)
    else:  # lower_left
        bx = pad * 2
        by = int(h * 0.60)

    bg_alpha = int(200 * opacity)
    # Rounded background box
    draw.rounded_rectangle(
        [(bx - pad, by - pad), (bx + tw + pad, by + th + pad)],
        radius=8,
        fill=(10, 10, 20, bg_alpha),
    )

    # Accent dot
    draw.ellipse(
        [(bx - pad + 6, by + th // 2 - 3), (bx - pad + 12, by + th // 2 + 3)],
        fill=(0, 180, 255, int(255 * opacity)),
    )

    # Text
    draw.text(
        (bx, by),
        callout_text,
        fill=(255, 255, 255, int(255 * opacity)),
        font=font,
    )

    result = Image.alpha_composite(img, overlay)
    return np.array(result.convert("RGB"))


# ── Logo Watermark Overlay ───────────────────────────────


def render_logo_watermark(
    frame: np.ndarray,
    logo_image: Image.Image,
    frame_size: tuple[int, int] = None,
    scale: float = None,
    opacity: float = None,
    corner: str = "top_right",
    padding: int = 20,
) -> np.ndarray:
    """
    Render a logo as a subtle corner watermark overlay.
    Logos are NOT used as scene visuals — only as watermarks.
    """
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    if scale is None:
        scale = Config.LOGO_WATERMARK_SCALE
    if opacity is None:
        opacity = Config.LOGO_WATERMARK_OPACITY

    fw, fh = frame_size

    # Scale logo
    logo_w = int(fw * scale)
    logo = logo_image.copy()
    logo.thumbnail((logo_w, logo_w), Image.LANCZOS)
    lw, lh = logo.size

    # Position
    if corner == "top_right":
        lx = fw - lw - padding
        ly = padding
    elif corner == "top_left":
        lx = padding
        ly = padding
    elif corner == "bottom_right":
        lx = fw - lw - padding
        ly = fh - lh - padding
    else:
        lx = padding
        ly = fh - lh - padding

    # Composite with opacity
    bg_img = Image.fromarray(frame).convert("RGBA")
    logo_rgba = logo.convert("RGBA")

    # Apply opacity to alpha channel
    r, g, b, a = logo_rgba.split()
    a = a.point(lambda x: int(x * opacity))
    logo_rgba = Image.merge("RGBA", (r, g, b, a))

    bg_img.paste(logo_rgba, (lx, ly), logo_rgba)

    return np.array(bg_img.convert("RGB"))


# ── Black Frame ─────────────────────────────────────────


def black_frame(frame_size: tuple[int, int] = None) -> np.ndarray:
    """Create a solid black frame."""
    if frame_size is None:
        frame_size = Config.VIDEO_SIZE
    return np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)
