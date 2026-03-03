import asyncio
from typing import Optional
from app.models.job import JobRecord


class JobStore:
    """Thread-safe in-memory job registry."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def add(self, record: JobRecord) -> None:
        async with self._lock:
            self._jobs[record.job_id] = record

    async def get(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(self, record: JobRecord) -> None:
        async with self._lock:
            self._jobs[record.job_id] = record

    async def delete(self, job_id: str) -> None:
        async with self._lock:
            self._jobs.pop(job_id, None)

    async def all(self) -> list[JobRecord]:
        async with self._lock:
            return list(self._jobs.values())


# Singleton instance shared across the app
job_store = JobStore()