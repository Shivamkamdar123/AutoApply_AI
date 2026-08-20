"""
API routes
==========
Thin layer that connects HTTP requests to the services. Routes should stay
"thin" — the real logic lives in services/, this file just wires it up.
"""

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import DashboardSummary
from app.services.resume_parser import parse_resume
from app.services.matcher import rank_jobs
from app.services.job_scraper import get_jobs

router = APIRouter()


@router.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Accepts a resume file, parses it, and returns the structured profile."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(status_code=400, detail="Only .pdf, .docx, or .txt resumes are supported.")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        profile = parse_resume(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return profile


@router.get("/jobs/match")
async def match_jobs(query: str = "", location: str = ""):
    """
    For the demo/dashboard: parses a bundled sample profile against the
    sample job list and returns ranked matches. In a full build, this
    would take the logged-in user's already-parsed profile instead.
    """
    from app.models.schemas import ResumeProfile

    demo_profile = ResumeProfile(
        full_name="Demo Candidate",
        skills=["python", "fastapi", "sql", "docker", "git"],
        raw_text=(
            "Backend developer experienced with Python, FastAPI, SQL, "
            "Docker, and Git. 2020 - 2023 building REST APIs."
        ),
    )

    jobs = get_jobs(query=query, location=location)
    matches = rank_jobs(demo_profile, jobs)
    return matches


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary():
    """Aggregate stats for the dashboard's top stat cards."""
    from app.models.schemas import ResumeProfile

    demo_profile = ResumeProfile(
        skills=["python", "fastapi", "sql", "docker", "git"],
        raw_text="Backend developer experienced with Python, FastAPI, SQL, Docker, and Git.",
    )
    jobs = get_jobs()
    matches = rank_jobs(demo_profile, jobs)

    recommended = [m for m in matches if m.recommended]
    avg_score = sum(m.score for m in matches) / len(matches) if matches else 0.0

    return DashboardSummary(
        total_matched=len(matches),
        total_applied=0,          # will be real once the browser agent exists
        total_needs_review=len(recommended),
        average_match_score=round(avg_score, 3),
        agent_active=False,       # flips to True once the agent loop is running
    )
