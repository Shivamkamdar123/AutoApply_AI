"""
Resume Parser
=============
Converts uploaded resumes (.pdf, .docx, .txt) into a structured ResumeProfile.
Hardened with multi-column layout support, scanned-image detection,
language validation, and typed exception handling.
"""

import os
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import docx
import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

from app.core.exceptions import (
    CorruptResumeError,
    EmptyResumeError,
    NonEnglishResumeError,
    ResumeParseError,
    ScannedImageResumeError,
    UnsupportedFormatError,
)
from app.core.logging import get_logger
from app.models.schemas import ResumeProfile

logger = get_logger("resume_parser")

# Expanded skills vocabulary
SKILLS_VOCAB = [
    "python", "java", "c++", "c#", "javascript", "typescript", "golang", "go",
    "rust", "ruby", "php", "sql", "react", "vue", "angular", "node.js",
    "django", "flask", "fastapi", "spring", "playwright", "selenium",
    "machine learning", "deep learning", "nlp", "computer vision", "pandas",
    "numpy", "scikit-learn", "pytorch", "tensorflow", "docker", "kubernetes",
    "aws", "gcp", "azure", "git", "html", "css", "rest api", "graphql",
    "mongodb", "postgresql", "mysql", "redis", "linux", "ci/cd", "terraform",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}|\b\d{10}\b"
)
YEAR_RANGE_RE = re.compile(
    r"(20\d{2}|19\d{2})\s*(?:-|to|–|—)\s*(20\d{2}|present|current)",
    re.IGNORECASE,
)


def _check_language(text: str) -> Tuple[str, List[str]]:
    """
    Detects if the text is predominantly non-English.
    Returns detected language tag and any warnings.
    """
    if not text.strip():
        return "en", []

    cleaned = "".join(ch for ch in text if ch.isalpha())
    if not cleaned:
        return "en", []

    # Check non-Latin character proportion
    non_latin_count = sum(
        1 for ch in cleaned if "LATIN" not in unicodedata.name(ch, "")
    )
    ratio = non_latin_count / len(cleaned)

    if ratio > 0.40:
        raise NonEnglishResumeError(
            f"Resume appears to be predominantly non-English ({round(ratio * 100)}% non-Latin scripts). "
            "AutoApply AI currently requires English resumes for accurate skill parsing and job matching."
        )

    # Check common English stopwords
    text_lower = text.lower()
    common_words = ["the", "and", "in", "of", "to", "for", "with", "experience"]
    found_count = sum(1 for w in common_words if re.search(rf"\b{w}\b", text_lower))
    warnings = []
    if found_count < 2 and len(cleaned) > 200:
        warnings.append("Low density of standard English resume terms detected.")

    return "en", warnings


def _extract_pdf_text_layout(pdf: pdfplumber.PDF) -> Tuple[str, bool]:
    """
    Extracts text from PDF while handling multi-column layouts and checking
    for scanned images. Returns (extracted_text, has_images).
    """
    pages_text: List[str] = []
    has_images = False

    for page_idx, page in enumerate(pdf.pages):
        # Check for raster images
        if page.images and len(page.images) > 0:
            has_images = True

        # Extract layout-preserved text
        try:
            # layout=True helps preserve multi-column structure
            text = page.extract_text(layout=True)
            if not text or len(text.strip()) < 15:
                # Fallback to standard word extraction sorted by coordinates
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                if words:
                    # Sort top-to-bottom, left-to-right
                    words.sort(key=lambda w: (round(w["top"] / 10) * 10, w["x0"]))
                    text = " ".join(w["text"] for w in words)
            pages_text.append(text or "")
        except Exception as e:
            logger.warning("pdf_page_extract_error", page=page_idx, error=str(e))
            pages_text.append("")

    full_text = "\n".join(pages_text).strip()
    return full_text, has_images


