<div align="center">

# 🎬 PDF2Video

**Transform PDFs into cinematic, AI-narrated videos — not slideshows.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5.2-412991?logo=openai&logoColor=white)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Upload a PDF → AI writes a documentary-style script → generates HD voiceover → classifies every image → composes a polished video with cinematic effects.

[Getting Started](#-getting-started) · [Features](#-features) · [Architecture](#-architecture) · [API Costs](#-api-cost-estimates)

</div>

---

## 🎥 What It Does

PDF2Video takes any PDF document and produces a professional narrated video:

1. **Extracts** text and images from your PDF (PyMuPDF + pdfplumber)
2. **Classifies** every image using AI vision — charts, diagrams, tables, photos, logos
3. **Writes** a documentary-style narration script (GPT-5.2 Responses API)
4. **Generates** HD voiceover (OpenAI TTS with 6 voice options)
5. **Creates** atmospheric AI backgrounds for scenes that need them (gpt-image-1)
6. **Composes** a cinematic video with Ken Burns effects, smart layouts, transitions, and overlays
7. **Exports** with GPU acceleration (NVENC) or automatic CPU fallback

All orchestrated through a modern web UI with real-time progress tracking.

---

## ✨ Features

### AI Pipeline
- **Smart Image Classification** — AI vision categorizes every image (chart, diagram, table, photo, logo, decorative) for optimal composition
- **Structured Script Generation** — GPT-5.2 with structured output produces scene-by-scene narration with layout hints
- **HD Voiceover** — OpenAI TTS with 6 voice options for natural narration
- **AI Backgrounds** — gpt-image-1 generates atmospheric visuals for scenes that need them

### Video Composition
- **Multi-Layout Engine** — Split-screen, picture-in-picture, carousel, and single layouts chosen per-scene by AI
- **Ken Burns Effects** — Cinematic pan/zoom with per-image parameters based on content type
- **Smart Overlays** — Lower-third text, callout boxes for charts, logo watermarks
- **Crossfade Transitions** — Smooth scene-to-scene transitions with color grading and vignettes
- **Background Music** — Optional music track mixed under narration at configurable volume

### Full-Stack Web App
- **Next.js 15 Frontend** — React 19, shadcn/ui, Tailwind CSS 4, dark/light theme
- **FastAPI Backend** — Async Python with PostgreSQL, JWT auth, file uploads
- **Real-Time Progress** — SSE streaming shows live pipeline status in the browser
- **Job Queue** — Background workers with async task dispatch
- **Drag-and-Drop Upload** — PDF, image, and music upload with progress bars
- **Video Library** — Browse, stream, and download generated videos

### Performance
- **GPU-Accelerated Export** — NVIDIA NVENC encoding with automatic CPU (libx264) fallback
- **Auto-Tuned Workers** — Thread pool sized to your hardware
- **Async Everything** — Non-blocking I/O from database to file storage

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15+**
- **FFmpeg** (with NVENC support for GPU encoding, or CPU-only is fine)
- **OpenAI API Key** with access to GPT, TTS, and image generation

### 1. Clone

```bash
git clone https://github.com/Sacred-G/pdf2video.git
cd pdf2video
```

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb pdf2video
# Or with psql:
# CREATE USER pdf2video WITH PASSWORD 'password';
# CREATE DATABASE pdf2video OWNER pdf2video;
```

Update `DATABASE_URL` in `.env` if your credentials differ from the defaults.

### 4. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
cd ..
```

### 5. Run

```bash
# Terminal 1 — Backend (from project root)
source .venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open **http://localhost:3000** — register an account, upload a PDF, and generate your first video.

---

## 🎙️ Voice Options

| Voice | Style | Best For |
|-------|-------|----------|
| **onyx** | Deep, authoritative | Documentaries, training, reports |
| **alloy** | Balanced, versatile | General purpose |
| **echo** | Warm, conversational | Friendly explainers |
| **fable** | Expressive, dynamic | Storytelling |
| **nova** | Bright, engaging | Upbeat content |
| **shimmer** | Soft, clear | Gentle presentations |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (Next.js 15)                       │
│  Dashboard · Create Job · Job Progress · Video Library       │
│  React 19 · shadcn/ui · Tailwind · Zustand · SSE            │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼──────────────────────────────────┐
│                   FASTAPI BACKEND                            │
│                                                              │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐  │
│  │ Auth    │  │ Jobs API │  │ Uploads │  │ Video Stream │  │
│  │ (JWT)   │  │ (CRUD)   │  │ (Files) │  │ (Range)      │  │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └──────────────┘  │
│       │            │             │                           │
│  ┌────▼────────────▼─────────────▼────────────────────────┐ │
│  │           Background Worker (ThreadPool)                │ │
│  │                                                         │ │
│  │  PDF Extract → Classify → Script → TTS → Compose → Export │
│  │       ↑            ↑         ↑       ↑        ↑          │ │
│  │    PyMuPDF    GPT Vision   GPT-5.2  TTS   MoviePy+FFmpeg │ │
│  └─────────────────────────────────────────────────────────┘ │
│       │                                                      │
│  ┌────▼─────┐  ┌───────────┐  ┌────────────────────────┐   │
│  │PostgreSQL│  │   Redis   │  │  File Storage (local)  │   │
│  │(metadata)│  │(jobs/cache)│  │  uploads/ videos/ temp/│   │
│  └──────────┘  └───────────┘  └────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Core Pipeline Flow

```
PDF → Extract text + images
        │
        ├─→ AI Vision classifies each image (chart/diagram/table/photo/logo)
        │
        ├─→ GPT-5.2 writes scene-by-scene script with layout hints
        │
        ├─→ OpenAI TTS generates voiceover per scene
        │
        ├─→ gpt-image-1 creates AI backgrounds (optional)
        │
        └─→ Video Composer assembles everything:
              • Ken Burns pan/zoom per image type
              • Split-screen, PiP, carousel layouts
              • Text overlays, logo watermarks
              • Crossfade transitions, color grading
              • GPU export (NVENC) or CPU fallback (libx264)
                    │
                    ▼
               MP4 Video
```

---

## 📁 Project Structure

```
pdf2video/
├── core/                          # AI video pipeline (standalone)
│   ├── pipeline.py                # End-to-end orchestrator
│   ├── pdf_extractor.py           # PDF content extraction
│   ├── ai_services.py             # OpenAI GPT + TTS + image generation
│   ├── image_classifier.py        # AI vision image classification
│   ├── video_composer.py          # Video assembly, layouts, export
│   ├── effects.py                 # Ken Burns, overlays, transitions
│   ├── content_input.py           # Content data structures
│   └── config.py                  # Centralized settings
│
├── backend/                       # FastAPI server
│   ├── main.py                    # App factory, CORS, lifespan
│   ├── config.py                  # Pydantic settings
│   ├── api/v1/                    # REST endpoints
│   │   ├── auth.py                # Register, login, JWT refresh
│   │   ├── jobs.py                # Job CRUD + background dispatch
│   │   ├── uploads.py             # File upload (PDF, images, music)
│   │   ├── videos.py              # Stream, download, delete
│   │   └── health.py              # Health check + GPU status
│   ├── models/                    # SQLAlchemy ORM (User, Job, Video, Upload)
│   ├── services/                  # Business logic layer
│   ├── workers/                   # Background job workers
│   └── db/                        # Database session + migrations
│
├── frontend/                      # Next.js 15 app
│   ├── src/app/                   # App Router pages
│   │   ├── page.tsx               # Dashboard
│   │   ├── create/                # Job creation wizard
│   │   ├── jobs/                  # Job list + detail + progress
│   │   ├── videos/                # Video library + player
│   │   ├── login/ & register/     # Authentication
│   │   └── settings/              # User settings
│   ├── src/components/            # UI components (shadcn/ui)
│   ├── src/hooks/                 # React hooks (auth, upload, SSE)
│   ├── src/stores/                # Zustand state (auth, jobs)
│   └── src/lib/                   # API client, auth helpers
│
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
└── docs/ARCHITECTURE_PLAN.md      # Detailed architecture document
```

---

## 💰 API Cost Estimates

Per video (approximate, varies by PDF length):

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| GPT-5.2 | Image classification + script generation | ~$0.05 |
| OpenAI TTS | Narration (~500 words) | ~$0.03 |
| gpt-image-1 | AI backgrounds (2-4 per video) | ~$0.08-0.16 |
| **Total** | | **~$0.16-0.24** |

Disable AI backgrounds in job settings to cut costs roughly in half.

---

## ⚙️ Configuration

Key settings in `.env`:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# AI Models
OPENAI_CHAT_MODEL=gpt-5.2          # Script generation
OPENAI_TTS_MODEL=tts-1             # Voiceover (tts-1 or tts-1-hd)
OPENAI_TTS_VOICE=onyx              # Default voice
OPENAI_IMAGE_MODEL=gpt-image-1     # AI backgrounds

# Video Output
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080
VIDEO_FPS=30
VIDEO_BITRATE=12M

# Database
DATABASE_URL=postgresql+asyncpg://pdf2video:password@localhost:5432/pdf2video

# Performance
NUM_WORKERS=8                       # CPU threads for rendering
AUTO_TUNE_WORKERS=true              # Auto-detect optimal thread count
```

### GPU vs CPU

The app auto-detects your hardware:
- **NVIDIA GPU (NVENC)**: Fast encoding, recommended for production
- **CPU (libx264)**: Works on any machine, just slower for the export step

No configuration needed — it falls back automatically.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| NVENC not found | Works fine on CPU — this is just informational |
| OPENAI_API_KEY not set | Copy `.env.example` to `.env` and add your key |
| TTS model access denied | Enable TTS models in your OpenAI project settings |
| Slow rendering | Expected on CPU; GPU (NVENC) is ~5-10x faster |
| Database connection error | Ensure PostgreSQL is running and `DATABASE_URL` is correct |
| Frontend can't reach backend | Backend must be running on port 8000 |

---

## 🗺️ Roadmap

- [ ] Preset system (save/load video generation settings)
- [ ] Redis integration for scalable job queue
- [ ] Docker Compose for one-command setup
- [ ] Celery workers for horizontal scaling
- [ ] Video editing / scene-level regeneration
- [ ] Public sharing with signed URLs
- [ ] Batch processing (ZIP of PDFs)
- [ ] Multi-language narration

See [ARCHITECTURE_PLAN.md](docs/ARCHITECTURE_PLAN.md) for the full technical roadmap.

---

## 📄 License

MIT

---

<div align="center">

Built with [FastAPI](https://fastapi.tiangolo.com) · [Next.js](https://nextjs.org) · [OpenAI](https://openai.com) · [MoviePy](https://zulko.github.io/moviepy/) · [shadcn/ui](https://ui.shadcn.com)

</div>
