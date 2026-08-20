"""
Shared data shapes. Keeping these in one file means the parser, matcher,
API, and (later) agent core all agree on what a "resume" or "job" looks like.
"""

from pydantic import BaseModel
from typing import List, Optional


class ResumeProfile(BaseModel):
    """Structured output of the resume parser."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    years_experience: Optional[float] = None
    raw_text: str = ""


class JobPosting(BaseModel):
    """A single job listing, however it was sourced."""
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str = "sample"  # e.g. "linkedin", "naukri", "sample"


class MatchResult(BaseModel):
    """A job scored against a resume profile."""
    job: JobPosting
    score: float           # 0.0 - 1.0
    matched_skills: List[str]
    recommended: bool


class ApplicationStatus(BaseModel):
    """Tracks the lifecycle of one application through the pipeline."""
    job_id: str
    company: str
    title: str
    stage: str              # matched | queued | applied | needs_review | submitted | failed
    match_score: float
    updated_at: str


class DashboardSummary(BaseModel):
    """Aggregate numbers the dashboard's stat cards show."""
    total_matched: int
    total_applied: int
    total_needs_review: int
    average_match_score: float
    agent_active: bool
