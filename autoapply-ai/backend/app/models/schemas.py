"""
Shared Data Schemas
===================
Typed Pydantic interfaces shared across parser, matcher, scraper,
browser agent, persistent storage, and API routes.
"""

from typing import Any, Dict, List, Literal, Optional
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
    linkedin: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    experience: List[Any] = Field(default_factory=list)


class JobPosting(BaseModel):
    """Normalized job listing from any source adapter."""
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str = "sample"  # e.g. "greenhouse", "lever", "arbeitnow", "adzuna", "jsearch", "usajobs", "remotive", "remoteok", "sample"
    posted_at: Optional[str] = None
    raw_hash: Optional[str] = None
    salary_range: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None


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
    stage: Literal[
        "matched",
        "queued",
        "needs_review",
        "applied",
        "submitted",
        "failed",
        "rejected",
        "interview",
        "offer",
        "saved",
    ]
    match_score: float
    updated_at: str
    user_id: Optional[str] = None
    source: str = "server_agent"  # "server_agent" or "extension"
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
    user_id: Optional[str] = None
    total_resumes: int = 0
    has_active_resume: bool = False


# Extension & Field Mapping API Schemas
class DetectedDOMField(BaseModel):
    """DOM field detected by the browser extension or Playwright agent."""
    selector: str
    label_text: str = ""
    name: str = ""
    element_id: str = ""
    input_type: str = "text"
    placeholder: str = ""
    aria_label: str = ""
    autocomplete: str = ""
    required: bool = False


class FieldMappingRequest(BaseModel):
    """Request to propose form field mappings from candidate profile."""
    fields: List[DetectedDOMField]
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_description: Optional[str] = None


class ExtensionEventRequest(BaseModel):
    """Event logged by the AutoApply Copilot browser extension."""
    event_type: Literal["prepared", "filled", "applied"]
    job_id: str
    company: str
    title: str
    url: Optional[str] = None
    location: Optional[str] = None
    match_score: Optional[float] = None
    field_mappings: List[FieldMappingDecision] = Field(default_factory=list)
    notes: Optional[str] = None


class AtsCheckRequest(BaseModel):
    """Request to analyze ATS resume keyword gap against a job description."""
    job_description: str
    job_title: Optional[str] = None
    company: Optional[str] = None


class AtsCheckResponse(BaseModel):
    """ATS keyword analysis and tailoring suggestions."""
    ats_score: int = Field(ge=0, le=100, description="ATS match percentage")
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    tailored_bullets: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ScrapedJobBatch(BaseModel):
    """Result of a scraping execution across adapters."""
    source: str
    query: str
    location: str
    total_found: int
    jobs: List[JobPosting]
    warnings: List[str] = Field(default_factory=list)


# -------------------------------------------------------------
# User Accounts & Authentication Schemas
# -------------------------------------------------------------
class UserCreate(BaseModel):
    """Signup request body."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Login request body."""
    email: str
    password: str


class UserResponse(BaseModel):
    """Public user identity model."""
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    email_verified: bool = False
    created_at: str


class TokenResponse(BaseModel):
    """JWT Token response for signup/login/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request body."""
    email: str


class ResetPasswordRequest(BaseModel):
    """Reset password request body."""
    token: str
    new_password: str = Field(..., min_length=6)


# -------------------------------------------------------------
# User Profile & Resume Schemas
# -------------------------------------------------------------
class UserProfileResponse(BaseModel):
    """Complete user profile information."""
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    location: Optional[str] = None
    desired_role: Optional[str] = None
    desired_location: Optional[str] = None
    remote_preference: Literal["remote", "hybrid", "onsite", "any"] = "any"
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    bio: Optional[str] = None
    active_resume_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Partial update for user profile. All fields optional."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    location: Optional[str] = None
    desired_role: Optional[str] = None
    desired_location: Optional[str] = None
    remote_preference: Optional[Literal["remote", "hybrid", "onsite", "any"]] = None
    skills: Optional[List[str]] = None
    years_experience: Optional[float] = None
    bio: Optional[str] = None
    active_resume_id: Optional[str] = None


class ResumeItemResponse(BaseModel):
    """Stored resume metadata record."""
    id: str
    user_id: str
    filename: str
    uploaded_at: str
    is_active: bool = True


class JobMatchResponse(BaseModel):
    """Full match response including per-source statuses for UI feedback."""
    matches: List[MatchResult]
    sources_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    total_found: int = 0


class CoverLetterRequest(BaseModel):
    """Request to generate a tailored cover letter."""
    company: str
    title: str
    description: str
    job_id: Optional[str] = None


class CoverLetterResponse(BaseModel):
    """Generated cover letter response."""
    cover_letter: str
    generated_by: str


class FormFieldMetadata(BaseModel):
    """Extracted DOM metadata for an input element."""
    tag: str
    element_id: str = ""
    name: str = ""
    input_type: str = "text"
    placeholder: str = ""
    label_text: str = ""
    aria_label: str = ""
    autocomplete: str = ""
    selector: str
    required: bool = False


class DetectedDOMField(BaseModel):
    """DOM field extracted by browser extension content script."""
    name: str
    selector: str
    field_type: str = "text"
    label: Optional[str] = None
    placeholder: Optional[str] = None
    required: bool = False


class FieldMappingRequest(BaseModel):
    """Request from browser extension to map detected fields."""
    fields: List[DetectedDOMField]
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_description: Optional[str] = None


class ExtensionEventRequest(BaseModel):
    """Application event synced from the browser extension."""
    job_id: str
    url: str
    company: str
    title: str
    stage: str  # prepared, filled, applied, submitted
    event_type: str = "apply_click"
    notes: Optional[str] = None
    field_mappings: Optional[List[FieldMappingDecision]] = None


class AtsCheckRequest(BaseModel):
    """Request to compute ATS fit score and missing keywords."""
    job_id: Optional[str] = ""
    job_title: str
    job_description: str
    company: Optional[str] = ""


class AtsCheckResponse(BaseModel):
    """Response containing ATS fit score, missing keywords, and tailored snippets."""
    job_id: Optional[str] = ""
    ats_score: float
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    tailored_cover_letter: str = ""
    suggested_bullet_points: List[str] = Field(default_factory=list)

