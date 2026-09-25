"""
Pytest configuration & fixtures
================================
Provides fixtures for resumes (PDF, DOCX, TXT, scanned, edge cases),
job postings, profiles, and temporary test directories.
"""

import os
import tempfile
from pathlib import Path
import docx
import pytest

from app.db.storage import storage
from app.models.schemas import JobPosting, ResumeProfile


@pytest.fixture(autouse=True)
def isolate_test_db(tmp_path: Path, monkeypatch):
    """Ensures each test case runs against an isolated, fresh SQLite database."""
    test_db = tmp_path / "isolated_test.db"
    monkeypatch.setattr(storage, "db_path", test_db)
    storage._init_db()
    yield


@pytest.fixture
def sample_resume_text() -> str:
    return (
        "Jane Doe\n"
        "jane.doe@example.com | +1 (555) 234-5678\n"
        "Senior Software Engineer\n\n"
        "Summary:\n"
        "Experienced Backend Developer specializing in Python, FastAPI, Docker, and PostgreSQL.\n\n"
        "Experience:\n"
        "Acme Technologies — Senior Engineer (2020 - 2024)\n"
        "- Built scalable REST APIs using FastAPI and Python.\n"
        "- Managed deployments using Docker and Kubernetes.\n"
        "- Maintained relational databases using PostgreSQL and SQL.\n\n"
        "Skills:\n"
        "Python, FastAPI, Docker, Kubernetes, PostgreSQL, SQL, Git, Linux, REST API\n"
    )


@pytest.fixture
def sample_docx_resume(tmp_path: Path, sample_resume_text: str) -> Path:
    file_path = tmp_path / "resume.docx"
    doc = docx.Document()
    for line in sample_resume_text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    
    # Add a table to test table extraction
    table = doc.add_table(rows=1, cols=2)
    row_cells = table.rows[0].cells
    row_cells[0].text = "Key Skill"
    row_cells[1].text = "Machine Learning, PyTorch, Scikit-learn"
    
    doc.save(str(file_path))
    return file_path


@pytest.fixture
def sample_txt_resume(tmp_path: Path, sample_resume_text: str) -> Path:
    file_path = tmp_path / "resume.txt"
    file_path.write_text(sample_resume_text, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_profile(sample_resume_text: str) -> ResumeProfile:
    return ResumeProfile(
        full_name="Jane Doe",
        email="jane.doe@example.com",
        phone="+1 (555) 234-5678",
        skills=["python", "fastapi", "docker", "postgresql", "sql", "git", "rest api"],
        years_experience=4.0,
        raw_text=sample_resume_text,
    )


@pytest.fixture
def matching_job() -> JobPosting:
    return JobPosting(
        id="job-python-1",
        title="Senior Python Backend Engineer",
        company="ScaleUp Solutions",
        location="Remote",
        description=(
            "We are seeking a Senior Python Engineer with extensive FastAPI experience. "
            "You will build high-throughput REST APIs, architect PostgreSQL databases, "
            "and containerize microservices with Docker and Git."
        ),
        url="https://example.com/jobs/job-python-1",
        source="sample",
    )


@pytest.fixture
def non_matching_job() -> JobPosting:
    return JobPosting(
        id="job-sales-2",
        title="Account Executive - Enterprise Sales",
        company="Global Sales Corp",
        location="New York, NY",
        description=(
            "Responsible for outbound prospecting, closing enterprise software deals, "
            "negotiating contracts, and exceeding sales quotas. CRM experience required."
        ),
        url="https://example.com/jobs/job-sales-2",
        source="sample",
    )
