"""
Resume parser
=============
Turns an uploaded resume file (.pdf, .docx, or .txt) into a structured
ResumeProfile the rest of the system can work with.

This module is fully self-contained and has no dependency on the agent
or browser layer, so it can be built and tested completely on its own —
just run this file directly with a sample resume path.

How it works (deliberately simple, upgradeable later):
1. Extract raw text from the file, regardless of format.
2. Pull out contact info (email, phone) with regex.
3. Pull out skills by matching against a known skills vocabulary.
   This is a lot more reliable for a student project than trying to
   train/host an NER model — swap in spaCy or an LLM call later if
   you want fuzzier extraction, the interface below won't need to change.
4. Estimate years of experience from date ranges in the text.
"""

import re
from pathlib import Path

import pdfplumber
import docx

from app.models.schemas import ResumeProfile

# A starter vocabulary — extend this list with skills relevant to the
# roles you're targeting. This is intentionally a plain list (not ML)
# so it's transparent and easy to explain in a viva/demo.
SKILLS_VOCAB = [
    "python", "java", "c++", "javascript", "typescript", "sql", "react",
    "node.js", "django", "flask", "fastapi", "playwright", "selenium",
    "machine learning", "deep learning", "nlp", "pandas", "numpy",
    "scikit-learn", "pytorch", "tensorflow", "docker", "kubernetes",
    "aws", "gcp", "azure", "git", "html", "css", "rest api", "graphql",
    "mongodb", "postgresql", "mysql", "linux", "ci/cd",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+\d{1,3}[-.\s]?)?(?:\d[-.\s]?){9,12}\d")
YEAR_RANGE_RE = re.compile(r"(20\d{2}|19\d{2})\s*(?:-|to|–)\s*(20\d{2}|present|current)", re.IGNORECASE)


def extract_text(file_path: str) -> str:
    """Extract raw text from a resume file, regardless of format."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)

    if suffix == ".docx":
        document = docx.Document(path)
        return "\n".join(p.text for p in document.paragraphs)

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"Unsupported resume format: {suffix}")


def extract_skills(text: str) -> list[str]:
    """Match known skills against the resume text (case-insensitive)."""
    text_lower = text.lower()
    found = [skill for skill in SKILLS_VOCAB if skill in text_lower]
    return sorted(set(found))


def extract_contact_info(text: str) -> tuple[str | None, str | None]:
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    email = email_match.group(0) if email_match else None
    phone = phone_match.group(0).strip() if phone_match else None
    return email, phone


def estimate_years_experience(text: str) -> float | None:
    """
    Rough estimate: sum up the spans of any "YYYY - YYYY" or "YYYY - Present"
    ranges found in the resume. Good enough as a baseline signal for matching;
    not meant to be exact.
    """
    total_years = 0.0
    for match in YEAR_RANGE_RE.finditer(text):
        start_year = int(match.group(1))
        end_raw = match.group(2).lower()
        end_year = 2026 if end_raw in ("present", "current") else int(end_raw)
        if end_year >= start_year:
            total_years += (end_year - start_year)
    return round(total_years, 1) if total_years > 0 else None


def guess_name(text: str) -> str | None:
    """
    Heuristic: the name is usually the first non-empty line that isn't
    an email/phone and doesn't look like a section header. Not bulletproof —
    fine for a baseline, flag this as a known limitation in your report.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if EMAIL_RE.search(stripped) or PHONE_RE.search(stripped):
            continue
        if stripped.isupper() and len(stripped.split()) > 4:
            continue
        return stripped
    return None


def parse_resume(file_path: str) -> ResumeProfile:
    """Main entry point — file path in, structured profile out."""
    raw_text = extract_text(file_path)
    email, phone = extract_contact_info(raw_text)

    return ResumeProfile(
        full_name=guess_name(raw_text),
        email=email,
        phone=phone,
        skills=extract_skills(raw_text),
        years_experience=estimate_years_experience(raw_text),
        raw_text=raw_text,
    )


if __name__ == "__main__":
    # Quick manual test: python resume_parser.py path/to/resume.pdf
    import sys

    if len(sys.argv) != 2:
        print("Usage: python resume_parser.py <path-to-resume>")
        sys.exit(1)

    profile = parse_resume(sys.argv[1])
    print(profile.model_dump_json(indent=2, exclude={"raw_text"}))
