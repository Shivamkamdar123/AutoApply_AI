"""
Shared Data Schemas
===================
Typed Pydantic interfaces shared across parser, matcher, scraper,
browser agent, persistent storage, and API routes.
"""

from typing import List, Optional, Literal, Dict
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    """Structured output of the resume parser."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    language: str = "en"
    warnings: List[str] = Field(default_factory=list)
    raw_text: str = ""


class JobPosting(BaseModel):
    """Normalized job listing from any source adapter."""
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str = "sample"  # e.g. "greenhouse", "lever", "job_board", "sample"
    posted_at: Optional[str] = None
    raw_hash: Optional[str] = None


class MatchResult(BaseModel):
    """A job scored against a candidate's resume profile."""
    job: JobPosting
    score: float = Field(ge=0.0, le=1.0, description="Match score normalized between 0.0 and 1.0")
    matched_skills: List[str] = Field(default_factory=list)
    recommended: bool
    scoring_method: str = "tfidf"
    notes: Optional[str] = None


class FieldMappingDecision(BaseModel):
    """Logged decision for every field mapped by the browser agent."""
    field_name: str
    field_type: str = "text"
    selector: str
    value_filled: str  # Note: sensitive fields like passwords are never logged here
    confidence: float = Field(ge=0.0, le=1.0)
    source_field: str
    rationale: str


class ApplicationStatus(BaseModel):
    """Lifecycle tracking for an application across the pipeline."""
    job_id: str
    company: str
    title: str
    stage: Literal["matched", "queued", "needs_review", "applied", "submitted", "failed", "rejected"]
    match_score: float
    updated_at: str
    dry_run: bool = True
    screenshot_path: Optional[str] = None
    field_mappings: List[FieldMappingDecision] = Field(default_factory=list)
    notes: Optional[str] = None


class ReviewActionRequest(BaseModel):
    """User human-in-the-loop action on a pending application."""
    job_id: str
    action: Literal["approve", "reject"]
    auto_submit_override: bool = False
    edited_fields: Optional[Dict[str, str]] = None


class DashboardSummary(BaseModel):
    """Aggregated numbers for dashboard display."""
    total_matched: int
    total_applied: int
    total_needs_review: int
    average_match_score: float
    agent_active: bool
    dry_run_mode: bool = True


class ScrapedJobBatch(BaseModel):
    """Result of a scraping execution across adapters."""
    source: str
    query: str
    location: str
    total_found: int
    jobs: List[JobPosting]
    warnings: List[str] = Field(default_factory=list)
