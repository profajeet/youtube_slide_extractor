# YouTube Lecture Slide Extractor

A production-ready **FastAPI** service that downloads YouTube lecture videos,
automatically detects unique PowerPoint/slide transitions using computer vision,
and returns a compiled, titled PDF — all via a simple REST API.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Service](#running-the-service)
- [API Reference](#api-reference)
  - [Health Check](#health-check)
  - [Submit a Job](#submit-a-job)
  - [Poll Job Status](#poll-job-status)
  - [Download PDF](#download-pdf)
- [How It Works](#how-it-works)
  - [Pipeline Stages](#pipeline-stages)
  - [Slide Detection Algorithm](#slide-detection-algorithm)
  - [PDF Naming](#pdf-naming)
- [Module Reference](#module-reference)
  - [app/core](#appcore)
  - [app/models](#appmodels)
  - [app/services](#appservices)
  - [app/api](#appapi)
  - [app/utils](#apputils)
- [Testing](#testing)
- [Docker](#docker)
- [Tuning Guide](#tuning-guide)
- [Error Handling](#error-handling)
- [Contributing](#contributing)

---

## Overview

This service accepts a YouTube URL and asynchronously processes the video
through a four-stage computer-vision pipeline:

```
YouTube URL  ->  Download  ->  Frame Sampling  ->  Slide Detection  ->  PDF Output
```

Clients submit a URL, receive a `job_id`, poll for progress, and download the
finished PDF when complete. The PDF is automatically named after the video title
(e.g., `Introduction_to_Neural_Networks.pdf`).

---

## Features

| Feature | Detail |
|---|---|
| **Async job queue** | Long videos run in background threads; the API never blocks |
| **Real-time progress** | Per-stage progress percentage (0-100%) via polling |
| **Smart slide detection** | SSIM structural similarity and edge-density heuristics filter camera shots and black-screen transitions |
| **Title-based PDF naming** | Filename derived from the YouTube video title, slugified for filesystem safety |
| **Configurable sensitivity** | Sampling interval and SSIM threshold are per-request parameters |
| **OpenAPI docs** | Interactive Swagger UI at `/docs`, ReDoc at `/redoc` |
| **Env-driven config** | All settings override-able via `.env` or environment variables |
| **Docker-ready** | Single `docker build` and `docker run` for deployment |

---

## Architecture

```
+--------------------------------------------------------------+
|                        FastAPI App                           |
|                                                              |
|  POST /api/v1/jobs ---> JobStore (in-memory)                 |
|                               |                              |
|                               v                              |
|                      BackgroundTask                          |
|                          worker.py                           |
|                               |                              |
|         +---------+-----------+------------+                 |
|         v                     v            v                 |
|   download_video       extract_frames   detect_slides        |
|   (yt-dlp)             (OpenCV)         (SSIM)               |
|                                             v                |
|                                        build_pdf             |
|                                        (ReportLab)           |
|                                             v                |
|                            outputs/{title}__{id}.pdf         |
+--------------------------------------------------------------+
```

All CPU-heavy work (video processing, SSIM comparisons) runs in a
**thread pool executor** so the async event loop stays responsive for API requests.

---

## Project Structure

```
youtube_slide_extractor/
|
+-- app/
|   +-- __init__.py
|   +-- main.py                        # App factory, lifespan, CORS, router mount
|   |
|   +-- api/
|   |   +-- v1/
|   |       +-- __init__.py
|   |       +-- router.py              # Mounts all v1 endpoint routers
|   |       +-- endpoints/
|   |           +-- __init__.py
|   |           +-- jobs.py            # POST /jobs, GET /jobs/{id}
|   |           +-- download.py        # GET /jobs/{id}/download
|   |
|   +-- core/
|   |   +-- __init__.py
|   |   +-- config.py                  # Pydantic-settings: env-driven configuration
|   |   +-- logging.py                 # Structured logging setup
|   |
|   +-- models/
|   |   +-- __init__.py
|   |   +-- job.py                     # All Pydantic schemas (request, response, internal)
|   |
|   +-- services/
|   |   +-- __init__.py
|   |   +-- extractor.py               # Core pipeline: download, frames, slides, PDF
|   |   +-- job_store.py               # Async in-memory job registry
|   |   +-- worker.py                  # Background task orchestrator
|   |
|   +-- utils/
|       +-- __init__.py
|       +-- file_utils.py              # temp_workdir context manager + slugify helper
|
+-- tests/
|   +-- conftest.py                    # Async test client fixture
|   +-- test_jobs.py                   # API endpoint integration tests
|   +-- test_extractor.py              # Unit tests for CV helpers
|
+-- .env.example                       # Environment variable template
+-- requirements.txt                   # Python dependencies
+-- Dockerfile                         # Container definition
+-- README.md                          # This file
```

---

## Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| pip | latest | Package management |
| ffmpeg | any recent | Video decoding via yt-dlp |
| libgl1 | system | OpenCV headless dependency (Linux) |

**Install system dependencies:**

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt-get install -y ffmpeg libgl1 libglib2.0-0

# Windows
# Download ffmpeg from https://ffmpeg.org and add to PATH
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/youtube_slide_extractor
cd youtube_slide_extractor
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Copy and configure environment

```bash
cp .env.example .env
# Edit .env as needed (see Configuration section)
```

---

## Configuration

All settings live in `app/core/config.py` and are driven by environment variables
or a `.env` file in the project root. Every field can be overridden at runtime.

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_ENV` | string | `development` | `development` or `production` |
| `APP_TITLE` | string | `YouTube Slide Extractor` | Shown in OpenAPI UI |
| `APP_VERSION` | string | `1.0.0` | Shown in `/docs` and `/health` |
| `OUTPUT_DIR` | path | `./outputs` | Where completed PDFs are stored on disk |
| `MAX_CONCURRENT_JOBS` | int | `3` | Max simultaneous extraction jobs |
| `JOB_TTL_SECONDS` | int | `3600` | Reserved for future auto-cleanup of old PDFs |
| `LOG_LEVEL` | string | `INFO` | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

**Example `.env` for production:**

```env
APP_ENV=production
APP_VERSION=1.2.0
OUTPUT_DIR=/data/slides
MAX_CONCURRENT_JOBS=5
JOB_TTL_SECONDS=7200
LOG_LEVEL=WARNING
```

`OUTPUT_DIR` is created automatically on startup if it does not exist.

---

## Running the Service

### Development (hot-reload enabled)

```bash
uvicorn app.main:app --reload --port 8000
```

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

| URL | Purpose |
|---|---|
| `http://localhost:8000/api/v1` | API base path |
| `http://localhost:8000/docs` | Swagger UI (interactive) |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/health` | Liveness probe |

---

## API Reference

### Health Check

```
GET /health
```

Returns service version and liveness status.
Use for load-balancer or container orchestration health probes.

**Response `200 OK`**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### Submit a Job

```
POST /api/v1/jobs
```

Submits a YouTube video URL for slide extraction. Returns immediately with a
`job_id`; processing continues in the background.

**Request Body**

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `youtube_url` | string (URL) | Yes | - | Valid HTTP/HTTPS URL | Full YouTube video URL |
| `sample_interval_sec` | float | No | `1.0` | `0.1` to `10.0` | Seconds between sampled frames |
| `similarity_threshold` | float | No | `0.90` | `0.5` to `1.0` | SSIM cutoff for slide-change detection |

**Example Request**

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=aircAruvnKk",
    "sample_interval_sec": 1.0,
    "similarity_threshold": 0.90
  }'
```

**Response `202 Accepted`**

```json
{
  "job_id": "a1b2c3d4",
  "status": "queued",
  "created_at": "2024-06-01T10:30:00.000Z"
}
```

**Response `422 Unprocessable Entity`** — invalid URL or out-of-range numeric field

```json
{
  "detail": [
    {
      "type": "url_parsing",
      "loc": ["body", "youtube_url"],
      "msg": "Input should be a valid URL"
    }
  ]
}
```

---

### Poll Job Status

```
GET /api/v1/jobs/{job_id}
```

Returns the current state of a job.
Poll until `status` is `"completed"` or `"failed"`.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | The 8-character hex ID returned by `POST /api/v1/jobs` |

**Example Request**

```bash
curl http://localhost:8000/api/v1/jobs/a1b2c3d4
```

**Response `200 OK` - in progress**

```json
{
  "job_id": "a1b2c3d4",
  "status": "processing",
  "stage": "detecting_slides",
  "progress_pct": 72,
  "slide_count": null,
  "video_title": "3Blue1Brown - But what is a neural network?",
  "error": null,
  "created_at": "2024-06-01T10:30:00.000Z",
  "completed_at": null
}
```

**Response `200 OK` - completed**

```json
{
  "job_id": "a1b2c3d4",
  "status": "completed",
  "stage": "done",
  "progress_pct": 100,
  "slide_count": 47,
  "video_title": "3Blue1Brown - But what is a neural network?",
  "error": null,
  "created_at": "2024-06-01T10:30:00.000Z",
  "completed_at": "2024-06-01T10:37:22.000Z"
}
```

**Response `200 OK` - failed**

```json
{
  "job_id": "a1b2c3d4",
  "status": "failed",
  "stage": "download",
  "progress_pct": 5,
  "slide_count": null,
  "video_title": null,
  "error": "Video unavailable",
  "created_at": "2024-06-01T10:30:00.000Z",
  "completed_at": "2024-06-01T10:30:08.000Z"
}
```

**Status values**

| Value | Meaning |
|---|---|
| `queued` | Job accepted, waiting to start |
| `processing` | Pipeline is actively running |
| `completed` | PDF is ready to download |
| `failed` | An error occurred - see the `error` field |

**Stage values and progress ranges**

| Stage | Progress | Description |
|---|---|---|
| `download` | 0 - 25% | Fetching video with yt-dlp |
| `extracting_frames` | 25 - 55% | Sampling frames with OpenCV |
| `detecting_slides` | 55 - 85% | Running SSIM comparison across frames |
| `building_pdf` | 85 - 100% | Assembling slides into PDF with ReportLab |
| `done` | 100% | All stages complete |

**Response `404 Not Found`**

```json
{ "detail": "Job 'a1b2c3d4' not found." }
```

---

### Download PDF

```
GET /api/v1/jobs/{job_id}/download
```

Streams the completed PDF to the client.
Only available when `status == "completed"`.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | The 8-character hex job ID |

**Example Requests**

```bash
# Use the server-suggested filename (video title)
curl -OJ http://localhost:8000/api/v1/jobs/a1b2c3d4/download

# Save with a custom local filename
curl -o my_slides.pdf http://localhost:8000/api/v1/jobs/a1b2c3d4/download
```

**Response `200 OK`**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="But_what_is_a_neural_network.pdf"
```

Body: raw PDF binary.

**Error Responses**

| Code | Condition |
|---|---|
| `404 Not Found` | `job_id` does not exist |
| `409 Conflict` | Job is not yet completed |
| `500 Internal Server Error` | Job completed but `pdf_path` is missing |

---

## How It Works

### Pipeline Stages

#### Stage 1 - Download (0-25%)

`yt-dlp` fetches the video at up to 720p MP4. Choosing 720p over 1080p cuts
file size by roughly 60% with no meaningful impact on slide legibility.

The video `title` is extracted from the yt-dlp metadata during this step and
stored immediately on the `JobRecord`, so it becomes visible in status polls
before the rest of the pipeline finishes.

#### Stage 2 - Frame Sampling (25-55%)

OpenCV opens the MP4 and seeks to every Nth frame, where N = `fps x interval_sec`.
Each frame is saved as a JPEG at quality 90. For a 60-minute lecture at 25fps
with `interval=1.0s`, this produces roughly 3,600 frames.

#### Stage 3 - Slide Detection (55-85%)

Each consecutive frame pair is compared using SSIM (Structural Similarity Index).
When the score drops below `similarity_threshold`, the previous stable run is
evaluated as a potential slide. Two additional heuristics filter non-slide candidates:

- **Brightness gate**: frames with mean pixel brightness below 30/255 are black
  screens or transitions and are discarded.
- **Edge density gate**: frames where more than 15% of pixels are Canny edges
  are camera footage or complex scenes and are discarded.

The representative frame chosen for each slide is the **middle frame** of the
stable run, avoiding mid-transition artifacts.

#### Stage 4 - PDF Assembly (85-100%)

ReportLab opens a canvas with landscape 16:9 pages (1280 x 720 pt). Each slide
image is scaled to fill the page while preserving aspect ratio. A small grey
`Slide N / Total` label is added to the bottom-left corner of each page.

---

### Slide Detection Algorithm

Full logic in `app/services/extractor.py`:

```
for each consecutive pair (frame[i], frame[i+1]):

  1. Resize both to 320x180 grayscale thumbnails  (speed optimisation)
  2. Compute SSIM(thumbnail_i, thumbnail_i+1)

  3. if SSIM < similarity_threshold:
       run_length = i - run_start

       if run_length >= min_run_frames (default: 3):
         candidate = middle frame of run

         if mean_brightness(candidate) > 30:      # not a dark transition
           if edge_density(candidate) < 0.15:      # not camera footage
             add candidate to slides list

       run_start = i

4. After loop: apply same logic to the final run
```

**Why SSIM over pixel difference?**

SSIM accounts for luminance, contrast, and structural patterns simultaneously.
A simple mean-absolute-difference triggers false positives on encoding
artifacts, cursor movement, or subtle lighting flicker that do not represent
real slide changes.

**Why a minimum run length?**

Requiring 3+ consecutive similar frames suppresses single-frame anomalies
such as flash effects, animated GIFs, or laser-pointer movements that would
otherwise create spurious slide entries.

---

### PDF Naming

```
Raw title:  "3Blue1Brown - But what is a neural network? | Chapter 1, deep learning"
    |
    v  strip whitespace
    v  remove non-word characters
    v  collapse spaces and hyphens to underscores
    v  truncate to 100 characters
    v  fallback to "slides" if result is empty

On disk:    "3Blue1Brown_But_what_is_a_neural_network__a1b2c3d4.pdf"
To client:  "3Blue1Brown_But_what_is_a_neural_network.pdf"
```

The `job_id` suffix on disk ensures uniqueness when two jobs process the same
video. It is stripped from the client-facing filename.

---

## Module Reference

### `app/core`

| File | Responsibility |
|---|---|
| `config.py` | Pydantic `BaseSettings` singleton `settings`. Reads `.env` and env vars. Auto-creates `OUTPUT_DIR` on import. |
| `logging.py` | Configures stdout logging with timestamp, level, and logger name. Quiets `yt_dlp` and `urllib3`. Called once from `main.py` lifespan. |

---

### `app/models`

All I/O contracts are Pydantic v2 models in `job.py`.

| Model | Direction | Description |
|---|---|---|
| `JobCreate` | Request body | Validates `POST /jobs` - enforces URL format and numeric ranges |
| `JobQueued` | Response | `202 Accepted` body: `job_id`, `status`, `created_at` |
| `JobResponse` | Response | `GET /jobs/{id}` body: all progress fields including `video_title` |
| `JobRecord` | Internal | Full state in `JobStore`. Has `.to_response()` projecting into `JobResponse` |
| `JobStatus` | Enum | `queued`, `processing`, `completed`, `failed` |
| `JobStage` | Enum | `download`, `extracting_frames`, `detecting_slides`, `building_pdf`, `done` |

---

### `app/services`

#### `extractor.py`

Pure synchronous functions - all run in thread pool via `loop.run_in_executor()`.

| Function | Returns | Description |
|---|---|---|
| `download_video(url, work_dir, on_progress)` | `tuple[Path, str]` | Downloads video; returns `(path, video_title)` |
| `extract_frames(video_path, work_dir, interval_sec, on_progress)` | `list[Path]` | Samples frames at configured interval |
| `detect_slides(frame_paths, threshold, min_run, on_progress)` | `list[Path]` | One representative path per unique slide |
| `build_pdf(slide_paths, output_pdf, on_progress)` | `int` | Writes PDF; returns slide count |

All accept `on_progress: Callable[[int, str], None]` invoked with
`(percent, stage_name)` allowing the worker to push live updates to `JobStore`.

#### `job_store.py`

Async-safe in-memory dictionary wrapped with `asyncio.Lock()`.
Exported as module-level singleton `job_store`.

| Method | Description |
|---|---|
| `add(record)` | Insert a new `JobRecord` |
| `get(job_id)` | Fetch by ID - returns `None` if not found |
| `update(record)` | Overwrite an existing record |
| `delete(job_id)` | Remove a job |
| `all()` | Return all current records as a list |

#### `worker.py`

`run_job(record)` is an async coroutine added to FastAPI `BackgroundTasks`:

1. Sets `status = processing` and updates the store
2. Orchestrates each pipeline stage via `loop.run_in_executor()`
3. After `download_video`, immediately stores `video_title` so it appears in polls
4. Constructs output path as `{OUTPUT_DIR}/{slug}__{job_id}.pdf`
5. On success: sets `status = completed`, stores `pdf_path`, `slide_count`, `completed_at`
6. On any exception: sets `status = failed`, stores error message and `completed_at`

---

### `app/api`

#### `endpoints/jobs.py`

**`POST /api/v1/jobs`** - validates `JobCreate`, builds a `JobRecord`, stores it
in `job_store`, enqueues `run_job` as a `BackgroundTask`, returns `202` immediately.

**`GET /api/v1/jobs/{job_id}`** - fetches the record, calls `.to_response()`,
returns result. Returns `404` if ID is unknown.

#### `endpoints/download.py`

**`GET /api/v1/jobs/{job_id}/download`** - validates job exists and has
`status == completed`, then returns a `FileResponse`. The `filename` in
`Content-Disposition` is the slugified video title without the job ID suffix.

#### `router.py`

Mounts both endpoint routers under the shared `/api/v1` prefix.

---

### `app/utils`

#### `file_utils.py`

| Utility | Signature | Description |
|---|---|---|
| `temp_workdir()` | `@contextmanager -> Path` | Creates `tempfile.mkdtemp()` directory; guarantees deletion via `shutil.rmtree()` on exit, even if an exception is raised |
| `slugify(text, max_len)` | `(str, int=100) -> str` | Converts arbitrary text (e.g. video title) to a filesystem-safe string |

---

## Testing

Tests use `pytest` with `pytest-asyncio` and an in-process `httpx.AsyncClient`.
No real network calls or video downloads are made.

### Run all tests

```bash
pytest tests/ -v
```

### Run with coverage report

```bash
pip install pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

### Run a single test file

```bash
pytest tests/test_extractor.py -v
```

### Test overview

| File | Scope | What is tested |
|---|---|---|
| `conftest.py` | Fixture | `client` async fixture via `httpx.AsyncClient` with `ASGITransport` |
| `test_jobs.py` | Integration | Health; job creation (valid + invalid URLs); 404 for unknown jobs; 409 for premature downloads |
| `test_extractor.py` | Unit | `_ssim_similar()` with identical/different frames; `_is_slide_like()` with dark/bright synthetic numpy arrays |

### Example test pattern

```python
@pytest.mark.asyncio
async def test_create_job_custom_threshold(client):
    payload = {
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "similarity_threshold": 0.85,
        "sample_interval_sec": 0.5,
    }
    r = await client.post("/api/v1/jobs", json=payload)
    assert r.status_code == 202
    assert r.json()["status"] == "queued"
```

---

## Docker

### Build the image

```bash
docker build -t yt-slide-extractor:latest .
```

### Run a container

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  -e LOG_LEVEL=INFO \
  -e MAX_CONCURRENT_JOBS=5 \
  --name slide-extractor \
  yt-slide-extractor:latest
```

Mounting `./outputs` as a volume persists generated PDFs across container restarts.

### Useful commands

```bash
# View logs
docker logs -f slide-extractor

# Stop and remove
docker stop slide-extractor && docker rm slide-extractor

# Rebuild and restart
docker build -t yt-slide-extractor:latest .
docker run -d -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  --name slide-extractor \
  yt-slide-extractor:latest
```

### Dockerfile overview

```dockerfile
FROM python:3.11-slim

# System deps: OpenCV headless + ffmpeg for video decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p outputs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Tuning Guide

### Too few slides captured?

The detector is being too conservative. Lower the threshold and sample more frequently:

```json
{ "sample_interval_sec": 0.5, "similarity_threshold": 0.85 }
```

### Too many duplicate slides in the PDF?

The detector is too sensitive. Raise the threshold and sample less frequently:

```json
{ "sample_interval_sec": 2.0, "similarity_threshold": 0.93 }
```

### Recommended presets by lecture type

| Lecture Type | interval | threshold | Notes |
|---|---|---|---|
| Fast-paced (slides every 10-20s) | `0.5` | `0.87` | Captures rapid transitions |
| Standard academic lecture | `1.0` | `0.90` | Good default for most videos |
| Slow lecture or webinar | `2.0` | `0.92` | Fewer frames, faster processing |
| Lecture with heavy camera cuts | `1.0` | `0.80` | Edge filter handles camera frames |

### Estimated processing times

| Video Length | Interval | Approximate Time |
|---|---|---|
| 30 minutes | 1.0s | 3 - 5 minutes |
| 60 minutes | 1.0s | 6 - 10 minutes |
| 60 minutes | 2.0s | 3 - 5 minutes |
| 90 minutes | 1.0s | 9 - 15 minutes |

Processing runs in a background thread and never blocks the API.

---

## Error Handling

### API-level errors

| Scenario | HTTP Code | Response |
|---|---|---|
| Invalid `youtube_url` format | `422` | Pydantic validation detail |
| Numeric field out of range | `422` | Pydantic validation detail |
| Unknown `job_id` | `404` | `{"detail": "Job 'xyz' not found."}` |
| Download before completion | `409` | `{"detail": "Job is not completed yet (status: processing)."}` |
| PDF path missing after completion | `500` | `{"detail": "PDF path missing."}` |

### Job-level errors

When any pipeline stage raises an exception, the job transitions to
`status: "failed"` and the `error` field contains the exception message.

| Error Message | Likely Cause | Resolution |
|---|---|---|
| `Sign in to confirm you're not a bot` | YouTube rate limiting or bot detection | Wait a few minutes and retry |
| `Video unavailable` | Private, deleted, or geo-restricted video | Use a publicly accessible video |
| `This video is age-restricted` | Age-gated content requires authentication | Not supported without auth cookies |
| `Cannot open video` | Corrupt download or unsupported codec | Verify ffmpeg is installed and on PATH |
| `Downloaded video missing` | yt-dlp wrote file with unexpected extension | Run `pip install -U yt-dlp` |
| `No module named 'cv2'` | OpenCV not installed | Run `pip install opencv-python-headless` |

---

## Contributing

### Setup for development

```bash
git clone https://github.com/your-org/youtube_slide_extractor
cd youtube_slide_extractor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Write tests covering the new behaviour in `tests/`
4. Ensure all tests pass: `pytest tests/ -v`
5. Format and lint: `black app/ tests/ && ruff check app/ tests/`
6. Submit a pull request with a clear description of the change

### Code style tools

```bash
pip install black ruff
black app/ tests/
ruff check app/ tests/
```

---

<!-- ## License -->

<!-- MIT License. See `LICENSE` for details. -->
