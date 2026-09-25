# AutoApply AI — Autonomous Human-Supervised Job Application Agent

AutoApply AI is a production-grade, multi-tenant autonomous job application agent that pairs multi-source job board aggregation with a Playwright browser automation state machine.

Built with an uncompromising **human-in-the-loop safety valve**, AutoApply AI maps, fills, and screenshots application forms, then halts at `AWAITING_REVIEW` with explainable field-mapping decisions (confidence scores + rationales) for human approval before anything is ever submitted.

---

## Architecture & Module Layout

```
autoapply-ai/
├── docker-compose.yml                   Orchestrates backend, frontend, and persistent volumes
├── SECURITY.md                          Security policies, encryption model & KMS upgrade path
├── backend/                             FastAPI service — the multi-tenant "brain"
│   ├── Dockerfile                       Multi-stage container with Python 3.12 & Playwright Chromium
│   ├── app/
│   │   ├── main.py                      FastAPI app, CORS, auth/api routers, and static file mount
│   │   ├── config.py                    Pydantic Settings (JWT, secrets, CORS origins, thresholds)
│   │   ├── core/
│   │   │   ├── logging.py               Structured logging (structlog) with correlation IDs & zero PII
│   │   │   ├── exceptions.py            Typed domain exceptions hierarchy (Auth, Parse, Scrape, Browser)
│   │   │   └── security.py              Bcrypt hashing, JWT generation, and Fernet SecretsManager
│   │   ├── db/
│   │   │   └── storage.py               Multi-tenant SQLite (WAL mode) with user_id foreign keys
│   │   ├── models/
│   │   │   └── schemas.py               Shared Pydantic models (Auth, Profiles, Resumes, Jobs, Queue)
│   │   ├── services/
│   │   │   ├── resume_parser.py         Hardened resume parser (.pdf, .docx, .txt) with layout awareness
│   │   │   ├── matcher.py               TF-IDF + cosine similarity engine & weighted skill overlap
│   │   │   ├── job_scraper.py           Multi-board scraper orchestrator with health telemetry
│   │   │   ├── cover_letter.py          Tailored application notes (Anthropic Claude + heuristic fallback)
│   │   │   ├── scrapers/                Site-specific adapters with robots.txt & crawl-delay checks
│   │   │   │   ├── base.py              JobScraperAdapter, RateLimiter, RobotsChecker
│   │   │   │   ├── greenhouse.py        Greenhouse ATS board adapter
│   │   │   │   ├── lever.py             Lever ATS board adapter
│   │   │   │   ├── remotefeed.py        Remotive developer feed adapter
│   │   │   │   ├── remoteok.py          RemoteOK live board adapter
│   │   │   │   └── sample.py            Offline fixture replay adapter
│   │   │   └── browser_agent.py         Playwright state-machine agent with namespaced screenshots
│   │   ├── api/
│   │   │   ├── auth.py                  Signup, login, logout, me, refresh, password reset endpoints
│   │   │   └── routes.py                Multi-tenant routes (profile, resumes, jobs, review queue)
│   │   └── data/
│   │       ├── fixtures/                HTML form replay fixtures for CI testing
│   │       ├── screenshots/             Per-user namespaced form verification snapshots
│   │       ├── resumes/                 Per-user versioned resume storage
│   │       └── sample_jobs.json         Offline job postings for local verification
│   ├── tests/                           Comprehensive test suite (54 tests, 100% pass rate)
│   │   ├── conftest.py                  Isolated DB, test candidate fixtures, and JWT auth headers
│   │   ├── test_auth.py                 Auth tests (signup, login, duplicates, tokens, rate limits)
│   │   ├── test_profile.py              Profile CRUD, optional fields, and resume versioning tests
│   │   ├── test_resume_parser.py        Unit tests for parser, multi-column layout, and edge cases
│   │   ├── test_matcher.py              Unit tests for matcher & scoring
│   │   ├── test_job_scraper.py          Unit tests for scrapers, RemoteOK, and deduplication
│   │   ├── test_browser_agent.py        Playwright fixture-replay test harness
│   │   ├── test_storage.py              Unit tests for tenant isolation, idempotency & storage
│   │   ├── test_api_routes.py           API integration & multi-tenant cross-account isolation tests
│   │   └── test_end_to_end_pipeline.py  Full autonomous pipeline integration test
│   └── requirements.txt                 Production dependencies
├── frontend/                            Split frontend app shell (No build step required)
│   ├── index.html                       Public landing page with safety model pitch & hero terminal
│   ├── login.html                       Authentication portal (Sign In, Create Account, Reset Password)
│   ├── dashboard.html                   Protected dashboard (Search filters, metrics, pipeline, review queue)
│   ├── profile.html                     Dedicated profile & settings page (Editable fields, skills, resumes)
│   ├── style.css                        Modern dark-mode CSS design system with responsive layouts
│   ├── app.js                           Centralized auth client, client router, and API orchestrator
│   └── server.py                        Local development server (port 5500)
└── .github/workflows/
    └── ci.yml                           GitHub Actions workflow executing pytest on Python 3.12
```

---

## What's Real vs. Stubbed (Honesty Table)

