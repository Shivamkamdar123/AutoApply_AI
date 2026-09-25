"""Scraper adapters package for AutoApply AI."""

from app.services.scrapers.base import JobScraperAdapter, compute_job_hash
from app.services.scrapers.greenhouse import GreenhouseJobAdapter
from app.services.scrapers.lever import LeverJobAdapter
from app.services.scrapers.remotefeed import RemoteFeedJobAdapter
from app.services.scrapers.remoteok import RemoteOKJobAdapter
from app.services.scrapers.sample import SampleJobAdapter

__all__ = [
    "JobScraperAdapter",
    "compute_job_hash",
    "GreenhouseJobAdapter",
    "LeverJobAdapter",
    "RemoteFeedJobAdapter",
    "RemoteOKJobAdapter",
    "SampleJobAdapter",
]
