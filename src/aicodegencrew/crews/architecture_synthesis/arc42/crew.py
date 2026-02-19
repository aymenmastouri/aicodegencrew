"""
Arc42 Crew - Phase 3b: Mini-Crews Pattern
==========================================
Creates all 12 arc42 chapters + Quality Gate

Architecture Fix:
- OLD: 1 Crew with 44 sequential tasks -> Context overflow after ~10 tasks
- NEW: 18 Mini-Crews (1 task each) -> Fresh context per chapter/sub-chapter

Chapters 5, 6, and 8 are split into sub-crews for maximum output quality:
- Chapter 5: 4 sub-crews (overview, controllers, services, domain)
- Chapter 6: 2 sub-crews (API flows, business flows)
- Chapter 8: 2 sub-crews (technical concepts, patterns)

Each Mini-Crew starts with a fresh LLM context window.
Data is passed via template variables (summaries), not inter-task context.
"""

import logging
from datetime import date

from crewai import Task

from ..base_crew import MiniCrewBase
from ..tools import ChunkedWriterTool
from .agents import ARC42_AGENT_CONFIG
from .tasks import (
    CH01_INTRODUCTION,
    CH02_CONSTRAINTS,
    CH03_CONTEXT,
    CH04_SOLUTION_STRATEGY,
    CH05_PART1_OVERVIEW,
    CH05_PART2_CONTROLLERS,
    CH05_PART3_SERVICES,
    CH05_PART4_DOMAIN,
    CH06_PART1_API_FLOWS,
    CH06_PART2_BUSINESS_FLOWS,
    CH07_DEPLOYMENT,
    CH08_PART1A_DOMAIN_SECURITY,
    CH08_PART1B_PERSISTENCE_OPS,
    CH08_PART2_PATTERNS,
    CH09_DECISIONS,
    CH10_QUALITY,
    CH11_RISKS,
    CH12_GLOSSARY,
    QUALITY_GATE_DESCRIPTION,
)

logger = logging.getLogger(__name__)


