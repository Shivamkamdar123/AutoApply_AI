"""
Job Scraper Service (Orchestrator)
==================================
Coordinates multiple site-specific adapters behind the unified JobScraperAdapter interface:
Arbeitnow, Adzuna, JSearch, USAJobs, Greenhouse, Lever, Remotive, RemoteOK, and offline local Sample.
Handles deduplication across sources, polite crawl delays, caching of raw vs normalized
postings, per-source execution diagnostics, graceful degradation, and live event publishing.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import JobPosting
from app.services.event_bus import event_bus
from app.services.scrapers.adzuna import AdzunaJobAdapter
from app.services.scrapers.arbeitnow import ArbeitnowJobAdapter
from app.services.scrapers.base import JobScraperAdapter
from app.services.scrapers.greenhouse import GreenhouseJobAdapter
from app.services.scrapers.jsearch import JSearchJobAdapter
from app.services.scrapers.lever import LeverJobAdapter
from app.services.scrapers.remotefeed import RemoteFeedJobAdapter
from app.services.scrapers.remoteok import RemoteOKJobAdapter
from app.services.scrapers.sample import SampleJobAdapter
from app.services.scrapers.usajobs import USAJobsAdapter as USAJobsJobAdapter

logger = get_logger("job_scraper_service")

ALL_DEFAULT_SOURCES = [
    "arbeitnow",
    "adzuna",
    "jsearch",
    "usajobs",
    "greenhouse",
    "lever",
    "remotive",
    "remoteok",
    "sample",
]


class JobScraperService:
    """
    Orchestrates real scraping across registered job board adapters.
    Deduplicates listings across sources, caches payloads, and records source health telemetry.
    """

    def __init__(self):
        self._adapters: dict[str, JobScraperAdapter] = {
            "arbeitnow": ArbeitnowJobAdapter(),
            "adzuna": AdzunaJobAdapter(),
            "jsearch": JSearchJobAdapter(),
            "usajobs": USAJobsJobAdapter(),
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
        sources_list = sources or ALL_DEFAULT_SOURCES
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

        event_bus.publish(
            event_type="JOB_SEARCH_START",
            message=f"Beginning job search across {len(sources_list)} sources for query='{query}' location='{location}'",
            level="INFO",
            correlation_id=correlation_id,
            data={"query": query, "location": location, "sources": sources_list},
        )

        for src_name in sources_list:
            adapter = self._adapters.get(src_name)
            if not adapter:
                sources_status[src_name] = {"status": "unsupported", "count": 0, "accepted": 0, "error": "Adapter not found"}
                continue

            try:
                # Fetch up to 10 jobs per source (or remaining limit)
                fetch_limit = min(limit, 10)
                postings = adapter.fetch_jobs(
                    query=query,
                    location=location,
                    limit=fetch_limit,
                    correlation_id=correlation_id,
                )
                added_for_source = 0
                for p in postings:
                    # Deduplicate across sources
                    if p.raw_hash and p.raw_hash in seen_hashes:
                        continue
                    if p.raw_hash:
                        seen_hashes.add(p.raw_hash)
                    if len(all_postings) < limit:
                        all_postings.append(p)
                        added_for_source += 1

                status_val = "ok" if len(postings) > 0 else "no_results"
                sources_status[src_name] = {
                    "status": status_val,
                    "count": len(postings),
                    "accepted": added_for_source,
                    "error": None,
                }
                event_bus.publish(
                    event_type="SOURCE_FETCH_COMPLETE",
                    message=f"[{src_name.upper()}] Fetched {len(postings)} jobs ({added_for_source} accepted, deduplicated)",
                    level="INFO",
                    correlation_id=correlation_id,
                    data={"source": src_name, "count": len(postings), "accepted": added_for_source},
                )
            except ValueError as ve:
                # Missing API key
                log.info("adapter_no_key", source=src_name, error=str(ve))
                sources_status[src_name] = {
                    "status": "no_key",
                    "count": 0,
                    "accepted": 0,
                    "error": str(ve),
                }
                event_bus.publish(
                    event_type="SOURCE_NO_KEY",
                    message=f"[{src_name.upper()}] Skipped: API key not configured",
                    level="WARNING",
                    correlation_id=correlation_id,
                    data={"source": src_name},
                )
            except RuntimeError as re:
                err_str = str(re).lower()
                is_rate = "rate" in err_str or "429" in err_str
                status_val = "rate_limited" if is_rate else "error"
                log.warning("adapter_runtime_error", source=src_name, error=str(re))
                sources_status[src_name] = {
                    "status": status_val,
                    "count": 0,
                    "accepted": 0,
                    "error": str(re),
                }
                event_bus.publish(
                    event_type=f"SOURCE_{status_val.upper()}",
                    message=f"[{src_name.upper()}] {status_val.replace('_', ' ').capitalize()}: {re}",
                    level="WARNING",
                    correlation_id=correlation_id,
                    data={"source": src_name, "error": str(re)},
                )
            except Exception as e:
                log.warning("adapter_execution_failed", source=src_name, error=str(e))
                sources_status[src_name] = {
                    "status": "error",
                    "count": 0,
                    "accepted": 0,
                    "error": str(e),
                }
                event_bus.publish(
                    event_type="SOURCE_ERROR",
                    message=f"[{src_name.upper()}] Error: {e}",
                    level="ERROR",
                    correlation_id=correlation_id,
                    data={"source": src_name, "error": str(e)},
                )
                continue

        # Fallback to sample adapter if zero live jobs could be collected (e.g. offline environment)
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
            event_bus.publish(
                event_type="FALLBACK_SAMPLE_JOBS",
                message=f"Zero live results from network; loaded {len(all_postings)} verified sample fixtures",
                level="INFO",
                correlation_id=correlation_id,
            )

        log.info("job_collection_complete", total_postings=len(all_postings))
        event_bus.publish(
            event_type="JOB_SEARCH_COMPLETE",
            message=f"Job aggregation complete: {len(all_postings)} unique postings ready for matching",
            level="INFO",
            correlation_id=correlation_id,
            data={"total_jobs": len(all_postings)},
        )

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
