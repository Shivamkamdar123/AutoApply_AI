"""
Central place for settings so nothing is hardcoded deep inside the app.
Reads from environment variables (see .env.example) with sane defaults
so the project still runs out of the box for local development.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500",
).split(",")

# A job below this score won't be marked as "recommended" on the dashboard.
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.30"))

SAMPLE_JOBS_FILE = DATA_DIR / "sample_jobs.json"
