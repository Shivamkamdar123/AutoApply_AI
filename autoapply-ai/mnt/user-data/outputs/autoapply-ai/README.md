# AutoApply AI

An autonomous browser agent for intelligent job application automation.

This repo is organized so each piece of the pipeline is its own module — you can
build, test, and demo one stage at a time instead of needing the whole system
working before you see progress.

## Project layout

```
autoapply-ai/
├── backend/                 FastAPI service — the "brain" of the system
│   ├── app/
│   │   ├── main.py          App entry point, wires everything together
│   │   ├── config.py        Settings (paths, keys, thresholds)
│   │   ├── models/
│   │   │   └── schemas.py   Data shapes shared across the app (Pydantic)
│   │   ├── services/
│   │   │   ├── resume_parser.py   Resume file -> structured profile
│   │   │   ├── matcher.py         Profile + job -> match score
│   │   │   ├── job_scraper.py     Job board -> list of postings (stub)
│   │   │   └── browser_agent.py   Decides + performs form-filling actions (stub)
│   │   ├── api/
│   │   │   └── routes.py    HTTP endpoints the dashboard calls
│   │   └── data/
│   │       └── sample_jobs.json   Fake job postings for local testing
│   └── requirements.txt
└── frontend/                 The dashboard (plain HTML/CSS/JS, no build step)
    ├── index.html
    ├── style.css
    └── app.js
```

## Build order (recommended)

This mirrors the architecture diagram: build bottom-up in reliability order,
not top-down in pipeline order.

1. **Resume parser** (`services/resume_parser.py`) — fully working, no external
   dependencies beyond the parsing libraries. Test it on your own resume first.
2. **Matcher** (`services/matcher.py`) — fully working, uses TF-IDF similarity
   as a solid baseline. Swap in embeddings later if you want (see comments).
3. **Dashboard** (`frontend/`) — fully working against the sample data, so you
   always have something demoable even before the agent/browser layer exists.
4. **Job scraper** (`services/job_scraper.py`) — currently a stub returning
   sample data. This is where you plug in a real scraper per job site.
5. **Browser agent** (`services/browser_agent.py`) — currently a stub with the
   intended interface documented. This is the part that needs live iteration
   against real websites — build it last, and expect to rewrite it a few times.

## Running the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Running the dashboard

Just open `frontend/index.html` in a browser — it works standalone with
sample data. Once the backend is running on port 8000, it automatically
switches to live data (see `app.js`, `USE_LIVE_API`).

## What's real vs. stubbed right now

| Module | Status |
|---|---|
| Resume parser | Working — extracts skills, contact info, experience |
| Matcher | Working — TF-IDF + cosine similarity ranking |
| Dashboard | Working — full UI, sample data + live API support |
| Job scraper | Stub — returns sample data, real scraping not implemented |
| Browser agent | Stub — interface only, no live browser control yet |

Being upfront about this in your report/demo is a strength, not a weakness —
it shows you understand what's genuinely solved vs. what's still in progress.
