"""
Job scraper
===========
STATUS: STUB. Returns sample data so the rest of the system (matcher,
dashboard) has something real to work with while this piece is built.

Why this is stubbed rather than "fake-implemented": scraping real job
boards means dealing with per-site HTML structure, login walls, rate
limiting, and terms-of-service constraints — none of which can be built
or verified without running against the live site. That work belongs in
its own iteration cycle, not guessed at here.

Planned real implementation:
    Each job site gets its own class implementing the same `fetch_jobs`
    interface (e.g. `LinkedInScraper`, `NaukriScraper`), using Playwright
    to load search results and extract postings. `get_jobs()` below would
    pick which scraper(s) to run based on user preferences.

    class LinkedInScraper(JobScraper):
        def fetch_jobs(self, query, location, limit=20):
            # Playwright: open search URL, wait for results, parse cards
            ...
"""

import json

from app.config import SAMPLE_JOBS_FILE
from app.models.schemas import JobPosting


class JobScraper:
    """Base interface every real site-specific scraper should implement."""

    def fetch_jobs(self, query: str, location: str, limit: int = 20) -> list[JobPosting]:
        raise NotImplementedError


class SampleJobScraper(JobScraper):
    """Reads from the bundled sample_jobs.json — used until real scrapers exist."""

    def fetch_jobs(self, query: str = "", location: str = "", limit: int = 20) -> list[JobPosting]:
        with open(SAMPLE_JOBS_FILE, "r", encoding="utf-8") as f:
            raw_jobs = json.load(f)
        jobs = [JobPosting(**job) for job in raw_jobs]

        if query:
            query_lower = query.lower()
            jobs = [j for j in jobs if query_lower in j.title.lower() or query_lower in j.description.lower()]

        return jobs[:limit]


def get_jobs(query: str = "", location: str = "", limit: int = 20) -> list[JobPosting]:
    """
    Entry point the rest of the app calls. Currently always uses the sample
    scraper — swap this to select a real scraper once one exists, without
    touching any calling code.
    """
    scraper = SampleJobScraper()
    return scraper.fetch_jobs(query=query, location=location, limit=limit)