| Module | Status | Production Implementation Details |
|---|---|---|
| **Authentication & Accounts** | **Production Real** | Secure signup, login, session validation (`/api/auth/me`), token refresh, and password reset. Password hashing via salted `bcrypt`. Stateless JWT access tokens + refresh tokens. Tenant-gated dependency (`get_current_user`). Rate-limited endpoints. |
| **Multi-Tenant Isolation** | **Production Real** | Foreign key `user_id` on all entities (`applications`, `user_profiles`, `resumes`, `agent_status`). Strict tenant filtering on all queries (`WHERE user_id = :user_id`). User A cannot access User B's applications or review queue (verified in CI). |
| **Editable Profile & Settings** | **Production Real** | Full CRUD on `user_profiles` (`GET`/`PATCH /api/profile`). All fields optional: personal contact info, LinkedIn/GitHub/portfolio URLs, target role, desired location, remote preference, years experience, bio, and interactive skills tag editor. |
| **Resume Parser & Versioning** | **Production Real** | Multi-column layout awareness via `pdfplumber`, scanned PDF detection, script filtering, skill & contact extraction. Resumes stored in user directories (`data/resumes/{user_id}/`) with history and version management. |
| **Job Matcher** | **Production Real** | TF-IDF + n-gram vectorization with cosine similarity and weighted skill overlap bonus. Pluggable `SIMILARITY_ENGINE` interface. Dynamic query and location filtering from dashboard inputs. |
| **Job Scrapers** | **Production Real** | Adapters for Greenhouse, Lever, Remotive, and RemoteOK + offline sample fallback. Respects `robots.txt`, implements exponential backoff rate limiting, SHA-256 content deduplication, and returns real-time per-source health telemetry (`sources_status`). |
| **Browser Agent & Review Queue** | **Production Real** | Playwright state machine (`LOCATING_FORM → INSPECTING_FIELDS → MAPPING_FIELDS → FILLING_FORM → CAPTURING_SCREENSHOT → AWAITING_REVIEW`). Unconditionally halts at `AWAITING_REVIEW` with explainable per-field confidence rationales and high-resolution form snapshots. `DRY_RUN=True` and `AUTO_SUBMIT_ENABLED=False` hardcoded defaults. |
| **Cover Letter Generator** | **Production Real** | Generates personalized application notes per job using candidate profile & job requirements. Supports Anthropic Claude (`claude-3-haiku-20240307`) with deterministic rule-based heuristic fallback. |

---

## Quickstart: Running Locally

### 1. Backend Service

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\activate            # Linux/macOS: source venv/bin/activate

# Install dependencies & Playwright Chromium
pip install -r requirements.txt
playwright install chromium

# Copy environment template
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Development Server

In a second terminal:

```bash
cd frontend
python server.py
```
Open **http://127.0.0.1:5500/** in your browser:
- Landing Page: `http://127.0.0.1:5500/index.html`
- Sign In / Sign Up: `http://127.0.0.1:5500/login.html`
- Protected Dashboard: `http://127.0.0.1:5500/dashboard.html`
- Profile & Settings: `http://127.0.0.1:5500/profile.html`

---

## Quickstart: Docker Compose

Bring up the complete production-ready stack with one command:

```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:5500`
- Backend API & Docs: `http://localhost:8000/docs`

---

## Running the Test Suite

Execute all 54 tests spanning unit tests, integration tests, and Playwright fixture-replay browser automation:

```bash
cd backend
.\venv\Scripts\pytest -v
```

All 54 tests pass synchronously:
```
tests/test_api_routes.py::test_root_endpoint PASSED
tests/test_api_routes.py::test_match_jobs_endpoint PASSED
tests/test_api_routes.py::test_dashboard_summary_endpoint PASSED
tests/test_api_routes.py::test_review_queue_and_action PASSED
tests/test_api_routes.py::test_resume_upload_and_parse_endpoint PASSED
tests/test_api_routes.py::test_agent_toggle_endpoint PASSED
tests/test_api_routes.py::test_multi_tenant_data_isolation PASSED
tests/test_auth.py::test_signup_success PASSED
tests/test_auth.py::test_signup_duplicate_email PASSED
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_invalid_password PASSED
tests/test_auth.py::test_login_nonexistent_email PASSED
tests/test_auth.py::test_get_current_user_me PASSED
tests/test_auth.py::test_unauthorized_access_no_token PASSED
tests/test_auth.py::test_unauthorized_access_invalid_token PASSED
tests/test_auth.py::test_refresh_token_flow PASSED
tests/test_auth.py::test_forgot_password_flow PASSED
tests/test_auth.py::test_reset_password_flow PASSED
tests/test_profile.py::test_get_profile_defaults PASSED
tests/test_profile.py::test_patch_profile_fields PASSED
tests/test_profile.py::test_patch_profile_optional_nulls PASSED
tests/test_profile.py::test_resume_upload_populates_profile_and_history PASSED
tests/test_profile.py::test_delete_resume_version PASSED
tests/test_browser_agent.py::... PASSED (Playwright state machine tests)
tests/test_end_to_end_pipeline.py::test_end_to_end_autonomous_pipeline PASSED
```

---

## Security & Safety Commitments

1. **Human-in-the-Loop Safety Valve**: Forms are verified in dry-run mode and require human confirmation in the Review Queue. Auto-submit requires explicit per-action user opt-in (`auto_submit_override=True`).
2. **Multi-Tenant Protection**: Strict foreign-key scoping prevents cross-account data leaks.
3. **Encrypted Secrets**: Local secrets encrypted via AES-128-CBC / Fernet with PBKDF2 derivation. Production requires explicit keys and fails startup if defaults are detected.
4. **Zero PII Logging**: All logs pass through structured loggers with PII suppression.
