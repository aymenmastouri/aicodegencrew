"""Service for reading log files."""

from ..config import settings
from ..schemas import LogResponse


def read_log(filename: str = "current.log", tail: int = 200) -> LogResponse:
    """Read the last N lines of a log file."""
    log_path = settings.logs_dir / filename

    # Security: prevent path traversal — resolve strict=True to reject
    # symlinks and TOCTOU races (the path must exist and be real).
    base_resolved = settings.logs_dir.resolve()
    try:
        resolved = log_path.resolve(strict=True)
    except OSError:
        return LogResponse(lines=[], total_lines=0, file_path=str(log_path))
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError("Path traversal not allowed")

    with open(resolved, encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    total = len(all_lines)
    lines = [line.rstrip("\n") for line in all_lines[-tail:]]

    return LogResponse(lines=lines, total_lines=total, file_path=str(log_path))


def list_log_files() -> list[str]:
    """List available log files."""
    if not settings.logs_dir.exists():
        return []
    return sorted(f.name for f in settings.logs_dir.iterdir() if f.is_file() and f.suffix == ".log")
