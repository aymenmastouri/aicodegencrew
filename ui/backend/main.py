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

from .config import settings
from .routers import diagrams, env, inputs, knowledge, logs, metrics, phases, pipeline, reports
from .schemas import HealthResponse

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


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        knowledge_dir_exists=settings.knowledge_dir.exists(),
        phases_config_exists=settings.phases_config.exists(),
    )


# Serve Angular static files in production
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist" / "dashboard"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
