#!/bin/sh
# =============================================================================
# Docker Entrypoint for SDLC Pilot Backend
#
# Runs as root to fix bind-mount permissions, then drops to appuser via gosu.
# Named volumes (knowledge, logs, inputs, reports) are owned by root by default
# but accessible by appuser since Docker creates them with proper permissions.
# Only bind-mounts (config/, .env) need ownership fix.
# =============================================================================
set -e

# Fix ownership of bind-mounted files (host UID may differ from appuser)
chown -R appuser:appuser /app/config 2>/dev/null || true
chown appuser:appuser /app/.env /app/.env.example 2>/dev/null || true

# Drop privileges and exec the CMD
exec gosu appuser "$@"
