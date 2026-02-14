# ============================================================
# AICodeGenCrew - Multi-Stage Docker Build
# PROPRIETARY: Source code only in build stage
# ============================================================

# ============================================================
# Stage 1: Build wheel (SOURCE CODE ONLY HERE)
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
COPY src/ src/
COPY config/ config/

RUN pip install --no-cache-dir build && \
    python -m build --wheel --outdir /dist

# ============================================================
# Stage 2: Runtime (NO SOURCE CODE)
# ============================================================
FROM python:3.12-slim AS runtime

LABEL maintainer="Aymen Mastouri" \
      description="AI Code Generation Crew - SDLC Automation" \
      license="Proprietary"

WORKDIR /app

# Install wheel + optional parsers (DOCX, Excel)
COPY --from=builder /dist/*.whl /tmp/
RUN WHEEL=$(ls /tmp/aicodegencrew-*.whl) && \
    pip install --no-cache-dir "${WHEEL}[parsers]" && \
    rm -rf /tmp/*.whl

# Copy config (non-sensitive, needed at runtime)
COPY --from=builder /build/config/ /app/config/

# Create working directories
RUN mkdir -p /app/inputs/tasks /app/inputs/requirements \
             /app/inputs/logs /app/inputs/reference \
             /app/knowledge /app/.cache

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["aicodegencrew"]
CMD ["--help"]
