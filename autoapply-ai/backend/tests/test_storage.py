"""
Unit tests for Persistent Storage & Idempotency
================================================
"""

from pathlib import Path
import pytest
from app.db.storage import JobStorage
from app.models.schemas import ApplicationStatus, FieldMappingDecision


@pytest.fixture
def temp_storage(tmp_path: Path) -> JobStorage:
    db_file = tmp_path / "test_autoapply.db"
    return JobStorage(db_file)


def test_save_and_retrieve_application(temp_storage: JobStorage):
    app = ApplicationStatus(
        job_id="job-101",
        company="Acme Corp",
        title="Backend Engineer",
        stage="needs_review",
        match_score=0.75,
        updated_at="2026-09-24T12:00:00Z",
        dry_run=True,
        notes="High match score",
    )
    temp_storage.save_or_update_application(app)

    retrieved = temp_storage.get_application("job-101")
    assert retrieved is not None
    assert retrieved.company == "Acme Corp"
    assert retrieved.stage == "needs_review"
    assert retrieved.match_score == 0.75
    assert retrieved.dry_run is True


def test_idempotency_check(temp_storage: JobStorage):
    assert temp_storage.is_job_applied_or_submitted("job-202") is False

    app = ApplicationStatus(
        job_id="job-202",
        company="Beta Inc",
        title="Python Dev",
        stage="applied",
        match_score=0.88,
        updated_at="2026-09-24T12:00:00Z",
        dry_run=True,
    )
    temp_storage.save_or_update_application(app)

    assert temp_storage.is_job_applied_or_submitted("job-202") is True


def test_raw_job_saving_and_deduplication(temp_storage: JobStorage):
    hash_val = "sha256_mock_hash_abc123"
    assert temp_storage.is_content_seen(hash_val) is False

    temp_storage.record_content_hash(hash_val, "job-303")
    assert temp_storage.is_content_seen(hash_val) is True

    temp_storage.save_raw_job("job-303", "greenhouse", "https://example.com/303", hash_val, {"raw": "data"})
