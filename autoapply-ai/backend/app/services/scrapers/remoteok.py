"""
RemoteOK Job Scraper Adapter
============================
Fetches public software and tech job listings from RemoteOK's public API feed.
Implements the unified JobScraperAdapter interface with polite crawl delays,
robots.txt verification, content hashing, and raw payload caching.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_remoteok")


class RemoteOKJobAdapter(JobScraperAdapter):
    """Adapter for querying RemoteOK public developer postings."""

    @property
    def source_name(self) -> str:
        return "remoteok"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 20,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_remoteok", correlation_id=correlation_id)
        log.info("remoteok_fetch_start", query=query, location=location)

        postings: List[JobPosting] = []
        api_url = "https://remoteok.com/api"

        try:
            self.check_compliance(api_url)
        except Exception as e:
            log.warning("remoteok_compliance_skip", reason=str(e))
            return []

        try:
            headers = {
                "User-Agent": "AutoApplyAI-Bot/1.0 (+https://github.com/Shivamkamdar123/AutoApply_AI)",
                "Accept": "application/json",
            }
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.get(api_url, headers=headers)
                if resp.status_code != 200:
                    log.debug("remoteok_non_200", status=resp.status_code)
                    return []

                data = resp.json()
                # RemoteOK returns an array where the first item is a legal/info disclaimer object
                items = data[1:] if isinstance(data, list) and len(data) > 1 else []

                for item in items:
                    if len(postings) >= limit:
                        break

                    job_id_num = item.get("id") or item.get("slug", "")
                    if not job_id_num:
                        continue

                    job_id = f"rok-{job_id_num}"
                    title = item.get("position", "")
                    company = item.get("company", "Remote Company")
                    loc_name = item.get("location") or "Worldwide / Remote"
                    raw_desc = item.get("description", "")
                    job_url = item.get("url") or f"https://remoteok.com/remote-jobs/{job_id_num}"
                    pub_date = item.get("date")

                    # Strip HTML formatting from description
                    soup = BeautifulSoup(raw_desc, "html.parser")
                    description = soup.get_text(separator=" ", strip=True) or title

                    # Filter by query keyword if provided
                    if query:
                        q_lower = query.lower()
                        tags = " ".join(item.get("tags", [])).lower()
                        if (
                            q_lower not in title.lower()
                            and q_lower not in description.lower()
                            and q_lower not in tags
                        ):
                            continue

                    # Filter by location if specified
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
                        continue

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
                    )
                    postings.append(posting)

        except Exception as e:
            log.warning("remoteok_fetch_error", error=str(e))

        log.info("remoteok_fetch_complete", count=len(postings))
        return postings
