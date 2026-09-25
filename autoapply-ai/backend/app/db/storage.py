"""
Persistent Storage & Idempotency Layer
======================================
Stores raw scraped jobs, normalized applications, review queue items, and deduplication hashes.
Implements SQLite with WAL (Write-Ahead Logging) for high concurrency and zero locks.

PostgreSQL Migration Path:
--------------------------
To migrate this module to PostgreSQL for cloud deployment:
1. Replace `sqlite3.connect` with an `asyncpg` or SQLAlchemy `AsyncSession` pool.
2. The schema below maps directly to Postgres DDL:
   - TEXT -> VARCHAR / TEXT
   - INTEGER -> BOOLEAN / INTEGER
   - REAL -> NUMERIC(5, 3)
   - TIMESTAMP -> TIMESTAMPTZ DEFAULT NOW()
3. The method signatures below (`save_application`, `is_job_applied`, etc.)
   remain identical, preserving calling code.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.models.schemas import ApplicationStatus, FieldMappingDecision, JobPosting

logger = get_logger("storage")


class JobStorage:
    """
    Persistent repository for job listings, raw scrape caches, and application lifecycles.
    Thread-safe through isolated connections per transaction.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error("db_connection_failed", error=str(e), path=str(self.db_path))
            raise StorageError(f"Database connection error: {e}") from e

    def _init_db(self) -> None:
        """Creates the required tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                -- Raw scraped job payloads (preserves raw crawl data for re-normalization)
                CREATE TABLE IF NOT EXISTS raw_scraped_jobs (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    raw_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    scraped_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_raw_jobs_source ON raw_scraped_jobs(source);
                CREATE INDEX IF NOT EXISTS idx_raw_jobs_hash ON raw_scraped_jobs(raw_hash);

                -- Deduplication cache to prevent re-applying or scraping stale listings
                CREATE TABLE IF NOT EXISTS dedup_cache (
                    content_hash TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    seen_at TEXT NOT NULL
                );

                -- Applications lifecycle state machine
                CREATE TABLE IF NOT EXISTS applications (
                    job_id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    location TEXT,
                    url TEXT NOT NULL,
                    stage TEXT NOT NULL, -- matched | queued | needs_review | applied | submitted | failed | rejected
                    match_score REAL NOT NULL,
                    dry_run INTEGER NOT NULL DEFAULT 1,
                    screenshot_path TEXT,
                    field_mappings_json TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_applications_stage ON applications(stage);
                CREATE INDEX IF NOT EXISTS idx_applications_updated ON applications(updated_at DESC);
                """
            )

    # -------------------------------------------------------------
    # Raw Job Caching & Deduplication
    # -------------------------------------------------------------
    def save_raw_job(self, job_id: str, source: str, url: str, raw_hash: str, payload: Dict[str, Any]) -> None:
        """Stores a raw scraped payload to enable re-normalization without re-scraping."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO raw_scraped_jobs (id, source, url, raw_hash, payload_json, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        raw_hash = excluded.raw_hash,
                        payload_json = excluded.payload_json,
                        scraped_at = excluded.scraped_at
                    """,
                    (job_id, source, url, raw_hash, json.dumps(payload), now),
                )
        except Exception as e:
            logger.warning("save_raw_job_error", job_id=job_id, error=str(e))

    def is_content_seen(self, content_hash: str) -> bool:
        """Checks if this exact job posting hash has been seen previously."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM dedup_cache WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None

    def record_content_hash(self, content_hash: str, job_id: str) -> None:
        """Records a job hash into the deduplication cache."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO dedup_cache (content_hash, job_id, seen_at) VALUES (?, ?, ?)",
                (content_hash, job_id, now),
            )

    # -------------------------------------------------------------
    # Application State & Idempotency
    # -------------------------------------------------------------
    def is_job_applied_or_submitted(self, job_id: str) -> bool:
        """
        Idempotency check: returns True if an application has already been
        submitted or applied for this job, preventing duplicate submissions.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT stage FROM applications WHERE job_id = ? AND stage IN ('applied', 'submitted')",
                (job_id,),
            )
            return cursor.fetchone() is not None

    def save_or_update_application(self, app: ApplicationStatus, url: str = "", location: str = "") -> None:
        """Persists or updates an application's lifecycle record."""
        now = datetime.now(timezone.utc).isoformat()
        mappings_json = json.dumps([m.model_dump() for m in app.field_mappings]) if app.field_mappings else "[]"
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO applications (
                    job_id, company, title, location, url, stage, match_score,
                    dry_run, screenshot_path, field_mappings_json, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    stage = excluded.stage,
                    match_score = excluded.match_score,
                    dry_run = excluded.dry_run,
                    screenshot_path = COALESCE(excluded.screenshot_path, applications.screenshot_path),
                    field_mappings_json = excluded.field_mappings_json,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    app.job_id,
                    app.company,
                    app.title,
                    location,
                    url,
                    app.stage,
                    app.match_score,
                    1 if app.dry_run else 0,
                    app.screenshot_path,
                    mappings_json,
                    app.notes,
                    now,
                    now,
                ),
            )

    def get_application(self, job_id: str) -> Optional[ApplicationStatus]:
        """Retrieves an application by job_id."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_application(row)

    def list_applications(self, stage: Optional[str] = None, limit: int = 100) -> List[ApplicationStatus]:
        """Lists applications, optionally filtered by lifecycle stage."""
        with self._get_connection() as conn:
            if stage:
                cursor = conn.execute(
                    "SELECT * FROM applications WHERE stage = ? ORDER BY updated_at DESC LIMIT ?",
                    (stage, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM applications ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_application(row) for row in cursor.fetchall()]

    def get_counts(self) -> Dict[str, int]:
        """Returns aggregate metrics for dashboard stat cards."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT stage, COUNT(*) as cnt
                FROM applications
                GROUP BY stage
                """
            )
            counts = {row["stage"]: row["cnt"] for row in cursor.fetchall()}
            return {
                "matched": counts.get("matched", 0),
                "queued": counts.get("queued", 0),
                "needs_review": counts.get("needs_review", 0),
                "applied": counts.get("applied", 0),
                "submitted": counts.get("submitted", 0),
                "failed": counts.get("failed", 0),
                "rejected": counts.get("rejected", 0),
            }

    def _row_to_application(self, row: sqlite3.Row) -> ApplicationStatus:
        field_mappings_raw = row["field_mappings_json"]
        field_mappings = []
        if field_mappings_raw:
            try:
                parsed = json.loads(field_mappings_raw)
                field_mappings = [FieldMappingDecision(**item) for item in parsed]
            except Exception:
                field_mappings = []

        return ApplicationStatus(
            job_id=row["job_id"],
            company=row["company"],
            title=row["title"],
            stage=row["stage"],
            match_score=float(row["match_score"]),
            updated_at=row["updated_at"],
            dry_run=bool(row["dry_run"]),
            screenshot_path=row["screenshot_path"],
            field_mappings=field_mappings,
            notes=row["notes"],
        )


# Global storage instance
storage = JobStorage()
