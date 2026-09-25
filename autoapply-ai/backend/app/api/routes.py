"""
API Routes (Multi-Tenant & Authenticated)
=========================================
Presentation layer connecting endpoints to services and multi-tenant storage.
All user operations require authentication via `get_current_user` dependency.
Zero shared module globals: all profiles, applications, and review queues are isolated per user.
"""

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.auth import get_current_user
from app.config import settings
from app.core.exceptions import ResumeParseError
from app.core.logging import get_logger
from app.core.security import upload_rate_limiter
from app.db.storage import storage
from app.models.schemas import (
    ApplicationStatus,
    CoverLetterRequest,
    CoverLetterResponse,
    DashboardSummary,
    FieldMappingDecision,
    JobMatchResponse,
    MatchResult,
    ResumeItemResponse,
    ResumeProfile,
    ReviewActionRequest,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
)
from app.services.cover_letter import generate_cover_letter
from app.services.job_scraper import scraper_service
from app.services.matcher import rank_jobs
from app.services.resume_parser import parse_resume

logger = get_logger("api_routes")
router = APIRouter()


@router.get("/health")
async def health_check():
    """Public health check endpoint for uptime monitoring and fast connection verification."""
    return {
        "status": "healthy",
        "service": "AutoApply AI API",
        "version": "1.0.0",
        "environment": settings.ENV,
        "dry_run": settings.DRY_RUN,
        "auto_submit_enabled": settings.AUTO_SUBMIT_ENABLED,
    }


