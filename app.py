"""
PDF2Video — Streamlit Web UI
Upload a PDF and generate a cinematic video with AI narration.
"""

import subprocess
import streamlit as st
import tempfile
import time
from pathlib import Path
from PIL import Image
from core.config import Config
from core.content_input import content_from_text_and_images
from core.pipeline import PDF2VideoPipeline

# ── Page Config ─────────────────────────────────────────

st.set_page_config(
    page_title="PDF2Video",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .status-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────

st.markdown('<div class="main-header"><h1>🎬 PDF2Video</h1></div>', unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:#888; margin-top:-10px;'>"
    "Transform PDFs, text, and images into cinematic AI-narrated videos</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Sidebar Settings ────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("🔑 API Key")
    api_key = st.text_input(
        "OpenAI API Key",
        value=Config.OPENAI_API_KEY,
        type="password",
        help="Your OpenAI API key for GPT-5.2, TTS, and gpt-image-1",
    )

    st.divider()
    st.subheader("🎙️ Voice")
    voice = st.selectbox(
        "Narrator Voice",
        options=["onyx", "alloy", "echo", "fable", "nova", "shimmer"],
        index=0,
        help="OpenAI TTS voice for narration",
    )

    voice_descriptions = {
        "onyx": "Deep, authoritative — great for documentaries",
        "alloy": "Balanced, versatile — good all-rounder",
        "echo": "Warm, conversational — friendly explainers",
        "fable": "Expressive, dynamic — storytelling",
        "nova": "Bright, engaging — upbeat content",
        "shimmer": "Soft, clear — gentle presentations",
    }
    st.caption(voice_descriptions.get(voice, ""))

    st.divider()
    st.subheader("🎨 Video Options")

    resolution = st.selectbox(
        "Resolution",
        options=["1920x1080 (Full HD)", "2560x1440 (2K)", "3840x2160 (4K)"],
        index=0,
    )
    res_map = {
        "1920x1080 (Full HD)": (1920, 1080),
        "2560x1440 (2K)": (2560, 1440),
        "3840x2160 (4K)": (3840, 2160),
    }

    fps = st.selectbox("Frame Rate", [24, 30, 60], index=1)

    generate_backgrounds = st.checkbox(
        "Generate AI backgrounds",
        value=True,
        help="Use gpt-image-1 to create atmospheric backgrounds for scenes",
    )

    st.divider()
    st.subheader("🎵 Background Music")
    music_file = st.file_uploader(
        "Upload music (optional)",
        type=["mp3", "wav", "ogg", "m4a"],
        help="Optional background music played softly under narration",
    )

    st.divider()
    st.subheader("🖥️ GPU Status")
    # Quick GPU check
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        has_nvenc = "h264_nvenc" in result.stdout
    except Exception:
        has_nvenc = False

    if has_nvenc:
        st.success("✅ NVIDIA NVENC detected")
    else:
        st.warning("⚠️ NVENC not found — using CPU encoding")

# ── Main Area — Tabbed Input ───────────────────────────────

tab_pdf, tab_text = st.tabs(["📄 Upload PDF", "✏️ Text & Images"])

# ---- PDF Tab ----
with tab_pdf:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📄 Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload the PDF you want to convert to video",
            key="pdf_uploader",
        )

        if uploaded_file:
            st.success(f"📎 {uploaded_file.name} ({uploaded_file.size / 1024:.0f} KB)")

            # PDF Preview
            with st.expander("📋 PDF Preview", expanded=False):
                try:
                    import fitz
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    try:
                        doc = fitz.open(tmp_path)
                        st.caption(f"Pages: {len(doc)}")
                        page = doc[0]
                        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                        st.image(
                            pix.tobytes("png"),
                            caption="Page 1 preview",
                            use_container_width=True,
                        )
                        doc.close()
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                except Exception as e:
                    st.error(f"Preview failed: {e}")

    with col2:
        st.subheader("🎬 Generate Video")

        if uploaded_file and api_key:
            if st.button("🚀 Generate Video", type="primary", use_container_width=True, key="pdf_generate"):
                # Set configuration
                Config.OPENAI_API_KEY = api_key
                w, h = res_map[resolution]
                Config.VIDEO_WIDTH = w
                Config.VIDEO_HEIGHT = h
                Config.VIDEO_SIZE = (w, h)
                Config.VIDEO_FPS = fps

                # Save uploaded PDF to temp file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                    tmp_pdf.write(uploaded_file.getvalue())
                    pdf_path = Path(tmp_pdf.name)

                # Save music if provided
                music_path = None
                if music_file:
                    with tempfile.NamedTemporaryFile(
                        suffix=f".{music_file.name.split('.')[-1]}",
                        delete=False,
                    ) as tmp_music:
                        tmp_music.write(music_file.getvalue())
                        music_path = tmp_music.name

                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress_pdf(step: str, pct: float):
                    progress_bar.progress(min(pct, 1.0))
                    status_text.markdown(f"**{step}**")

                try:
                    start = time.time()

                    pipeline = PDF2VideoPipeline()
                    output_path = Config.OUTPUT_DIR / f"{uploaded_file.name.rsplit('.', 1)[0]}_video.mp4"

                    result_path = pipeline.run(
                        pdf_path=pdf_path,
                        output_path=output_path,
                        background_music=music_path,
                        voice=voice,
                        generate_backgrounds=generate_backgrounds,
                        progress_callback=update_progress_pdf,
                    )

                    elapsed = time.time() - start
                    progress_bar.progress(1.0)
                    status_text.markdown("**✅ Video generated!**")

                    st.balloons()
                    st.success(f"Video created in {elapsed:.1f} seconds!")

                    if result_path.exists():
                        st.video(str(result_path))
                        with open(result_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Video",
                                data=f.read(),
                                file_name=result_path.name,
                                mime="video/mp4",
                                type="primary",
                                use_container_width=True,
                                key="pdf_download",
                            )

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.exception(e)

        elif not api_key:
            st.info("👈 Enter your OpenAI API key in the sidebar to get started.")
        else:
            st.info("👆 Upload a PDF file to begin.")

# ---- Text & Images Tab ----
with tab_text:
    col_input, col_gen = st.columns([1, 1])

    with col_input:
        st.subheader("✏️ Your Content")

        video_title = st.text_input(
            "Video Title",
            placeholder="My Awesome Video",
            help="Title for your video (used in intro card)",
        )

        text_content = st.text_area(
            "Text / Script",
            height=250,
            placeholder=(
                "Paste your text here. Separate sections with blank lines.\n\n"
                "Each paragraph becomes a potential video scene.\n\n"
                "The AI will write engaging narration based on your content "
                "and intelligently place your uploaded images."
            ),
            help="The AI will turn this into a cinematic narration. Separate sections with blank lines.",
        )

        st.subheader("🖼️ Upload Images")
        uploaded_images = st.file_uploader(
            "Choose images",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif"],
            accept_multiple_files=True,
            help="Upload images to include in the video. The AI will decide where each image fits best and generate additional visuals for scenes that need them.",
            key="image_uploader",
        )

        if uploaded_images:
            st.success(f"🖼️ {len(uploaded_images)} image(s) uploaded")
            # Image preview grid
            preview_cols = st.columns(min(len(uploaded_images), 4))
            for i, img_file in enumerate(uploaded_images):
                with preview_cols[i % len(preview_cols)]:
                    st.image(
                        img_file,
                        caption=img_file.name,
                        use_container_width=True,
                    )

    with col_gen:
        st.subheader("🎬 Generate Video")

        has_content = bool(text_content and text_content.strip())
        has_images = bool(uploaded_images)

        if has_content and api_key:
            if has_images:
                st.info(
                    f"📷 **{len(uploaded_images)} images** will be analyzed by AI vision. "
                    f"The AI will place each image in the most relevant scene and "
                    f"generate additional backgrounds only where needed."
                )
            else:
                st.info(
                    "🎨 No images uploaded — the AI will generate all visual backgrounds. "
                    "Upload images for a more personalized video!"
                )

            if st.button("🚀 Generate Video", type="primary", use_container_width=True, key="text_generate"):
                # Set configuration
                Config.OPENAI_API_KEY = api_key
                w, h = res_map[resolution]
                Config.VIDEO_WIDTH = w
                Config.VIDEO_HEIGHT = h
                Config.VIDEO_SIZE = (w, h)
                Config.VIDEO_FPS = fps

                # Load uploaded images as PIL
                pil_images = []
                image_labels = []
                for img_file in (uploaded_images or []):
                    try:
                        pil_img = Image.open(img_file).convert("RGB")
                        pil_images.append(pil_img)
                        image_labels.append(img_file.name)
                    except Exception as e:
                        st.warning(f"Could not load {img_file.name}: {e}")

                # Build ContentInput
                content = content_from_text_and_images(
                    title=video_title or "Untitled Video",
                    text=text_content,
                    images=pil_images,
                    image_labels=image_labels,
                )

                # Save music if provided
                music_path = None
                if music_file:
                    with tempfile.NamedTemporaryFile(
                        suffix=f".{music_file.name.split('.')[-1]}",
                        delete=False,
                    ) as tmp_music:
                        tmp_music.write(music_file.getvalue())
                        music_path = tmp_music.name

                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress_text(step: str, pct: float):
                    progress_bar.progress(min(pct, 1.0))
                    status_text.markdown(f"**{step}**")

                try:
                    start = time.time()

                    pipeline = PDF2VideoPipeline()

                    result_path = pipeline.run_from_content(
                        content=content,
                        background_music=music_path,
                        voice=voice,
                        generate_backgrounds=generate_backgrounds,
                        progress_callback=update_progress_text,
                    )

                    elapsed = time.time() - start
                    progress_bar.progress(1.0)
                    status_text.markdown("**✅ Video generated!**")

                    st.balloons()
                    st.success(f"Video created in {elapsed:.1f} seconds!")

                    if result_path.exists():
                        st.video(str(result_path))
                        with open(result_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Video",
                                data=f.read(),
                                file_name=result_path.name,
                                mime="video/mp4",
                                type="primary",
                                use_container_width=True,
                                key="text_download",
                            )

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.exception(e)

        elif not api_key:
            st.info("👈 Enter your OpenAI API key in the sidebar to get started.")
        elif not has_content:
            st.info("✏️ Enter some text to begin. Images are optional but recommended!")

# ── Footer ──────────────────────────────────────────────

st.divider()
st.markdown(
    "<p style='text-align:center; color:#666; font-size:0.85rem;'>"
    "PDF2Video • Powered by OpenAI GPT-5.2, TTS HD, gpt-image-1 • "
    "GPU-accelerated with NVIDIA NVENC"
    "</p>",
    unsafe_allow_html=True,
)
