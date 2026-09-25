"""
Base Job Scraper Adapter & Rate Limiting
========================================
Defines the common interface for job board adapters, respectful rate limiting,
robots.txt policy verification, and payload hashing.
"""

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import urllib.robotparser

import httpx

from app.config import settings
from app.core.exceptions import RateLimitExceededError, RobotsDisallowedError
from app.core.logging import get_logger
from app.models.schemas import JobPosting

logger = get_logger("scraper_base")


class RobotsChecker:
    """
    Caches and evaluates robots.txt policies per domain.
    Flags any site where automated scraping is disallowed rather than silently ignoring.
    """

    def __init__(self, user_agent: str = settings.SCRAPER_USER_AGENT):
        self.user_agent = user_agent
        self._cache: Dict[str, urllib.robotparser.RobotFileParser] = {}

    def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        if not domain or domain == "://":
            return True

        if domain not in self._cache:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{domain}/robots.txt"
            try:
                # Synchronous read with short timeout
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(robots_url)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.allow_all = True
            except Exception as e:
                logger.debug("robots_txt_fetch_failed", domain=domain, error=str(e))
                rp.allow_all = True
            self._cache[domain] = rp

        parser = self._cache[domain]
        allowed = parser.can_fetch(self.user_agent, url)
        if not allowed:
            logger.warning("scraping_disallowed_by_robots", url=url, domain=domain)
        return allowed


class RateLimiter:
    """
    Ensures polite crawl delays and exponential backoff on HTTP 429.
    """

    def __init__(self, min_delay_seconds: float = settings.SCRAPE_DELAY_SECONDS):
        self.min_delay = min_delay_seconds
        self.last_call_time = 0.0

    async def wait(self) -> None:
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self.last_call_time = time.time()

    async def handle_backoff(self, attempt: int, max_attempts: int = 3) -> None:
        delay = (2 ** attempt) + (self.min_delay * 0.5)
        logger.warning("rate_limit_backoff", attempt=attempt, delay=delay)
        await asyncio.sleep(delay)


def compute_job_hash(company: str, title: str, description_snippet: str) -> str:
    """Computes a stable deterministic SHA-256 fingerprint for deduplication."""
    content = f"{company.strip().lower()}|{title.strip().lower()}|{description_snippet[:200].strip().lower()}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class JobScraperAdapter(ABC):
    """
    Common contract for all site-specific and board-specific job scrapers.
    Adding a new job site requires implementing this interface only.
    """

    def __init__(self):
        self.rate_limiter = RateLimiter(settings.SCRAPE_DELAY_SECONDS)
        self.robots_checker = RobotsChecker()

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source (e.g. 'greenhouse', 'lever')."""
        pass

    def check_compliance(self, url: str) -> None:
        """Verifies robots.txt compliance before initiating a fetch."""
        if not self.robots_checker.is_allowed(url):
            raise RobotsDisallowedError(
                f"Scraping is explicitly disallowed on '{url}' per robots.txt terms of service."
            )

    @abstractmethod
    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 20,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        """
        Fetches, normalizes, and returns job postings.
        Must persist raw payloads via storage before returning.
        """
        pass
