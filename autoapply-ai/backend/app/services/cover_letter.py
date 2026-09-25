"""
Cover Letter & Application Note Generator
=========================================
Generates customized, professional cover letters and application notes
matching candidate profile attributes against specific job requirements.
Supports optional Anthropic Claude integration via ANTHROPIC_API_KEY with
an intelligent deterministic fallback when no API key is configured.
"""

from typing import Optional, Tuple
import httpx

from app.config import settings
from app.core.logging import get_logger
from app.models.schemas import UserProfileResponse

logger = get_logger("cover_letter_service")


def generate_cover_letter(
    profile: UserProfileResponse,
    company: str,
    title: str,
    description: str,
    correlation_id: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generates a tailored cover letter for a specific job application.
    Returns: (cover_letter_text, generator_engine)
    """
    log = get_logger("cover_letter_service", correlation_id=correlation_id)

    # 1. Check for Anthropic API Key
    if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip():
        try:
            prompt = (
                f"You are a professional career advisor writing a concise, compelling cover letter (3-4 paragraphs).\n"
                f"Candidate Name: {profile.full_name or 'Applicant'}\n"
                f"Candidate Email: {profile.email or ''}\n"
                f"Skills: {', '.join(profile.skills) if profile.skills else 'Software Engineering'}\n"
                f"Years of Experience: {profile.years_experience or 3}\n"
                f"Bio/Summary: {profile.bio or ''}\n\n"
                f"Target Job:\n"
                f"Company: {company}\n"
                f"Role Title: {title}\n"
                f"Job Description Excerpt: {description[:1200]}\n\n"
                f"Write a polished, authentic cover letter directly from the candidate to the hiring team. Do not invent false credentials."
            )

            headers = {
                "x-api-key": settings.ANTHROPIC_API_KEY.strip(),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            body = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            }

            with httpx.Client(timeout=10.0) as client:
                resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("content", [])
                    if content and "text" in content[0]:
                        log.info("cover_letter_generated_via_claude", company=company, title=title)
                        return content[0]["text"].strip(), "anthropic:claude-3-haiku"
        except Exception as e:
            log.warning("claude_generation_failed_fallback_heuristic", error=str(e))

    # 2. Deterministic Heuristic Fallback (Zero external dependency, 100% reliable)
    name = profile.full_name or "Alex Rivera"
    email = profile.email or "candidate@example.com"
    phone = profile.phone or ""
    contact_line = f"{email} | {phone}" if phone else email
    skills_list = profile.skills[:5] if profile.skills else ["Python", "FastAPI", "REST APIs", "SQL"]
    skills_str = ", ".join(skills_list)
    years = profile.years_experience or 3.0

    letter = (
        f"Dear {company} Hiring Team,\n\n"
        f"I am writing to express my strong interest in the {title} position at {company}. "
        f"With over {years:.1f} years of engineering experience and core competencies in {skills_str}, "
        f"I am enthusiastic about the opportunity to contribute to your team's mission.\n\n"
        f"Throughout my career, I have focused on engineering resilient systems and clean software architectures. "
        f"My background aligning technical requirements with measurable outcomes directly matches the challenges outlined for the {title} role. "
        f"Specifically, my proficiency with {skills_str} enables me to onboard swiftly and deliver high-quality results.\n\n"
        f"Thank you for your time and consideration. I welcome the opportunity to discuss how my skill set and experience can support {company}'s ongoing objectives.\n\n"
        f"Sincerely,\n"
        f"{name}\n"
        f"{contact_line}"
    )

    log.info("cover_letter_generated_via_heuristic", company=company, title=title)
    return letter, "deterministic_heuristic"