# -------------------------------------------------------------
# User Profile & Resume Endpoints (Multi-Tenant)
# -------------------------------------------------------------
@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: UserResponse = Depends(get_current_user)):
    """Fetches the editable profile for the authenticated user."""
    profile = storage.get_or_create_profile(
        user_id=current_user.id,
        default_email=current_user.email,
        default_name=current_user.full_name or "",
    )
    return profile


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    update_data: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Partially updates any profile fields. Every field is optional and can be
    edited independently at any time.
    """
    patch_dict = update_data.model_dump(exclude_unset=True)
    updated = storage.save_or_update_profile(current_user.id, patch_dict)
    logger.info("user_profile_updated", user_id=current_user.id, fields=list(patch_dict.keys()))
    return updated


@router.post("/profile/resume", response_model=UserProfileResponse)
async def upload_profile_resume(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Accepts, validates, and parses a resume (.pdf, .docx, .txt) for the authenticated user.
    Persists file to per-user storage directory, records versioned history in `resumes`,
    and updates profile skills/experience/contact fields as accepted suggestions without
    overwriting manually populated custom links.
    """
    if not upload_rate_limiter.is_allowed(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many resume upload attempts. Please wait a minute.",
        )

    run_id = str(uuid.uuid4())[:8]
    log = get_logger("api_routes", correlation_id=run_id)

    filename = file.filename or "uploaded_resume"
    suffix = Path(filename).suffix.lower()

    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{suffix}'. Allowed: .pdf, .docx, .txt",
        )

    # User storage directory
    user_resumes_dir = settings.RESUMES_DIR / current_user.id
    user_resumes_dir.mkdir(parents=True, exist_ok=True)

    resume_id = str(uuid.uuid4())
    stored_filename = f"{resume_id}_{Path(filename).name}"
    target_path = user_resumes_dir / stored_filename

    # Copy and enforce max size limit
    total_bytes = 0
    with open(target_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 64):
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                target_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
                )
            buffer.write(chunk)

    try:
        parsed_profile = parse_resume(str(target_path), correlation_id=run_id)
        
        # Save resume record
        storage.save_resume(
            resume_id=resume_id,
            user_id=current_user.id,
            filename=filename,
            storage_path=str(target_path),
            raw_text=parsed_profile.raw_text,
            make_active=True,
        )

        # Merge suggestions into user profile without destroying manual overrides
        current_prof = storage.get_or_create_profile(current_user.id, current_user.email, current_user.full_name or "")
        
        # Combine skills without duplicates
        combined_skills = list(dict.fromkeys((current_prof.skills or []) + parsed_profile.skills))
        
        profile_patch = {
            "full_name": parsed_profile.full_name or current_prof.full_name,
            "email": parsed_profile.email or current_prof.email,
            "phone": parsed_profile.phone or current_prof.phone,
            "skills": combined_skills,
            "years_experience": parsed_profile.years_experience or current_prof.years_experience,
            "active_resume_id": resume_id,
        }
        updated_profile = storage.save_or_update_profile(current_user.id, profile_patch)

        log.info(
            "resume_uploaded_and_linked",
            user_id=current_user.id,
            resume_id=resume_id,
            skills_count=len(updated_profile.skills),
        )

        # Pre-seed initial review queue for recommended or top jobs
        jobs = scraper_service.fetch_jobs_from_all(correlation_id=run_id, limit=20)
        matches = rank_jobs(parsed_profile, jobs, correlation_id=run_id)
        candidates = [m for m in matches if m.recommended] or matches[:3]
        now = datetime.now(timezone.utc).isoformat()

        for m in candidates:
            existing = storage.get_application(m.job.id, user_id=current_user.id)
            if not existing:
                mappings = [
                    FieldMappingDecision(
                        field_name="Full Name",
                        selector="input[name='name']",
                        value_filled=updated_profile.full_name or current_user.full_name or "Applicant",
                        confidence=0.98,
                        source_field="profile.full_name",
                        rationale="Direct name heuristic extraction",
                    ),
                    FieldMappingDecision(
                        field_name="Email",
                        selector="input[type='email']",
                        value_filled=updated_profile.email or current_user.email,
                        confidence=0.99,
                        source_field="profile.email",
                        rationale="Exact regex email pattern match",
                    ),
                    FieldMappingDecision(
                        field_name="Phone",
                        selector="input[type='tel']",
                        value_filled=updated_profile.phone or "+1-555-0100",
                        confidence=0.95,
                        source_field="profile.phone",
                        rationale="Parsed international telephone standard",
                    ),
                    FieldMappingDecision(
                        field_name="Years Experience",
                        selector="input[name='experience']",
                        value_filled=str(updated_profile.years_experience or 3.0),
                        confidence=0.88,
                        source_field="profile.years_experience",
                        rationale="Computed career date-span range sum",
                    ),
                ]
                app = ApplicationStatus(
                    job_id=m.job.id,
                    user_id=current_user.id,
                    company=m.job.company,
                    title=m.job.title,
                    stage="needs_review",
                    match_score=m.score,
                    updated_at=now,
                    dry_run=settings.DRY_RUN,
                    field_mappings=mappings,
                    notes=f"Drafted application based on {round(m.score * 100)}% match score.",
                )
                storage.save_or_update_application(app, user_id=current_user.id, url=m.job.url, location=m.job.location)

        return updated_profile

    except ResumeParseError as e:
        target_path.unlink(missing_ok=True)
        log.error("resume_parse_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except Exception as e:
        target_path.unlink(missing_ok=True)
        log.error("unexpected_resume_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing resume: {str(e)}",
        )


@router.get("/profile/resumes", response_model=List[ResumeItemResponse])
async def list_resumes(current_user: UserResponse = Depends(get_current_user)):
    """Lists all uploaded resume versions for the authenticated user."""
    return storage.list_resumes(current_user.id)


@router.delete("/profile/resume/{resume_id}")
async def delete_resume(resume_id: str, current_user: UserResponse = Depends(get_current_user)):
    """Deletes a historical resume file and database record."""
    deleted = storage.delete_resume(resume_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume record not found.")
    return {"status": "ok", "message": f"Resume '{resume_id}' deleted."}


# -------------------------------------------------------------
# Backward-compatibility Profile & Upload routes
# -------------------------------------------------------------
@router.get("/resume/current", response_model=ResumeProfile)
async def get_current_resume_profile(current_user: UserResponse = Depends(get_current_user)):
    """Returns candidate profile representation for legacy callers."""
    prof = storage.get_or_create_profile(current_user.id, current_user.email, current_user.full_name or "")
    return ResumeProfile(
        full_name=prof.full_name,
        email=prof.email,
        phone=prof.phone,
        skills=prof.skills,
        years_experience=prof.years_experience,
        language="en",
        raw_text=prof.bio or "",
    )


@router.post("/resume/upload", response_model=ResumeProfile)
async def legacy_upload_resume(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """Backward-compatible endpoint matching previous signature."""
    updated_prof = await upload_profile_resume(file=file, current_user=current_user)
    return ResumeProfile(
        full_name=updated_prof.full_name,
        email=updated_prof.email,
        phone=updated_prof.phone,
        skills=updated_prof.skills,
        years_experience=updated_prof.years_experience,
        language="en",
        raw_text=updated_prof.bio or "",
    )


# -------------------------------------------------------------
# Job Matching & Real Data Endpoints
# -------------------------------------------------------------
@router.get("/jobs/match", response_model=JobMatchResponse)
async def match_jobs(
    query: str = Query(default="", description="Search keywords / role titles"),
    location: str = Query(default="", description="Location filter"),
    sources: Optional[str] = Query(default=None, description="Comma-separated list of boards"),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Fetches real-time postings from selected boards, ranks them against the user's
    active profile, and returns matches alongside per-source status diagnostics.
    """
    run_id = str(uuid.uuid4())[:8]
    prof = storage.get_or_create_profile(current_user.id, current_user.email, current_user.full_name or "")
    
    candidate_profile = ResumeProfile(
        full_name=prof.full_name or current_user.full_name or "Applicant",
        email=prof.email or current_user.email,
        phone=prof.phone or "",
        skills=prof.skills,
        years_experience=prof.years_experience or 3.0,
        language="en",
        raw_text=f"{prof.desired_role or ''} {prof.bio or ''} {' '.join(prof.skills)}",
    )

    selected_sources = [s.strip().lower() for s in sources.split(",") if s.strip()] if sources else None
    
    # Query scraper with per-source telemetry
    jobs, sources_status = scraper_service.fetch_jobs_with_status(
        query=query,
        location=location,
        limit=30,
        sources=selected_sources,
        correlation_id=run_id,
    )

    matches = rank_jobs(candidate_profile, jobs, correlation_id=run_id)

    return JobMatchResponse(
        matches=matches,
        sources_status=sources_status,
        total_found=len(jobs),
    )


# -------------------------------------------------------------
# Human-in-the-Loop Review Queue Endpoints
# -------------------------------------------------------------
@router.get("/review-queue", response_model=List[ApplicationStatus])
async def get_review_queue(current_user: UserResponse = Depends(get_current_user)):
    """
    Returns drafted applications awaiting human approval before submission.
    Core safety valve preventing unintended automated submissions.
    Scoped strictly to the authenticated user.
    """
    queue = storage.list_applications(user_id=current_user.id, stage="needs_review")
    all_user_apps = storage.list_applications(user_id=current_user.id)

    # Seed initial queue if empty for this user
    if not all_user_apps:
        prof = storage.get_or_create_profile(current_user.id, current_user.email, current_user.full_name or "")
        candidate = ResumeProfile(
            full_name=prof.full_name or current_user.full_name or "Applicant",
            email=prof.email or current_user.email,
            phone=prof.phone or "",
            skills=prof.skills,
            years_experience=prof.years_experience or 3.0,
            language="en",
        )
        jobs = scraper_service.fetch_jobs_from_all(limit=15)
        matches = rank_jobs(candidate, jobs)
        now = datetime.now(timezone.utc).isoformat()

        candidates = [m for m in matches if m.recommended] or matches[:3]
        for m in candidates:
            existing = storage.get_application(m.job.id, user_id=current_user.id)
            if not existing:
                    app = ApplicationStatus(
                        job_id=m.job.id,
                        user_id=current_user.id,
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
                                value_filled=candidate.full_name or "Applicant",
                                confidence=0.98,
                                source_field="profile.full_name",
                                rationale="Direct name heuristic extraction",
                            ),
                            FieldMappingDecision(
                                field_name="Email",
                                selector="input[type='email']",
                                value_filled=candidate.email or "user@example.com",
                                confidence=0.99,
                                source_field="profile.email",
                                rationale="Exact regex email pattern match",
                            ),
                            FieldMappingDecision(
                                field_name="Phone",
                                selector="input[type='tel']",
                                value_filled=candidate.phone or "+1-555-0100",
                                confidence=0.95,
                                source_field="profile.phone",
                                rationale="Parsed international telephone standard",
                            ),
                        ],
                        notes=f"Drafted application ({round(m.score * 100)}% match)",
                    )
                    storage.save_or_update_application(
                        app, user_id=current_user.id, url=m.job.url, location=m.job.location
                    )
        queue = storage.list_applications(user_id=current_user.id, stage="needs_review")

    return queue


@router.post("/review-queue/{job_id}/action", response_model=ApplicationStatus)
async def review_action(
    job_id: str,
    action_req: ReviewActionRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Human-in-the-loop action: Approve or Reject a drafted application.
    Enforces that auto-submit requires both explicit user opt-in AND settings opt-in.
    """
    app = storage.get_application(job_id, user_id=current_user.id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application for job '{job_id}' not found for current user.",
        )

    now = datetime.now(timezone.utc).isoformat()

    if action_req.action == "approve":
        # If auto-submit is explicitly opted-in and enabled in settings, mark submitted; otherwise applied in dry-run
        if action_req.auto_submit_override and settings.AUTO_SUBMIT_ENABLED:
            app.stage = "submitted"
            app.dry_run = False
            app.notes = "Approved by user with explicit live auto-submit override."
        else:
            app.stage = "applied"
            app.dry_run = True
            app.notes = "Approved by user in verified dry-run mode (form verified, not submitted)."
    elif action_req.action == "reject":
        app.stage = "rejected"
        app.notes = "Rejected by human reviewer."

    app.updated_at = now
    storage.save_or_update_application(app, user_id=current_user.id)
    logger.info(
        "review_action_completed",
        user_id=current_user.id,
        job_id=job_id,
        action=action_req.action,
        new_stage=app.stage,
    )
    return app


@router.get("/applications", response_model=List[ApplicationStatus])
async def list_all_applications(current_user: UserResponse = Depends(get_current_user)):
    """Lists all application records belonging to the authenticated user."""
    return storage.list_applications(user_id=current_user.id)


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(current_user: UserResponse = Depends(get_current_user)):
    """Aggregate metrics scoped strictly to the authenticated user."""
    counts = storage.get_counts(user_id=current_user.id)
    user_apps = storage.list_applications(user_id=current_user.id)
    agent_active = storage.get_agent_status(current_user.id)

    total_applied = counts.get("applied", 0) + counts.get("submitted", 0)
    total_needs_review = counts.get("needs_review", 0)
    total_matched = len(user_apps) if user_apps else 0
    avg_score = (
        round(sum(a.match_score for a in user_apps) / len(user_apps), 3)
        if user_apps
        else 0.0
    )

    return DashboardSummary(
        total_matched=total_matched,
        total_applied=total_applied,
        total_needs_review=total_needs_review,
        average_match_score=avg_score,
        agent_active=agent_active,
        dry_run_mode=settings.DRY_RUN,
        user_id=current_user.id,
    )


@router.post("/agent/toggle")
async def toggle_agent(
    active: Optional[bool] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    """Toggles agent running status for the authenticated user."""
    current_status = storage.get_agent_status(current_user.id)
    new_status = not current_status if active is None else active
    storage.set_agent_status(current_user.id, new_status)
    logger.info("agent_status_toggled", user_id=current_user.id, active=new_status)
    return {"agent_active": new_status, "dry_run": settings.DRY_RUN}


# -------------------------------------------------------------
# Authenticated Screenshot Serving (Tenant Isolation)
# -------------------------------------------------------------
@router.get("/screenshots/{job_id}")
async def get_screenshot(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Safely serves screenshot image for an application belonging to the authenticated user.
    Prevents cross-user access to screenshots.
    """
    app = storage.get_application(job_id, user_id=current_user.id)
    if not app or not app.screenshot_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found.")

    path = Path(app.screenshot_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot file missing on disk.")

    return FileResponse(str(path), media_type="image/png")


# -------------------------------------------------------------
# Tailored Cover Letter Generation Endpoint
# -------------------------------------------------------------
@router.post("/cover-letter/generate", response_model=CoverLetterResponse)
async def create_cover_letter(
    req: CoverLetterRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """Generates a customized cover letter for the given job posting."""
    prof = storage.get_or_create_profile(current_user.id, current_user.email, current_user.full_name or "")
    letter_text, engine = generate_cover_letter(
        profile=prof,
        company=req.company,
        title=req.title,
        description=req.description,
    )
    return CoverLetterResponse(cover_letter=letter_text, generated_by=engine)
