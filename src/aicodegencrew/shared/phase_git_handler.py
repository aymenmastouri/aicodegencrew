"""Git handler for knowledge/ auto-commit after each pipeline phase.

Extracted from SDLCOrchestrator._git_commit_after_phase (BUG-C5).
Encapsulates all git subprocess logic so the orchestrator stays clean.

Environment guard:
    CODEGEN_COMMIT_KNOWLEDGE=false  — disable auto-commits (default: enabled)
"""

import os
import subprocess
from datetime import datetime

from .utils.logger import logger


class PhaseGitHandler:
    """
    Commits the knowledge/ directory to git after each phase.

    Stages knowledge/ and creates a timestamped commit message.
    Silently skips if:
    - CODEGEN_COMMIT_KNOWLEDGE=false
    - Not a git repository
    - git is not installed
    - No staged changes

    Usage::

        handler = PhaseGitHandler()
        handler.commit_knowledge("plan")
    """

    def commit_knowledge(self, phase_id: str) -> bool:
        """Stage knowledge/ and git commit. Returns True if committed.

        Args:
            phase_id: The completed phase ID (used in commit message).

        Returns:
            True if a commit was created, False otherwise.
        """
        if os.getenv("CODEGEN_COMMIT_KNOWLEDGE", "true").lower() in ("false", "0", "no"):
            logger.debug("[PhaseGitHandler] CODEGEN_COMMIT_KNOWLEDGE=false — skipping knowledge/ commit")
            return False

        try:
            # Guard: check if we're inside a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.debug("[PhaseGitHandler] Not a git repository, skipping commit")
                return False

            # Stage knowledge/ directory
            subprocess.run(
                ["git", "add", "knowledge/"],
                capture_output=True,
                check=True,
            )

            # Check if there are staged changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True,
            )
            if result.returncode == 0:
                logger.debug("[PhaseGitHandler] No changes to commit")
                return False

            # Commit with descriptive message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"[aicodegencrew] {phase_id} completed - {timestamp}"

            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                check=True,
            )

            logger.info("[PhaseGitHandler] Git commit: %s", commit_msg)
            return True

        except subprocess.CalledProcessError as e:
            logger.warning("[PhaseGitHandler] Git commit failed: %s", e)
            return False
        except FileNotFoundError:
            logger.debug("[PhaseGitHandler] Git not found, skipping commit")
            return False
