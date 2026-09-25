"""
Persistent Storage & Idempotency Layer
======================================
Stores raw scraped jobs, normalized applications, review queue items, deduplication hashes,
multi-tenant user accounts, editable profiles, and versioned resume histories.
Implements SQLite with WAL (Write-Ahead Logging) for high concurrency and zero locks.

PostgreSQL Migration Path:
--------------------------
To migrate this module to PostgreSQL for cloud deployment:
1. Replace `sqlite3.connect` with an `asyncpg` or SQLAlchemy `AsyncSession` pool.
2. The schema below maps directly to Postgres DDL:
   - TEXT -> VARCHAR / TEXT
   - INTEGER -> BOOLEAN / INTEGER / BIGINT
   - REAL -> NUMERIC(5, 3)
   - TIMESTAMP -> TIMESTAMPTZ DEFAULT NOW()
3. The method signatures below (`save_or_update_application`, `get_profile`, etc.)
   remain identical, preserving calling code.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.exceptions import StorageError, UserAlreadyExistsError
from app.core.logging import get_logger
from app.models.schemas import (
    ApplicationStatus,
    FieldMappingDecision,
    ResumeItemResponse,
    UserProfileResponse,
    UserResponse,
)

logger = get_logger("storage")


class JobStorage:
    """
    Persistent multi-tenant repository for user accounts, profiles, resumes,
    job listings, raw scrape caches, and application lifecycles.
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
        """Creates the required tables and indexes if they do not exist, handling schema evolution."""
        with self._get_connection() as conn:
            # 1. User accounts table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")

            # 2. Editable User Profiles table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    full_name TEXT,
                    email TEXT,
                    phone TEXT,
                    linkedin_url TEXT,
                    github_url TEXT,
                    portfolio_url TEXT,
                    location TEXT,
                    desired_role TEXT,
                    desired_location TEXT,
                    remote_preference TEXT DEFAULT 'any',
                    skills_json TEXT DEFAULT '[]',
                    years_experience REAL,
                    bio TEXT,
                    active_resume_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # 3. Resumes metadata and history
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resumes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    raw_text TEXT,
                    uploaded_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);")

            # 4. Agent Status per user
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_status (
                    user_id TEXT PRIMARY KEY,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # 5. Password Reset tokens
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS password_resets (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pw_reset_user ON password_resets(user_id);")

            # 6. Raw scraped jobs & deduplication cache (global public cache)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_scraped_jobs (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    raw_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    scraped_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_jobs_source ON raw_scraped_jobs(source);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_jobs_hash ON raw_scraped_jobs(raw_hash);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dedup_cache (
                    content_hash TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    seen_at TEXT NOT NULL
                );
                """
            )

            # 7. Applications table with user_id multi-tenancy
            cursor = conn.execute("PRAGMA table_info(applications);")
            cols = [r["name"] for r in cursor.fetchall()]

            if not cols:
                # Fresh creation
                conn.execute(
                    """
                    CREATE TABLE applications (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL DEFAULT 'legacy_user',
                        job_id TEXT NOT NULL,
                        company TEXT NOT NULL,
                        title TEXT NOT NULL,
                        location TEXT,
                        url TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        match_score REAL NOT NULL,
                        dry_run INTEGER NOT NULL DEFAULT 1,
                        screenshot_path TEXT,
                        field_mappings_json TEXT,
                        notes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(user_id, job_id)
                    );
                    """
                )
            elif "user_id" not in cols:
                # Migrate existing table by renaming and recreating
                conn.execute("ALTER TABLE applications RENAME TO old_applications;")
                conn.execute(
                    """
                    CREATE TABLE applications (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL DEFAULT 'legacy_user',
                        job_id TEXT NOT NULL,
                        company TEXT NOT NULL,
                        title TEXT NOT NULL,
                        location TEXT,
                        url TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        match_score REAL NOT NULL,
                        dry_run INTEGER NOT NULL DEFAULT 1,
                        screenshot_path TEXT,
                        field_mappings_json TEXT,
                        notes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(user_id, job_id)
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT INTO applications (
                        id, user_id, job_id, company, title, location, url, stage, match_score,
                        dry_run, screenshot_path, field_mappings_json, notes, created_at, updated_at
                    ) SELECT 'legacy-' || job_id, 'legacy_user', job_id, company, title, location, url, stage, match_score,
                             dry_run, screenshot_path, field_mappings_json, notes, created_at, updated_at
                    FROM old_applications;
                    """
                )
                conn.execute("DROP TABLE old_applications;")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_user_stage ON applications(user_id, stage);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_user_updated ON applications(user_id, updated_at DESC);")

    # -------------------------------------------------------------
    # User Account Operations
    # -------------------------------------------------------------
    def create_user(self, email: str, password_hash: str, full_name: Optional[str] = None) -> UserResponse:
        """Registers a new user and returns their identity record."""
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        normalized_email = email.strip().lower()

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO users (id, email, password_hash, full_name, is_active, email_verified, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, 0, ?, ?)
                    """,
                    (user_id, normalized_email, password_hash, full_name, now, now),
                )
                # Seed blank initial profile for this user
                conn.execute(
                    """
                    INSERT INTO user_profiles (user_id, full_name, email, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, full_name, normalized_email, now, now),
                )
                # Seed agent status
                conn.execute(
                    """
                    INSERT INTO agent_status (user_id, is_active, updated_at)
                    VALUES (?, 0, ?)
                    """,
                    (user_id, now),
                )
        except sqlite3.IntegrityError as e:
            raise UserAlreadyExistsError(f"User with email '{normalized_email}' already exists.") from e

        return UserResponse(
            id=user_id,
            email=normalized_email,
            full_name=full_name,
            is_active=True,
            email_verified=False,
            created_at=now,
        )

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Retrieves user row by email for authentication verification."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Retrieves user row by id."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        """Updates user password hash."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, now, user_id),
            )
            return cursor.rowcount > 0

    def create_password_reset(self, token: str, user_id: str, expires_at: str) -> None:
        """Stores a password reset token."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO password_resets (token, user_id, expires_at, used) VALUES (?, ?, ?, 0)",
                (token, user_id, expires_at),
            )

    def get_password_reset(self, token: str) -> Optional[dict]:
        """Retrieves a reset token."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM password_resets WHERE token = ?", (token,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def mark_password_reset_used(self, token: str) -> None:
        """Marks a reset token as used."""
        with self._get_connection() as conn:
            conn.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))

    # -------------------------------------------------------------
    # User Profile Operations
    # -------------------------------------------------------------
    def get_profile(self, user_id: str) -> Optional[UserProfileResponse]:
        """Fetches the user's editable profile."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None

            skills = []
            if row["skills_json"]:
                try:
                    skills = json.loads(row["skills_json"])
                except Exception:
                    skills = []

            return UserProfileResponse(
                user_id=row["user_id"],
                full_name=row["full_name"],
                email=row["email"],
                phone=row["phone"],
                linkedin_url=row["linkedin_url"],
                github_url=row["github_url"],
                portfolio_url=row["portfolio_url"],
                location=row["location"],
                desired_role=row["desired_role"],
                desired_location=row["desired_location"],
                remote_preference=row["remote_preference"] or "any",
                skills=skills,
                years_experience=row["years_experience"],
                bio=row["bio"],
                active_resume_id=row["active_resume_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_or_create_profile(self, user_id: str, default_email: str = "", default_name: str = "") -> UserProfileResponse:
        """Returns existing profile or creates a default one if missing."""
        profile = self.get_profile(user_id)
        if profile:
            return profile

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_profiles (user_id, full_name, email, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, default_name, default_email, now, now),
            )
        return self.get_profile(user_id)  # type: ignore

    def save_or_update_profile(self, user_id: str, data: dict) -> UserProfileResponse:
        """Updates user profile fields and returns updated model."""
        now = datetime.now(timezone.utc).isoformat()
        existing = self.get_profile(user_id)
        
        # Build merge dictionary
        current_skills = existing.skills if existing else []
        skills_to_save = data.get("skills", current_skills)
        if skills_to_save is None:
            skills_to_save = current_skills

        fields = {
            "full_name": data.get("full_name", existing.full_name if existing else None),
            "email": data.get("email", existing.email if existing else None),
            "phone": data.get("phone", existing.phone if existing else None),
            "linkedin_url": data.get("linkedin_url", existing.linkedin_url if existing else None),
            "github_url": data.get("github_url", existing.github_url if existing else None),
            "portfolio_url": data.get("portfolio_url", existing.portfolio_url if existing else None),
            "location": data.get("location", existing.location if existing else None),
            "desired_role": data.get("desired_role", existing.desired_role if existing else None),
            "desired_location": data.get("desired_location", existing.desired_location if existing else None),
            "remote_preference": data.get("remote_preference", existing.remote_preference if existing else "any"),
            "skills_json": json.dumps(skills_to_save),
            "years_experience": data.get("years_experience", existing.years_experience if existing else None),
            "bio": data.get("bio", existing.bio if existing else None),
            "active_resume_id": data.get("active_resume_id", existing.active_resume_id if existing else None),
            "updated_at": now,
        }

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, full_name, email, phone, linkedin_url, github_url, portfolio_url,
                    location, desired_role, desired_location, remote_preference, skills_json,
                    years_experience, bio, active_resume_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    email = excluded.email,
                    phone = excluded.phone,
                    linkedin_url = excluded.linkedin_url,
                    github_url = excluded.github_url,
                    portfolio_url = excluded.portfolio_url,
                    location = excluded.location,
                    desired_role = excluded.desired_role,
                    desired_location = excluded.desired_location,
                    remote_preference = excluded.remote_preference,
                    skills_json = excluded.skills_json,
                    years_experience = excluded.years_experience,
                    bio = excluded.bio,
                    active_resume_id = excluded.active_resume_id,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    fields["full_name"],
                    fields["email"],
                    fields["phone"],
                    fields["linkedin_url"],
                    fields["github_url"],
                    fields["portfolio_url"],
                    fields["location"],
                    fields["desired_role"],
                    fields["desired_location"],
                    fields["remote_preference"],
                    fields["skills_json"],
                    fields["years_experience"],
                    fields["bio"],
                    fields["active_resume_id"],
                    existing.created_at if existing and existing.created_at else now,
                    now,
                ),
            )

        return self.get_profile(user_id)  # type: ignore

    # -------------------------------------------------------------
    # Resume History & Storage Operations
    # -------------------------------------------------------------
    def save_resume(
        self,
        resume_id: str,
        user_id: str,
        filename: str,
        storage_path: str,
        raw_text: str = "",
        make_active: bool = True,
    ) -> None:
        """Stores a parsed resume record, optionally setting it as active."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            if make_active:
                conn.execute("UPDATE resumes SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.execute(
                """
                INSERT INTO resumes (id, user_id, filename, storage_path, raw_text, uploaded_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (resume_id, user_id, filename, storage_path, raw_text, now, 1 if make_active else 0),
            )
            if make_active:
                conn.execute(
                    "UPDATE user_profiles SET active_resume_id = ?, updated_at = ? WHERE user_id = ?",
                    (resume_id, now, user_id),
                )

    def list_resumes(self, user_id: str) -> List[ResumeItemResponse]:
        """Lists all uploaded resume versions for this user."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, user_id, filename, uploaded_at, is_active FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC",
                (user_id,),
            )
            return [
                ResumeItemResponse(
                    id=row["id"],
                    user_id=row["user_id"],
                    filename=row["filename"],
                    uploaded_at=row["uploaded_at"],
                    is_active=bool(row["is_active"]),
                )
                for row in cursor.fetchall()
            ]

    def get_resume(self, resume_id: str, user_id: str) -> Optional[dict]:
        """Retrieves a single resume record ensuring tenant isolation."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM resumes WHERE id = ? AND user_id = ?",
                (resume_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_resume(self, resume_id: str, user_id: str) -> bool:
        """Deletes a resume record and cleans disk path."""
        resume = self.get_resume(resume_id, user_id)
        if not resume:
            return False

        path = Path(resume["storage_path"])
        if path.exists():
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("resume_file_delete_failed", path=str(path), error=str(e))

        with self._get_connection() as conn:
            conn.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user_id))
            # If deleted resume was active, set active_resume_id to null
            conn.execute(
                "UPDATE user_profiles SET active_resume_id = NULL WHERE user_id = ? AND active_resume_id = ?",
                (user_id, resume_id),
            )
        return True

    # -------------------------------------------------------------
    # Agent Running Status per user
    # -------------------------------------------------------------
    def get_agent_status(self, user_id: str) -> bool:
        """Returns whether the autonomous agent is active for this user."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT is_active FROM agent_status WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return bool(row["is_active"]) if row else False

    def set_agent_status(self, user_id: str, is_active: bool) -> bool:
        """Toggles or sets the agent active status for this user."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_status (user_id, is_active, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                (user_id, 1 if is_active else 0, now),
            )
        return is_active

    # -------------------------------------------------------------
    # Raw Job Caching & Deduplication (Global)
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
    # Application State & Idempotency (Multi-Tenant)
    # -------------------------------------------------------------
    def is_job_applied_or_submitted(self, job_id: str, user_id: str = "legacy_user") -> bool:
        """
        Idempotency check: returns True if an application has already been
        submitted or applied for this job for this user, preventing duplicate submissions.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT stage FROM applications WHERE user_id = ? AND job_id = ? AND stage IN ('applied', 'submitted')",
                (user_id, job_id),
            )
            return cursor.fetchone() is not None

    def save_or_update_application(
        self,
        app: ApplicationStatus,
        user_id: str = "legacy_user",
        url: str = "",
        location: str = "",
    ) -> None:
        """Persists or updates an application's lifecycle record scoped to user_id."""
        effective_user_id = app.user_id or user_id or "legacy_user"
        record_id = f"{effective_user_id}_{app.job_id}"
        now = datetime.now(timezone.utc).isoformat()
        mappings_json = (
            json.dumps([m.model_dump() for m in app.field_mappings]) if app.field_mappings else "[]"
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO applications (
                    id, user_id, job_id, company, title, location, url, stage, match_score,
                    dry_run, screenshot_path, field_mappings_json, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, job_id) DO UPDATE SET
                    company = excluded.company,
                    title = excluded.title,
                    location = CASE WHEN excluded.location != '' THEN excluded.location ELSE applications.location END,
                    url = CASE WHEN excluded.url != '' THEN excluded.url ELSE applications.url END,
                    stage = excluded.stage,
                    match_score = excluded.match_score,
                    dry_run = excluded.dry_run,
                    screenshot_path = COALESCE(excluded.screenshot_path, applications.screenshot_path),
                    field_mappings_json = excluded.field_mappings_json,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    record_id,
                    effective_user_id,
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

    def get_application(self, job_id: str, user_id: str = "legacy_user") -> Optional[ApplicationStatus]:
        """Retrieves an application by job_id for a specific user."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM applications WHERE user_id = ? AND job_id = ?",
                (user_id, job_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_application(row)

    def list_applications(
        self,
        user_id: str = "legacy_user",
        stage: Optional[str] = None,
        limit: int = 100,
    ) -> List[ApplicationStatus]:
        """Lists applications for a user, optionally filtered by stage."""
        with self._get_connection() as conn:
            if stage:
                cursor = conn.execute(
                    "SELECT * FROM applications WHERE user_id = ? AND stage = ? ORDER BY updated_at DESC LIMIT ?",
                    (user_id, stage, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM applications WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                    (user_id, limit),
                )
            return [self._row_to_application(row) for row in cursor.fetchall()]

    def get_counts(self, user_id: str = "legacy_user") -> Dict[str, int]:
        """Returns aggregate metrics for dashboard stat cards scoped to user_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT stage, COUNT(*) as cnt
                FROM applications
                WHERE user_id = ?
                GROUP BY stage
                """,
                (user_id,),
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
            user_id=row["user_id"] if "user_id" in row.keys() else None,
            dry_run=bool(row["dry_run"]),
            screenshot_path=row["screenshot_path"],
            field_mappings=field_mappings,
            notes=row["notes"],
        )


# Global storage instance
storage = JobStorage()
