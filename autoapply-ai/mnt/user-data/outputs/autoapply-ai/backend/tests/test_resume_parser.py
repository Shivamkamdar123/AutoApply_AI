"""
Unit tests for Resume Parser
=============================
Tests text extraction, contact info parsing, skills vocabulary matching,
multi-column layouts, and edge cases (scanned PDFs, non-English text, corrupt files).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.core.exceptions import (
    CorruptResumeError,
    EmptyResumeError,
    NonEnglishResumeError,
    ResumeParseError,
    ScannedImageResumeError,
    UnsupportedFormatError,
)
from app.services.resume_parser import (
    estimate_years_experience,
    extract_contact_info,
    extract_skills,
    guess_name,
    parse_resume,
)


def test_parse_txt_resume(sample_txt_resume: Path):
    """Test parsing a well-formed text resume."""
    profile = parse_resume(str(sample_txt_resume))
    assert profile.full_name == "Jane Doe"
    assert profile.email == "jane.doe@example.com"
    assert "555" in (profile.phone or "")
    assert "python" in profile.skills
    assert "fastapi" in profile.skills
    assert "docker" in profile.skills
    assert profile.years_experience is not None
    assert profile.years_experience >= 4.0
    assert profile.language == "en"


def test_parse_docx_resume(sample_docx_resume: Path):
    """Test parsing a DOCX resume including paragraph and table cell text."""
    profile = parse_resume(str(sample_docx_resume))
    assert profile.full_name == "Jane Doe"
    assert profile.email == "jane.doe@example.com"
    # Extracted from table
    assert "machine learning" in profile.skills
    assert "pytorch" in profile.skills


def test_missing_file_raises_error():
    """Attempting to parse a non-existent file must raise ResumeParseError."""
    with pytest.raises(ResumeParseError) as exc_info:
        parse_resume("non_existent_file_path_12345.pdf")
    assert "not found" in str(exc_info.value).lower()


def test_empty_file_raises_error(tmp_path: Path):
    """Empty 0-byte file must raise EmptyResumeError."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(EmptyResumeError):
        parse_resume(str(empty_file))


def test_unsupported_format_raises_error(tmp_path: Path):
    """Files with unsupported extensions must raise UnsupportedFormatError."""
    bad_file = tmp_path / "resume.exe"
    bad_file.write_text("dummy binary content", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError):
        parse_resume(str(bad_file))


def test_corrupt_docx_raises_error(tmp_path: Path):
    """Corrupted docx (invalid zip) must raise CorruptResumeError."""
    corrupt_docx = tmp_path / "bad.docx"
    corrupt_docx.write_bytes(b"This is not a real zip file")
    with pytest.raises(CorruptResumeError):
        parse_resume(str(corrupt_docx))


def test_non_english_resume_raises_error(tmp_path: Path):
    """Resume with predominantly non-Latin characters must raise NonEnglishResumeError."""
    chinese_resume = tmp_path / "chinese.txt"
    chinese_resume.write_text(
        "张伟\n软件工程师\n精通Python编程语言、微服务架构和分布式数据库开发。\n具有五年以上工作经验。",
        encoding="utf-8",
    )
    with pytest.raises(NonEnglishResumeError):
        parse_resume(str(chinese_resume))


def test_skills_boundary_matching():
    """Verify that skills like 'go' are matched with word boundaries, not inside 'good'."""
    text = "We are good developers who love python and write go code with postgresql."
    skills = extract_skills(text)
    assert "go" in skills
    assert "python" in skills
    assert "postgresql" in skills
    
    # Text without 'go' as a separate word
    text2 = "Good algorithmic skills and outgoing personality."
    skills2 = extract_skills(text2)
    assert "go" not in skills2


def test_extract_contact_info():
    """Test regex extraction of email addresses and phone formats."""
    text = "Contact Alex Smith at alex.smith+jobs@tech-corp.io or call +1-800-555-0199 for inquiries."
    email, phone = extract_contact_info(text)
    assert email == "alex.smith+jobs@tech-corp.io"
    assert phone is not None
    assert "555-0199" in phone


def test_estimate_years_experience():
    """Test experience calculation across date spans."""
    text = "Software Engineer (2018 - 2021) at Acme Corp\nSenior Engineer (2021 - Present) at MegaTech"
    years = estimate_years_experience(text)
    assert years is not None
    assert years >= 5.0


def test_guess_name_heuristics():
    """Test heuristic name identification."""
    text = "Curriculum Vitae\nJohn Doe\njohn@example.com\nSoftware Engineer"
    name = guess_name(text)
    assert name == "John Doe"


def test_scanned_pdf_detected(tmp_path: Path):
    """Mock a PDF that has images but zero extractable text to ensure ScannedImageResumeError."""
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock content")

    mock_page = MagicMock()
    mock_page.images = [{"stream": b"fake_image_bytes"}]
    mock_page.extract_text.return_value = ""
    mock_page.extract_words.return_value = []

    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf
        with pytest.raises(ScannedImageResumeError):
            parse_resume(str(pdf_path))
