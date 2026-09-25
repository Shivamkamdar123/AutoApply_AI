"""
Lever Job Board Adapter
=======================
Scrapes / queries public Lever board API (api.lever.co/v0/postings/{company}).
Stores raw postings separately and deduplicates listings.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_lever")

DEFAULT_LEVER_COMPANIES = ["palantir", "deliveroo", "reddit"]


class LeverJobAdapter(JobScraperAdapter):
    """Adapter for scraping public Lever ATS job postings."""

    @property
    def source_name(self) -> str:
        return "lever"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 20,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_lever", correlation_id=correlation_id)
        log.info("lever_fetch_start", query=query, location=location)

        postings: List[JobPosting] = []

        for company in DEFAULT_LEVER_COMPANIES:
            if len(postings) >= limit:
                break

            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            try:
                self.check_compliance(url)
            except Exception as e:
                log.warning("lever_compliance_skip", company=company, reason=str(e))
                continue

            try:
                with httpx.Client(timeout=8.0) as client:
                    resp = client.get(url, headers={"User-Agent": "AutoApplyAI-Bot/1.0"})
                    if resp.status_code != 200:
                        log.debug("lever_board_non_200", company=company, status=resp.status_code)
                        continue

                    raw_jobs = resp.json()
                    if not isinstance(raw_jobs, list):
                        continue

                    for item in raw_jobs:
                        if len(postings) >= limit:
                            break

                        job_id = f"lever-{item.get('id', '')}"
                        title = item.get("text", "")
                        categories = item.get("categories", {})
                        loc_name = categories.get("location", "Remote")
                        description_plain = item.get("descriptionPlain", "") or ""
                        job_url = item.get("hostedUrl", f"https://jobs.lever.co/{company}/{item.get('id')}")
                        created_at = str(item.get("createdAt", ""))

                        description = description_plain or title

                        if query and query.lower() not in title.lower() and query.lower() not in description.lower():
                            continue
                        if location and location.lower() not in loc_name.lower():
                            continue

                        raw_hash = compute_job_hash(company, title, description)

                        storage.save_raw_job(
                            job_id=job_id,
                            source=self.source_name,
                            url=job_url,
                            raw_hash=raw_hash,
                            payload=item,
                        )

                        if storage.is_content_seen(raw_hash):
                            log.debug("skipping_duplicate_lever_job", job_id=job_id)
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
                            posted_at=created_at,
                            raw_hash=raw_hash,
                        )
                        postings.append(posting)

            except Exception as e:
                log.warning("lever_fetch_error", company=company, error=str(e))
                continue

        log.info("lever_fetch_complete", count=len(postings))
        return postings
