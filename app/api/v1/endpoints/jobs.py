import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.job import JobCreate, JobQueued, JobResponse, JobRecord, JobStatus
from app.services.job_store import job_store
from app.services.worker import run_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobQueued, status_code=202,
             summary="Submit a new slide-extraction job")
async def create_job(payload: JobCreate, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:8]
    record = JobRecord(
        job_id=job_id,
        youtube_url=str(payload.youtube_url),
        sample_interval_sec=payload.sample_interval_sec,
        similarity_threshold=payload.similarity_threshold,
        created_at=datetime.now(timezone.utc),
    )
    await job_store.add(record)
    background_tasks.add_task(run_job, record)
    return JobQueued(job_id=job_id, status=record.status, created_at=record.created_at)


@router.get("/{job_id}", response_model=JobResponse, summary="Get job status")
async def get_job(job_id: str):
    record = await job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return record.to_response()