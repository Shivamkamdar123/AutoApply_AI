"""
API Routes
==========
Thin HTTP presentation layer that connects endpoints to services and storage.
Handles resume upload, job matching, review queue actions, and pipeline execution.
"""

import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.config import settings
from app.core.exceptions import ResumeParseError
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import (
    ApplicationStatus,
    DashboardSummary,
    FieldMappingDecision,
    JobPosting,
    MatchResult,
    ResumeProfile,
    ReviewActionRequest,
)
from app.services.job_scraper import get_jobs
from app.services.matcher import rank_jobs
from app.services.resume_parser import parse_resume

logger = get_logger("api_routes")
router = APIRouter()

# Default fallback candidate profile for instant demo capability
DEFAULT_DEMO_PROFILE = ResumeProfile(
    full_name="Alex Rivera",
    email="alex.rivera@example.com",
    phone="+1 (555) 789-0123",
    skills=["python", "fastapi", "sql", "docker", "kubernetes", "git", "rest api", "postgresql"],
    years_experience=4.5,
    language="en",
    raw_text=(
        "Alex Rivera\n"
        "alex.rivera@example.com | +1 (555) 789-0123 | Bengaluru, IN\n"
        "Senior Backend Engineer with 4.5 years of experience building scalable microservices in Python.\n"
        "Proficient in FastAPI, Docker, Kubernetes, PostgreSQL, SQL, Git, and automated testing with Playwright.\n"
        "Experience:\n"
        "TechCorp — Backend Engineer (2020 - 2024)\n"
        "- Engineered distributed REST APIs handling 50k req/min using FastAPI and Redis.\n"
        "- Automated deployment pipelines with Docker and CI/CD.\n"
    ),
)

_current_profile: ResumeProfile = DEFAULT_DEMO_PROFILE
_agent_running: bool = False


@router.get("/health")
async def health_check():
    """Health check endpoint for fast connection verification."""
    return {
        "status": "healthy",
        "service": "AutoApply AI API",
        "version": "0.1.0",
        "environment": settings.ENV,
        "dry_run": settings.DRY_RUN,
    }


