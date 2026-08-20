"""
Matching engine
================
Scores how well a resume fits a job posting, and ranks a list of postings.

Baseline approach: TF-IDF vectorization + cosine similarity between the
resume text and each job description. This is a legitimate, well-understood
IR technique — easy to explain in a viva, no external API calls, no cost,
deterministic (same input always gives same output, which matters for
demoing and debugging).

Upgrade path (mention this in your report as future work): swap
TfidfVectorizer for sentence embeddings (e.g. `sentence-transformers`) to
capture semantic similarity instead of keyword overlap. The function
signatures below (`score_job`, `rank_jobs`) would not need to change —
only what happens inside them.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.schemas import ResumeProfile, JobPosting, MatchResult
from app.config import MATCH_THRESHOLD


def _skill_overlap(resume_skills: list[str], job_text: str) -> list[str]:
    job_text_lower = job_text.lower()
    return sorted(skill for skill in resume_skills if skill in job_text_lower)


def score_job(resume: ResumeProfile, job: JobPosting) -> MatchResult:
    """Score a single job against a resume profile."""
    corpus = [resume.raw_text, job.description]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    matched_skills = _skill_overlap(resume.skills, job.description)

    return MatchResult(
        job=job,
        score=round(float(similarity), 3),
        matched_skills=matched_skills,
        recommended=similarity >= MATCH_THRESHOLD,
    )


def rank_jobs(resume: ResumeProfile, jobs: list[JobPosting]) -> list[MatchResult]:
    """Score every job in the list and return them sorted, best match first."""
    results = [score_job(resume, job) for job in jobs]
    return sorted(results, key=lambda r: r.score, reverse=True)


if __name__ == "__main__":
    # Quick manual sanity check with fabricated data.
    sample_resume = ResumeProfile(
        full_name="Test Candidate",
        skills=["python", "fastapi", "sql"],
        raw_text="Experienced backend developer skilled in Python, FastAPI, "
                  "SQL, and building REST APIs. Familiar with Docker and Git.",
    )
    sample_job = JobPosting(
        id="1",
        title="Backend Engineer",
        company="Acme Corp",
        location="Remote",
        description="Looking for a backend engineer with Python and FastAPI "
                     "experience, comfortable writing REST APIs and working "
                     "with SQL databases.",
        url="https://example.com/job/1",
    )
    result = score_job(sample_resume, sample_job)
    print(result.model_dump_json(indent=2))
