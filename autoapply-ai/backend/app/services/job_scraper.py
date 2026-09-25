"""
Job Scraper Service (Orchestrator)
==================================
Coordinates multiple site-specific adapters behind the unified JobScraperAdapter interface:
Greenhouse, Lever, Remotive, RemoteOK, and offline local Sample.
Handles deduplication across sources, polite crawl delays, caching of raw vs normalized
postings, per-source execution diagnostics, and graceful degradation.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.scrapers.base import JobScraperAdapter
from app.services.scrapers.greenhouse import GreenhouseJobAdapter
from app.services.scrapers.lever import LeverJobAdapter
from app.services.scrapers.remotefeed import RemoteFeedJobAdapter
from app.services.scrapers.remoteok import RemoteOKJobAdapter
from app.services.scrapers.sample import SampleJobAdapter

logger = get_logger("job_scraper_service")


class JobScraperService:
    """
    Orchestrates real scraping across registered job board adapters.
    Deduplicates listings across sources, caches payloads, and records source health telemetry.
    """

    def __init__(self):
        self._adapters: dict[str, JobScraperAdapter] = {
            "greenhouse": GreenhouseJobAdapter(),
            "lever": LeverJobAdapter(),
            "remotive": RemoteFeedJobAdapter(),
            "remoteok": RemoteOKJobAdapter(),
            "sample": SampleJobAdapter(),
        }
        self._cache: dict[str, tuple[float, List[JobPosting], Dict[str, Dict[str, Any]]]] = {}
        self._cache_ttl_seconds: float = 60.0

    def register_adapter(self, name: str, adapter: JobScraperAdapter) -> None:
        """Register a new job site adapter without modifying core pipeline logic."""
        self._adapters[name] = adapter
        logger.info("scraper_adapter_registered", name=name)

    def fetch_jobs_with_status(
        self,
        query: str = "",
        location: str = "",
        limit: int = 25,
        sources: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
    ) -> Tuple[List[JobPosting], Dict[str, Dict[str, Any]]]:
        """
        Gathers jobs from selected or all active adapters, reporting per-source diagnostics
        so the frontend UI can show real-time scraper connectivity status.
        """
        sources_list = sources or ["sample", "greenhouse", "lever", "remotive", "remoteok"]
        cache_key = f"{query.lower().strip()}:{location.lower().strip()}:{limit}:{','.join(sorted(sources_list))}"
        now = time.time()

        if cache_key in self._cache:
            cached_time, cached_jobs, cached_statuses = self._cache[cache_key]
            if now - cached_time < self._cache_ttl_seconds:
                return cached_jobs[:limit], cached_statuses

        log = get_logger("job_scraper_service", correlation_id=correlation_id)
        all_postings: List[JobPosting] = []
        seen_hashes: set[str] = set()
        sources_status: Dict[str, Dict[str, Any]] = {}

        for src_name in sources_list:
            adapter = self._adapters.get(src_name)
            if not adapter:
                sources_status[src_name] = {"status": "unsupported", "count": 0, "error": "Adapter not found"}
                continue

            try:
                postings = adapter.fetch_jobs(
                    query=query,
                    location=location,
                    limit=limit,
                    correlation_id=correlation_id,
                )
                added_for_source = 0
                for p in postings:
                    # Deduplicate across sources
                    if p.raw_hash and p.raw_hash in seen_hashes:
                        continue
                    if p.raw_hash:
                        seen_hashes.add(p.raw_hash)
                    all_postings.append(p)
                    added_for_source += 1
                    if len(all_postings) >= limit:
                        break

                sources_status[src_name] = {
                    "status": "ok",
                    "count": len(postings),
                    "accepted": added_for_source,
                    "error": None,
                }
            except Exception as e:
                log.warning("adapter_execution_failed", source=src_name, error=str(e))
                sources_status[src_name] = {
                    "status": "error",
                    "count": 0,
                    "accepted": 0,
                    "error": str(e),
                }
                continue

            if len(all_postings) >= limit:
                break

        # Fallback to sample adapter if no live jobs could be collected (e.g. offline environment)
        if not all_postings:
            log.info("falling_back_to_sample_jobs")
            all_postings = self._adapters["sample"].fetch_jobs(
                query=query,
                location=location,
                limit=limit,
                correlation_id=correlation_id,
            )
            sources_status["sample"] = {
                "status": "fallback",
                "count": len(all_postings),
                "accepted": len(all_postings),
                "error": None,
            }

        log.info("job_collection_complete", total_postings=len(all_postings))
        result_jobs = all_postings[:limit]
        self._cache[cache_key] = (now, result_jobs, sources_status)
        return result_jobs, sources_status

    def fetch_jobs_from_all(
        self,
        query: str = "",
        location: str = "",
        limit: int = 25,
        sources: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
    ) -> List[JobPosting]:
        """Backward-compatible helper returning list of postings."""
        jobs, _ = self.fetch_jobs_with_status(
            query=query,
            location=location,
            limit=limit,
            sources=sources,
            correlation_id=correlation_id,
        )
        return jobs


# Global scraper service singleton
scraper_service = JobScraperService()


def get_jobs(
    query: str = "",
    location: str = "",
    limit: int = 25,
    sources: Optional[List[str]] = None,
    correlation_id: Optional[str] = None,
) -> List[JobPosting]:
    """
    Main entry point for job sourcing across the system.
    Pulls from real adapters with automatic deduplication and caching.
    """
    return scraper_service.fetch_jobs_from_all(
        query=query,
        location=location,
        limit=limit,
        sources=sources,
        correlation_id=correlation_id,
    )
