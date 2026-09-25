"""
Sample Job Board Adapter
========================
Offline adapter that reads from the bundled sample_jobs.json fixture.
Guarantees deterministic, fast results for test suites and offline demos.
"""

import json
from typing import List, Optional

from app.config import settings
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_sample")


class SampleJobAdapter(JobScraperAdapter):
    """Adapter reading from local sample_jobs.json."""

    @property
    def source_name(self) -> str:
        return "sample"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 20,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_sample", correlation_id=correlation_id)
        if not settings.SAMPLE_JOBS_FILE.exists():
            log.warning("sample_jobs_file_missing", path=str(settings.SAMPLE_JOBS_FILE))
            return []

        try:
            with open(settings.SAMPLE_JOBS_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            postings: List[JobPosting] = []
            for item in raw_data:
                posting = JobPosting(**item)
                raw_hash = compute_job_hash(posting.company, posting.title, posting.description)
                posting.raw_hash = raw_hash

                # Cache raw payload in storage
                storage.save_raw_job(
                    job_id=posting.id,
                    source=self.source_name,
                    url=posting.url,
                    raw_hash=raw_hash,
                    payload=item,
                )

                if query:
                    q = query.lower()
                    if q not in posting.title.lower() and q not in posting.description.lower():
                        continue

                if location:
                    if location.lower() not in posting.location.lower():
                        continue

                postings.append(posting)

            return postings[:limit]
        except Exception as e:
            log.error("sample_jobs_read_error", error=str(e))
            return []
