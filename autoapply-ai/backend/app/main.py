"""
App entry point. Run with:
    uvicorn app.main:app --reload --port 8000
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import auth_router
from app.api.routes import router
from app.config import ALLOWED_ORIGINS

app = FastAPI(
    title="AutoApply AI",
    description="Multi-tenant backend for the AutoApply AI autonomous job application agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok", "service": "AutoApply AI backend", "version": "1.0.0"}


# Mount frontend static directory if available for single-container / unified deployments
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
