"""Timeout wrapper for CrewAI crew.kickoff() calls.

crew.kickoff() blocks indefinitely when the LLM is unreachable (e.g. after
laptop sleep/wake causes network drop). This module provides a shared
timeout wrapper used by all crew classes to enforce a wall-clock limit.

Usage:
    from aicodegencrew.shared.utils.crew_timeout import kickoff_with_timeout
    result = kickoff_with_timeout(crew)
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

logger = logging.getLogger(__name__)

# Default 900s (15 min). Override via CREW_KICKOFF_TIMEOUT_SECONDS env var.
_KICKOFF_TIMEOUT_S: int = int(os.getenv("CREW_KICKOFF_TIMEOUT_SECONDS", "900"))


def kickoff_with_timeout(crew: Any, timeout: int | None = None, **kwargs: Any) -> Any:
    """Run crew.kickoff() with a wall-clock timeout.

    Args:
        crew: CrewAI Crew instance.
        timeout: Override timeout in seconds (default: CREW_KICKOFF_TIMEOUT_SECONDS or 900).
        **kwargs: Passed through to crew.kickoff() (e.g. inputs=...).

    Returns:
        The result of crew.kickoff().

    Raises:
        TimeoutError: If kickoff exceeds the timeout.
    """
    limit = timeout or _KICKOFF_TIMEOUT_S
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(crew.kickoff, **kwargs)
    try:
        return future.result(timeout=limit)
    except FuturesTimeoutError:
        # shutdown(wait=False) so we don't block waiting for the stuck thread.
        # The orphaned thread will die when the process exits.
        pool.shutdown(wait=False, cancel_futures=True)
        logger.error(
            "crew.kickoff() timed out after %ds (LLM unreachable?). "
            "Set CREW_KICKOFF_TIMEOUT_SECONDS env var to adjust.",
            limit,
        )
        raise TimeoutError(
            f"Crew execution timed out after {limit}s. "
            f"The LLM may be unreachable (network drop after sleep?)."
        )
    finally:
        # Normal path: wait for cleanup. Timeout path: already shut down above.
        pool.shutdown(wait=False)
