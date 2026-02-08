"""Git repository manager for cloning/pulling remote repos.

Allows specifying a Git URL instead of a local PROJECT_PATH.
The repo is cloned into .cache/repos/<repo_name>/ and kept up-to-date.
"""

from __future__ import annotations

import getpass
import logging
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("aicodegencrew")


class GitRepoManager:
    """Clone or update a Git repository for local analysis.

    Args:
        repo_url: HTTPS Git URL (e.g. https://gitlab.example.com/team/project.git)
        branch: Branch name. Empty string = auto-detect default branch.
        cache_base: Base directory for cloned repos (default: .cache/repos).

    Submodules are always cloned/updated.
    """

    def __init__(
        self,
        repo_url: str,
        branch: str = "",
        cache_base: Path | None = None,
    ) -> None:
        self.repo_url = repo_url.strip()
        self._branch = branch.strip()
        self._cache_base = cache_base or Path(".cache/repos")
        self._username: str | None = None
        self._password: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def repo_name(self) -> str:
        """Extract repository name from URL (e.g. 'uvz' from '...uvz.git')."""
        path = urlparse(self.repo_url).path
        name = Path(path).stem  # strips .git
        return name or "repo"

    @property
    def clone_dir(self) -> Path:
        """Local directory where the repo is/will be cloned."""
        return self._cache_base / self.repo_name

    @property
    def branch(self) -> str:
        """Resolved branch name (auto-detected if not explicitly set)."""
        return self._branch

    def ensure_repo(self) -> Path:
        """Clone or update the repository. Returns the local path.

        - If clone_dir doesn't exist: prompts for credentials and clones.
        - If clone_dir exists: fetches and pulls the target branch.
        - If branch is empty: auto-detects the default branch first.
        """
        # Auto-detect default branch if not specified
        if not self._branch:
            self._branch = self._detect_default_branch()
            logger.info(f"[GIT] Auto-detected default branch: {self._branch}")

        if self.clone_dir.exists() and (self.clone_dir / ".git").exists():
            logger.info(f"[GIT] Updating existing clone: {self.clone_dir}")
            self._update_existing()
        else:
            logger.info(f"[GIT] Cloning {self.repo_url} -> {self.clone_dir}")
            self._clone_fresh()

        logger.info(f"[GIT] Repository ready at: {self.clone_dir}")
        return self.clone_dir

    # ------------------------------------------------------------------
    # Branch detection
    # ------------------------------------------------------------------

    def _detect_default_branch(self) -> str:
        """Detect the default branch via git ls-remote.

        Parses 'ref: refs/heads/main  HEAD' from ls-remote --symref output.
        Falls back to 'main' if detection fails.
        """
        try:
            url = self._build_authenticated_url() if self._username else self.repo_url
            result = self._run_git(
                ["ls-remote", "--symref", url, "HEAD"],
                cwd=None,
                capture=True,
            )
            # Parse: ref: refs/heads/main\tHEAD
            match = re.search(r"ref:\s+refs/heads/(\S+)\s+HEAD", result.stdout)
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"[GIT] Default branch detection failed: {e}")

        logger.info("[GIT] Falling back to 'main' as default branch")
        return "main"

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def _prompt_credentials(self) -> None:
        """Prompt for Git username and password via getpass."""
        logger.info("[GIT] Authentication required for repository access")
        self._username = input("Git username: ").strip()
        self._password = getpass.getpass("Git password/token: ")

    def _build_authenticated_url(self) -> str:
        """Insert credentials into the HTTPS URL (in-memory only).

        Example: https://user:token@gitlab.example.com/team/project.git
        """
        if not self._username or not self._password:
            return self.repo_url

        parsed = urlparse(self.repo_url)
        # Rebuild with credentials
        auth_url = (
            f"{parsed.scheme}://"
            f"{self._username}:{self._password}"
            f"@{parsed.hostname}"
        )
        if parsed.port:
            auth_url += f":{parsed.port}"
        auth_url += parsed.path
        return auth_url

    # ------------------------------------------------------------------
    # Clone / Update
    # ------------------------------------------------------------------

    def _clone_fresh(self) -> None:
        """Clone the repository from scratch."""
        # Ensure parent directory exists
        self._cache_base.mkdir(parents=True, exist_ok=True)

        # Clean up partial clone if it exists
        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir)

        # Try without credentials first, prompt on auth failure
        url = self.repo_url
        try:
            self._do_clone(url)
        except subprocess.CalledProcessError:
            logger.info("[GIT] Clone failed, trying with credentials...")
            self._prompt_credentials()
            url = self._build_authenticated_url()
            # Clean up partial clone from failed attempt
            if self.clone_dir.exists():
                shutil.rmtree(self.clone_dir)
            try:
                self._do_clone(url)
            except subprocess.CalledProcessError as e:
                # Clean up on final failure
                if self.clone_dir.exists():
                    shutil.rmtree(self.clone_dir)
                raise RuntimeError(
                    f"Git clone failed. Check URL and credentials.\n"
                    f"URL: {self.repo_url}\n"
                    f"Branch: {self._branch}\n"
                    f"Error: {self._sanitize(str(e))}"
                ) from None

    def _do_clone(self, url: str) -> None:
        """Execute the actual git clone command."""
        cmd = ["clone", "--recurse-submodules", "--branch", self._branch, url, str(self.clone_dir)]
        self._run_git(cmd, cwd=None)

    def _update_existing(self) -> None:
        """Fetch and pull latest changes for the target branch."""
        cwd = self.clone_dir

        try:
            self._run_git(["fetch", "--all", "--prune"], cwd=cwd)
        except subprocess.CalledProcessError:
            logger.info("[GIT] Fetch failed, trying with credentials...")
            self._prompt_credentials()
            url = self._build_authenticated_url()
            self._run_git(["remote", "set-url", "origin", url], cwd=cwd)
            self._run_git(["fetch", "--all", "--prune"], cwd=cwd)

        # Checkout and pull target branch
        self._run_git(["checkout", self._branch], cwd=cwd)
        self._run_git(["pull", "--ff-only"], cwd=cwd)
        self._run_git(["submodule", "update", "--init", "--recursive"], cwd=cwd)

        logger.info(f"[GIT] Updated to latest {self._branch}")

    # ------------------------------------------------------------------
    # Subprocess wrapper
    # ------------------------------------------------------------------

    def _run_git(
        self,
        args: list[str],
        cwd: Path | None,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command with sanitized logging.

        Sets GIT_TERMINAL_PROMPT=0 to prevent hanging on auth prompts.
        """
        cmd = ["git"] + args
        env_extra = {"GIT_TERMINAL_PROMPT": "0"}

        # Build env: inherit current env + our overrides
        import os
        env = {**os.environ, **env_extra}

        logger.debug(f"[GIT] Running: git {self._sanitize(' '.join(args))}")

        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 min timeout
        )

        if capture:
            return result

        if result.stdout.strip():
            logger.debug(f"[GIT] {self._sanitize(result.stdout.strip()[:200])}")

        return result

    def _sanitize(self, text: str) -> str:
        """Replace credentials in text with '***'."""
        sanitized = text
        if self._password:
            sanitized = sanitized.replace(self._password, "***")
        if self._username:
            sanitized = sanitized.replace(self._username, "***")
        return sanitized
