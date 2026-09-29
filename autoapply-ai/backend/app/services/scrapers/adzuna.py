"""
Adzuna Job Aggregator Adapter
=============================
Queries Adzuna API (api.adzuna.com) for real live job listings with salary data.
Degrades gracefully when ADZUNA_APP_ID or ADZUNA_APP_KEY are not configured.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_adzuna")


class AdzunaJobAdapter(JobScraperAdapter):
    """Adapter for querying Adzuna Job Aggregator API."""

    @property
    def source_name(self) -> str:
        return "adzuna"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 25,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_adzuna", correlation_id=correlation_id)

        # Check configuration
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            log.info("adzuna_no_key_configured", note="Get free API key at developer.adzuna.com")
            # Raising an informative ValueError lets the orchestrator report 'no_key' status
            raise ValueError("No API key configured (get free key at https://developer.adzuna.com/)")

        log.info("adzuna_fetch_start", query=query, location=location)
        postings: List[JobPosting] = []

        country = "us"
        q = query or "developer"
        loc = location or ""
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": str(min(limit, 50)),
            "what": q,
            "content-type": "application/json",
        }
        if loc:
            params["where"] = loc

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 429:
                    raise RuntimeError("Rate limited by Adzuna API (HTTP 429)")
                if resp.status_code != 200:
                    log.warning("adzuna_non_200", status=resp.status_code, body=resp.text[:200])
                    return []

                data = resp.json()
                results = data.get("results", [])

                for item in results:
                    if len(postings) >= limit:
                        break

                    job_id = f"adz-{item.get('id', '')}"
                    title = item.get("title", "")
                    company_obj = item.get("company", {})
                    company = company_obj.get("display_name", "Technology Employer") if isinstance(company_obj, dict) else "Technology Employer"
                    loc_obj = item.get("location", {})
                    loc_name = loc_obj.get("display_name", "United States") if isinstance(loc_obj, dict) else "United States"
                    raw_desc = item.get("description", "")
                    job_url = item.get("redirect_url", "")
                    pub_date = item.get("created")

                    sal_min = item.get("salary_min")
                    sal_max = item.get("salary_max")
                    sal_range = None
                    if sal_min and sal_max:
                        sal_range = f"${int(sal_min):,} - ${int(sal_max):,}"
                    elif sal_min:
                        sal_range = f"From ${int(sal_min):,}"

                    soup = BeautifulSoup(raw_desc, "html.parser")
                    clean_desc = soup.get_text(separator=" ", strip=True) or title

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
                        salary_range=sal_range,
                        salary_min=float(sal_min) if sal_min else None,
                        salary_max=float(sal_max) if sal_max else None,
                    )
                    postings.append(posting)

        except Exception as e:
            log.warning("adzuna_fetch_failed", error=str(e))
            raise

        log.info("adzuna_fetch_complete", count=len(postings))
        return postings
