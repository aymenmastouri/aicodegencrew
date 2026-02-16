"""Deterministic preflight validation before starting the implement crew.

Validates plan, repository, and build readiness — zero LLM tokens.
Aborts BEFORE any tokens are burned.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ....shared.utils.logger import setup_logger
from ..schemas import CodegenPlanInput
from .import_index import ImportIndex, ImportIndexBuilder

logger = setup_logger(__name__)


@dataclass
class PreflightResult:
    """Result of deterministic preflight validation."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    import_symbols: int = 0
    buildable_containers: int = 0


def detect_buildable_containers(
    repo_path: Path,
    facts_path: Path,
) -> list[dict[str, str]]:
    """Auto-detect buildable containers from architecture_facts.json.

    Returns a list of dicts with id, name, root_path, build_system.
    """
    if not facts_path.exists():
        return []

    try:
        with open(facts_path, encoding="utf-8") as f:
            facts = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("[Preflight] Could not read architecture_facts: %s", e)
        return []

    skip_types = {"test", "e2e"}
    result: list[dict[str, str]] = []

    for container in facts.get("containers", []):
        cid = container.get("id", "")
        ctype = container.get("type", "")
        root = container.get("root_path", "").replace("\\", "/").strip("/")

        if ctype in skip_types or "e2e" in cid.lower():
            continue

        meta = container.get("metadata", {})
        build_system = meta.get("build_system", "")

        if not build_system:
            continue

        result.append({
            "id": cid,
            "name": container.get("name", root),
            "root_path": root,
            "build_system": build_system,
            "language": meta.get("language", ""),
        })

    return result


class PreflightValidator:
    """Validates plan and repository readiness before LLM work begins."""

    def __init__(
        self,
        repo_path: str,
        facts_path: str = "knowledge/extract/architecture_facts.json",
    ):
        self.repo_path = Path(repo_path)
        self.facts_path = Path(facts_path)

    def run(
        self,
        plan: CodegenPlanInput,
        import_index: ImportIndex | None = None,
    ) -> tuple[PreflightResult, ImportIndex]:
        errors: list[str] = []
        warnings: list[str] = []

        if not plan.task_id:
            errors.append("Plan missing task_id")

        if not plan.affected_components:
            errors.append("Plan has no affected_components")

        if not self.repo_path.exists() or not self.repo_path.is_dir():
            errors.append(f"Repository path not found: {self.repo_path}")

        missing_components = 0
        for comp in plan.affected_components:
            if comp.change_type in ("create", "delete"):
                continue
            if not comp.file_path:
                missing_components += 1
                continue

            p = Path(comp.file_path)
            if p.is_absolute():
                exists = p.exists()
            else:
                exists = (self.repo_path / comp.file_path).exists()

            if not exists:
                missing_components += 1

        if missing_components:
            errors.append(f"{missing_components} affected component file(s) not found")

        built_index = import_index
        if built_index is None:
            built_index = ImportIndexBuilder(
                repo_path=str(self.repo_path), facts_path=str(self.facts_path),
            ).run()

        import_symbols = built_index.total_symbols
        if import_symbols <= 0:
            errors.append("Import index is empty (0 symbols)")

        containers = detect_buildable_containers(self.repo_path, self.facts_path)
        buildable_containers = len(containers)
        if buildable_containers == 0:
            errors.append("No buildable containers detected")

        if not self.facts_path.exists():
            warnings.append(f"Facts file not found: {self.facts_path}")

        result = PreflightResult(
            ok=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            import_symbols=import_symbols,
            buildable_containers=buildable_containers,
        )

        if not result.ok:
            logger.error("[Preflight] Validation failed: %s", "; ".join(result.errors))
        else:
            logger.info(
                "[Preflight] OK: symbols=%d, buildable_containers=%d",
                result.import_symbols, result.buildable_containers,
            )

        return result, built_index
