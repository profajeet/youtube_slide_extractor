from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.models.job import JobStatus
from app.services.job_store import job_store
from app.utils.file_utils import slugify

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}/download", summary="Download the generated PDF")
async def download_pdf(job_id: str):
    record = await job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if record.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=409,
                            detail=f"Job is not completed yet (status: {record.status}).")
    if not record.pdf_path:
        raise HTTPException(status_code=500, detail="PDF path missing.")

    # Use the video title for the downloaded filename seen by the browser/client
    safe_name = slugify(record.video_title or "slides")
    download_filename = f"{safe_name}.pdf"

    return FileResponse(
        path=record.pdf_path,
        media_type="application/pdf",
        filename=download_filename,       # ← "Intro_to_ML_Lecture_3.pdf"
    )