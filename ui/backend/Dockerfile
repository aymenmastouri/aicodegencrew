# =============================================================================
# SDLC Pilot Backend — Multi-Stage Docker Build
# =============================================================================
#
# Features:
#   - Python 3.12 + Node.js 22 LTS (MCP servers) + git (repo analysis)
#   - All dependencies from pyproject.toml (single source of truth)
#   - MCP packages pre-cached (no runtime downloads)
#   - Source compiled to bytecode (.pyc) — no .py in final image
#
# Build context: ui/backend/ (with src_bundle/ copied in by deploy.sh)
#
#   deploy.sh copies:
#     src/aicodegencrew/  →  ui/backend/src_bundle/
#     pyproject.toml      →  ui/backend/src_bundle/pyproject.toml
#
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: BUILD
# Install deps from pyproject.toml, compile .py → .pyc, strip source.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS build

WORKDIR /build

# System deps: curl (for Node.js setup), ca-certificates (TLS)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Node.js 22 LTS — needed to pre-cache MCP packages
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Pre-cache MCP package so npx doesn't download at runtime
RUN npx -y @modelcontextprotocol/server-sequential-thinking --help 2>/dev/null; exit 0

# Install ALL Python dependencies from pyproject.toml (single source of truth)
# install_deps.py extracts deps from pyproject.toml + adds server deps (uvicorn, fastapi)
COPY install_deps.py /tmp/install_deps.py
COPY src_bundle/pyproject.toml /tmp/pyproject.toml
RUN python3 /tmp/install_deps.py /tmp/pyproject.toml /tmp/deps.txt && \
    pip install --no-cache-dir --target=/build/deps -r /tmp/deps.txt

# Copy application code
COPY . /build/ui/backend/
COPY src_bundle/ /build/src/aicodegencrew/

# Compile Python to bytecode, remove .py source, flatten __pycache__
COPY compile_bytecode.py /tmp/compile_bytecode.py
RUN python /tmp/compile_bytecode.py /build/ui /build/src

# ---------------------------------------------------------------------------
# Stage 2: RUNTIME
# Minimal image: Python + Node.js + git. No build tools. Non-root user.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Node.js 22 LTS (MCP servers), git (repo analysis), curl (Node.js setup)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Non-root user (best practice: never run as root in production)
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Compiled bytecode + all Python dependencies
COPY --from=build /build/deps /usr/local/lib/python3.12/site-packages/
COPY --from=build /build/ui/backend/ /app/ui/backend/
COPY --from=build /build/src/aicodegencrew/ /app/src/aicodegencrew/

# Pre-cached MCP packages (no npx download at runtime)
COPY --from=build /root/.npm /home/appuser/.npm
RUN chown -R appuser:appuser /home/appuser/.npm

# Ensure __init__.pyc exists for all bytecode-only packages
COPY ensure_init.py /tmp/ensure_init.py
RUN python3 /tmp/ensure_init.py /app && rm /tmp/ensure_init.py

# Writable directories for runtime data
RUN mkdir -p /app/knowledge /app/logs /app/inputs /app/reports /app/config && \
    chown -R appuser:appuser /app

ENV PYTHONPATH=/app/src:/app
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8001

# Built-in healthcheck (defense-in-depth, works even without docker-compose)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')" || exit 1

# Run as non-root user
USER appuser

ENTRYPOINT ["python3", "-m", "uvicorn", "ui.backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
