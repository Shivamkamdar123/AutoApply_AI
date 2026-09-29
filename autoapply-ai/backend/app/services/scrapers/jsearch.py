"""
JSearch via RapidAPI Job Aggregator Adapter
===========================================
Queries JSearch (rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch).
Aggregates live job postings across LinkedIn, Indeed, Glassdoor, and ZipRecruiter.
Degrades gracefully when RAPIDAPI_KEY is not configured.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_jsearch")


class JSearchJobAdapter(JobScraperAdapter):
    """Adapter for querying JSearch multi-platform aggregator API."""

    @property
    def source_name(self) -> str:
        return "jsearch"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 25,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_jsearch", correlation_id=correlation_id)

        # Check configuration
        if not settings.RAPIDAPI_KEY or not settings.RAPIDAPI_KEY.strip():
            log.info("jsearch_no_key_configured", note="Sign up for free key at rapidapi.com")
            raise ValueError("No RapidAPI key configured (sign up at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)")

        log.info("jsearch_fetch_start", query=query, location=location)
        postings: List[JobPosting] = []

        q_terms = [t for t in [query or "software developer", location] if t]
        search_query = " in ".join(q_terms)
        api_url = "https://jsearch.p.rapidapi.com/search"

        headers = {
            "x-rapidapi-key": settings.RAPIDAPI_KEY.strip(),
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
            "User-Agent": "AutoApplyAI-Bot/1.0",
        }
        params = {
            "query": search_query,
            "page": "1",
            "num_pages": "1",
        }

        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(api_url, headers=headers, params=params)
                if resp.status_code == 429:
                    raise RuntimeError("Rate limited by RapidAPI JSearch (HTTP 429)")
                if resp.status_code != 200:
                    log.warning("jsearch_non_200", status=resp.status_code, body=resp.text[:200])
                    return []

                data = resp.json()
                raw_items = data.get("data", [])

                for item in raw_items:
                    if len(postings) >= limit:
                        break

                    job_id = f"js-{item.get('job_id', '')[:30]}"
                    title = item.get("job_title", "")
                    company = item.get("employer_name", "Tech Company")
                    city = item.get("job_city") or ""
                    country = item.get("job_country") or ""
                    loc_name = f"{city}, {country}".strip(", ") or ("Remote" if item.get("job_is_remote") else "Worldwide")
                    raw_desc = item.get("job_description", "")
                    job_url = item.get("job_apply_link") or item.get("job_google_link") or ""
                    pub_date = item.get("job_posted_at_datetime_utc")

                    sal_min = item.get("job_min_salary")
                    sal_max = item.get("job_max_salary")
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
            log.warning("jsearch_fetch_failed", error=str(e))
            raise

        log.info("jsearch_fetch_complete", count=len(postings))
        return postings
