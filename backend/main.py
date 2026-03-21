"""
main.py
=======
FastAPI application entry point for GenSheet Drill.
Run from the backend/ directory:
    uvicorn main:app --reload --port 8000
"""
from datetime import datetime, timezone

from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of backend/), falling back to cwd
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv()  # also check cwd for local overrides

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import session as session_router
from routers import questions as questions_router
from cache import session_cache, question_cache

app = FastAPI(
    title="GenSheet Drill API",
    description="Victorian Curriculum Maths drill platform — Years 7-9",
    version="1.0.0",
)

# Allow all origins during development; Iteration 4 will tighten this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router.router)
app.include_router(questions_router.router)


@app.get("/api/health")
async def health():
    """Keep-alive endpoint — pinged by UptimeRobot every 14 min in production."""
    return {
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat(),
        "cache_size": session_cache.size() + question_cache.size(),
    }
