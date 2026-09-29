"""
Remote Job Feed Adapter
=======================
Scrapes / queries public software developer remote feeds (e.g. Remotive Developer API).
Provides live, high-quality tech postings for matching without login gates.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_remotefeed")


class RemoteFeedJobAdapter(JobScraperAdapter):
    """Adapter for querying public remote developer job feeds."""

    @property
    def source_name(self) -> str:
        return "remotive"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 20,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_remotefeed", correlation_id=correlation_id)
        log.info("remotefeed_fetch_start", query=query, location=location)

        postings: List[JobPosting] = []
        if query:
            feed_url = f"https://remotive.com/api/remote-jobs?search={httpx.URL('', params={'q': query}).params.get('q')}&limit={limit}"
        else:
            feed_url = f"https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(feed_url, headers={"User-Agent": "AutoApplyAI-Bot/1.0"})
                if resp.status_code == 429:
                    raise RuntimeError("Rate limited by Remotive API (HTTP 429)")
                if resp.status_code != 200:
                    log.debug("remotefeed_non_200", status=resp.status_code)
                    return []

                data = resp.json()
                raw_jobs = data.get("jobs", [])

                for item in raw_jobs:
                    if len(postings) >= limit:
                        break

                    job_id = f"rem-{item.get('id', '')}"
                    title = item.get("title", "")
                    company = item.get("company_name", "Remote Company")
                    loc_name = item.get("candidate_required_location", "Remote")
                    raw_desc = item.get("description", "")
                    job_url = item.get("url", "")
                    pub_date = item.get("publication_date")
                    sal_range = item.get("salary") or None

                    # Strip HTML
                    soup = BeautifulSoup(raw_desc, "html.parser")
                    description = soup.get_text(separator=" ", strip=True) or title

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
                    storage.record_content_hash(raw_hash, job_id)

                    posting = JobPosting(
                        id=job_id,
                        title=title,
                        company=company,
                        location=loc_name,
                        description=description,
                        url=job_url,
                        source=self.source_name,
                        posted_at=pub_date,
                        raw_hash=raw_hash,
                        salary_range=sal_range,
                    )
                    postings.append(posting)

        except Exception as e:
            log.warning("remotefeed_fetch_error", error=str(e))

        log.info("remotefeed_fetch_complete", count=len(postings))
        return postings
