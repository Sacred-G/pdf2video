# 🎬 PDF2Video

Convert any PDF into a cinematic, AI-narrated video — not a slideshow.

**PDF2Video** extracts content from your PDF, writes a documentary-style script with GPT-5.2 (Responses API with structured output), generates HD voiceover with OpenAI TTS, creates atmospheric backgrounds with gpt-image-1, and renders everything into a polished video with cinematic effects — all GPU-accelerated on your RTX 5090.

---

## ✨ Features

- **AI Script Generation** — GPT-5.2 analyzes your PDF and writes a compelling narrative (Responses API + structured output)
- **HD Voiceover** — OpenAI TTS-HD with 6 voice options for natural narration
- **AI-Generated Backgrounds** — gpt-image-1 creates atmospheric visuals for scenes that need them
- **Cinematic Effects** — Ken Burns pan/zoom, crossfades, vignettes, color grading
- **Smart Text Overlays** — Animated lower-thirds with fade effects
- **GPU-Accelerated Export** — NVIDIA NVENC encoding on RTX 5090 for fast renders
- **Background Music** — Optional music track mixed under narration
- **Web UI** — Clean Streamlit interface for drag-and-drop operation
- **CLI** — Full command-line support for batch processing

---

## 🖥️ System Requirements

Optimized for your rig:
- **CPU:** AMD Ryzen 9 9950X3D (16C/32T utilized for parallel processing)
- **GPU:** NVIDIA RTX 5090 32GB (NVENC encoding, CUDA acceleration)
- **RAM:** 64GB (comfortable headroom for 4K rendering)
- **OS:** Windows 10/11 with latest NVIDIA drivers

### Software Prerequisites

1. **Python 3.11+** — [python.org](https://www.python.org/downloads/)
2. **FFmpeg with NVENC** — Required for GPU-accelerated encoding
3. **OpenAI API Key** — For GPT-5.2, TTS, and gpt-image-1

---

## 🚀 Setup

### 1. Install FFmpeg with NVENC Support

**Option A: Using Chocolatey (recommended)**
```powershell
choco install ffmpeg-full
```

**Option B: Manual Install**
Download from [gyan.dev/ffmpeg](https://www.gyan.dev/ffmpeg/builds/) (get the "full" build), extract, and add to PATH.

Verify NVENC:
```powershell
ffmpeg -encoders | findstr nvenc
# Should show: h264_nvenc, hevc_nvenc
```

### 2. Clone & Install

```powershell
# Navigate to your projects folder
cd C:\Projects

# Clone or copy the pdf2video folder
# Then install dependencies:
cd pdf2video
pip install -r requirements.txt
```

### 3. Configure

```powershell
# Copy the example env file
copy .env.example .env

# Edit .env and add your OpenAI API key
notepad .env
```

Set at minimum:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

---

## 📖 Usage

### Web UI (Recommended)

```powershell
streamlit run app.py
```

This opens a browser UI where you can:
1. Upload your PDF
2. Choose voice, resolution, and options
3. Click Generate and watch it build
4. Preview and download the video

### Command Line

```powershell
# Basic usage
python -m core.pipeline your_document.pdf

# With options
python -m core.pipeline presentation.pdf -o output.mp4 -v nova --no-backgrounds

# With background music
python -m core.pipeline report.pdf -m ambient_music.mp3 -v onyx
```

**CLI Options:**
| Flag | Description |
|------|-------------|
| `-o, --output` | Output video path |
| `-v, --voice` | TTS voice: alloy, echo, fable, onyx, nova, shimmer |
| `-m, --music` | Background music file (mp3/wav) |
| `--no-backgrounds` | Skip AI background generation (faster/cheaper) |

---

## 🎙️ Voice Options

| Voice | Style | Best For |
|-------|-------|----------|
| **onyx** | Deep, authoritative | Documentaries, reports |
| **alloy** | Balanced, versatile | General purpose |
| **echo** | Warm, conversational | Friendly explainers |
| **fable** | Expressive, dynamic | Storytelling |
| **nova** | Bright, engaging | Upbeat content |
| **shimmer** | Soft, clear | Gentle presentations |

---

## 🏗️ Architecture

```
PDF Upload
    │
    ▼
┌─────────────────────┐
│  PDF Extractor       │  ← PyMuPDF: text, images, page renders
│  (pdf_extractor.py)  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  AI Script Writer    │  ← GPT-5.2 Responses API: narrative script
│  (ai_services.py)    │
└─────────┬───────────┘
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
┌──────┐┌────┐┌──────┐
│ TTS  ││ img ││Script│
│ HD   ││ -1  ││ Data │
└──┬───┘└─┬──┘└──┬───┘
   │      │      │
   ▼      ▼      ▼
┌─────────────────────┐
│  Video Composer      │  ← MoviePy + NumPy: Ken Burns, transitions
│  (video_composer.py) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  NVENC GPU Export    │  ← FFmpeg h264_nvenc on RTX 5090
│  (ffmpeg)            │
└─────────┬───────────┘
          │
          ▼
     MP4 Video
```

---

## 💰 API Cost Estimates

Per video (approximate, varies by PDF length):

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| GPT-5.2 | Script generation (~2K tokens) | ~$0.03 |
| TTS-HD | Narration (~500 words) | ~$0.05 |
| gpt-image-1 | 2-4 backgrounds | ~$0.08-0.16 |
| **Total** | | **~$0.16-0.24** |

Use `--no-backgrounds` to cut costs roughly in half.

---

## 🔧 Customization

### Video Quality Presets

In `.env`:
```bash
# Fast preview
VIDEO_FPS=24
VIDEO_BITRATE=6M

# High quality (default)
VIDEO_FPS=30
VIDEO_BITRATE=12M

# Maximum quality (4K)
VIDEO_WIDTH=3840
VIDEO_HEIGHT=2160
VIDEO_FPS=60
VIDEO_BITRATE=30M
```

### Custom Fonts

Drop `.ttf` files in `assets/fonts/` and update the font paths in `core/effects.py`.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "NVENC not found" | Update NVIDIA drivers, ensure FFmpeg has NVENC support |
| "OPENAI_API_KEY not set" | Create `.env` file from `.env.example` |
| Slow rendering | Check GPU utilization with `nvidia-smi` |
| Audio sync issues | Ensure FFmpeg is up to date |
| Out of memory | Reduce resolution or close other GPU apps |

---

## 📁 Project Structure

```
pdf2video/
├── app.py                 # Streamlit web UI
├── requirements.txt       # Python dependencies
├── .env.example          # Environment config template
├── core/
│   ├── __init__.py
│   ├── config.py         # Centralized settings
│   ├── pdf_extractor.py  # PDF content extraction
│   ├── ai_services.py    # OpenAI integration
│   ├── effects.py        # Visual effects engine
│   ├── video_composer.py # Video assembly & export
│   └── pipeline.py       # End-to-end orchestrator
├── assets/               # Static assets (fonts, etc.)
├── output/               # Generated videos
└── temp/                 # Temporary working files
```
