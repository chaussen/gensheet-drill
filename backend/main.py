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

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from routers import session as session_router  # noqa: E402
from routers import questions as questions_router  # noqa: E402
from routers import progress as progress_router  # noqa: E402
from cache import session_cache, question_cache  # noqa: E402
from config.tiers import get_tier_config  # noqa: E402
from models.schemas import TierConfigResponse  # noqa: E402
import analytics  # noqa: E402

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
app.include_router(progress_router.router)


_FRONTEND_DIST = Path(__file__).parent / "static"

if _FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="assets",
    )


@app.get("/api/config/limits", response_model=TierConfigResponse)
async def get_limits():
    """Return usage limits for the current tier (always 'free' until subscriptions are added)."""
    return get_tier_config()


@app.head("/api/health", include_in_schema=False)
async def health_head():
    """Explicit HEAD handler for UptimeRobot (free tier only supports HEAD)."""
    return Response(status_code=200)


@app.get("/api/health")
async def health():
    """Keep-alive endpoint — pinged by UptimeRobot every 14 min in production."""
    return {
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat(),
        "cache_size": session_cache.size() + question_cache.size(),
    }


@app.get("/api/stats")
async def get_stats():
    """
    Return in-memory usage counters since the last redeploy.
    For historical data, filter Render logs by the 'event' field.
    """
    return analytics.get_stats()


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Serve index.html for all non-API paths (React SPA routing)."""
    index = _FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"error": "frontend not built"}, status_code=503)