class Arc42Crew(MiniCrewBase):
    """
    Arc42 Crew - Creates all 12 arc42 chapters using Mini-Crews pattern.

    Each chapter group runs in its own Mini-Crew with fresh LLM context.
    This prevents context overflow that occurred with 44 tasks in 1 Crew.

    Mini-Crews (1 task each for reliability with on-prem models):
    1-8. Chapters 1-5 (ch05 split into 4 sub-crews)
    9-10. Chapter 6 (runtime view split into 2 sub-crews)
    11. Chapter 7 (deployment)
    12-14. Chapter 8 (crosscutting split into 3 sub-crews)
    15-18. Chapters 9-12
    19. Quality Gate (validation)

    Total: 19 mini-crews (was 18 before ch08 part1 splitting)
    """

    @property
    def crew_name(self) -> str:
        return "Arc42"

    @property
    def agent_config(self) -> dict[str, str]:
        return ARC42_AGENT_CONFIG

    def _get_extra_tools(self) -> list:
        """Arc42 needs ChunkedWriterTool for large chapters."""
        return [ChunkedWriterTool(output_dir=str(self._output_dir))]

    def _summarize_facts(self) -> dict[str, str]:
        """Create summaries combining Phase 1 facts and Phase 2 analysis."""
        facts = self.facts
        analysis = self.analysis

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")

        arch_info = analysis.get("architecture", {})
        macro_arch = analysis.get("macro_architecture", {})
        micro_arch = analysis.get("micro_architecture", {})

        # Support both legacy Phase 2 output (`architecture`/`patterns`) and the current
        # MapReduceAnalysisCrew output (`macro_architecture`/`micro_architecture`).
        patterns = analysis.get("patterns", []) or []
        if not patterns and isinstance(micro_arch, dict):
            derived_patterns: list[str] = []
            seen_patterns: set[str] = set()
            for container_info in micro_arch.values():
                pattern = (container_info or {}).get("primary_pattern")
                if pattern and pattern != "Unknown" and pattern not in seen_patterns:
                    seen_patterns.add(pattern)
                    derived_patterns.append(pattern)
            patterns = derived_patterns

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})

        by_stereotype: dict[str, int] = {}
        for comp in components:
            stereo = comp.get("stereotype", "unknown")
            by_stereotype[stereo] = by_stereotype.get(stereo, 0) + 1

        arch_style = arch_info.get("primary_style") or macro_arch.get("style") or "UNKNOWN - use tools to discover"

        system_summary = f"""SYSTEM: {system_name}

ARCHITECTURE (from Phase 2 analysis):
- Primary Style: {arch_style}
- Patterns: {", ".join([p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in patterns]) if patterns else "Use tools to discover"}

STATISTICS (from Phase 1 facts):
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGIES:
{chr(10).join([f"- {t}" for t in tech_stack]) if tech_stack else "- Use tools to discover"}

COMPONENT COUNTS BY STEREOTYPE:
{chr(10).join([f"- {k}: {v}" for k, v in sorted(by_stereotype.items())]) if by_stereotype else "- Use tools to discover"}

IMPORTANT: Use MCP tools (get_statistics, get_architecture_summary, list_components_by_stereotype) to get REAL data!"""

        container_lines = [f"- {c.get('name', '?')}: {c.get('technology', '?')}" for c in containers]

        containers_summary = f"""CONTAINERS:
{chr(10).join(container_lines) if container_lines else "- Use query_architecture_facts to discover"}"""

        components_summary = "Use list_components_by_stereotype tool to query components by type."
        interfaces_summary = (
            f"Total interfaces: {len(interfaces)}. Use query_architecture_facts with category='interfaces' for details."
        )
        relations_summary = (
            f"Total relations: {len(relations)}. Use query_architecture_facts with category='relations' for details."
        )
        building_blocks_data = (
            "Use list_components_by_stereotype for each layer (controller, service, repository, entity)."
        )

        return {
            "system_name": system_name,
            "system_summary": self.escape_braces(system_summary),
            "containers_summary": self.escape_braces(containers_summary),
            "components_summary": self.escape_braces(components_summary),
            "relations_summary": self.escape_braces(relations_summary),
            "interfaces_summary": self.escape_braces(interfaces_summary),
            "building_blocks_data": self.escape_braces(building_blocks_data),
            "current_date": date.today().isoformat(),
        }

    # -------------------------------------------------------------------------
    # MERGE BUILDING BLOCKS
    # -------------------------------------------------------------------------

    def _merge_building_blocks(self) -> None:
        """Merge 4 building-blocks part files into 05-building-blocks.md."""
        base = self._output_dir / "arc42"
        parts = [
            "05-part1-overview.md",
            "05-part2-controllers.md",
            "05-part3-services.md",
            "05-part4-domain.md",
        ]

        merged_lines: list[str] = []
        for part_file in parts:
            path = base / part_file
            if path.exists() and path.stat().st_size > 100:
                content = path.read_text(encoding="utf-8").strip()
                # Remove duplicate chapter title from parts 2-4
                if merged_lines and content.startswith("# 05"):
                    lines = content.split("\n", 1)
                    content = lines[1].strip() if len(lines) > 1 else content
                merged_lines.append(content)
                merged_lines.append("")  # blank separator
                logger.info(f"[Arc42] Merged {part_file} ({len(content)} chars)")
            else:
                logger.warning(f"[Arc42] Part file missing: {part_file}")

        if merged_lines:
            merged = "\n".join(merged_lines)
            target = base / "05-building-blocks.md"
            target.write_text(merged, encoding="utf-8")
            logger.info(f"[Arc42] Merged building-blocks: {len(merged)} chars -> {target}")

    # -------------------------------------------------------------------------
    # MERGE RUNTIME VIEW
    # -------------------------------------------------------------------------

    def _merge_runtime_view(self) -> None:
        """Merge 2 runtime-view part files into 06-runtime-view.md."""
        base = self._output_dir / "arc42"
        parts = [
            "06-part1-api-flows.md",
            "06-part2-business-flows.md",
        ]

        merged_lines: list[str] = []
        for part_file in parts:
            path = base / part_file
            if path.exists() and path.stat().st_size > 100:
                content = path.read_text(encoding="utf-8").strip()
                # Remove duplicate chapter title from part 2
                if merged_lines and content.startswith("# 06"):
                    lines = content.split("\n", 1)
                    content = lines[1].strip() if len(lines) > 1 else content
                merged_lines.append(content)
                merged_lines.append("")  # blank separator
                logger.info(f"[Arc42] Merged {part_file} ({len(content)} chars)")
            else:
                logger.warning(f"[Arc42] Part file missing: {part_file}")

        if merged_lines:
            merged = "\n".join(merged_lines)
            target = base / "06-runtime-view.md"
            target.write_text(merged, encoding="utf-8")
            logger.info(f"[Arc42] Merged runtime-view: {len(merged)} chars -> {target}")

    # -------------------------------------------------------------------------
    # MERGE CROSSCUTTING
    # -------------------------------------------------------------------------

    def _merge_crosscutting(self) -> None:
        """Merge 3 crosscutting part files into 08-crosscutting.md."""
        base = self._output_dir / "arc42"
        parts = [
            "08-part1a-domain-security.md",
            "08-part1b-persistence-ops.md",
            "08-part2-patterns.md",
        ]

        merged_lines: list[str] = []
        for part_file in parts:
            path = base / part_file
            if path.exists() and path.stat().st_size > 100:
                content = path.read_text(encoding="utf-8").strip()
                # Remove duplicate chapter title from part 2
                if merged_lines and content.startswith("# 08"):
                    lines = content.split("\n", 1)
                    content = lines[1].strip() if len(lines) > 1 else content
                merged_lines.append(content)
                merged_lines.append("")  # blank separator
                logger.info(f"[Arc42] Merged {part_file} ({len(content)} chars)")
            else:
                logger.warning(f"[Arc42] Part file missing: {part_file}")

        if merged_lines:
            merged = "\n".join(merged_lines)
            target = base / "08-crosscutting.md"
            target.write_text(merged, encoding="utf-8")
            logger.info(f"[Arc42] Merged crosscutting: {len(merged)} chars -> {target}")

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def run(self) -> str:
        """
        Execute all 13 Mini-Crews sequentially with resume support.

        On failure, completed mini-crews are checkpointed. Re-running
        skips already-completed mini-crews automatically.

        1 task per crew for maximum reliability with on-prem models.
        """
        completed = self._load_checkpoint()
        results = []

        # Define mini-crews as (name, [(desc, expected_output)], [expected_files])
        # IMPORTANT: Max 1 task per crew — each chapter gets its own fresh
        # LLM context. The on-prem model frequently fails on the 2nd task
        # in a crew (writes ch03 but not ch04, etc.).
        mini_crews: list[tuple[str, list[tuple[str, str]], list[str]]] = [
            (
                "introduction",
                [
                    (CH01_INTRODUCTION, "Complete arc42 Introduction chapter"),
                ],
                ["arc42/01-introduction.md"],
            ),
            (
                "constraints",
                [
                    (CH02_CONSTRAINTS, "Complete arc42 Constraints chapter"),
                ],
                ["arc42/02-constraints.md"],
            ),
            (
                "context",
                [
                    (CH03_CONTEXT, "Complete arc42 Context chapter"),
                ],
                ["arc42/03-context.md"],
            ),
            (
                "solution-strategy",
                [
                    (CH04_SOLUTION_STRATEGY, "Complete arc42 Solution Strategy chapter"),
                ],
                ["arc42/04-solution-strategy.md"],
            ),
            (
                "building-blocks-overview",
                [
                    (CH05_PART1_OVERVIEW, "Building Blocks overview and system whitebox"),
                ],
                ["arc42/05-part1-overview.md"],
            ),
            (
                "building-blocks-controllers",
                [
                    (CH05_PART2_CONTROLLERS, "Building Blocks presentation layer"),
                ],
                ["arc42/05-part2-controllers.md"],
            ),
            (
                "building-blocks-services",
                [
                    (CH05_PART3_SERVICES, "Building Blocks business layer"),
                ],
                ["arc42/05-part3-services.md"],
            ),
            (
                "building-blocks-domain",
                [
                    (CH05_PART4_DOMAIN, "Building Blocks domain and persistence"),
                ],
                ["arc42/05-part4-domain.md"],
            ),
            (
                "runtime-view-api-flows",
                [
                    (CH06_PART1_API_FLOWS, "Arc42 Runtime View Part 1: API flows"),
                ],
                ["arc42/06-part1-api-flows.md"],
            ),
            (
                "runtime-view-business-flows",
                [
                    (CH06_PART2_BUSINESS_FLOWS, "Arc42 Runtime View Part 2: Business flows"),
                ],
                ["arc42/06-part2-business-flows.md"],
            ),
            (
                "deployment",
                [
                    (CH07_DEPLOYMENT, "Complete arc42 Deployment View chapter"),
                ],
                ["arc42/07-deployment.md"],
            ),
            (
                "crosscutting-technical-a",
                [
                    (CH08_PART1A_DOMAIN_SECURITY, "Arc42 Crosscutting Part 1A: Domain + Security"),
                ],
                ["arc42/08-part1a-domain-security.md"],
            ),
            (
                "crosscutting-technical-b",
                [
                    (CH08_PART1B_PERSISTENCE_OPS, "Arc42 Crosscutting Part 1B: Persistence + Ops"),
                ],
                ["arc42/08-part1b-persistence-ops.md"],
            ),
            (
                "crosscutting-patterns",
                [
                    (CH08_PART2_PATTERNS, "Arc42 Crosscutting Part 2: Patterns"),
                ],
                ["arc42/08-part2-patterns.md"],
            ),
            (
                "decisions",
                [
                    (CH09_DECISIONS, "Complete arc42 Decisions chapter"),
                ],
                ["arc42/09-decisions.md"],
            ),
            (
                "quality",
                [
                    (CH10_QUALITY, "Complete arc42 Quality chapter"),
                ],
                ["arc42/10-quality.md"],
            ),
            (
                "risks",
                [
                    (CH11_RISKS, "Complete arc42 Risks chapter"),
                ],
                ["arc42/11-risks.md"],
            ),
            (
                "glossary",
                [
                    (CH12_GLOSSARY, "Complete arc42 Glossary"),
                ],
                ["arc42/12-glossary.md"],
            ),
        ]

        # Get template data for filling {system_summary} placeholders
        template_data = self._summarize_facts()

        # Simple/formulaic chapters that can use the fast (cheaper) model
        _fast_model_crews = {"introduction", "constraints", "glossary"}

        for name, task_specs, expected_files in mini_crews:
            if not self.should_skip(name, completed):
                try:
                    agent = self._create_agent(use_fast_model=(name in _fast_model_crews))
                    tasks = [
                        Task(description=desc.format(**template_data), expected_output=output, agent=agent)
                        for desc, output in task_specs
                    ]
                    self._run_mini_crew(name, tasks, expected_files=expected_files)
                except Exception as e:
                    logger.error(f"[Arc42] Mini-crew {name} failed, continuing: {e}")
            results.append(f"{name}: Done")

        # Merge part files into final chapter files
        self._merge_building_blocks()
        self._merge_runtime_view()
        self._merge_crosscutting()

        # Quality Gate (validation only — use fast model)
        if not self.should_skip("quality-gate", completed):
            try:
                agent = self._create_agent(use_fast_model=True)
                self._run_mini_crew(
                    "quality-gate",
                    [
                        Task(
                            description=QUALITY_GATE_DESCRIPTION,
                            expected_output="Arc42 Quality report written to quality/arc42-report.md",
                            agent=agent,
                        ),
                    ],
                )
            except Exception as e:
                logger.error(f"[Arc42] Quality gate failed, continuing: {e}")
        results.append("Quality Gate: Done")

        self._clear_checkpoint()
        summary = "\n".join(results)
        logger.info(f"[Arc42] All Mini-Crews completed:\n{summary}")
        return summary
