"""
SDLC Dashboard - FastAPI Backend
=================================
Serves the Angular frontend and provides REST API for:
- Phase configuration and status
- Knowledge base browsing
- Metrics and log viewing
- Development plans and codegen reports
- Diagram browsing

Usage:
    uvicorn ui.backend.main:app --reload --port 8001
"""

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

from aicodegencrew import __version__
from aicodegencrew.shared.utils.phase_state import configure_state_dir

from .config import settings
from .routers import collectors, diagrams, env, inputs, knowledge, logs, mcps, metrics, phases, pipeline, reports, reset, tasks, triage
from .schemas import HealthResponse

# Point phase_state at the project's logs/ dir so it resolves correctly
# regardless of the process CWD when uvicorn is started.
configure_state_dir(settings.logs_dir)

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup and graceful shutdown."""
    logger.info("SDLC Pilot Backend v%s starting...", __version__)

    # B3: Auto-cleanup zombie runs from previous server lifecycle.
    # phase_state.json may contain "running" phases from a process that died.
    # read_all_phases() already performs PID-liveness crash recovery.
    try:
        from .services.pipeline_executor import PipelineExecutor
        executor = PipelineExecutor()
        if executor.state == "running":
            # Server restarted while pipeline was "running" — mark as failed
            logger.warning("Zombie pipeline detected at startup (state=running). Resetting to idle.")
            executor.state = "idle"
            executor.current_run = None
        # Also trigger phase_state.json crash recovery
        from aicodegencrew.shared.utils.phase_state import read_all_phases
        recovered = read_all_phases()
        if any(p.get("status") == "failed" and p.get("error", "").startswith("Process terminated")
               for p in recovered.get("phases", {}).values()):
            logger.info("Recovered stale 'running' phases from phase_state.json at startup.")
    except Exception as exc:
        logger.warning("Startup zombie cleanup failed (non-fatal): %s", exc)

    yield
    # Shutdown: stop any running pipeline gracefully
    logger.info("Shutting down — stopping running pipelines...")
    try:
        from .services.pipeline_executor import PipelineExecutor
        executor = PipelineExecutor()
        if executor.state == "running":
            executor.cancel()
            logger.info("Pipeline cancelled.")
    except Exception:
        pass
    logger.info("Shutdown complete.")


app = FastAPI(
    title="AICodeGenCrew Dashboard",
    description="SDLC Pipeline Dashboard API",
    version=__version__,
    lifespan=lifespan,
)

# CORS for Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# ---------------------------------------------------------------------------
# In-memory rate limiter for expensive/destructive endpoints (H4)
# ---------------------------------------------------------------------------
_RATE_LIMIT_MAX = 5  # max requests per window
_RATE_LIMIT_WINDOW = 60  # seconds

# Paths subject to rate limiting
_RATE_LIMITED_PATHS: set[str] = {
    "/api/pipeline/run",
    "/api/triage",
    "/api/reset/all",
}

# key = (client_ip, path) -> list of timestamps
_rate_limit_log: dict[tuple[str, str], list[float]] = defaultdict(list)


_MAX_BODY_SIZE = 25 * 1024 * 1024  # 25 MB — matches nginx client_max_body_size


@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_BODY_SIZE:
        return JSONResponse(status_code=413, content={"detail": "Request body too large (max 25 MB)."})
    return await call_next(request)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "POST" and request.url.path in _RATE_LIMITED_PATHS:
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, request.url.path)
        now = time.monotonic()
        # Prune entries outside the window
        timestamps = _rate_limit_log[key]
        _rate_limit_log[key] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(_rate_limit_log[key]) >= _RATE_LIMIT_MAX:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
        _rate_limit_log[key].append(now)
    return await call_next(request)


# Register routers
app.include_router(phases.router)
app.include_router(knowledge.router)
app.include_router(metrics.router)
app.include_router(reports.router)
app.include_router(logs.router)
app.include_router(diagrams.router)
app.include_router(pipeline.router)
app.include_router(env.router)
app.include_router(inputs.router)
app.include_router(collectors.router)
app.include_router(reset.router)
app.include_router(mcps.router)  # MCP Registry
app.include_router(triage.router)
app.include_router(tasks.router)


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=__version__,
        knowledge_dir_exists=settings.knowledge_dir.exists(),
        phases_config_exists=settings.phases_config.exists(),
    )


@app.get("/api/health/setup-status")
def setup_status():
    """Check onboarding setup completeness with explicit error reasons.

    The UI can use the boolean flags for quick checks and the 'errors' list
    to surface concrete misconfigurations to the user.
    """
    from .services.env_manager import read_env

    errors: list[str] = []

    try:
        env_vals = read_env()
    except Exception as exc:  # pragma: no cover - defensive guardrail
        env_vals = {}
        errors.append(f"Failed to read .env: {exc}")

    # Prefer os.environ (set by docker-compose) over .env file value
    project_path = os.environ.get("PROJECT_PATH") or env_vals.get("PROJECT_PATH", "")
    repo_configured = bool(project_path) and Path(project_path).is_dir()
    if not repo_configured:
        errors.append(
            "PROJECT_PATH is not configured or does not point to an existing directory.",
        )

    llm_configured = all(env_vals.get(k) for k in ("LLM_PROVIDER", "MODEL", "API_BASE"))
    if not llm_configured:
        missing = [k for k in ("LLM_PROVIDER", "MODEL", "API_BASE") if not env_vals.get(k)]
        errors.append(f"Missing LLM configuration: {', '.join(missing)}.")

    # Check for input files in configured task input dir
    task_input_dir = settings.project_root / env_vals.get("TASK_INPUT_DIR", "inputs/tasks")
    try:
        has_input_files = task_input_dir.is_dir() and any(task_input_dir.iterdir())
    except Exception as exc:  # pragma: no cover - defensive guardrail
        has_input_files = False
        errors.append(f"Failed to inspect TASK_INPUT_DIR='{task_input_dir}': {exc}")

    # Check run history
    try:
        has_run_history = settings.run_history.exists() and settings.run_history.stat().st_size > 0
    except Exception as exc:  # pragma: no cover - defensive guardrail
        has_run_history = False
        errors.append(f"Failed to read run history file '{settings.run_history}': {exc}")

    return {
        "repo_configured": repo_configured,
        "llm_configured": llm_configured,
        "has_input_files": has_input_files,
        "has_run_history": has_run_history,
        "errors": errors,
    }


# Serve Angular static files in production
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist" / "dashboard"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
