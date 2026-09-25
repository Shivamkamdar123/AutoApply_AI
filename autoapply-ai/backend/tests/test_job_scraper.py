"""
Unit tests for Job Scrapers and Adapters
=========================================
Tests adapter interface, rate limiting, robots.txt compliance,
deduplication across sources, and raw payload separation.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.models.schemas import JobPosting
from app.services.job_scraper import JobScraperService, get_jobs
from app.services.scrapers.base import RateLimiter, RobotsChecker, compute_job_hash
from app.services.scrapers.greenhouse import GreenhouseJobAdapter
from app.services.scrapers.lever import LeverJobAdapter
from app.services.scrapers.sample import SampleJobAdapter


def test_compute_job_hash():
    """Verify hash consistency for deduplication."""
    hash1 = compute_job_hash("Acme", "Backend Engineer", "FastAPI Python SQL")
    hash2 = compute_job_hash("acme ", "backend engineer", "fastapi python sql")
    assert hash1 == hash2


def test_sample_adapter_returns_postings():
    """Sample adapter reads sample_jobs.json and returns typed JobPosting models."""
    adapter = SampleJobAdapter()
    jobs = adapter.fetch_jobs(limit=5)
    assert len(jobs) > 0
    assert all(isinstance(j, JobPosting) for j in jobs)
    assert all(j.raw_hash is not None for j in jobs)


def test_robots_checker_allows_standard_urls():
    """Robots checker should allow standard endpoints when robots.txt is accessible or permissive."""
    checker = RobotsChecker()
    # Mocking internal parser to avoid external network call
    checker._cache["https://example.com"] = MagicMock(can_fetch=lambda ua, url: True)
    assert checker.is_allowed("https://example.com/jobs/1") is True


def test_scraper_service_deduplication():
    """Service must remove duplicate postings sharing the same content hash."""
    service = JobScraperService()
    # Mock adapters that return overlapping listings
    mock_adapter1 = MagicMock()
    dup_posting = JobPosting(
        id="dup-1",
        title="Software Engineer",
        company="DupeCorp",
        location="Remote",
        description="Python FastAPI backend",
        url="https://example.com/1",
        raw_hash="hash_same_123",
    )
    mock_adapter1.fetch_jobs.return_value = [dup_posting]

    mock_adapter2 = MagicMock()
    dup_posting2 = JobPosting(
        id="dup-2",
        title="Software Engineer",
        company="DupeCorp",
        location="Remote",
        description="Python FastAPI backend",
        url="https://example.com/2",
        raw_hash="hash_same_123",
    )
    mock_adapter2.fetch_jobs.return_value = [dup_posting2]

    service._adapters = {"source1": mock_adapter1, "source2": mock_adapter2}
    results = service.fetch_jobs_from_all(sources=["source1", "source2"], limit=10)
    assert len(results) == 1
    assert results[0].id == "dup-1"


@patch("httpx.Client.get")
def test_greenhouse_adapter_mock_response(mock_get):
    """Test Greenhouse adapter parsing against mock API payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [
            {
                "id": 123456,
                "title": "Staff Python Developer",
                "location": {"name": "Remote"},
                "content": "<p>Build scalable microservices with FastAPI.</p>",
                "absolute_url": "https://boards.greenhouse.io/canonical/jobs/123456",
                "updated_at": "2026-09-24T12:00:00Z",
            }
        ]
    }
    mock_get.return_value = mock_response

    adapter = GreenhouseJobAdapter()
    with patch.object(adapter, "check_compliance"):
        jobs = adapter.fetch_jobs(limit=1)
        assert len(jobs) == 1
        assert jobs[0].title == "Staff Python Developer"
        assert jobs[0].company == "Canonical"
        assert jobs[0].source == "greenhouse"
