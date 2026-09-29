"""
USAJobs Official Government Job API Adapter
===========================================
Queries USAJobs Developer API (data.usajobs.gov/api/search).
Free, official federal employment listings with strict salary transparency.
Degrades gracefully when USAJOBS_API_KEY is not configured.
"""

from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter, compute_job_hash

logger = get_logger("scraper_usajobs")


class USAJobsAdapter(JobScraperAdapter):
    """Adapter for querying USAJobs federal job search API."""

    @property
    def source_name(self) -> str:
        return "usajobs"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 25,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        log = get_logger("scraper_usajobs", correlation_id=correlation_id)

        # Check configuration
        if not settings.USAJOBS_API_KEY or not settings.USAJOBS_API_KEY.strip():
            log.info("usajobs_no_key_configured", note="Sign up for free key at developer.usajobs.gov")
            raise ValueError("No USAJobs API key configured (sign up at https://developer.usajobs.gov/)")

        log.info("usajobs_fetch_start", query=query, location=location)
        postings: List[JobPosting] = []

        api_url = "https://data.usajobs.gov/api/search"
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": settings.USAJOBS_USER_AGENT or "autoapply-ai@example.com",
            "Authorization-Key": settings.USAJOBS_API_KEY.strip(),
        }
        params = {
            "Keyword": query or "technology",
            "ResultsPerPage": str(min(limit, 50)),
        }
        if location:
            params["LocationName"] = location

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(api_url, headers=headers, params=params)
                if resp.status_code == 429:
                    raise RuntimeError("Rate limited by USAJobs API (HTTP 429)")
                if resp.status_code != 200:
                    log.warning("usajobs_non_200", status=resp.status_code, body=resp.text[:200])
                    return []

                data = resp.json()
                items = data.get("SearchResult", {}).get("SearchResultItems", [])

                for item in items:
                    if len(postings) >= limit:
                        break

                    desc = item.get("MatchedObjectDescriptor", {})
                    job_id = f"usajobs-{desc.get('PositionID') or item.get('MatchedObjectId', '')}"
                    title = desc.get("PositionTitle", "")
                    company = desc.get("OrganizationName", "US Federal Agency")
                    
                    locations_list = desc.get("PositionLocation", [])
                    loc_name = locations_list[0].get("LocationName", "United States") if locations_list else "United States"
                    
                    job_url = desc.get("PositionURI", "")
                    pub_date = desc.get("PositionStartDate")

                    user_area = desc.get("UserArea", {}).get("Details", {})
                    summary = user_area.get("JobSummary", "")

                    remun = desc.get("PositionRemuneration", [{}])
                    sal_min = remun[0].get("MinimumRange") if remun else None
                    sal_max = remun[0].get("MaximumRange") if remun else None
                    sal_range = None
                    if sal_min and sal_max:
                        sal_range = f"${float(sal_min):,.0f} - ${float(sal_max):,.0f}"

                    clean_desc = BeautifulSoup(summary, "html.parser").get_text(separator=" ", strip=True) or title

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
            log.warning("usajobs_fetch_failed", error=str(e))
            raise

        log.info("usajobs_fetch_complete", count=len(postings))
        return postings