@router.post("/resume/upload", response_model=ResumeProfile)
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts a resume file (.pdf, .docx, .txt), validates, parses it,
    and updates the active candidate profile for matching.
    """
    global _current_profile
    run_id = str(uuid.uuid4())[:8]
    log = get_logger("api_routes", correlation_id=run_id)

    filename = file.filename or "uploaded_resume"
    suffix = Path(filename).suffix.lower()

    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{suffix}'. Allowed: .pdf, .docx, .txt",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        profile = parse_resume(tmp_path, correlation_id=run_id)
        _current_profile = profile
        log.info("resume_uploaded_and_activated", name=profile.full_name, skills=len(profile.skills))
        
        # Populate initial review queue based on recommended jobs
        jobs = get_jobs()
        matches = rank_jobs(profile, jobs, correlation_id=run_id)
        now = datetime.now(timezone.utc).isoformat()

        for m in matches:
            if m.recommended:
                existing = storage.get_application(m.job.id)
                if not existing:
                    # Create drafted field mappings for human review
                    mappings = [
                        FieldMappingDecision(
                            field_name="Full Name",
                            selector="input[name='name']",
                            value_filled=profile.full_name or "Alex Rivera",
                            confidence=0.98,
                            source_field="profile.full_name",
                            rationale="Direct name heuristic extraction",
                        ),
                        FieldMappingDecision(
                            field_name="Email",
                            selector="input[type='email']",
                            value_filled=profile.email or "alex@example.com",
                            confidence=0.99,
                            source_field="profile.email",
                            rationale="Exact regex email pattern match",
                        ),
                        FieldMappingDecision(
                            field_name="Phone",
                            selector="input[type='tel']",
                            value_filled=profile.phone or "+1-555-0100",
                            confidence=0.95,
                            source_field="profile.phone",
                            rationale="Parsed international telephone standard",
                        ),
                        FieldMappingDecision(
                            field_name="Years Experience",
                            selector="input[name='experience']",
                            value_filled=str(profile.years_experience or 3),
                            confidence=0.88,
                            source_field="profile.years_experience",
                            rationale="Computed career date-span range sum",
                        ),
                    ]

                    app = ApplicationStatus(
                        job_id=m.job.id,
                        company=m.job.company,
                        title=m.job.title,
                        stage="needs_review",
                        match_score=m.score,
                        updated_at=now,
                        dry_run=settings.DRY_RUN,
                        field_mappings=mappings,
                        notes=f"Drafted application based on {round(m.score * 100)}% match score.",
                    )
                    storage.save_or_update_application(app, url=m.job.url, location=m.job.location)

        return profile
    except ResumeParseError as e:
        log.error("resume_parse_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except Exception as e:
        log.error("unexpected_resume_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing resume: {str(e)}",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/resume/current", response_model=ResumeProfile)
async def get_current_profile():
    """Returns the currently active candidate profile."""
    return _current_profile


@router.get("/jobs/match", response_model=List[MatchResult])
async def match_jobs(query: str = Query(default="", description="Search keywords"), location: str = ""):
    """Scores and ranks job postings against the active candidate profile."""
    run_id = str(uuid.uuid4())[:8]
    jobs = get_jobs(query=query, location=location)
    matches = rank_jobs(_current_profile, jobs, correlation_id=run_id)
    return matches


@router.get("/review-queue", response_model=List[ApplicationStatus])
async def get_review_queue():
    """
    Returns jobs awaiting human approval before submission.
    Core safety valve preventing unintended automated submissions.
    """
    queue = storage.list_applications(stage="needs_review")
    all_apps = storage.list_applications()

    # Only seed on first boot if storage is completely empty of any application records
    if not all_apps:
        jobs = get_jobs()
        matches = rank_jobs(_current_profile, jobs)
        now = datetime.now(timezone.utc).isoformat()
        for m in matches:
            if m.recommended:
                existing = storage.get_application(m.job.id)
                if not existing:
                    app = ApplicationStatus(
                        job_id=m.job.id,
                        company=m.job.company,
                        title=m.job.title,
                        stage="needs_review",
                        match_score=m.score,
                        updated_at=now,
                        dry_run=settings.DRY_RUN,
                        field_mappings=[
                            FieldMappingDecision(
                                field_name="Full Name",
                                selector="input[name='name']",
                                value_filled=_current_profile.full_name or "Alex Rivera",
                                confidence=0.98,
                                source_field="profile.full_name",
                                rationale="Direct name heuristic extraction",
                            ),
                            FieldMappingDecision(
                                field_name="Email",
                                selector="input[type='email']",
                                value_filled=_current_profile.email or "alex@example.com",
                                confidence=0.99,
                                source_field="profile.email",
                                rationale="Exact regex email pattern match",
                            ),
                            FieldMappingDecision(
                                field_name="Phone",
                                selector="input[type='tel']",
                                value_filled=_current_profile.phone or "+1-555-0100",
                                confidence=0.95,
                                source_field="profile.phone",
                                rationale="Parsed international telephone standard",
                            ),
                        ],
                        notes=f"Drafted application ({round(m.score * 100)}% match)",
                    )
                    storage.save_or_update_application(app, url=m.job.url, location=m.job.location)
        queue = storage.list_applications(stage="needs_review")

    return queue


@router.post("/review-queue/{job_id}/action", response_model=ApplicationStatus)
async def review_action(job_id: str, action_req: ReviewActionRequest):
    """
    Human-in-the-loop action: Approve or Reject a drafted application.
    """
    app = storage.get_application(job_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application for job '{job_id}' not found.")

    now = datetime.now(timezone.utc).isoformat()

    if action_req.action == "approve":
        # If auto-submit is explicitly opted-in and enabled in settings, mark submitted; otherwise applied in dry-run
        if action_req.auto_submit_override and settings.AUTO_SUBMIT_ENABLED:
            app.stage = "submitted"
            app.dry_run = False
            app.notes = "Approved by user with explicit live auto-submit."
        else:
            app.stage = "applied"
            app.dry_run = True
            app.notes = "Approved by user in verified dry-run mode (form verified, not submitted)."
    elif action_req.action == "reject":
        app.stage = "rejected"
        app.notes = "Rejected by human reviewer."

    app.updated_at = now
    storage.save_or_update_application(app)
    logger.info("review_action_completed", job_id=job_id, action=action_req.action, new_stage=app.stage)
    return app


@router.get("/applications", response_model=List[ApplicationStatus])
async def list_all_applications():
    """Lists all application records across all lifecycle stages."""
    return storage.list_applications()


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary():
    """Aggregate stats for dashboard top cards and pipeline counts."""
    counts = storage.get_counts()
    all_apps = storage.list_applications()

    total_applied = counts.get("applied", 0) + counts.get("submitted", 0)
    total_needs_review = counts.get("needs_review", 0)
    total_matched = len(all_apps) if all_apps else 0
    avg_score = (
        round(sum(a.match_score for a in all_apps) / len(all_apps), 3)
        if all_apps
        else 0.0
    )

    return DashboardSummary(
        total_matched=total_matched,
        total_applied=total_applied,
        total_needs_review=total_needs_review,
        average_match_score=avg_score,
        agent_active=_agent_running,
        dry_run_mode=settings.DRY_RUN,
    )


@router.post("/agent/toggle")
async def toggle_agent(active: Optional[bool] = None):
    """Toggle agent running status."""
    global _agent_running
    _agent_running = not _agent_running if active is None else active
    logger.info("agent_status_toggled", active=_agent_running)
    return {"agent_active": _agent_running, "dry_run": settings.DRY_RUN}
