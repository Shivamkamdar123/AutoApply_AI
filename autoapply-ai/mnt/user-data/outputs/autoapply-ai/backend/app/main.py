"""
App entry point. Run with:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import ALLOWED_ORIGINS

app = FastAPI(
    title="AutoApply AI",
    description="Backend for the AutoApply AI job application agent.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok", "service": "AutoApply AI backend"}
