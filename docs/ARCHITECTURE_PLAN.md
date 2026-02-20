# PDF2Video — Production Architecture Plan

## Next.js + FastAPI Full-Stack Conversion

> **Goal**: Convert from Streamlit to a production-grade Next.js frontend + FastAPI backend, preserving the entire `core/` pipeline, with async job processing, real-time progress, authentication, and an extensible architecture for future features.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Project Structure](#2-project-structure)
3. [Backend — FastAPI](#3-backend--fastapi)
4. [Frontend — Next.js](#4-frontend--nextjs)
5. [Database Layer](#5-database-layer)
6. [Async Job System](#6-async-job-system)
7. [File Storage & Media Serving](#7-file-storage--media-serving)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [Real-Time Progress (SSE / WebSocket)](#9-real-time-progress-sse--websocket)
10. [API Design — Full Endpoint Specification](#10-api-design--full-endpoint-specification)
11. [Frontend Pages & Components](#11-frontend-pages--components)
12. [Configuration & Environment](#12-configuration--environment)
13. [Error Handling & Logging](#13-error-handling--logging)
14. [Testing Strategy](#14-testing-strategy)
15. [Deployment & Infrastructure](#15-deployment--infrastructure)
16. [Performance & Scaling](#16-performance--scaling)
17. [Security Hardening](#17-security-hardening)
18. [Future Feature Hooks](#18-future-feature-hooks)
19. [Migration Checklist](#19-migration-checklist)
20. [Dependency Manifest](#20-dependency-manifest)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER (Client)                         │
│  Next.js 15 App Router  •  React 19  •  Tailwind  •  shadcn/ui │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │ Dashboard │ │ New Job  │ │ Job View │ │ Video Preview/DL   │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
│         │            │            ▲                              │
│         └────────────┼────────────┼──────── REST + SSE ─────────┤
└─────────────────────────────────────────────────────────────────┘
                       │            │
                       ▼            │
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI SERVER (Python)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ REST API     │  │ SSE Endpoint │  │ Static File Server    │ │
│  │ /api/v1/*    │  │ /api/v1/jobs │  │ /media/*              │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────────┘ │
│         │                 │                                     │
│  ┌──────▼─────────────────▼──────────────────────────────────┐ │
│  │              Job Manager (async task dispatch)             │ │
│  │  Celery + Redis  OR  BackgroundTasks + in-process queue   │ │
│  └──────┬────────────────────────────────────────────────────┘ │
│         │                                                       │
│  ┌──────▼────────────────────────────────────────────────────┐ │
│  │                    core/ (UNCHANGED)                       │ │
│  │  pipeline.py → ai_services.py → image_classifier.py       │ │
│  │  → video_composer.py → effects.py → pdf_extractor.py      │ │
│  └───────────────────────────────────────────────────────────┘ │
│         │                                                       │
│  ┌──────▼──────┐  ┌──────────────┐  ┌────────────────────────┐│
│  │  PostgreSQL  │  │    Redis     │  │  File Storage          ││
│  │  (metadata)  │  │  (jobs/cache)│  │  (local / S3)          ││
│  └─────────────┘  └──────────────┘  └────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

- **`core/` is untouched** — all AI, video, and effects logic stays as-is
- **Backend is a thin API layer** — wraps `core/` pipeline with HTTP endpoints, auth, and job management
- **Frontend is decoupled** — communicates only via REST + SSE, can be deployed independently
- **Jobs are async** — video generation runs in background workers, frontend polls/streams progress
- **Everything is typed** — Pydantic models on backend, TypeScript on frontend, shared via OpenAPI schema

---

## 2. Project Structure

```
pdf2video/
├── core/                          # ← EXISTING — NO CHANGES
│   ├── __init__.py
│   ├── config.py
│   ├── content_input.py
│   ├── pdf_extractor.py
│   ├── ai_services.py
│   ├── image_classifier.py
│   ├── effects.py
│   ├── video_composer.py
│   └── pipeline.py
│
├── backend/                       # ← NEW — FastAPI server
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory, lifespan, CORS
│   ├── config.py                  # Backend-specific settings (Pydantic BaseSettings)
│   ├── dependencies.py            # Dependency injection (get_db, get_current_user, etc.)
│   │
│   ├── api/                       # API route modules
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # Aggregates all v1 routers
│   │   │   ├── jobs.py            # POST /jobs, GET /jobs, GET /jobs/{id}, DELETE /jobs/{id}
│   │   │   ├── jobs_progress.py   # GET /jobs/{id}/progress (SSE stream)
│   │   │   ├── uploads.py         # POST /uploads/pdf, POST /uploads/images, POST /uploads/music
│   │   │   ├── videos.py          # GET /videos/{id}/stream, GET /videos/{id}/download
│   │   │   ├── presets.py         # GET /presets, POST /presets (saved configurations)
│   │   │   ├── auth.py            # POST /auth/register, POST /auth/login, POST /auth/refresh
│   │   │   └── health.py          # GET /health, GET /health/gpu
│   │   └── __init__.py
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── job.py
│   │   ├── video.py
│   │   ├── upload.py
│   │   └── preset.py
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── job.py                 # JobCreate, JobResponse, JobProgress, JobList
│   │   ├── upload.py              # UploadResponse, UploadedFile
│   │   ├── video.py               # VideoResponse, VideoMeta
│   │   ├── auth.py                # LoginRequest, TokenResponse, UserResponse
│   │   ├── preset.py              # PresetCreate, PresetResponse
│   │   └── common.py              # PaginatedResponse, ErrorResponse
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── job_service.py         # Create/cancel/retry jobs, dispatch to workers
│   │   ├── upload_service.py      # Handle file uploads, validation, storage
│   │   ├── video_service.py       # Serve videos, generate thumbnails, cleanup
│   │   ├── auth_service.py        # JWT token management, password hashing
│   │   └── preset_service.py      # Save/load user presets
│   │
│   ├── workers/                   # Background job workers
│   │   ├── __init__.py
│   │   ├── celery_app.py          # Celery configuration (if using Celery)
│   │   ├── video_worker.py        # The actual job: calls core/ pipeline with progress callbacks
│   │   └── cleanup_worker.py      # Periodic cleanup of old temp files and expired jobs
│   │
│   ├── middleware/                 # Custom middleware
│   │   ├── __init__.py
│   │   ├── rate_limit.py          # Per-user rate limiting
│   │   ├── request_id.py          # Attach unique request ID for tracing
│   │   └── error_handler.py       # Global exception → JSON error response
│   │
│   ├── db/                        # Database setup
│   │   ├── __init__.py
│   │   ├── session.py             # SQLAlchemy async engine + session factory
│   │   ├── base.py                # Declarative base
│   │   └── migrations/            # Alembic migrations
│   │       ├── env.py
│   │       ├── alembic.ini
│   │       └── versions/
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── storage.py             # Abstract file storage (local FS / S3 adapter)
│       ├── progress.py            # Progress tracking + SSE broadcast
│       └── security.py            # Password hashing, JWT encode/decode
│
├── frontend/                      # ← NEW — Next.js app
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── components.json            # shadcn/ui config
│   │
│   ├── public/
│   │   ├── logo.svg
│   │   └── og-image.png
│   │
│   ├── src/
│   │   ├── app/                   # Next.js App Router
│   │   │   ├── layout.tsx         # Root layout (providers, nav, theme)
│   │   │   ├── page.tsx           # Landing / dashboard
│   │   │   ├── globals.css
│   │   │   │
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   │
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx       # Job history, stats, recent videos
│   │   │   │
│   │   │   ├── create/
│   │   │   │   ├── page.tsx       # New job wizard (tabbed: PDF / Text+Images)
│   │   │   │   └── layout.tsx
│   │   │   │
│   │   │   ├── jobs/
│   │   │   │   ├── page.tsx       # All jobs list with filters
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx   # Single job: progress → preview → download
│   │   │   │
│   │   │   ├── videos/
│   │   │   │   ├── page.tsx       # Video library / gallery
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx   # Full video player + metadata + share
│   │   │   │
│   │   │   └── settings/
│   │   │       └── page.tsx       # API key, defaults, presets
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                # shadcn/ui primitives (auto-generated)
│   │   │   │
│   │   │   ├── layout/
│   │   │   │   ├── app-sidebar.tsx
│   │   │   │   ├── header.tsx
│   │   │   │   ├── nav-user.tsx
│   │   │   │   └── theme-toggle.tsx
│   │   │   │
│   │   │   ├── jobs/
│   │   │   │   ├── job-card.tsx
│   │   │   │   ├── job-progress.tsx      # Real-time progress bar + step indicator
│   │   │   │   ├── job-create-form.tsx   # Multi-step form with validation
│   │   │   │   └── job-list.tsx
│   │   │   │
│   │   │   ├── upload/
│   │   │   │   ├── pdf-dropzone.tsx      # Drag-and-drop PDF upload with preview
│   │   │   │   ├── image-dropzone.tsx    # Multi-image upload with grid preview
│   │   │   │   ├── music-upload.tsx
│   │   │   │   └── file-preview.tsx
│   │   │   │
│   │   │   ├── video/
│   │   │   │   ├── video-player.tsx      # Custom player with controls
│   │   │   │   ├── video-card.tsx
│   │   │   │   └── video-gallery.tsx
│   │   │   │
│   │   │   └── shared/
│   │   │       ├── loading-spinner.tsx
│   │   │       ├── error-boundary.tsx
│   │   │       ├── confirm-dialog.tsx
│   │   │       └── empty-state.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── use-job-progress.ts       # SSE hook for real-time progress
│   │   │   ├── use-auth.ts
│   │   │   ├── use-upload.ts             # File upload with progress
│   │   │   └── use-api.ts               # Typed fetch wrapper
│   │   │
│   │   ├── lib/
│   │   │   ├── api-client.ts            # Axios/fetch client with interceptors
│   │   │   ├── auth.ts                  # Token storage, refresh logic
│   │   │   ├── utils.ts                 # cn(), formatDuration(), etc.
│   │   │   └── constants.ts             # Voice options, resolution presets, etc.
│   │   │
│   │   ├── stores/                      # Zustand stores (lightweight global state)
│   │   │   ├── auth-store.ts
│   │   │   └── job-store.ts
│   │   │
│   │   └── types/
│   │       ├── api.ts                   # Auto-generated from OpenAPI or manual mirror
│   │       ├── job.ts
│   │       ├── video.ts
│   │       └── user.ts
│   │
│   └── .env.local                       # NEXT_PUBLIC_API_URL=http://localhost:8000
│
├── docker/                        # ← NEW — Container configs
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.worker
│   ├── docker-compose.yml         # Full stack: backend + frontend + postgres + redis
│   └── docker-compose.dev.yml     # Dev overrides (hot reload, volumes)
│
├── docs/                          # ← Documentation
│   ├── ARCHITECTURE_PLAN.md       # THIS FILE
│   ├── API_REFERENCE.md           # Auto-generated or hand-maintained
│   └── DEPLOYMENT.md
│
├── scripts/                       # ← Utility scripts
│   ├── seed_db.py                 # Create initial admin user, sample presets
│   ├── generate_openapi.py        # Export OpenAPI JSON for frontend types
│   └── migrate.sh                 # Run Alembic migrations
│
├── tests/                         # ← Test suite
│   ├── backend/
│   │   ├── test_api_jobs.py
│   │   ├── test_api_uploads.py
│   │   ├── test_api_auth.py
│   │   ├── test_worker.py
│   │   └── conftest.py            # Fixtures: test DB, test client, mock OpenAI
│   ├── frontend/
│   │   ├── __tests__/
│   │   └── e2e/                   # Playwright end-to-end tests
│   └── core/                      # Tests for existing core/ modules
│       ├── test_pipeline.py
│       ├── test_effects.py
│       └── test_classifier.py
│
├── .env.example                   # Updated with all new env vars
├── .gitignore
├── pyproject.toml                 # Python project config (replaces requirements.txt)
├── requirements.txt               # Kept for backward compat, generated from pyproject.toml
└── README.md                      # Updated with new setup instructions
```

---

## 3. Backend — FastAPI

### 3.1 App Factory (`backend/main.py`)

```python
# Responsibilities:
# - Create FastAPI app with lifespan (startup/shutdown hooks)
# - Mount API v1 router
# - Configure CORS for frontend origin
# - Mount static file server for /media
# - Register global exception handlers
# - Initialize DB connection pool on startup
# - Initialize Redis connection on startup
```

**Key decisions:**
- **Versioned API** (`/api/v1/`) — allows breaking changes in v2 without disrupting clients
- **Lifespan context manager** — async startup/shutdown for DB pool, Redis, temp dir cleanup
- **CORS** — allow `http://localhost:3000` in dev, configurable origins in prod

### 3.2 Configuration (`backend/config.py`)

Use Pydantic `BaseSettings` with `.env` file support:

```
# New env vars (in addition to existing core/ vars):
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pdf2video
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=<random-256-bit-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
STORAGE_BACKEND=local              # "local" or "s3"
STORAGE_LOCAL_PATH=./storage
S3_BUCKET=pdf2video-media
S3_REGION=us-east-1
MAX_UPLOAD_SIZE_MB=100
MAX_CONCURRENT_JOBS=3
CORS_ORIGINS=["http://localhost:3000"]
```

### 3.3 Service Layer Pattern

Every API route delegates to a service class. Services contain business logic and call `core/` modules. This keeps routes thin and testable.

```
Route (jobs.py) → JobService → core/pipeline.py
Route (uploads.py) → UploadService → storage.py
Route (auth.py) → AuthService → security.py + User model
```

---

## 4. Frontend — Next.js

### 4.1 Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| Next.js | 15.x | App Router, SSR, API routes (proxy if needed) |
| React | 19.x | UI framework |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first styling |
| shadcn/ui | latest | Component library (Button, Dialog, Card, Table, etc.) |
| Zustand | 5.x | Lightweight global state (auth, active jobs) |
| Lucide React | latest | Icons |
| React Hook Form | 7.x | Form management with validation |
| Zod | 3.x | Schema validation (shared with form) |
| next-themes | latest | Dark/light mode |
| sonner | latest | Toast notifications |
| nuqs | latest | URL search params state |

### 4.2 App Router Structure

```
/                    → Dashboard (recent jobs, quick stats, "New Video" CTA)
/create              → New job wizard (PDF tab / Text+Images tab)
/jobs                → All jobs with filters (status, date, search)
/jobs/[id]           → Single job view (progress → result → download)
/videos              → Video library gallery
/videos/[id]         → Full video player + metadata + share link
/settings            → API key config, default presets, account
/login               → Auth
/register            → Auth
```

### 4.3 Key UI Patterns

**Job Creation Flow (multi-step form):**
1. **Input** — Upload PDF or enter text + images (drag-and-drop zones)
2. **Configure** — Voice, resolution, FPS, background music, AI backgrounds toggle
3. **Review** — Summary of inputs, estimated cost/time
4. **Submit** — Creates job, redirects to `/jobs/[id]` with live progress

**Real-Time Progress:**
- SSE connection opens when user lands on `/jobs/[id]`
- Progress bar with step labels: "Classifying images..." → "Generating script..." → "Voiceover..." → "Composing video..."
- Each step shows a percentage sub-bar
- On completion: auto-play video preview + download button

**Video Library:**
- Grid of video cards with thumbnails (auto-generated from first frame)
- Filter by date, source type (PDF vs text), status
- Click to open full player with metadata sidebar

### 4.4 API Client

A typed fetch wrapper that:
- Attaches JWT `Authorization: Bearer <token>` header
- Auto-refreshes expired tokens
- Handles 401 → redirect to login
- Provides typed responses matching Pydantic schemas
- Supports file upload with progress callbacks

---

## 5. Database Layer

### 5.1 ORM: SQLAlchemy 2.x (async)

Using `asyncpg` driver for PostgreSQL async support.

### 5.2 Models

**User**
```
id: UUID (PK)
email: str (unique, indexed)
password_hash: str
display_name: str
openai_api_key_encrypted: str (nullable — user can store their key)
created_at: datetime
updated_at: datetime
is_active: bool
```

**Job**
```
id: UUID (PK)
user_id: UUID (FK → User)
status: enum (pending, classifying, scripting, voiceover, backgrounds, composing, exporting, completed, failed, cancelled)
source_type: str ("pdf" | "text_images")
title: str
settings: JSONB {
    voice: str,
    resolution: str,
    fps: int,
    generate_backgrounds: bool,
    ...
}
progress: float (0.0 → 1.0)
current_step: str
error_message: str (nullable)
created_at: datetime
started_at: datetime (nullable)
completed_at: datetime (nullable)
video_id: UUID (FK → Video, nullable)
```

**Video**
```
id: UUID (PK)
job_id: UUID (FK → Job)
user_id: UUID (FK → User)
title: str
file_path: str
file_size: int
duration_seconds: float
resolution: str
thumbnail_path: str (nullable)
metadata: JSONB {
    scenes: int,
    mood: str,
    source_pages: int,
    ...
}
created_at: datetime
```

**Upload**
```
id: UUID (PK)
job_id: UUID (FK → Job, nullable — uploads can exist before job creation)
user_id: UUID (FK → User)
file_type: str ("pdf" | "image" | "music")
original_filename: str
stored_path: str
file_size: int
mime_type: str
created_at: datetime
```

**Preset**
```
id: UUID (PK)
user_id: UUID (FK → User)
name: str
settings: JSONB {
    voice: str,
    resolution: str,
    fps: int,
    generate_backgrounds: bool,
    ...
}
is_default: bool
created_at: datetime
```

### 5.3 Migrations

Alembic with async support. Initial migration creates all tables. Each schema change gets a versioned migration file.

---

## 6. Async Job System

### 6.1 Architecture Options

**Option A: Celery + Redis (recommended for production)**
- Celery worker process runs `core/` pipeline
- Redis as message broker + result backend
- Supports multiple workers, retries, rate limiting, scheduled tasks
- Progress updates pushed to Redis pub/sub → SSE endpoint reads them

**Option B: FastAPI BackgroundTasks + in-process queue (simpler, single-server)**
- `asyncio` background tasks with a `ThreadPoolExecutor` for CPU-bound work
- Progress stored in Redis or in-memory dict
- Simpler to deploy, but doesn't scale horizontally

**Recommendation**: Start with **Option B** for development speed, design the interfaces so switching to **Option A** is a config change, not a rewrite.

### 6.2 Worker Flow

```python
# backend/workers/video_worker.py (simplified)

async def process_video_job(job_id: UUID, db: Session, storage: Storage):
    job = await db.get(Job, job_id)
    job.status = "processing"
    job.started_at = utcnow()
    
    # Build progress callback that writes to Redis/SSE
    def on_progress(step: str, pct: float):
        job.current_step = step
        job.progress = pct
        publish_progress(job_id, step, pct)  # → Redis pub/sub
    
    try:
        # Reconstruct inputs from uploaded files
        content = build_content_from_uploads(job)
        
        # Run the existing core/ pipeline
        pipeline = PDF2VideoPipeline()
        result_path = pipeline.run_from_content(
            content=content,
            voice=job.settings["voice"],
            generate_backgrounds=job.settings["generate_backgrounds"],
            progress_callback=on_progress,
        )
        
        # Move result to permanent storage
        video_path = storage.store(result_path, f"videos/{job_id}.mp4")
        
        # Create Video record
        video = Video(job_id=job_id, user_id=job.user_id, file_path=video_path, ...)
        db.add(video)
        job.status = "completed"
        job.video_id = video.id
        job.completed_at = utcnow()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
    
    await db.commit()
```

### 6.3 Progress Broadcasting

```
Worker → Redis PUBLISH job:{id}:progress {"step": "Composing video...", "pct": 0.65}
                                    ↓
SSE Endpoint ← Redis SUBSCRIBE job:{id}:progress
                                    ↓
                              Browser (EventSource)
```

---

## 7. File Storage & Media Serving

### 7.1 Storage Abstraction

```python
# backend/utils/storage.py

class StorageBackend(ABC):
    async def store(self, local_path: Path, key: str) -> str: ...
    async def retrieve(self, key: str) -> Path: ...
    async def delete(self, key: str) -> None: ...
    async def get_url(self, key: str) -> str: ...

class LocalStorage(StorageBackend):
    """Stores files on local filesystem under STORAGE_LOCAL_PATH."""

class S3Storage(StorageBackend):
    """Stores files in S3 with presigned URLs for downloads."""
```

### 7.2 Directory Layout (Local Storage)

```
storage/
├── uploads/
│   ├── {user_id}/
│   │   ├── {upload_id}.pdf
│   │   ├── {upload_id}.png
│   │   └── {upload_id}.mp3
├── videos/
│   ├── {video_id}.mp4
│   └── {video_id}_thumb.jpg
└── temp/
    └── {job_id}/                  # Working directory per job, cleaned up after
```

### 7.3 Media Serving

- **Local**: FastAPI `StaticFiles` mount at `/media/` or streaming `FileResponse`
- **S3**: Presigned URLs with expiry (e.g., 1 hour)
- **Video streaming**: Support `Range` headers for seeking in the video player

---

## 8. Authentication & Authorization

### 8.1 Auth Flow

```
1. POST /api/v1/auth/register  →  Create user, return tokens
2. POST /api/v1/auth/login     →  Verify credentials, return tokens
3. All other endpoints          →  Require Authorization: Bearer <access_token>
4. POST /api/v1/auth/refresh   →  Exchange refresh token for new access token
```

### 8.2 Token Strategy

- **Access token**: JWT, 30-minute expiry, stored in memory (Zustand store)
- **Refresh token**: JWT, 7-day expiry, stored in `httpOnly` cookie (secure, sameSite)
- **Password hashing**: `bcrypt` via `passlib`

### 8.3 Authorization Rules

| Resource | Owner | Admin | Public |
|----------|-------|-------|--------|
| Jobs | CRUD own | CRUD all | — |
| Videos | Read/delete own | CRUD all | Read if shared |
| Uploads | CRUD own | CRUD all | — |
| Presets | CRUD own | CRUD all | Read defaults |
| Users | Read/update own | CRUD all | — |

### 8.4 API Key Management

Users can optionally store their OpenAI API key (encrypted at rest with Fernet symmetric encryption). If not provided, the server's default key is used (if configured).

---

## 9. Real-Time Progress (SSE / WebSocket)

### 9.1 Server-Sent Events (SSE) — Recommended

SSE is simpler than WebSocket for one-way server→client streaming, which is all we need for progress updates.

```python
# backend/api/v1/jobs_progress.py

@router.get("/jobs/{job_id}/progress")
async def stream_job_progress(job_id: UUID, current_user: User = Depends(get_current_user)):
    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"job:{job_id}:progress")
        
        # Send current state immediately
        job = await get_job(job_id)
        yield {"event": "progress", "data": json.dumps({
            "status": job.status,
            "step": job.current_step,
            "progress": job.progress,
        })}
        
        # Stream updates
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield {"event": "progress", "data": message["data"]}
                data = json.loads(message["data"])
                if data.get("status") in ("completed", "failed", "cancelled"):
                    break
    
    return EventSourceResponse(event_generator())
```

### 9.2 Frontend Hook

```typescript
// src/hooks/use-job-progress.ts

function useJobProgress(jobId: string) {
  const [progress, setProgress] = useState<JobProgress | null>(null);
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/jobs/${jobId}/progress`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    
    eventSource.addEventListener("progress", (e) => {
      setProgress(JSON.parse(e.data));
    });
    
    return () => eventSource.close();
  }, [jobId]);
  
  return progress;
}
```

---

## 10. API Design — Full Endpoint Specification

### Authentication

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/register` | Create account | No |
| POST | `/api/v1/auth/login` | Get tokens | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | Cookie |
| POST | `/api/v1/auth/logout` | Invalidate refresh token | Yes |
| GET | `/api/v1/auth/me` | Get current user | Yes |

### Uploads

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/uploads/pdf` | Upload PDF file | Yes |
| POST | `/api/v1/uploads/images` | Upload images (multipart, multiple) | Yes |
| POST | `/api/v1/uploads/music` | Upload background music | Yes |
| GET | `/api/v1/uploads` | List user's uploads | Yes |
| DELETE | `/api/v1/uploads/{id}` | Delete an upload | Yes |

### Jobs

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/jobs` | Create and start a video generation job | Yes |
| GET | `/api/v1/jobs` | List user's jobs (paginated, filterable) | Yes |
| GET | `/api/v1/jobs/{id}` | Get job details | Yes |
| GET | `/api/v1/jobs/{id}/progress` | SSE stream of progress updates | Yes |
| POST | `/api/v1/jobs/{id}/cancel` | Cancel a running job | Yes |
| POST | `/api/v1/jobs/{id}/retry` | Retry a failed job | Yes |
| DELETE | `/api/v1/jobs/{id}` | Delete job and associated files | Yes |

**POST `/api/v1/jobs` request body:**
```json
{
  "source_type": "pdf",
  "title": "My Video",
  "pdf_upload_id": "uuid-of-uploaded-pdf",
  "image_upload_ids": ["uuid1", "uuid2"],
  "music_upload_id": "uuid-or-null",
  "text_content": null,
  "settings": {
    "voice": "onyx",
    "resolution": "1920x1080",
    "fps": 30,
    "generate_backgrounds": true
  },
  "preset_id": null
}
```

### Videos

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/videos` | List user's videos (paginated) | Yes |
| GET | `/api/v1/videos/{id}` | Get video metadata | Yes |
| GET | `/api/v1/videos/{id}/stream` | Stream video (supports Range) | Yes |
| GET | `/api/v1/videos/{id}/download` | Download video file | Yes |
| GET | `/api/v1/videos/{id}/thumbnail` | Get video thumbnail | Yes |
| DELETE | `/api/v1/videos/{id}` | Delete video | Yes |

### Presets

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/presets` | List user's presets | Yes |
| POST | `/api/v1/presets` | Create a preset | Yes |
| PUT | `/api/v1/presets/{id}` | Update a preset | Yes |
| DELETE | `/api/v1/presets/{id}` | Delete a preset | Yes |

### System

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/health` | Health check | No |
| GET | `/api/v1/health/gpu` | GPU/NVENC availability | No |

---

## 11. Frontend Pages & Components

### 11.1 Dashboard (`/`)

- **Stats row**: Total videos, total jobs, storage used, GPU status
- **Recent jobs**: Last 5 jobs with status badges
- **Quick action**: "New Video" button → `/create`
- **Recent videos**: Thumbnail grid of last 4 videos

### 11.2 Create Page (`/create`)

Tabbed interface:

**PDF Tab:**
- PDF dropzone (drag-and-drop, click to browse)
- PDF preview (first page thumbnail after upload)
- Page count display

**Text + Images Tab:**
- Title input
- Rich text area for content
- Image dropzone (multi-file, grid preview with reorder)

**Shared Settings Panel (sidebar or bottom):**
- Voice selector (dropdown with audio preview samples)
- Resolution selector (1080p / 2K / 4K)
- FPS selector (24 / 30 / 60)
- AI backgrounds toggle
- Music upload (optional)
- Preset selector (load saved settings)
- "Save as Preset" button

**Submit:**
- Review summary card
- "Generate Video" button → creates job → redirect to `/jobs/[id]`

### 11.3 Job Detail Page (`/jobs/[id]`)

**While processing:**
- Large progress bar with percentage
- Step indicator (classify → script → voiceover → backgrounds → compose → export)
- Current step label with animated dots
- Estimated time remaining (based on progress rate)
- Cancel button

**On completion:**
- Inline video player (auto-play)
- Download button (primary CTA)
- Video metadata card (duration, resolution, scenes, file size)
- "Create Another" button
- Share link (if sharing is enabled)

**On failure:**
- Error message with details
- "Retry" button
- "Edit & Retry" button (goes back to create with same inputs)

### 11.4 Video Library (`/videos`)

- Grid/list toggle
- Sort by date, title, duration
- Search by title
- Video cards with: thumbnail, title, duration, date, resolution badge
- Bulk delete

### 11.5 Settings (`/settings`)

- **Profile**: Display name, email
- **API Key**: OpenAI API key input (masked, encrypted storage)
- **Defaults**: Default voice, resolution, FPS, backgrounds
- **Presets**: List of saved presets with edit/delete
- **Storage**: Usage stats, cleanup old files

---

## 12. Configuration & Environment

### 12.1 Updated `.env.example`

```bash
# ── OpenAI (used by core/) ──────────────────────────
OPENAI_API_KEY=sk-your-key-here
OPENAI_CHAT_MODEL=gpt-5.2
OPENAI_TTS_MODEL=tts-1-hd
OPENAI_TTS_VOICE=onyx
OPENAI_IMAGE_MODEL=gpt-image-1

# ── Video Settings (used by core/) ──────────────────
VIDEO_WIDTH=1920
VIDEO_HEIGHT=1080
VIDEO_FPS=30
VIDEO_CODEC=h264_nvenc
VIDEO_BITRATE=12M

# ── Database ────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://pdf2video:password@localhost:5432/pdf2video

# ── Redis ───────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Authentication ──────────────────────────────────
JWT_SECRET_KEY=change-me-to-a-random-256-bit-string
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Storage ─────────────────────────────────────────
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./storage
# S3_BUCKET=pdf2video-media
# S3_REGION=us-east-1
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=

# ── Server ──────────────────────────────────────────
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
MAX_UPLOAD_SIZE_MB=100
MAX_CONCURRENT_JOBS=3

# ── Frontend ────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=PDF2Video
```

---

## 13. Error Handling & Logging

### 13.1 Backend Error Strategy

- **Global exception handler** → catches all unhandled exceptions, returns structured JSON:
  ```json
  {"error": {"code": "JOB_NOT_FOUND", "message": "...", "details": {}}}
  ```
- **Domain exceptions** → `JobNotFoundError`, `UploadTooLargeError`, `InvalidFileTypeError`, etc.
- **Validation errors** → Pydantic auto-generates 422 responses with field-level details
- **OpenAI errors** → caught in `core/`, surfaced as job failure with user-friendly message

### 13.2 Logging

- **Structured JSON logging** via `structlog`
- **Request ID** attached to every log line (via middleware)
- **Log levels**: DEBUG (dev), INFO (prod), ERROR (always)
- **Separate log streams**: API requests, job processing, OpenAI calls, errors

### 13.3 Frontend Error Handling

- **Error boundaries** at route level (catch React render errors)
- **Toast notifications** for API errors (via `sonner`)
- **Retry logic** in API client for transient failures (429, 503)
- **Offline detection** with reconnect banner

---

## 14. Testing Strategy

### 14.1 Backend Tests (pytest + httpx)

| Layer | What to test | How |
|-------|-------------|-----|
| **API routes** | Request/response contracts, auth, validation | `httpx.AsyncClient` with `TestClient` |
| **Services** | Business logic, edge cases | Unit tests with mocked DB and storage |
| **Workers** | Job processing, progress callbacks | Unit tests with mocked `core/` pipeline |
| **Models** | DB constraints, relationships | Test against real PostgreSQL (Docker) |
| **Auth** | Token generation, refresh, expiry | Unit tests |

**Mocking OpenAI**: Create a `MockOpenAI` fixture that returns canned responses for script generation, TTS, and image generation. This allows testing the full pipeline without API calls.

### 14.2 Frontend Tests

| Type | Tool | What |
|------|------|------|
| **Unit** | Vitest + React Testing Library | Component rendering, hooks, utils |
| **Integration** | Vitest + MSW (Mock Service Worker) | API interactions, form submissions |
| **E2E** | Playwright | Full user flows: upload → create → progress → download |

### 14.3 Core Tests

| Module | Key tests |
|--------|-----------|
| `effects.py` | Each effect function produces correct array shapes, no NaN/overflow |
| `image_classifier.py` | Batch classification with mocked API, fallback on failure |
| `video_composer.py` | Each layout mode produces valid frames, logo watermark applied |
| `pipeline.py` | Full pipeline with mocked AI services |

---

## 15. Deployment & Infrastructure

### 15.1 Docker Compose (Development)

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: pdf2video
      POSTGRES_USER: pdf2video
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: { context: ., dockerfile: docker/Dockerfile.backend }
    ports: ["8000:8000"]
    volumes:
      - ./core:/app/core
      - ./backend:/app/backend
      - ./storage:/app/storage
    env_file: .env
    depends_on: [postgres, redis]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  frontend:
    build: { context: ./frontend, dockerfile: ../docker/Dockerfile.frontend }
    ports: ["3000:3000"]
    volumes: [./frontend/src:/app/src]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
```

### 15.2 Production Deployment Options

**Option A: Single Server (GPU machine)**
- Docker Compose on a GPU instance (e.g., Lambda Labs, RunPod, or your own RTX 5090 machine)
- Nginx reverse proxy with SSL (Let's Encrypt)
- Backend + worker on same machine (GPU access needed for NVENC)

**Option B: Split Architecture**
- Frontend → Vercel (free tier, global CDN)
- Backend API → Railway / Render / Fly.io
- Worker → GPU instance (Lambda, RunPod) with Celery
- PostgreSQL → Neon / Supabase / managed RDS
- Redis → Upstash / ElastiCache
- Storage → S3 / Cloudflare R2

**Option C: Kubernetes (scale)**
- EKS/GKE cluster with GPU node pool for workers
- Horizontal pod autoscaling on API pods
- Separate GPU node group for video rendering workers

### 15.3 CI/CD

- **GitHub Actions** (or similar):
  - On PR: lint + type-check + test (backend + frontend)
  - On merge to main: build Docker images, push to registry, deploy
- **Pre-commit hooks**: `ruff` (Python lint), `eslint` + `prettier` (TypeScript)

---

## 16. Performance & Scaling

### 16.1 Backend Performance

- **Async everywhere**: FastAPI + asyncpg + aioredis — no blocking the event loop
- **Thread pool for CPU work**: `core/` pipeline runs in `ThreadPoolExecutor` to not block async
- **Connection pooling**: SQLAlchemy async pool (min 5, max 20 connections)
- **File upload streaming**: Large PDFs streamed to disk, not buffered in memory

### 16.2 Job Concurrency

- **MAX_CONCURRENT_JOBS** config limits parallel video generation
- **Queue with priority**: Paid users get higher priority (future)
- **Job timeout**: 30-minute max per job, auto-fail if exceeded
- **Retry with backoff**: Failed jobs can be retried up to 3 times

### 16.3 Frontend Performance

- **Next.js App Router**: Server components for initial load, client components for interactivity
- **Image optimization**: `next/image` for thumbnails
- **Code splitting**: Dynamic imports for heavy components (video player)
- **Stale-while-revalidate**: SWR pattern for job lists and video library

### 16.4 Caching

- **Redis cache**: Script generation results (keyed by content hash) — avoid re-generating for retries
- **HTTP cache headers**: Video thumbnails (immutable), static assets (long max-age)
- **Next.js ISR**: Dashboard stats can be revalidated every 60s

---

## 17. Security Hardening

| Concern | Mitigation |
|---------|-----------|
| **SQL injection** | SQLAlchemy ORM (parameterized queries) |
| **XSS** | React auto-escapes, CSP headers |
| **CSRF** | SameSite cookies, CORS whitelist |
| **File upload attacks** | Validate MIME types, scan file headers, size limits |
| **Path traversal** | Storage abstraction normalizes paths, no user input in file paths |
| **API key exposure** | Encrypted at rest (Fernet), never returned in API responses |
| **Rate limiting** | Per-user rate limits on job creation and uploads |
| **JWT security** | Short-lived access tokens, httpOnly refresh cookies, token rotation |
| **Dependency vulnerabilities** | `pip-audit` + `npm audit` in CI |
| **HTTPS** | Enforced in production via Nginx/Cloudflare |

---

## 18. Future Feature Hooks

The architecture is designed to support these without major refactoring:

| Feature | Where it plugs in |
|---------|-------------------|
| **Template library** | New `templates` model + API routes, frontend gallery page |
| **Custom branding** | Extend `Preset` model with brand colors, logo, fonts |
| **Collaboration / teams** | Add `Organization` model, team-based auth scopes |
| **Video editing / timeline** | New frontend page with canvas-based timeline editor, calls API to re-render specific scenes |
| **Webhook notifications** | Worker publishes to webhook URL on job completion |
| **Batch processing** | New "batch job" endpoint that creates multiple jobs from a ZIP of PDFs |
| **Video analytics** | Track views, downloads, shares per video |
| **Custom AI models** | Extend `settings` JSONB to support model selection (GPT-5.2 vs others) |
| **Multi-language narration** | Add `language` to job settings, pass to TTS |
| **Subtitle generation** | Post-processing step in worker: transcribe audio → SRT → burn-in or sidecar |
| **Scene-level editing** | API to regenerate individual scenes (re-run partial pipeline) |
| **Plugin system** | Effects plugins loaded from `core/plugins/`, registered at startup |
| **Public sharing** | Signed URLs with expiry, public video pages with OG meta |
| **Usage metering / billing** | Track API calls and compute time per user, integrate Stripe |

---

## 19. Migration Checklist

### Phase 1: Backend Foundation
- [ ] Initialize `backend/` package structure
- [ ] Set up FastAPI app factory with CORS, lifespan
- [ ] Set up PostgreSQL with SQLAlchemy async + Alembic
- [ ] Set up Redis connection
- [ ] Implement storage abstraction (local filesystem)
- [ ] Create all ORM models + initial migration
- [ ] Implement auth service (register, login, JWT)
- [ ] Implement auth API routes
- [ ] Add global error handling middleware
- [ ] Add request ID middleware
- [ ] Write health check endpoint

### Phase 2: Core API
- [ ] Implement upload service + API routes (PDF, images, music)
- [ ] Implement job service (create, list, get, cancel, retry, delete)
- [ ] Implement job API routes
- [ ] Implement video worker (wraps `core/` pipeline)
- [ ] Implement progress broadcasting (Redis pub/sub → SSE)
- [ ] Implement SSE progress endpoint
- [ ] Implement video service + API routes (stream, download, thumbnail)
- [ ] Implement preset service + API routes
- [ ] Write OpenAPI schema export script

### Phase 3: Frontend Foundation
- [ ] Initialize Next.js 15 project with TypeScript
- [ ] Install and configure Tailwind CSS 4 + shadcn/ui
- [ ] Set up project structure (app router, components, hooks, lib, stores)
- [ ] Implement API client with auth interceptors
- [ ] Implement auth store (Zustand)
- [ ] Build login + register pages
- [ ] Build root layout (sidebar, header, theme toggle)
- [ ] Build dashboard page

### Phase 4: Frontend Features
- [ ] Build PDF dropzone component
- [ ] Build image dropzone component (multi-file, grid preview)
- [ ] Build music upload component
- [ ] Build create page (multi-step form with tabs)
- [ ] Build job progress component (SSE hook + progress bar + step indicator)
- [ ] Build job detail page (progress → result → download)
- [ ] Build job list page with filters
- [ ] Build video player component
- [ ] Build video library page
- [ ] Build settings page (API key, defaults, presets)

### Phase 5: Polish & Production
- [ ] Add toast notifications for all actions
- [ ] Add loading states and skeleton screens
- [ ] Add empty states for all list pages
- [ ] Add error boundaries
- [ ] Implement dark/light theme
- [ ] Add responsive design (mobile-friendly)
- [ ] Write backend tests (API, services, workers)
- [ ] Write frontend tests (components, hooks, E2E)
- [ ] Write core/ tests (effects, classifier, composer)
- [ ] Set up Docker Compose (dev + prod)
- [ ] Set up CI/CD pipeline
- [ ] Write deployment documentation
- [ ] Security audit (rate limiting, input validation, CORS)
- [ ] Performance testing (concurrent jobs, large PDFs)

### Phase 6: Retire Streamlit
- [ ] Verify all Streamlit functionality is replicated
- [ ] Remove `app.py` (Streamlit)
- [ ] Update README with new setup instructions
- [ ] Tag v2.0.0 release

---

## 20. Dependency Manifest

### Backend (Python — `pyproject.toml`)

```
# Web framework
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.12

# Database
sqlalchemy[asyncio]>=2.0.36
asyncpg>=0.30.0
alembic>=1.14.0

# Cache / Queue
redis[hiredis]>=5.2.0
sse-starlette>=2.1.0

# Auth
pyjwt>=2.10.0
passlib[bcrypt]>=1.7.4
cryptography>=44.0.0

# Validation / Config
pydantic>=2.10.0
pydantic-settings>=2.7.0

# Storage
boto3>=1.35.0          # Only if using S3
aiofiles>=24.1.0

# Logging
structlog>=24.4.0

# Testing
pytest>=8.3.0
pytest-asyncio>=0.24.0
httpx>=0.28.0

# Existing core/ dependencies (carried over)
PyMuPDF>=1.24.14
pdfplumber>=0.11.4
openai>=1.86.0
moviepy>=2.1.2
Pillow>=11.1.0
opencv-python-headless>=4.10.0
numpy>=2.1.3
scipy>=1.14.1
pydub>=0.25.1
ffmpeg-python>=0.2.0
imageio[ffmpeg]>=2.36.1
python-dotenv>=1.0.1
tqdm>=4.67.1
rich>=13.9.4
```

### Frontend (Node.js — `package.json`)

```
# Framework
next: ^15.0.0
react: ^19.0.0
react-dom: ^19.0.0
typescript: ^5.7.0

# Styling
tailwindcss: ^4.0.0
@tailwindcss/postcss: ^4.0.0

# UI Components
shadcn/ui components (installed via CLI)
lucide-react: ^0.460.0
sonner: ^1.7.0
next-themes: ^0.4.0

# State & Data
zustand: ^5.0.0
zod: ^3.24.0
react-hook-form: ^7.54.0
@hookform/resolvers: ^3.9.0
nuqs: ^2.0.0

# Utilities
clsx: ^2.1.0
tailwind-merge: ^2.6.0
date-fns: ^4.1.0

# Dev
eslint: ^9.0.0
prettier: ^3.4.0
@playwright/test: ^1.49.0
vitest: ^2.1.0
@testing-library/react: ^16.0.0
msw: ^2.7.0
```

---

## Appendix: Key Design Decisions

### Why FastAPI over Django/Flask?
- **Async-native** — critical for SSE, file streaming, and non-blocking job dispatch
- **Pydantic integration** — automatic request validation, OpenAPI schema generation
- **Performance** — one of the fastest Python frameworks
- **Type hints** — first-class support, matches our typed `core/` codebase

### Why Next.js App Router over Vite SPA?
- **SSR for SEO** — if we ever add public video pages
- **File-based routing** — clean URL structure without manual router config
- **Server components** — reduce client JS bundle for static pages (dashboard, library)
- **Built-in optimizations** — image optimization, code splitting, prefetching

### Why PostgreSQL over SQLite?
- **JSONB** — native JSON column type for flexible settings/metadata
- **Concurrent access** — multiple workers writing job status simultaneously
- **Full-text search** — future video search by title/content
- **Production-ready** — connection pooling, replication, backups

### Why Redis?
- **Pub/sub** — real-time progress broadcasting to SSE endpoints
- **Job queue** — Celery broker (if we upgrade from in-process)
- **Caching** — script generation results, rate limit counters
- **Session store** — refresh token blacklist

### Why Zustand over Redux/Context?
- **Minimal boilerplate** — no actions, reducers, or providers
- **TypeScript-first** — excellent type inference
- **Small bundle** — ~1KB vs Redux's ~7KB
- **Sufficient** — we only need auth state and active job tracking globally
