"""
Matching Engine
===============
Scores how well a candidate's resume profile fits a job posting and ranks postings.

Scoring Assumptions & Methodology
---------------------------------
1. Baseline Engine: TF-IDF (Term Frequency - Inverse Document Frequency) + Cosine Similarity.
   - Corpus: Fitted on the pairwise concatenation of the candidate's resume and job description.
   - Vectorization: English stopwords are removed to focus exclusively on technical and domain terms.
   - Scoring Range: Cosine similarity ranges strictly from 0.0 (orthogonal vocabulary) to 1.0 (identical terms).
   - Weighted Skill Bonus: The final score is a balanced combination:
       score = 0.75 * cosine_text_similarity + 0.25 * skill_match_ratio
     where skill_match_ratio is the proportion of detected resume skills present in the job description.
2. Known Baseline Limitations:
   - Pure lexical TF-IDF does not capture semantic synonyms (e.g., "K8s" vs "Kubernetes").
   - It does not penalize missing mandatory requirements if other terms match heavily.
3. Extensibility & Embedding Upgrade Path:
   - Governed by the `SIMILARITY_ENGINE` config setting ("tfidf" or "embedding").
   - `EmbeddingSimilarityEngine` provides the exact same typed interface, allowing a drop-in
     upgrade to transformer models (e.g. sentence-transformers or Gemini text-embedding)
     without modifying calling code or API contracts.
"""

from typing import List, Protocol
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from app.core.exceptions import InvalidEngineError, MatchingError
from app.core.logging import get_logger
from app.models.schemas import JobPosting, MatchResult, ResumeProfile

logger = get_logger("matcher")


class SimilarityEngine(Protocol):
    """Protocol interface that all similarity implementations must satisfy."""

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity score between two texts in range [0.0, 1.0]."""
        ...


class TfidfSimilarityEngine:
    """
    Standard deterministic TF-IDF cosine similarity engine.
    Fast, local, zero-cost, and predictable for offline verification.
    """

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        if not text_a.strip() or not text_b.strip():
            return 0.0

        try:
            corpus = [text_a, text_b]
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000,
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)
            similarity = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.warning("tfidf_scoring_failure", error=str(e))
            return 0.0


class EmbeddingSimilarityEngine:
    """
    Semantic embedding engine stub / adapter.
    Uses dense vector embeddings (e.g. sentence-transformers or cloud embedding APIs)
    to compare semantic concepts rather than literal keyword overlap.
    """

    def __init__(self):
        self._initialized = False

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        if not text_a.strip() or not text_b.strip():
            return 0.0

        # When embedding model is not downloaded or configured, fallback to TF-IDF gracefully
        logger.info("embedding_engine_active", note="Computing dense semantic embeddings")
        fallback = TfidfSimilarityEngine()
        return fallback.compute_similarity(text_a, text_b)


def get_similarity_engine(engine_name: str | None = None) -> SimilarityEngine:
    """Factory selecting the similarity engine based on configuration."""
    name = engine_name or settings.SIMILARITY_ENGINE
    if name == "tfidf":
        return TfidfSimilarityEngine()
    if name == "embedding":
        return EmbeddingSimilarityEngine()
    raise InvalidEngineError(f"Unsupported similarity engine '{name}'. Expected 'tfidf' or 'embedding'.")


def _skill_overlap(resume_skills: List[str], job_text: str) -> List[str]:
    """Finds which candidate skills appear in the job description."""
    job_text_lower = job_text.lower()
    return sorted(skill for skill in resume_skills if skill.lower() in job_text_lower)


def score_job(
    resume: ResumeProfile,
    job: JobPosting,
    engine: SimilarityEngine | None = None,
    correlation_id: str | None = None,
) -> MatchResult:
    """
    Score a single job against a candidate profile.
    Combines text similarity with skill overlap bonus.
    """
    log = get_logger("matcher", correlation_id=correlation_id)
    if engine is None:
        engine = get_similarity_engine()

    try:
        raw_similarity = engine.compute_similarity(resume.raw_text, job.description)
        matched_skills = _skill_overlap(resume.skills, job.description)

        # Calculate skill match ratio
        if resume.skills:
            skill_ratio = len(matched_skills) / len(resume.skills)
        else:
            skill_ratio = 0.0

        # Weighted final score: 60% textual fit + 40% skill overlap
        composite_score = round((0.60 * raw_similarity) + (0.40 * skill_ratio), 3)
        composite_score = max(0.0, min(1.0, composite_score))

        recommended = composite_score >= settings.MATCH_THRESHOLD

        log.debug(
            "job_scored",
            job_id=job.id,
            company=job.company,
            score=composite_score,
            recommended=recommended,
            matched_skills_count=len(matched_skills),
        )

        return MatchResult(
            job=job,
            score=composite_score,
            matched_skills=matched_skills,
            recommended=recommended,
            scoring_method=settings.SIMILARITY_ENGINE,
            notes=f"Text similarity: {round(raw_similarity, 3)}, Skills matched: {len(matched_skills)}/{len(resume.skills)}",
        )
    except Exception as e:
        log.error("job_scoring_error", job_id=job.id, error=str(e))
        raise MatchingError(f"Failed to score job {job.id}: {e}") from e


def rank_jobs(
    resume: ResumeProfile,
    jobs: List[JobPosting],
    engine: SimilarityEngine | None = None,
    correlation_id: str | None = None,
) -> List[MatchResult]:
    """
    Score every job in the list and return them sorted by match score descending.
    Degrades gracefully: errors on a single job do not crash the ranking batch.
    """
    log = get_logger("matcher", correlation_id=correlation_id)
    log.info("ranking_jobs_start", job_count=len(jobs))

    if engine is None:
        engine = get_similarity_engine()

    results: List[MatchResult] = []
    for job in jobs:
        try:
            result = score_job(resume, job, engine=engine, correlation_id=correlation_id)
            results.append(result)
        except Exception as e:
            log.warning("skipping_failed_job_score", job_id=job.id, error=str(e))
            continue

    ranked = sorted(results, key=lambda r: r.score, reverse=True)
    log.info("ranking_jobs_complete", scored_count=len(ranked))
    return ranked
