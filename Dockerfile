FROM python:3.11-slim

# System deps for OpenCV
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

## 🔄 Full Request Lifecycle
```
POST /api/v1/jobs
       │
       ▼
  JobRecord created (status=queued)  →  stored in JobStore
       │
       ▼
  BackgroundTask: worker.run_job()
       │
       ├── extractor.download_video()     (progress 0–25%)
       ├── extractor.extract_frames()     (progress 25–55%)
       ├── extractor.detect_slides()      (progress 55–85%)
       └── extractor.build_pdf()          (progress 85–100%)
                                          PDF saved to outputs/{job_id}.pdf
                                          status=completed

GET /api/v1/jobs/{id}          → poll status & progress
GET /api/v1/jobs/{id}/download → stream PDF (409 if not done)