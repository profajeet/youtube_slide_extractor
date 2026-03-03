"""
Background worker: runs the full pipeline and keeps JobRecord updated.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.job import JobRecord, JobStatus, JobStage
from app.services.job_store import job_store
from app.services import extractor
from app.utils.file_utils import temp_workdir,  slugify

log = logging.getLogger(__name__)


async def run_job(record: JobRecord) -> None:
    loop = asyncio.get_event_loop()

    def progress(pct: int, stage: str) -> None:
        record.progress_pct = pct
        record.stage = JobStage(stage) if stage in JobStage._value2member_map_ else record.stage
        asyncio.run_coroutine_threadsafe(job_store.update(record), loop)

    record.status = JobStatus.PROCESSING
    await job_store.update(record)

    try:
        with temp_workdir() as work_dir:
            # download_video now returns (path, title)
            video, title = await loop.run_in_executor(
                None, extractor.download_video, record.youtube_url, work_dir, progress
            )

            # Store title on record immediately so polling shows it early
            record.video_title = title
            await job_store.update(record)

            # Build a safe filename from the title, keep job_id as suffix for uniqueness
            safe_title = slugify(title)
            output_pdf = settings.OUTPUT_DIR / f"{safe_title}__{record.job_id}.pdf"

            frames = await loop.run_in_executor(
                None, extractor.extract_frames, video, work_dir,
                record.sample_interval_sec, progress
            )
            slides = await loop.run_in_executor(
                None, extractor.detect_slides, frames,
                record.similarity_threshold, 3, progress
            )
            slide_count = await loop.run_in_executor(
                None, extractor.build_pdf, slides, output_pdf, progress
            )

        record.status = JobStatus.COMPLETED
        record.stage = JobStage.DONE
        record.progress_pct = 100
        record.slide_count = slide_count
        record.pdf_path = str(output_pdf)
        record.completed_at = datetime.now(timezone.utc)
        log.info("Job %s completed — %d slides → %s", record.job_id, slide_count, output_pdf.name)

    except Exception as exc:
        log.exception("Job %s failed", record.job_id)
        record.status = JobStatus.FAILED
        record.error = str(exc)
        record.completed_at = datetime.now(timezone.utc)

    await job_store.update(record)