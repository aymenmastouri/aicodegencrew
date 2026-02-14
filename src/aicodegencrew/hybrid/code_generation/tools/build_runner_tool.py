"""
Build Runner Tool - Run build commands per container.

Reuses container detection, build command derivation, and subprocess handling
from Stage 4b (Build Verifier). Supports Gradle, Maven, npm/Angular with
Windows/Unix compatibility.
"""

import json
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import truncate_response

logger = setup_logger(__name__)

IS_WINDOWS = platform.system() == "Windows"
BUILD_TIMEOUT = 600  # seconds


@dataclass
class ContainerConfig:
    """Build configuration for a target-repo container."""

    container_id: str
    name: str
    root_path: str
    build_cwd: str
    build_command: str
    build_tool: str
    timeout: int = BUILD_TIMEOUT


def _detect_containers(repo_path: Path, facts_path: Path) -> list[ContainerConfig]:
    """Auto-detect buildable containers from architecture_facts.json."""
    containers: list[dict] = []
    if facts_path.exists():
        try:
            with open(facts_path, encoding="utf-8") as f:
                facts = json.load(f)
            containers = facts.get("containers", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[BuildRunner] Could not read architecture_facts: {e}")
            return []

    configs: list[ContainerConfig] = []
    skip_types = {"test", "e2e"}

    for container in containers:
        cid = container.get("id", "")
        ctype = container.get("type", "")
        root = container.get("root_path", "").replace("\\", "/").strip("/")

        if ctype in skip_types or "e2e" in cid.lower():
            continue

        meta = container.get("metadata", {})
        build_tool = meta.get("build_system", "")

        if not build_tool:
            continue

        build_cmd = _derive_build_command(build_tool, repo_path, root)
        if not build_cmd:
            continue

        configs.append(ContainerConfig(
            container_id=cid,
            name=container.get("name", root),
            root_path=root + "/",
            build_cwd=root,
            build_command=build_cmd,
            build_tool=build_tool,
        ))

    return configs


def _derive_build_command(build_tool: str, repo_path: Path, container_root: str) -> str:
    """Derive the shell build command from build tool type + disk scan."""
    build_dir = repo_path / container_root

    if build_tool == "gradle":
        has_wrapper = (build_dir / "gradlew").exists() or (build_dir / "gradlew.bat").exists()
        if has_wrapper:
            if IS_WINDOWS:
                return r".\gradlew.bat clean build --info"
            return "./gradlew clean build --info"
        return "gradle clean build --info"

    elif build_tool == "maven":
        has_wrapper = (build_dir / "mvnw").exists() or (build_dir / "mvnw.cmd").exists()
        if has_wrapper:
            if IS_WINDOWS:
                return r".\mvnw.cmd clean compile"
            return "./mvnw clean compile"
        return "mvn clean compile"

    elif build_tool == "npm":
        pkg_path = build_dir / "package.json"
        if pkg_path.exists():
            try:
                with open(pkg_path, encoding="utf-8") as f:
                    pkg = json.load(f)
                scripts = pkg.get("scripts", {})
                for script_name in ("build:cap-ci", "build:prod", "build"):
                    if script_name in scripts:
                        return f"npm run {script_name}"
            except (json.JSONDecodeError, OSError):
                pass
        if (build_dir / "angular.json").exists():
            return "npx ng build"
        return ""

    return ""


def _run_build(build_command: str, build_dir: Path, timeout: int) -> tuple[int, str]:
    """Run build command via shell. Returns (exit_code, combined_output)."""
    if not build_dir.exists():
        msg = f"Build directory not found: {build_dir}"
        logger.error(f"[BuildRunner] {msg}")
        return -1, msg

    try:
        result = subprocess.run(
            build_command,
            cwd=str(build_dir),
            capture_output=True,
            timeout=timeout,
            shell=True,
        )
        stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        output = stdout + "\n" + stderr
        return result.returncode, output.strip()
    except FileNotFoundError:
        msg = f"Build tool not found for: {build_command}"
        logger.error(f"[BuildRunner] {msg}")
        return -1, msg
    except subprocess.TimeoutExpired:
        msg = f"Build timed out after {timeout}s"
        logger.error(f"[BuildRunner] {msg}")
        return -1, msg
    except Exception as e:
        msg = f"Build error: {e}"
        logger.error(f"[BuildRunner] {msg}")
        return -1, msg


class BuildRunnerInput(BaseModel):
    """Input schema for BuildRunnerTool."""

    container_id: str = Field(
        ..., description="Container ID from architecture facts (e.g. 'container.backend')"
    )
    baseline: bool = Field(
        default=False,
        description="If True, run a baseline build WITHOUT any staged files applied",
    )


class BuildRunnerTool(BaseTool):
    """
    Run build commands for a specific container in the target repository.

    Auto-detects build system (Gradle, Maven, npm/Angular) from architecture
    facts and disk scan. Supports Windows and Unix.

    Usage Examples:
    1. run_build(container_id="container.backend")
    2. run_build(container_id="container.frontend", baseline=True)
    """

    name: str = "run_build"
    description: str = (
        "Run the build command for a container in the target repository. "
        "Auto-detects Gradle/Maven/npm from architecture facts. "
        "Use baseline=True to check if the build passes without generated code."
    )
    args_schema: type[BaseModel] = BuildRunnerInput

    # Configuration
    repo_path: str = ""
    facts_path: str = "knowledge/extract/architecture_facts.json"

    # Shared staging dict (for applying files before build)
    _staging: dict = {}

    # Cached container configs
    _container_configs: list[ContainerConfig] | None = None

    def __init__(
        self,
        repo_path: str = "",
        facts_path: str = "knowledge/extract/architecture_facts.json",
        staging: dict | None = None,
        **kwargs,
    ):
        """Initialize with repo path and facts path."""
        super().__init__(**kwargs)
        if repo_path:
            self.repo_path = repo_path
        if facts_path:
            self.facts_path = facts_path
        self._staging = staging if staging is not None else {}
        self._container_configs = None

    @property
    def container_configs(self) -> list[ContainerConfig]:
        """Lazy-load container configs."""
        if self._container_configs is None:
            self._container_configs = _detect_containers(
                Path(self.repo_path), Path(self.facts_path)
            )
        return self._container_configs

    def _run(self, container_id: str, baseline: bool = False) -> str:
        """Run build for a container."""
        try:
            # Find the container config
            config = None
            for c in self.container_configs:
                if c.container_id == container_id:
                    config = c
                    break

            if config is None:
                available = [c.container_id for c in self.container_configs]
                return json.dumps({
                    "error": f"Container not found: {container_id}",
                    "available_containers": available,
                })

            build_dir = Path(self.repo_path) / config.build_cwd

            # Apply staged files to disk if not baseline
            backup = {}
            if not baseline and self._staging:
                backup = self._apply_staging(config)

            try:
                start = time.time()
                exit_code, output = _run_build(config.build_command, build_dir, config.timeout)
                duration = time.time() - start
            finally:
                # Always restore original files
                if backup:
                    self._restore_backup(backup)

            # Truncate output for token budget
            max_output = 4000
            truncated_output = output[-max_output:] if len(output) > max_output else output
            if len(output) > max_output:
                truncated_output = f"... (truncated, showing last {max_output} chars)\n" + truncated_output

            result = {
                "container_id": container_id,
                "container_name": config.name,
                "build_tool": config.build_tool,
                "build_command": config.build_command,
                "exit_code": exit_code,
                "success": exit_code == 0,
                "duration_seconds": round(duration, 1),
                "baseline": baseline,
                "output": truncated_output,
            }

            output_str = json.dumps(result, ensure_ascii=False)
            return truncate_response(output_str, hint="build output truncated")

        except Exception as e:
            logger.error(f"BuildRunnerTool error: {e}")
            return json.dumps({"error": str(e), "container_id": container_id})

    def _apply_staging(self, config: ContainerConfig) -> dict[str, str | None]:
        """Apply staged files to disk, returning backup of originals."""
        backup: dict[str, str | None] = {}
        repo = Path(self.repo_path)

        for file_path, staged in self._staging.items():
            # Only apply files belonging to this container
            try:
                rel = Path(file_path).relative_to(repo).as_posix()
            except ValueError:
                rel = file_path.replace("\\", "/")

            if not rel.startswith(config.root_path):
                continue

            p = Path(file_path) if Path(file_path).is_absolute() else repo / file_path

            # Backup original
            if p.exists():
                try:
                    backup[str(p)] = p.read_text(encoding="utf-8")
                except Exception:
                    backup[str(p)] = None
            else:
                backup[str(p)] = None

            # Write staged content
            action = staged.get("action", "modify")
            if action == "delete":
                if p.exists():
                    p.unlink()
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(staged.get("content", ""), encoding="utf-8")

        return backup

    @staticmethod
    def _restore_backup(backup: dict[str, str | None]) -> None:
        """Restore files from backup."""
        for file_path, original in backup.items():
            p = Path(file_path)
            try:
                if original is None:
                    if p.exists():
                        p.unlink()
                else:
                    p.write_text(original, encoding="utf-8")
            except Exception as e:
                logger.warning(f"[BuildRunner] Failed to restore {file_path}: {e}")
