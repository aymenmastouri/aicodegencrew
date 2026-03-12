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

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aicodegencrew import __version__
from aicodegencrew.shared.utils.phase_state import configure_state_dir

from .config import settings
from .routers import collectors, diagrams, env, inputs, knowledge, logs, mcps, metrics, phases, pipeline, reports, reset, tasks, triage
from .schemas import HealthResponse

# Point phase_state at the project's logs/ dir so it resolves correctly
# regardless of the process CWD when uvicorn is started.
configure_state_dir(settings.logs_dir)

app = FastAPI(
    title="AICodeGenCrew Dashboard",
    description="SDLC Pipeline Dashboard API",
    version=__version__,
)

# CORS for Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    project_path = env_vals.get("PROJECT_PATH", "")
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
    task_input_dir = settings.project_root / env_vals.get("TASK_INPUT_DIR", "task_inputs")
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
