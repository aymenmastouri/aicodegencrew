"""Collector service — list, toggle, read output for dashboard API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

# Import registry and config from the core pipeline
from src.aicodegencrew.pipelines.architecture_facts.collectors.collector_config import (
    load_collector_config,
    toggle_collector,
)
from src.aicodegencrew.pipelines.architecture_facts.collectors.registry import (
    COLLECTOR_REGISTRY,
)

from ..config import settings
from ..schemas import CollectorInfo, CollectorListResponse, CollectorOutput, EcosystemInfo, EcosystemListResponse

from src.aicodegencrew.shared.ecosystems.ecosystem_config import (
    load_ecosystem_config,
    toggle_ecosystem as toggle_ecosystem_config,
    update_priority as update_priority_config,
)


def _get_specialist_info() -> dict:
    """Get specialist collector info per ecosystem sub-package.

    Returns dict: {
        "java_jvm": {"specialist_count": 15, "dimensions": ["runtime", "dependencies", ...]},
        ...
    }
    """
    from src.aicodegencrew.pipelines.architecture_facts import collectors as collectors_pkg

    collectors_dir = Path(collectors_pkg.__file__).parent

    eco_packages = {
        "java_jvm": "spring",
        "javascript_typescript": "angular",
        "python": "python_eco",
        "c_cpp": "cpp",
    }

    # Map specialist filenames to dimension names
    dim_mapping = {
        "runtime_collector": "runtime",
        "dependency_collector": "dependencies",
        "test_collector": "tests",
        "data_model_collector": "data_model",
        "workflow_collector": "workflows",
        "workflow_detail_collector": "workflows",
        "build_system_collector": "build_system",
        "security_detail_collector": "security_details",
        "security_collector": "security_details",
        "validation_collector": "validation",
        "validation_detail_collector": "validation",
        "error_collector": "error_handling",
        "error_detail_collector": "error_handling",
        "interface_detail_collector": "interfaces",
        "interface_collector": "interfaces",
        "component_collector": "components",
        "rest_collector": "components",
        "service_collector": "components",
        "repository_collector": "components",
        "config_collector": "components",
        "module_collector": "components",
        "routing_collector": "interfaces",
        "openapi_collector": "interfaces",
        "state_collector": "components",
        "configuration_collector": "configuration",
        "logging_collector": "logging_observability",
        "communication_collector": "communication_patterns",
    }

    result = {}
    for eco_id, pkg_name in eco_packages.items():
        pkg_dir = collectors_dir / pkg_name
        if not pkg_dir.is_dir():
            result[eco_id] = {"specialist_count": 0, "dimensions": []}
            continue

        specialist_files = [f for f in pkg_dir.glob("*.py") if f.name != "__init__.py"]
        dimensions = set()
        for f in specialist_files:
            dim = dim_mapping.get(f.stem)
            if dim:
                dimensions.add(dim)

        result[eco_id] = {
            "specialist_count": len(specialist_files),
            "dimensions": sorted(dimensions),
        }

    return result


def _config_dir() -> Path:
    """Return the config directory (alongside phases_config.yaml)."""
    return settings.project_root / "config"


def _output_dir() -> Path:
    """Return the knowledge/extract output directory."""
    return settings.knowledge_dir / "extract"


def _get_output_stats(output_file: str) -> tuple[int | None, str | None, int]:
    """Get fact count, last_modified, and file size for an output file.

    Returns (fact_count, last_modified_iso, file_size_bytes).
    """
    filepath = _output_dir() / output_file
    if not filepath.exists():
        return None, None, 0

    try:
        stat = filepath.stat()
        file_size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # Count facts: if list, len; if dict with list values, sum of list lengths
        if isinstance(data, list):
            fact_count = len(data)
        elif isinstance(data, dict):
            # For data_model.json: sum of entities + tables + migrations
            total = 0
            for v in data.values():
                if isinstance(v, list):
                    total += len(v)
            fact_count = total if total > 0 else 1
        else:
            fact_count = 1

        return fact_count, mtime, file_size
    except (json.JSONDecodeError, OSError):
        return None, None, 0


def list_collectors() -> CollectorListResponse:
    """List all collectors with status, config, and output stats."""
    config = load_collector_config(_config_dir())

    collectors = []
    for reg in COLLECTOR_REGISTRY:
        cid = reg["id"]
        enabled = config.get(cid, True)
        # Core collectors are always enabled regardless of config
        if not reg["can_disable"]:
            enabled = True

        fact_count, last_modified, _ = _get_output_stats(reg["output_file"])

        collectors.append(
            CollectorInfo(
                id=cid,
                name=reg["name"],
                description=reg["description"],
                dimension=reg["dimension"],
                category=reg["category"],
                collector_type=reg.get("collector_type"),
                step=reg["step"],
                output_file=reg["output_file"],
                can_disable=reg["can_disable"],
                enabled=enabled,
                fact_count=fact_count,
                last_modified=last_modified,
                ecosystems=reg.get("ecosystems", []),
            )
        )

    # Compute specialist delegation counts per collector
    specialist_info = _get_specialist_info()
    total_specialists = sum(v["specialist_count"] for v in specialist_info.values())

    for c in collectors:
        # Count how many ecosystems delegate this collector's dimension to specialists
        c.specialist_count = sum(
            1 for eid in c.ecosystems
            if c.dimension in specialist_info.get(eid, {}).get("dimensions", [])
        )

    enabled_count = sum(1 for c in collectors if c.enabled)
    return CollectorListResponse(
        collectors=collectors,
        total=len(collectors),
        enabled_count=enabled_count,
        specialist_count=total_specialists,
    )


def toggle_collector_state(collector_id: str, enabled: bool) -> CollectorInfo:
    """Toggle a collector's enabled state and return updated info."""
    toggle_collector(_config_dir(), collector_id, enabled)

    # Find the registry entry
    for reg in COLLECTOR_REGISTRY:
        if reg["id"] == collector_id:
            fact_count, last_modified, _ = _get_output_stats(reg["output_file"])
            return CollectorInfo(
                id=collector_id,
                name=reg["name"],
                description=reg["description"],
                dimension=reg["dimension"],
                category=reg["category"],
                collector_type=reg.get("collector_type"),
                step=reg["step"],
                output_file=reg["output_file"],
                can_disable=reg["can_disable"],
                enabled=enabled,
                fact_count=fact_count,
                last_modified=last_modified,
                ecosystems=reg.get("ecosystems", []),
            )

    raise ValueError(f"Unknown collector: {collector_id}")


