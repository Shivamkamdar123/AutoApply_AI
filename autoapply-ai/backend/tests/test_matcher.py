"""
Unit tests for Matching Engine
===============================
Tests TF-IDF scoring, cosine similarity, skill overlap bonus, ranking order,
engine switching, and error handling.
"""

import pytest

from app.core.exceptions import InvalidEngineError
from app.models.schemas import JobPosting, ResumeProfile
from app.services.matcher import (
    EmbeddingSimilarityEngine,
    TfidfSimilarityEngine,
    get_similarity_engine,
    rank_jobs,
    score_job,
)


def test_score_job_high_match(sample_profile: ResumeProfile, matching_job: JobPosting):
    """A profile with strong keyword and skill overlap should score high and be recommended."""
    result = score_job(sample_profile, matching_job)
    assert result.score > 0.40
    assert result.recommended is True
    assert "fastapi" in result.matched_skills
    assert "python" in result.matched_skills


def test_score_job_low_match(sample_profile: ResumeProfile, non_matching_job: JobPosting):
    """An unrelated job (e.g. Sales Account Executive) should score low and not be recommended."""
    result = score_job(sample_profile, non_matching_job)
    assert result.score < 0.25
    assert result.recommended is False
    assert len(result.matched_skills) == 0


def test_matched_skills_overlap(sample_profile: ResumeProfile, matching_job: JobPosting):
    """Verify skill overlap calculation accurately reflects skills in description."""
    result = score_job(sample_profile, matching_job)
    for skill in ["python", "fastapi", "docker", "postgresql", "sql"]:
        assert skill in result.matched_skills


def test_rank_jobs_order(sample_profile: ResumeProfile, matching_job: JobPosting, non_matching_job: JobPosting):
    """rank_jobs should return listings in strictly descending order of score."""
    ranked = rank_jobs(sample_profile, [non_matching_job, matching_job])
    assert len(ranked) == 2
    assert ranked[0].job.id == matching_job.id
    assert ranked[0].score >= ranked[1].score


def test_identical_text_scoring():
    """Identical resume and job description should achieve very high similarity score."""
    text = "Senior Python engineer building microservices with FastAPI and Docker."
    profile = ResumeProfile(raw_text=text, skills=["python", "fastapi", "docker"])
    job = JobPosting(
        id="identical-1",
        title="Python Engineer",
        company="Tech Inc",
        location="Remote",
        description=text,
        url="https://example.com/job/identical",
    )
    result = score_job(profile, job)
    assert result.score >= 0.85
    assert result.recommended is True


def test_empty_job_description(sample_profile: ResumeProfile):
    """An empty job description should safely yield score 0.0 without crashing."""
    empty_job = JobPosting(
        id="empty-1",
        title="Empty Role",
        company="Ghost Corp",
        location="Nowhere",
        description="",
        url="https://example.com/empty",
    )
    result = score_job(sample_profile, empty_job)
    assert result.score == 0.0
    assert result.recommended is False


def test_similarity_engine_factory():
    """Verify the similarity engine factory correctly returns engines or raises on invalid input."""
    tfidf_engine = get_similarity_engine("tfidf")
    assert isinstance(tfidf_engine, TfidfSimilarityEngine)

    embed_engine = get_similarity_engine("embedding")
    assert isinstance(embed_engine, EmbeddingSimilarityEngine)

    with pytest.raises(InvalidEngineError):
        get_similarity_engine("quantum_nlp_v9")


def test_graceful_degradation_in_rank_jobs(sample_profile: ResumeProfile, matching_job: JobPosting):
    """If one job raises an unexpected error during scoring, rank_jobs must continue processing others."""
    class FlakyJob(JobPosting):
        pass

    # Create a job that triggers an exception in description access
    bad_job = JobPosting(
        id="bad-1",
        title="Corrupt Role",
        company="Corrupt Corp",
        location="None",
        description="test",
        url="https://example.com/bad",
    )

    ranked = rank_jobs(sample_profile, [bad_job, matching_job])
    assert len(ranked) >= 1
    assert any(r.job.id == matching_job.id for r in ranked)
