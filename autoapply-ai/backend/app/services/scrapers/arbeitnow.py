"""
Arbeitnow Job Board API Adapter
===============================
Queries Arbeitnow's public REST API (https://www.arbeitnow.com/api/job-board-api).
Completely free, no API key required, reliable real-time tech job postings.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_arbeitnow")


class ArbeitnowJobAdapter(JobScraperAdapter):
    """Adapter for querying Arbeitnow's public job board API."""

    @property
    def source_name(self) -> str:
        return "arbeitnow"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 25,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_arbeitnow", correlation_id=correlation_id)
        log.info("arbeitnow_fetch_start", query=query, location=location)

        postings: List[JobPosting] = []
        api_url = "https://www.arbeitnow.com/api/job-board-api"

        try:
            headers = {
                "User-Agent": "AutoApplyAI-Bot/1.0 (+https://github.com/Shivamkamdar123/AutoApply_AI)",
                "Accept": "application/json",
            }
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(api_url, headers=headers)
                if resp.status_code != 200:
                    log.warning("arbeitnow_non_200", status=resp.status_code)
                    return []

                data = resp.json()
                raw_items = data.get("data", [])

                for item in raw_items:
                    if len(postings) >= limit:
                        break

                    slug = item.get("slug") or item.get("id") or ""
                    job_id = f"arbeit-{slug[:30]}"
                    title = item.get("title", "")
                    company = item.get("company_name", "Tech Company")
                    loc_name = item.get("location", "Remote" if item.get("remote") else "Worldwide")
                    raw_desc = item.get("description", "")
                    job_url = item.get("url", "")
                    pub_date = str(item.get("created_at", ""))
                    tags = item.get("tags", [])

                    # Clean HTML description
                    soup = BeautifulSoup(raw_desc, "html.parser")
                    clean_desc = soup.get_text(separator=" ", strip=True) or title
                    if tags:
                        clean_desc += f" Required skills and keywords: {', '.join(tags)}."

                    # Query / location filter
                    if query:
                        q_lower = query.lower()
                        if (
                            q_lower not in title.lower()
                            and q_lower not in clean_desc.lower()
                            and not any(q_lower in t.lower() for t in tags)
                        ):
                            continue

                    if location and location.lower() not in loc_name.lower():
                        continue

                    raw_hash = compute_job_hash(company, title, clean_desc)

                    storage.save_raw_job(
                        job_id=job_id,
                        source=self.source_name,
                        url=job_url,
                        raw_hash=raw_hash,
                        payload=item,
                    )

                    posting = JobPosting(
                        id=job_id,
                        title=title,
                        company=company,
                        location=loc_name,
                        description=clean_desc,
                        url=job_url,
                        source=self.source_name,
                        posted_at=pub_date,
                        raw_hash=raw_hash,
                    )
                    postings.append(posting)

        except Exception as e:
            log.warning("arbeitnow_fetch_failed", error=str(e))
            raise

        log.info("arbeitnow_fetch_complete", count=len(postings))
        return postings