def get_collector_output(collector_id: str) -> CollectorOutput:
    """Read a collector's output JSON file."""
    # Find the registry entry
    reg = None
    for r in COLLECTOR_REGISTRY:
        if r["id"] == collector_id:
            reg = r
            break

    if reg is None:
        raise ValueError(f"Unknown collector: {collector_id}")

    filepath = _output_dir() / reg["output_file"]
    if not filepath.exists():
        raise FileNotFoundError(f"Output file not found: {reg['output_file']}")

    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"Failed to read {reg['output_file']}: {e}") from e

    fact_count, _, file_size = _get_output_stats(reg["output_file"])

    return CollectorOutput(
        collector_id=collector_id,
        data=data,
        fact_count=fact_count or 0,
        file_size_bytes=file_size,
    )


def list_ecosystems() -> EcosystemListResponse:
    """List all ecosystems with detection status and extracted facts."""
    from src.aicodegencrew.shared.ecosystems import EcosystemRegistry

    registry = EcosystemRegistry()

    # Detect active ecosystems from manifest if available
    manifest_path = settings.knowledge_dir / "discover"
    active_ids: list[str] = []

    # Try to read ecosystems from manifest
    try:
        # Check active project first
        active_marker = manifest_path / ".active_project"
        if active_marker.exists():
            with open(active_marker, encoding="utf-8") as f:
                active_data = json.load(f)
            slug = active_data.get("slug", "")
            manifest_file = manifest_path / slug / "repo_manifest.json"
        else:
            # Legacy flat layout
            manifest_file = manifest_path / "repo_manifest.json"

        if manifest_file.exists():
            with open(manifest_file, encoding="utf-8") as f:
                manifest = json.load(f)
            active_ids = manifest.get("ecosystems", [])
    except Exception:
        pass

    # Load containers and versions from architecture_facts if available
    facts_path = _output_dir() / "architecture_facts.json"
    all_containers: list[dict] = []
    all_versions: list[dict] = []
    try:
        if facts_path.exists():
            with open(facts_path, encoding="utf-8") as f:
                facts = json.load(f)
            all_containers = facts.get("containers", [])
            # Versions can be in system.tech_versions or top-level tech_versions
            system = facts.get("system", {})
            all_versions = system.get("tech_versions", []) if isinstance(system, dict) else []
            if not all_versions:
                all_versions = facts.get("tech_versions", [])
    except Exception:
        pass

    # Also try dedicated output files
    if not all_containers:
        try:
            containers_file = _output_dir() / "containers.json"
            if containers_file.exists():
                with open(containers_file, encoding="utf-8") as f:
                    all_containers = json.load(f)
        except Exception:
            pass

    specialist_info = _get_specialist_info()

    # Load ecosystem config for enabled/priority state
    eco_config = load_ecosystem_config(_config_dir())

    ecosystems = []
    for eco in registry.all_ecosystems:
        # Match containers to this ecosystem by technology
        eco_techs = eco.get_component_technologies()
        eco_containers = [
            c for c in all_containers
            if isinstance(c, dict) and c.get("technology", "") in eco_techs
        ]

        # Match versions: heuristic by technology name overlap
        eco_id_lower = eco.id.lower()
        eco_versions = []
        for v in all_versions:
            if not isinstance(v, dict):
                continue
            tech = v.get("technology", "").lower()
            # Java ecosystem: Java, Spring Boot, Kotlin, Gradle, Maven
            if eco_id_lower == "java_jvm" and any(k in tech for k in ["java", "spring", "kotlin", "gradle", "maven"]):
                eco_versions.append(v)
            elif eco_id_lower == "javascript_typescript" and any(
                k in tech for k in ["angular", "react", "vue", "node", "typescript", "rxjs", "webpack", "vite", "jest", "karma", "cypress", "playwright"]
            ):
                eco_versions.append(v)
            elif eco_id_lower == "python" and "python" in tech:
                eco_versions.append(v)
            elif eco_id_lower == "c_cpp" and any(
                k in tech for k in ["cmake", "c standard", "c++ standard", "boost", "qt", "opencv", "conan", "vcpkg"]
            ):
                eco_versions.append(v)

        eco_entry = eco_config.get(eco.id, {})
        enabled = eco_entry.get("enabled", True)
        effective_priority = eco_entry.get("priority", eco.priority)

        eco_spec = specialist_info.get(eco.id, {"specialist_count": 0, "dimensions": []})
        ecosystems.append(
            EcosystemInfo(
                id=eco.id,
                name=eco.name,
                detected=eco.id in active_ids,
                priority=effective_priority,
                enabled=enabled,
                source_extensions=sorted(eco.source_extensions),
                exclude_extensions=sorted(eco.exclude_extensions),
                skip_directories=sorted(eco.skip_directories),
                marker_files=[
                    {"filename": m.filename, "framework_label": m.framework_label}
                    for m in eco.marker_files
                ],
                containers=eco_containers,
                versions=eco_versions,
                component_technologies=sorted(eco.get_component_technologies()),
                dimensions=eco_spec["dimensions"],
                specialist_count=eco_spec["specialist_count"],
            )
        )

    return EcosystemListResponse(
        ecosystems=ecosystems,
        active_ids=active_ids,
        total=len(ecosystems),
        active_count=len(active_ids),
    )


