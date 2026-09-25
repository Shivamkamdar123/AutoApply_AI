# AutoApply AI

An autonomous browser agent for intelligent, human-supervised job application automation.

This repo is organized so each piece of the pipeline is its own module — built, tested, and verifiable incrementally with strict production safeguards.

## Architecture & Module Layout

```
autoapply-ai/
├── backend/                             FastAPI service — the "brain" of the system
│   ├── app/
│   │   ├── main.py                      App entry point, CORS, and lifecycle
│   │   ├── config.py                    Settings validated via Pydantic (paths, keys, thresholds)
│   │   ├── core/
│   │   │   ├── logging.py               Structured logging (structlog) with correlation IDs
│   │   │   ├── exceptions.py            Typed domain exceptions hierarchy
│   │   │   └── security.py              Encrypted credentials manager (AES-128-CBC / Fernet)
│   │   ├── db/
│   │   │   └── storage.py               Persistent storage (SQLite WAL) & idempotency tracking
│   │   ├── models/
│   │   │   └── schemas.py               Shared Pydantic models for inputs/outputs
│   │   ├── services/
│   │   │   ├── resume_parser.py         Hardened resume parser (.pdf, .docx, .txt)
│   │   │   ├── matcher.py               TF-IDF + cosine similarity engine & embedding interface
│   │   │   ├── job_scraper.py           Multi-board scraper orchestrator
│   │   │   ├── scrapers/                Site-specific adapters (Greenhouse, Lever, Remotive, Sample)
│   │   │   │   ├── base.py              JobScraperAdapter, RateLimiter, RobotsChecker
│   │   │   │   ├── greenhouse.py        Greenhouse ATS board adapter
│   │   │   │   ├── lever.py             Lever ATS board adapter
│   │   │   │   ├── remotefeed.py        Remote developer feed adapter
│   │   │   │   └── sample.py            Offline fixture adapter
│   │   │   └── browser_agent.py         Playwright state-machine browser automation agent
│   │   ├── api/
│   │   │   └── routes.py                HTTP endpoints (upload, match, review queue, actions)
│   │   └── data/
│   │       ├── fixtures/                HTML form replay fixtures for CI testing
│   │       │   ├── standard_job_form.html
│   │       │   └── greenhouse_job_form.html
│   │       ├── screenshots/             Verification screenshots taken by the browser agent
│   │       └── sample_jobs.json         Offline job postings for local verification
│   ├── tests/                           Comprehensive test suite (37 tests)
│   │   ├── conftest.py                  Isolated database & resume fixtures
│   │   ├── test_resume_parser.py        Unit tests for parser & edge cases
│   │   ├── test_matcher.py              Unit tests for matcher & scoring
│   │   ├── test_job_scraper.py          Unit tests for scrapers & deduplication
│   │   ├── test_browser_agent.py        Playwright fixture-replay test harness
│   │   ├── test_storage.py              Unit tests for idempotency & storage
│   │   ├── test_api_routes.py           API integration tests
│   │   └── test_end_to_end_pipeline.py  Full autonomous pipeline integration test
│   └── requirements.txt                 Production dependencies
└── frontend/                            Dashboard (plain HTML/CSS/JS, no build step required)
    ├── index.html                       Console UI with Review Queue & Profile Bar
    ├── style.css                        Modern dark mode styles & responsive design
    └── app.js                           Live API client with fallback demo mode
```

## Running the Backend

```bash
cd backend
# Create virtual environment (if not already created)
python -m venv venv
# Activate virtual environment
source venv/bin/activate        # Windows: .\venv\Scripts\activate
# Install production & testing dependencies
pip install -r requirements.txt
# Install Playwright browser binary
playwright install chromium
# Run the FastAPI server
uvicorn app.main:app --reload --port 8000
```

## Running the Dashboard

Open `frontend/index.html` in any modern web browser.
- **Connected Mode**: When the backend is running on `http://localhost:8000`, the dashboard automatically connects to the live API, displays the active candidate profile, real-time match rankings, and pending review queue items.
- **Offline Demo Mode**: If the backend is not running, the dashboard gracefully switches to standalone demo mode with cached data so it remains fully presentable.

## Running the Test Suite

Run the full test suite across all 5 modules and the fixture-replay harness:

```bash
cd backend
.\venv\Scripts\pytest -v
```

## What's Real vs. Stubbed Right Now

| Module | Status | Production Implementation Details |
|---|---|---|
| **Resume Parser** | **Production Real** | Multi-column layout awareness via `pdfplumber`, scanned image PDF detection, non-English script validation, contact info and skill extraction, typed domain exceptions (`EmptyResumeError`, `ScannedImageResumeError`, etc.), 12 unit tests. |
| **Matcher** | **Production Real** | TF-IDF + n-gram vectorization with cosine similarity, weighted skill overlap bonus (60/40 balance), pluggable `SIMILARITY_ENGINE` ("tfidf" or "embedding"), documented scoring assumptions, 8 unit tests. |
| **Dashboard** | **Production Real** | Fully connected to live API (`USE_LIVE_API`), human-in-the-loop review queue for approving/rejecting drafted applications, drag-and-drop resume upload, loading/error/empty states, live decision log, polished dark theme. |
| **Job Scraper** | **Production Real** | Multi-adapter architecture (`JobScraperAdapter`) for Greenhouse, Lever, and public developer feeds, plus offline sample adapter; respectful crawl delay & backoff (`RateLimiter`), `robots.txt` compliance verification, raw payload caching in SQLite, cross-source content deduplication (`compute_job_hash`), 5 unit tests. |
| **Browser Agent** | **Production Real** | Playwright-powered autonomous state machine (`LOCATING_FORM` → `INSPECTING_FIELDS` → `MAPPING_FIELDS` → `FILLING_FORM` → `CAPTURING_SCREENSHOT` → `AWAITING_REVIEW`); explainable field mapping decisions with confidence scores & rationales; human-in-the-loop safety valve (dry-run mode by default, auto-submit requires explicit opt-in); persistent idempotency checks; HTML fixture-replay test harness. |

## Production & Safety Guarantees

1. **Human-in-the-Loop Safety Valve**: Auto-submit is `False` by default (`AUTO_SUBMIT_ENABLED=False`, `DRY_RUN=True`). The agent locates, maps, fills, and screenshots application forms, then halts at `AWAITING_REVIEW` for explicit user approval.
2. **Idempotency**: All job applications and content hashes are tracked in SQLite with WAL mode (`storage.is_job_applied_or_submitted()`), preventing duplicate applications across pipeline cycles. (Documented upgrade path to PostgreSQL available in `app/db/storage.py`).
3. **Structured Logging**: Configured via `structlog` with correlation IDs per agent run for forensic debugging and traceability.
4. **Secrets Handling**: Credentials and sensitive keys are encrypted locally using AES-128-CBC + HMAC-SHA256 (`LocalEncryptedSecretsManager`) with a clean interface for upgrading to HashiCorp Vault or cloud KMS.
5. **Fixture-Replay Testing**: Full browser automation testing runs against local HTML fixtures in CI without making unstable calls to live external websites.