def extract_text(file_path: str) -> Tuple[str, List[str]]:
    """
    Extracts raw text from a resume file (.pdf, .docx, or .txt).
    Validates file existence, integrity, and content.
    Returns (raw_text, warnings).
    """
    path = Path(file_path)
    warnings: List[str] = []

    if not path.exists():
        raise ResumeParseError(f"Resume file not found at path: {file_path}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise EmptyResumeError(f"Resume file is empty (0 bytes): {path.name}")

    if file_size > 15 * 1024 * 1024:
        raise ResumeParseError(f"Resume file exceeds 15MB maximum size limit: {path.name}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            with pdfplumber.open(path) as pdf:
                if len(pdf.pages) == 0:
                    raise EmptyResumeError("PDF contains 0 pages.")
                raw_text, has_images = _extract_pdf_text_layout(pdf)
        except PDFSyntaxError as e:
            raise CorruptResumeError(f"Corrupt or unreadable PDF: {e}") from e
        except EmptyResumeError:
            raise
        except Exception as e:
            raise CorruptResumeError(f"Failed to read PDF file: {e}") from e

        # Scanned image detection
        if len(raw_text.strip()) < 30:
            if has_images:
                raise ScannedImageResumeError(
                    "Uploaded PDF appears to be a scanned image or screenshot without an embedded text layer. "
                    "AutoApply AI requires a selectable, text-based PDF or DOCX file."
                )
            raise EmptyResumeError("PDF contains no readable text.")

        return raw_text, warnings

    if suffix == ".docx":
        try:
            document = docx.Document(path)
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            # Include text inside tables (common for header/skills columns in Word)
            table_cells = []
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text = cell.text.strip()
                        if text:
                            table_cells.append(text)

            raw_text = "\n".join(paragraphs + table_cells).strip()
        except zipfile.BadZipFile as e:
            raise CorruptResumeError(f"Corrupt or invalid DOCX document: {e}") from e
        except Exception as e:
            raise CorruptResumeError(f"Failed to read DOCX file: {e}") from e

        if not raw_text:
            raise EmptyResumeError("DOCX file contains no readable text.")

        return raw_text, warnings

    if suffix == ".txt":
        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as e:
            raise CorruptResumeError(f"Failed to read text file: {e}") from e

        if not raw_text:
            raise EmptyResumeError("Text file is empty.")

        return raw_text, warnings

    raise UnsupportedFormatError(
        f"Unsupported resume format '{suffix}'. Allowed formats: .pdf, .docx, .txt"
    )


def extract_skills(text: str) -> List[str]:
    """Matches known skills against the resume text using word boundaries."""
    text_lower = text.lower()
    found: set[str] = set()

    for skill in SKILLS_VOCAB:
        # Use regex boundary where appropriate to avoid partial matches
        # (e.g. "go" in "good", "c++" in text)
        escaped = re.escape(skill)
        pattern = rf"(?<!\w){escaped}(?!\w)"
        if re.search(pattern, text_lower):
            found.add(skill)

    return sorted(found)


def extract_contact_info(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts email and telephone numbers."""
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    email = email_match.group(0) if email_match else None
    phone = phone_match.group(0).strip() if phone_match else None
    return email, phone


def estimate_years_experience(text: str) -> Optional[float]:
    """
    Estimates total experience by summing distinct year ranges.
    Clamps reasonable ranges to avoid overlapping totals over 35 years.
    """
    total_years = 0.0
    for match in YEAR_RANGE_RE.finditer(text):
        try:
            start_year = int(match.group(1))
            end_raw = match.group(2).lower()
            end_year = 2026 if end_raw in ("present", "current") else int(end_raw)
            if 1970 <= start_year <= end_year <= 2030:
                span = end_year - start_year
                if 0 <= span <= 25:
                    total_years += span
        except (ValueError, TypeError):
            continue

    if total_years > 0:
        return min(round(total_years, 1), 35.0)
    return None


def guess_name(text: str) -> Optional[str]:
    """Heuristic identification of the candidate name."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if EMAIL_RE.search(stripped) or PHONE_RE.search(stripped):
            continue
        # Skip lines that look like addresses, URLs, or headers
        if any(term in stripped.lower() for term in ["resume", "curriculum", "page", "http", "linkedin", "github"]):
            continue
        if len(stripped.split()) in (2, 3, 4) and len(stripped) < 40:
            return stripped
    return None


def parse_resume(file_path: str, correlation_id: Optional[str] = None) -> ResumeProfile:
    """
    Main entry point for parsing a resume.
    Guaranteed to return a valid ResumeProfile or raise a typed ResumeParseError.
    """
    log = get_logger("resume_parser", correlation_id=correlation_id)
    log.info("parsing_resume_start", file_path=str(file_path))

    raw_text, warnings = extract_text(file_path)
    language, lang_warnings = _check_language(raw_text)
    warnings.extend(lang_warnings)

    email, phone = extract_contact_info(raw_text)
    skills = extract_skills(raw_text)
    experience = estimate_years_experience(raw_text)
    name = guess_name(raw_text)

    if not skills:
        warnings.append("No technical skills matched against current vocabulary.")

    profile = ResumeProfile(
        full_name=name,
        email=email,
        phone=phone,
        skills=skills,
        years_experience=experience,
        language=language,
        warnings=warnings,
        raw_text=raw_text,
    )

    log.info(
        "parsing_resume_complete",
        name=name,
        skills_count=len(skills),
        experience=experience,
        warnings_count=len(warnings),
    )
    return profile