def toggle_ecosystem_state(eco_id: str, enabled: bool) -> EcosystemInfo:
    """Toggle an ecosystem's enabled state, persist config, return updated info."""
    from src.aicodegencrew.shared.ecosystems import EcosystemRegistry

    # Validate ecosystem exists
    registry = EcosystemRegistry()
    eco = None
    for e in registry.all_ecosystems:
        if e.id == eco_id:
            eco = e
            break

    if eco is None:
        raise ValueError(f"Unknown ecosystem: {eco_id}")

    toggle_ecosystem_config(_config_dir(), eco_id, enabled)

    # Return updated info (re-fetch to get consistent state)
    eco_list = list_ecosystems()
    for ei in eco_list.ecosystems:
        if ei.id == eco_id:
            return ei

    raise ValueError(f"Ecosystem not found after toggle: {eco_id}")


def update_ecosystem_priority(eco_id: str, priority: int) -> EcosystemInfo:
    """Update an ecosystem's priority, persist config, return updated info."""
    from src.aicodegencrew.shared.ecosystems import EcosystemRegistry

    # Validate ecosystem exists
    registry = EcosystemRegistry()
    eco = None
    for e in registry.all_ecosystems:
        if e.id == eco_id:
            eco = e
            break

    if eco is None:
        raise ValueError(f"Unknown ecosystem: {eco_id}")

    update_priority_config(_config_dir(), eco_id, priority)

    # Return updated info (re-fetch to get consistent state)
    eco_list = list_ecosystems()
    for ei in eco_list.ecosystems:
        if ei.id == eco_id:
            return ei

    raise ValueError(f"Ecosystem not found after priority update: {eco_id}")
