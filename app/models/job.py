from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStage(str, Enum):
    DOWNLOAD = "download"
    EXTRACTING_FRAMES = "extracting_frames"
    DETECTING_SLIDES = "detecting_slides"
    BUILDING_PDF = "building_pdf"
    DONE = "done"


# ── Request / Response schemas ──────────────────────────────────────────────

class JobCreate(BaseModel):
    youtube_url: HttpUrl = Field(..., examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
    sample_interval_sec: float = Field(1.0, ge=0.1, le=10.0, description="Seconds between sampled frames")
    similarity_threshold: float = Field(0.90, ge=0.5, le=1.0, description="SSIM threshold for slide change")


class JobQueued(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage: Optional[JobStage] = None
    progress_pct: int = 0
    slide_count: Optional[int] = None
    video_title: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ── Internal record (not exposed directly) ──────────────────────────────────

class JobRecord(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    stage: Optional[JobStage] = None
    progress_pct: int = 0
    slide_count: Optional[int] = None
    video_title: Optional[str] = None
    error: Optional[str] = None
    pdf_path: Optional[str] = None
    youtube_url: str
    sample_interval_sec: float
    similarity_threshold: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_response(self) -> JobResponse:
        return JobResponse(**self.model_dump(exclude={"pdf_path", "youtube_url",
                                                       "sample_interval_sec", "similarity_threshold"}))