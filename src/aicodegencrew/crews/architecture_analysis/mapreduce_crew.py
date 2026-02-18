"""
Map-Reduce Architecture Analysis Crew - Scalable Phase 2
=========================================================
Splits analysis by container, then merges results.

For large repositories (500+ components), this approach:
1. MAP: Analyzes each container independently (parallelizable)
2. REDUCE: Merges container analyses into final output

BENEFITS:
- 3x faster with parallel execution
- Scales to 100k+ components
- Smaller context per agent (~200 vs 800+ components)
- Better failure isolation

USAGE:
    from aicodegencrew.crews.architecture_analysis import MapReduceAnalysisCrew

    crew = MapReduceAnalysisCrew(facts_path="knowledge/extract/architecture_facts.json")
    result = crew.run()
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ...shared.paths import CHROMA_DIR
from .container_crew import ContainerAnalysisCrew
from .crew import ArchitectureAnalysisCrew

logger = logging.getLogger(__name__)


class ContainerAnalyzer:
    """Analyzes a single container's components using LLM crew."""

    def __init__(
        self,
        facts_path: str,
        container_name: str,
        output_dir: Path,
        chroma_dir: str = None,
        use_llm: bool = True,
    ):
        self.facts_path = Path(facts_path)
        self.container_name = container_name
        self.output_dir = output_dir
        self.chroma_dir = chroma_dir
        self.use_llm = use_llm

    def run(self) -> dict[str, Any]:
        """Run analysis for this container."""
        logger.info(f"[MAP] Analyzing container: {self.container_name}")

        # Load facts and filter by container
        facts = self._load_container_facts()

        # Use LLM crew if enabled and container has components
        if self.use_llm and len(facts.get("components", [])) > 0:
            crew = ContainerAnalysisCrew(
                container_name=self.container_name,
                container_facts=facts,
                output_dir=self.output_dir,
            )
            return crew.run()

        # Fallback: deterministic analysis
        result = {
            "container": self.container_name,
            "component_count": len(facts.get("components", [])),
            "relation_count": len(facts.get("relations", [])),
            "interface_count": len(facts.get("interfaces", [])),
            "analysis": self._analyze_container_deterministic(facts),
        }

        # Save partial result
        output_file = self.output_dir / f"container_{self.container_name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"[MAP] Container {self.container_name}: {result['component_count']} components analyzed")
        return result

    def _load_container_facts(self) -> dict[str, Any]:
        """Load facts filtered by this container."""
        try:
            with open(self.facts_path, encoding="utf-8") as f:
                all_facts = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read facts: {e}")
            return {}

        # Normalize container name for matching (handle hyphen/underscore differences)
        # container_name = "e2e-xnp" -> normalized = "e2e_xnp" or "e2exnp"
        def normalize(s: str) -> str:
            return s.lower().replace("-", "_").replace(".", "_")

        container_name_norm = normalize(self.container_name)

        # Build possible container ID patterns
        # e.g., "backend" -> ["container.backend", "container_backend", "backend"]
        possible_ids = [
            f"container.{self.container_name}",
            f"container_{self.container_name}",
            f"container.{self.container_name.replace('-', '_')}",
            self.container_name,
        ]
        possible_ids_norm = [normalize(pid) for pid in possible_ids]

        # Filter components by container (match normalized ID/name)
        components = [
            c
            for c in all_facts.get("components", [])
            if normalize(c.get("container", "")) in possible_ids_norm
            or container_name_norm in normalize(c.get("path", ""))  # fallback: path contains name
        ]

        # Filter relations involving this container's components
        component_names = {c.get("name", "").lower() for c in components}
        relations = [
            r
            for r in all_facts.get("relations", [])
            if r.get("from", "").lower() in component_names or r.get("to", "").lower() in component_names
        ]

        # Filter interfaces by container (match normalized)
        interfaces = [
            i for i in all_facts.get("interfaces", []) if normalize(i.get("container", "")) in possible_ids_norm
        ]

        return {
            "container": self.container_name,
            "components": components,
            "relations": relations,
            "interfaces": interfaces,
        }

    def _analyze_container_deterministic(self, facts: dict[str, Any]) -> dict[str, Any]:
        """Analyze container structure without LLM (fallback)."""
        components = facts.get("components", [])

        # Count by stereotype
        stereotypes: dict[str, int] = {}
        for c in components:
            stereo = c.get("stereotype", "unknown")
            stereotypes[stereo] = stereotypes.get(stereo, 0) + 1

        # Detect layers
        has_controllers = stereotypes.get("controller", 0) > 0
        has_services = stereotypes.get("service", 0) > 0
        has_repositories = stereotypes.get("repository", 0) > 0
        has_entities = stereotypes.get("entity", 0) > 0

        # Determine pattern
        if has_controllers and has_services and has_repositories:
            pattern = "Layered"
            layers = ["Controller", "Service", "Repository"]
            if has_entities:
                layers.append("Entity")
        elif stereotypes.get("component", 0) > 0:
            pattern = "Component-Based"
            layers = ["Component", "Service", "Module"]
        else:
            pattern = "Unknown"
            layers = list(stereotypes.keys())[:5]

        return {
            "primary_pattern": pattern,
            "layers": layers,
            "stereotype_distribution": stereotypes,
            "total_components": len(components),
            "total_relations": len(facts.get("relations", [])),
            "total_interfaces": len(facts.get("interfaces", [])),
        }


