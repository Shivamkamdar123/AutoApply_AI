"""
Greenhouse Job Board Adapter
============================
Scrapes / queries public Greenhouse board endpoints (e.g. boards-api.greenhouse.io).
Stores raw postings separately from normalized JobPosting objects.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import ScraperParsingError
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_greenhouse")

# Default public tech companies using Greenhouse boards for testing
DEFAULT_COMPANIES = ["canonical", "cloudflare", "gitlab"]


class GreenhouseJobAdapter(JobScraperAdapter):
    """Adapter for scraping public Greenhouse ATS job postings."""

    @property
    def source_name(self) -> str:
        return "greenhouse"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 20,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_greenhouse", correlation_id=correlation_id)
        log.info("greenhouse_fetch_start", query=query, location=location)

        postings: List[JobPosting] = []

        # Iterate over known public board endpoints
        for company in DEFAULT_COMPANIES:
            if len(postings) >= limit:
                break

            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            try:
                self.check_compliance(url)
            except Exception as e:
                log.warning("greenhouse_compliance_skip", company=company, reason=str(e))
                continue

            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.get(url, headers={"User-Agent": "AutoApplyAI-Bot/1.0"})
                    if resp.status_code != 200:
                        log.debug("greenhouse_board_non_200", company=company, status=resp.status_code)
                        continue

                    data = resp.json()
                    raw_jobs = data.get("jobs", [])

                    for item in raw_jobs:
                        if len(postings) >= limit:
                            break

                        job_id = f"gh-{item.get('id', '')}"
                        title = item.get("title", "")
                        loc_name = item.get("location", {}).get("name", "Remote")
                        content_html = item.get("content", "")
                        job_url = item.get("absolute_url", f"https://boards.greenhouse.io/{company}/jobs/{item.get('id')}")
                        updated_at = item.get("updated_at")

                        # Strip HTML for description
                        soup = BeautifulSoup(content_html, "html.parser")
                        description = soup.get_text(separator=" ", strip=True) or title

                        # Filter by query & location if requested
                        if query and query.lower() not in title.lower() and query.lower() not in description.lower():
                            continue
                        if location and location.lower() not in loc_name.lower():
                            continue

                        # Compute fingerprint for deduplication
                        raw_hash = compute_job_hash(company, title, description)

                        # Separate raw payload storage from normalized model
                        storage.save_raw_job(
                            job_id=job_id,
                            source=self.source_name,
                            url=job_url,
                            raw_hash=raw_hash,
                            payload=item,
                        )

                        # Check deduplication
                        if storage.is_content_seen(raw_hash):
                            log.debug("skipping_duplicate_greenhouse_job", job_id=job_id)
                            continue

                        storage.record_content_hash(raw_hash, job_id)

                        posting = JobPosting(
                            id=job_id,
                            title=title,
                            company=company.capitalize(),
                            location=loc_name,
                            description=description,
                            url=job_url,
                            source=self.source_name,
                            posted_at=updated_at,
                            raw_hash=raw_hash,
                        )
                        postings.append(posting)

            except Exception as e:
                log.warning("greenhouse_fetch_error", company=company, error=str(e))
                continue

        log.info("greenhouse_fetch_complete", count=len(postings))
        return postings
