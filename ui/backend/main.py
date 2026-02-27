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
    version="0.3.0",
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
        knowledge_dir_exists=settings.knowledge_dir.exists(),
        phases_config_exists=settings.phases_config.exists(),
    )


@app.get("/api/health/setup-status")
def setup_status():
    """Check onboarding setup completeness."""
    from .services.env_manager import read_env

    try:
        env_vals = read_env()
    except Exception:
        env_vals = {}

    project_path = env_vals.get("PROJECT_PATH", "")
    repo_configured = bool(project_path) and Path(project_path).is_dir()
    llm_configured = all(env_vals.get(k) for k in ("LLM_PROVIDER", "MODEL", "API_BASE"))

    # Check for input files in configured task input dir
    task_input_dir = settings.project_root / env_vals.get("TASK_INPUT_DIR", "task_inputs")
    try:
        has_input_files = task_input_dir.is_dir() and any(task_input_dir.iterdir())
    except Exception:
        has_input_files = False

    # Check run history
    try:
        has_run_history = settings.run_history.exists() and settings.run_history.stat().st_size > 0
    except Exception:
        has_run_history = False

    return {
        "repo_configured": repo_configured,
        "llm_configured": llm_configured,
        "has_input_files": has_input_files,
        "has_run_history": has_run_history,
    }


# Serve Angular static files in production
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist" / "dashboard"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