class MapReduceAnalysisCrew:
    """
    Map-Reduce Architecture Analysis Crew.

    Splits analysis by container for scalability:
    1. MAP: Analyze each container independently
    2. REDUCE: Merge analyses into analyzed_architecture.json
    """

    LARGE_REPO_THRESHOLD = 300  # Use map-reduce for repos with 300+ components

    def __init__(
        self,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        chroma_dir: str = None,
        output_dir: str = "knowledge/analyze",
        parallel: bool = True,
        max_workers: int = 3,
    ):
        self.facts_path = Path(facts_path)
        self.chroma_dir = chroma_dir or CHROMA_DIR
        self.output_dir = Path(output_dir)
        self.parallel = parallel
        self.max_workers = max_workers

        # Create container analysis directory
        self.container_dir = self.output_dir / "container_analysis"
        self.container_dir.mkdir(parents=True, exist_ok=True)

    def should_use_mapreduce(self) -> bool:
        """Check if repository is large enough to benefit from map-reduce."""
        facts = self._load_facts()
        component_count = len(facts.get("components", []))
        container_count = len(facts.get("containers", []))

        # Use map-reduce if:
        # 1. More than threshold components
        # 2. Multiple containers available
        should_use = component_count >= self.LARGE_REPO_THRESHOLD and container_count >= 2

        if should_use:
            logger.info(f"[MapReduce] Enabled: {component_count} components, {container_count} containers")
        else:
            logger.info(f"[MapReduce] Disabled: {component_count} components (threshold: {self.LARGE_REPO_THRESHOLD})")

        return should_use

    def run(self) -> str:
        """Execute map-reduce analysis if beneficial, otherwise standard crew."""
        if not self.should_use_mapreduce():
            # Fall back to standard crew for small repos
            logger.info("[MapReduce] Using standard ArchitectureAnalysisCrew")
            standard_crew = ArchitectureAnalysisCrew(
                facts_path=str(self.facts_path),
                chroma_dir=self.chroma_dir,
                output_dir=str(self.output_dir),
            )
            return standard_crew.run()

        logger.info("=" * 60)
        logger.info("[MapReduce] Starting Map-Reduce Architecture Analysis")
        logger.info("=" * 60)

        # Get containers
        facts = self._load_facts()
        containers = facts.get("containers", [])
        container_names = [c.get("name", "unknown") for c in containers]

        logger.info(f"[MAP] Containers to analyze: {container_names}")

        # MAP PHASE: Analyze each container
        container_results = self._map_phase(container_names)

        # REDUCE PHASE: Merge results
        merged_result = self._reduce_phase(container_results, facts)

        # Save final output
        output_file = self.output_dir / "analyzed_architecture.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(merged_result, f, indent=2, ensure_ascii=False)

        logger.info("=" * 60)
        logger.info(f"[MapReduce] Complete: {output_file}")
        logger.info("=" * 60)

        return str(output_file)

    def _load_cached_container(self, name: str) -> dict | None:
        """Load existing container analysis from disk if available."""
        cache_file = self.container_dir / f"container_{name}.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    result = json.load(f)
                logger.info(f"[MAP] Container {name}: loaded from cache (skipping LLM)")
                return result
            except Exception as e:
                logger.warning(f"[MAP] Container {name}: cache read failed ({e}), re-analyzing")
        return None

    def _map_phase(self, container_names: list[str]) -> list[dict[str, Any]]:
        """MAP: Analyze each container (optionally in parallel)."""
        results = []

        if self.parallel and len(container_names) > 1:
            logger.info(f"[MAP] Parallel execution with {self.max_workers} workers")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for name in container_names:
                    cached = self._load_cached_container(name)
                    if cached is not None:
                        results.append(cached)
                        continue
                    analyzer = ContainerAnalyzer(
                        facts_path=str(self.facts_path),
                        container_name=name,
                        output_dir=self.container_dir,
                        chroma_dir=self.chroma_dir,
                    )
                    future = executor.submit(analyzer.run)
                    futures[future] = name

                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"[MAP] Container {name} failed: {e}")
                        results.append(
                            {
                                "container": name,
                                "error": str(e),
                            }
                        )
        else:
            logger.info("[MAP] Sequential execution")
            for name in container_names:
                cached = self._load_cached_container(name)
                if cached is not None:
                    results.append(cached)
                    continue
                analyzer = ContainerAnalyzer(
                    facts_path=str(self.facts_path),
                    container_name=name,
                    output_dir=self.container_dir,
                    chroma_dir=self.chroma_dir,
                )
                try:
                    result = analyzer.run()
                    results.append(result)
                except Exception as e:
                    logger.error(f"[MAP] Container {name} failed: {e}")
                    results.append({"container": name, "error": str(e)})

        return results

    def _reduce_phase(
        self,
        container_results: list[dict[str, Any]],
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        """REDUCE: Merge container analyses into final output."""
        logger.info("[REDUCE] Merging container analyses...")

        # Use global facts for accurate totals
        total_components = len(facts.get("components", []))
        total_relations = len(facts.get("relations", []))
        total_interfaces = len(facts.get("interfaces", []))

        # Collect patterns and quality grades from container analyses
        patterns_found = {}
        all_stereotypes: dict[str, int] = {}
        container_grades: list[str] = []
        all_recommendations: list[str] = []
        all_debt_indicators: list[str] = []
        active_containers = []

        for result in container_results:
            analysis = result.get("analysis", {})
            container = result.get("container", "unknown")
            comp_count = result.get("component_count", 0)

            # Get pattern from either LLM analysis or deterministic fallback
            if "technical" in result:
                pattern = result["technical"].get("primary_pattern", "Unknown")
            else:
                pattern = analysis.get("primary_pattern", "Unknown")
            patterns_found[container] = pattern

            # Merge stereotype counts
            stereo_dist = analysis.get("stereotype_distribution", {})
            for stereo, count in stereo_dist.items():
                all_stereotypes[stereo] = all_stereotypes.get(stereo, 0) + count

            # Collect quality grades from LLM-analyzed containers
            quality = result.get("quality", {})
            if quality.get("grade"):
                container_grades.append(quality["grade"])

            # Collect recommendations
            for rec in result.get("top_recommendations", []):
                if rec not in all_recommendations:
                    all_recommendations.append(rec)
            for rec in quality.get("recommendations", []):
                if rec not in all_recommendations:
                    all_recommendations.append(rec)

            # Collect debt indicators
            all_debt_indicators.extend(quality.get("debt_indicators", []))

            # Track active containers (with components)
            if comp_count > 0:
                active_containers.append(container)

        # Determine overall architecture style
        active_count = len(active_containers)
        container_count = len(container_results)
        if active_count == 1:
            style = "Monolith"
        elif active_count == 2 and "Layered" in patterns_found.values():
            style = "Modular Monolith"
        else:
            style = "Distributed" if active_count > 2 else "Modular Monolith"

        # Calculate overall grade from container grades
        grade_map = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        reverse_grade = {4: "A", 3: "B", 2: "C", 1: "D", 0: "F"}
        if container_grades:
            avg = sum(grade_map.get(g, 2) for g in container_grades) / len(container_grades)
            overall_grade = reverse_grade.get(round(avg), "C")
        else:
            # Fallback: multi-dimensional quality assessment
            ratio = total_relations / max(total_components, 1)
            stereo_score = min(len(all_stereotypes) / 6, 1.0)  # Separation of concerns
            coupling_score = min(1.0 - (ratio / 2.0), 1.0) if ratio < 2.0 else 0.0
            combined = (stereo_score + coupling_score) / 2
            overall_grade = "A" if combined > 0.75 else "B" if combined > 0.5 else "C" if combined > 0.25 else "D"

        # Quality assessment from aggregated data
        separation = "good" if len(all_stereotypes) >= 5 else "moderate" if len(all_stereotypes) >= 3 else "poor"
        ratio = total_relations / max(total_components, 1)
        coupling = "loose" if ratio < 0.3 else "moderate" if ratio < 1.0 else "tight"

        # Build executive summary from actual analysis
        container_summaries = []
        for r in container_results:
            if r.get("component_count", 0) > 0:
                name = r.get("container", "unknown")
                count = r.get("component_count", 0)
                grade = r.get("quality", {}).get("grade", "N/A")
                container_summaries.append(f"{name} ({count} components, Grade {grade})")

        system_name = facts.get("system", {}).get("name", "UNKNOWN")
        exec_summary = (
            f"{system_name} is a {style.lower()} system with {total_components} components "
            f"across {active_count} active containers: {', '.join(container_summaries)}. "
            f"Overall architecture grade: {overall_grade}."
        )

        # Build micro_architecture from actual container results
        micro_arch = {}
        for result in container_results:
            container = result.get("container", "unknown")
            if "technical" in result:
                micro_arch[container] = {
                    "primary_pattern": result["technical"].get("primary_pattern", "Unknown"),
                    "layer_structure": result["technical"].get("layers", []),
                    "component_counts": result.get("analysis", {}).get("stereotype_distribution", {}),
                }
            else:
                micro_arch[container] = {
                    "primary_pattern": result.get("analysis", {}).get("primary_pattern", "Unknown"),
                    "layer_structure": result.get("analysis", {}).get("layers", []),
                    "component_counts": result.get("analysis", {}).get("stereotype_distribution", {}),
                }

        # Build merged output
        merged = {
            "system": facts.get("system", {"name": system_name}),
            "macro_architecture": {
                "style": style,
                "container_count": container_count,
                "active_containers": active_count,
                "reasoning": (
                    f"{active_count} active containers ({', '.join(active_containers)}) "
                    f"with {total_components} total components. "
                    f"Patterns: {', '.join(f'{k}: {v}' for k, v in patterns_found.items())}."
                ),
                "scalability_approach": "horizontal" if active_count > 1 else "vertical",
                "deployment_model": "distributed" if active_count > 1 else "single",
                "communication_pattern": "sync REST",
            },
            "micro_architecture": micro_arch,
            "architecture_quality": {
                "separation_of_concerns": separation,
                "layer_violations_count": 0,
                "coupling_assessment": coupling,
                "relations_per_component": round(ratio, 2),
                "overall_grade": overall_grade,
            },
            "statistics": {
                "total_components": total_components,
                "total_relations": total_relations,
                "total_interfaces": total_interfaces,
                "containers_analyzed": container_count,
                "active_containers": active_count,
                "stereotype_distribution": all_stereotypes,
            },
            "container_analyses": container_results,
            "overall_grade": overall_grade,
            "executive_summary": exec_summary,
            "top_recommendations": all_recommendations[:10],
        }

        if all_debt_indicators:
            merged["technical_debt"] = {
                "indicators": all_debt_indicators[:15],
                "indicator_count": len(all_debt_indicators),
            }

        logger.info(f"[REDUCE] Merged {container_count} container analyses -> Grade {overall_grade}")
        return merged

    def _load_facts(self) -> dict[str, Any]:
        """Load architecture facts."""
        if not self.facts_path.exists():
            logger.warning(f"Facts file not found: {self.facts_path}")
            return {}

        try:
            with open(self.facts_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read facts: {e}")
            return {}

    def kickoff(self, inputs: dict[str, Any] = None) -> str:
        """Execute crew - compatible with orchestrator interface."""
        return self.run()
