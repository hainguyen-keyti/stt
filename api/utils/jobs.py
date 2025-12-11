"""
In-memory Job Queue Manager

Manages async subtitle generation jobs with status tracking.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import threading

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a subtitle generation job"""
    id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0  # 0-100
    result: Optional[Any] = None
    error: Optional[str] = None
    # Job parameters
    format: str = "srt"
    filename: str = ""


class JobManager:
    """
    In-memory job manager for async subtitle generation.

    Thread-safe storage for job status and results.
    Jobs are kept in memory and will be lost on restart.
    """

    def __init__(self, max_jobs: int = 100):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max_jobs = max_jobs

    def create_job(self, format: str = "srt", filename: str = "") -> Job:
        """Create a new job and return it"""
        with self._lock:
            # Clean up old completed jobs if we have too many
            if len(self._jobs) >= self._max_jobs:
                self._cleanup_old_jobs()

            job_id = str(uuid.uuid4())[:8]  # Short ID for convenience
            job = Job(
                id=job_id,
                format=format,
                filename=filename,
            )
            self._jobs[job_id] = job
            logger.info(f"Created job {job_id}")
            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status and data"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            if status:
                job.status = status
                if status == JobStatus.PROCESSING and not job.started_at:
                    job.started_at = datetime.now()
                elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    job.completed_at = datetime.now()

            if progress is not None:
                job.progress = progress

            if result is not None:
                job.result = result

            if error is not None:
                job.error = error

            return job

    def _cleanup_old_jobs(self):
        """Remove oldest completed jobs to free memory"""
        completed_jobs = [
            (job_id, job) for job_id, job in self._jobs.items()
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
        ]

        # Sort by completion time and remove oldest
        completed_jobs.sort(key=lambda x: x[1].completed_at or datetime.min)

        # Remove half of completed jobs
        to_remove = len(completed_jobs) // 2
        for job_id, _ in completed_jobs[:to_remove]:
            del self._jobs[job_id]
            logger.debug(f"Cleaned up old job {job_id}")

    def list_jobs(self) -> Dict[str, Job]:
        """List all jobs"""
        with self._lock:
            return dict(self._jobs)


# Global job manager instance
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get global job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
