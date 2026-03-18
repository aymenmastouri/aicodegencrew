"""
Stage 4: Plan Generator — direct litellm call (deterministic Pipeline + LLM pattern)

Synthesizes all previous stage outputs into a complete implementation plan using a
single litellm.completion() call. The reviewer agent's checklist is applied as a
post-call validation via the existing validate_plan_json guardrail.

Duration: 20-60 seconds (single LLM call)
"""

import json
import re
from typing import Any

from ....shared.llm_generator import LLMGenerator
from ....shared.utils.logger import setup_logger
from ....shared.utils.task_guardrails import validate_plan_json
from ..schemas import ImplementationPlan, TaskInput

logger = setup_logger(__name__)


class PlanGeneratorStage:
    """
    Generate implementation plan via direct litellm.completion() call.

    Replaces the 2-agent mini-crew (planner + reviewer) with a single LLM call.
    The reviewer's quality checklist is applied post-call via validate_plan_json.
    """

    # Planner system prompt (was the planner agent backstory)
    _SYSTEM_MESSAGE = (
        "You are a pragmatic software architect with 15+ years of experience. "
        "You plan upgrades, bugfixes, features, and refactorings for large enterprise "
        "codebases.\n\n"
        "YOUR PROCESS — follow this exact order:\n"
        "A. READ the Task Description + Technical Notes (JIRA comments). "
        "   Understand: What is being asked? What has already been done? What remains?\n"
        "B. READ the TRIAGE ANALYSIS completely. It contains:\n"
        "   - Big Picture (North Star: why does this task exist?)\n"
        "   - Scope Boundary (what is IN and OUT)\n"
        "   - Architecture Walkthrough (where does this piece fit?)\n"
        "   - Context Boundaries (risks, constraints, blockers)\n"
        "   - Anticipated Questions (developer concerns, already answered)\n"
        "   Your plan MUST be CONSISTENT with the triage analysis.\n"
        "C. THEN look at discovered components, patterns, and facts.\n"
        "D. THEN create the plan for REMAINING work only.\n\n"
        "GOLDEN RULES:\n"
        "1. TRIAGE IS YOUR FOUNDATION: The triage analysis defines the scope, "
        "   constraints, and risks. Your plan must respect them. If triage says "
        "   something is OUT of scope, don't plan it. If triage flags a BLOCKING "
        "   boundary, your plan must address it.\n"
        "2. THINK, DON'T COPY: Migration rules, component lists, and patterns are "
        "   REFERENCE material, not a copy-paste template. Critically evaluate "
        "   what is actually relevant to the remaining work.\n"
        "3. CURRENT STATE MATTERS: JIRA comments describe real progress. "
        "   The plan must reflect REMAINING work only, not repeat completed work.\n"
        "4. CONCRETE VERSIONS: When the task involves version changes, state the "
        "   exact current and target versions. Do NOT use vague ranges.\n"
        "5. COMPONENTS: Use ONLY components from DISCOVERED COMPONENTS. "
        "   Never invent component names or file paths. "
        "   Every implementation_step must name the component AND its file_path.\n"
        "6. PATTERNS: Populate test_strategy, security_considerations, and "
        "   error_handling from provided patterns — don't leave them empty.\n"
        "7. EMPTY DATA: If discovered_components, patterns, or facts are empty or "
        "   missing, state that explicitly in the plan and skip sections that depend "
        "   on them. Never fabricate components or file paths to fill gaps."
    )

    def __init__(
        self,
        analyzed_architecture: dict = None,
        supplementary_context: dict = None,
        extract_facts: dict = None,
    ):
        """
        Initialize plan generator.

        Args:
            analyzed_architecture: analyzed_architecture.json (from Phase 2)
            supplementary_context: Additional context by category
                {"requirements": "...", "logs": "...", "reference": "..."}
            extract_facts: architecture_facts.json (from Phase 1) — contains
                tech_versions, containers, dependencies, etc.
        """
        self.analyzed_architecture = analyzed_architecture or {}
        self.supplementary_context = supplementary_context or {}
        self.extract_facts = extract_facts or {}
        self._generator = LLMGenerator(phase_id="plan")

    def run(
        self,
        task: TaskInput,
        discovery_result: dict[str, Any],
        pattern_result: dict[str, Any],
        triage_context: dict[str, Any] | None = None,
    ) -> ImplementationPlan:
        """
        Generate implementation plan using a direct litellm call.

        Args:
            task: Task input (from Stage 1)
            discovery_result: Component discovery (from Stage 2)
            pattern_result: Pattern matching (from Stage 3)
            triage_context: Optional context from triage phase (scope, boundaries)

        Returns:
            ImplementationPlan
        """
        logger.info("[Stage4] Generating plan with LLMGenerator for task: %s", task.task_id)

        # Build task description (user message content)
        description = self._build_task_description(task, discovery_result, pattern_result, triage_context)
        original_messages = [
            {"role": "system", "content": self._SYSTEM_MESSAGE},
            {"role": "user", "content": description},
        ]

        raw = self._generator.generate(original_messages)
        logger.info("[PlanLLM] Received %d chars", len(raw))

        if not raw.strip():
            raise ValueError(
                "LLM returned empty result — check LLM connectivity and ensure the model is responding."
            )

        plan_json = self._extract_json(raw)

        # Post-call validation: apply the reviewer's quality checklist via guardrail.
        # validate_plan_json expects an object with .raw or str() — pass the raw string.
        class _RawWrapper:
            def __init__(self, text: str):
                self.raw = text

        validation_result = validate_plan_json(_RawWrapper(raw))
        if isinstance(validation_result, tuple):
            ok, feedback = validation_result
        else:
            ok = bool(validation_result)
            feedback = "" if ok else str(validation_result)

        if not ok and feedback:
            logger.warning("[Stage4] Plan failed guardrail validation: %s — retrying", feedback)
            raw = self._generator.retry_with_feedback(
                original_messages=original_messages,
                previous_output=raw,
                issues=[feedback],
            )
            logger.info("[PlanLLM] Retry received %d chars", len(raw))
            if raw.strip():
                try:
                    plan_json = self._extract_json(raw)
                except Exception as e:
                    logger.warning("[Stage4] Retry JSON parse failed: %s — using original", e)

        plan = self._plan_from_dict(plan_json, task)
        logger.info("[Stage4] Generated plan successfully")
        return plan

    def _build_task_description(
        self,
        task: TaskInput,
        discovery: dict[str, Any],
        patterns: dict[str, Any],
        triage_context: dict[str, Any] | None = None,
    ) -> str:
        """Build task description for CrewAI agent."""

        # Extract architecture context
        arch_style = self.analyzed_architecture.get("macro_architecture", {}).get("style", "Unknown")
        arch_quality = self.analyzed_architecture.get("architecture_quality", {}).get("overall_grade", "C")
        arch_summary = self._format_architecture_analysis()

        prompt = f"""Create an implementation plan for the REMAINING work.

YOUR READING ORDER (follow this exactly):
1. Read the TASK DESCRIPTION + Technical Notes (JIRA comments) below
   → Understand: What is the goal? What has been done? What remains?
2. Read the TRIAGE ANALYSIS section (at the end)
   → It explains WHY this task exists, WHERE it fits architecturally,
     what the SCOPE is (IN/OUT), what RISKS exist, and what questions
     developers would ask. Your plan MUST be consistent with this.
3. THEN use discovered components, patterns, and facts as building blocks.

TASK TYPE: {task.task_type}

TASK INPUT:
Task ID: {task.task_id}
Summary: {task.summary}
Description: {task.description}
Acceptance Criteria:
{self._format_list(task.acceptance_criteria)}

Labels: {", ".join(task.labels)}
Technical Notes (including JIRA comments — READ THESE to understand current state):
{task.technical_notes[:3000] if task.technical_notes else "(none)"}

DISCOVERED COMPONENTS:
{self._format_components(discovery.get("affected_components", []))}

DISCOVERED INTERFACES:
{self._format_interfaces(discovery.get("interfaces", []))}

DISCOVERED DEPENDENCIES:
{self._format_dependencies(discovery.get("dependencies", []))}

SIMILAR TEST PATTERNS:
{self._format_test_patterns(patterns.get("test_patterns", []))}

SECURITY PATTERNS:
{self._format_security_patterns(patterns.get("security_patterns", []))}

VALIDATION PATTERNS:
{self._format_validation_patterns(patterns.get("validation_patterns", []))}

ERROR HANDLING PATTERNS:
{self._format_error_patterns(patterns.get("error_patterns", []))}

EXTRACTED FACTS (from Phase 1 — Extract):
{self._format_extract_facts()}

ARCHITECTURE CONTEXT (from Phase 2 — Analyze):
{arch_summary}
{self._format_supplementary_context()}
{self._format_triage_context(triage_context)}"""

        # Inject upgrade assessment if available
        upgrade = patterns.get("upgrade_assessment", {})
        if upgrade.get("is_upgrade"):
            summary = upgrade.get("summary", {})
            context = upgrade.get("upgrade_context", {})
            prompt += f"""
UPGRADE REFERENCE DATA (from automated code scan — use as REFERENCE, not copy-paste):
Framework: {context.get("framework", "Unknown")}
Detected Current Version: {context.get("current_version", "Unknown")}
Detected Target Version: {context.get("target_version", "Unknown")}
NOTE: Verify these versions against the task description and JIRA comments.
      The actual target version in the task description takes precedence.
Breaking Changes: {summary.get("breaking_changes", 0)}
Deprecated APIs: {summary.get("deprecated_apis", 0)}
Total Affected Files: {summary.get("total_affected_files", 0)}
Estimated Effort: {summary.get("estimated_effort_hours", 0)} hours

MIGRATION RULES REFERENCE (evaluate each rule — exclude rules already completed per JIRA comments):
{self._format_migration_sequence(upgrade.get("migration_sequence", []))}

VERIFICATION COMMANDS:
{self._format_verification_commands(upgrade.get("verification_commands", []))}
{self._format_compatibility_report(upgrade.get("compatibility_report", {}))}"""

        # Build JSON schema section based on task type
        upgrade = patterns.get("upgrade_assessment", {})
        is_upgrade = upgrade.get("is_upgrade", False)

        upgrade_plan_schema = ""
        if is_upgrade:
            uc = upgrade.get("upgrade_context", {})
            uc_framework = uc.get("framework", "Unknown")
            uc_from = uc.get("current_version", "unknown")
            uc_to = uc.get("target_version", "unknown")
            upgrade_plan_schema = f"""
    "upgrade_plan": {{
      "framework": "{uc_framework}",
      "from_version": "{uc_from}",
      "to_version": "{uc_to}",
      "migration_sequence": [
        {{
          "rule_id": "rule ID from MIGRATION SEQUENCE above",
          "title": "Title",
          "severity": "breaking|deprecated|recommended",
          "migration_steps": ["Step 1", "Step 2"],
          "affected_files": ["file1.ts", "file2.ts"],
          "estimated_effort_minutes": 15,
          "schematic": "ng generate command (if applicable)"
        }}
      ],
      "verification_commands": ["command 1", "command 2"],
      "total_estimated_effort_hours": 8,
      "pre_migration_checks": ["Check 1", "Check 2"],
      "post_migration_checks": ["Check 1", "Check 2"]
    }},"""

        # Extract actual layer pattern from analyzed architecture if available
        layer_pattern = self.analyzed_architecture.get("macro_architecture", {}).get("layer_pattern") or (
            arch_style if arch_style != "Unknown" else "Presentation → Service → Repository → Domain"
        )

        prompt += f"""
OUTPUT INSTRUCTIONS:
Create a COMPLETE implementation plan as JSON following this EXACT structure.
Replace ALL placeholder values with REAL data from DISCOVERED COMPONENTS and patterns above.

{{
  "development_plan": {{
    "affected_components": [
      {{
        "id": "<ID from DISCOVERED COMPONENTS>",
        "name": "<name from DISCOVERED COMPONENTS>",
        "stereotype": "<stereotype from DISCOVERED COMPONENTS>",
        "layer": "<layer from DISCOVERED COMPONENTS>",
        "file_path": "<file_path from DISCOVERED COMPONENTS>",
        "relevance_score": <relevance_score from DISCOVERED COMPONENTS>,
        "change_type": "<change_type from DISCOVERED COMPONENTS>"
      }}
    ],
    "interfaces": [...],
    "dependencies": [...],
{upgrade_plan_schema}
    "implementation_steps": [
      "1. Action verb + ComponentName (file_path) — what changes and why",
      "2. Action verb + ComponentName (file_path) — what changes and why",
      "3. Run verification: <command>"
    ],

    "test_strategy": {{
      "unit_tests": ["Describe unit test for <ComponentName>"],
      "integration_tests": ["Describe integration test for <feature>"],
      "similar_patterns": []
    }},

    "security_considerations": [],
    "validation_strategy": [],
    "error_handling": [],

    "architecture_context": {{
      "style": "{arch_style}",
      "layer_pattern": "{layer_pattern}",
      "quality_grade": "{arch_quality}",
      "layer_compliance": ["Describe compliance check for this change"]
    }},

    "estimated_complexity": "Low|Medium|High",
    "complexity_reasoning": "Explain why this complexity was chosen",
    "estimated_files_changed": <number>,
    "risks": ["Risk 1", "Risk 2"],

    "evidence_sources": {{
      "components": "architecture_facts.json",
      "test_patterns": "architecture_facts.json",
      "architecture": "analyzed_architecture.json",
      "semantic_search": "Qdrant"
    }}
  }}
}}

MANDATORY RULES:
- Return ONLY valid JSON (no markdown, no explanations outside JSON)
- READ Technical Notes FIRST: Understand what work has been done and what remains
- affected_components: use EXACT objects from DISCOVERED COMPONENTS (id, name, stereotype, layer, file_path, relevance_score, change_type) — only include components relevant to REMAINING work
- implementation_steps: EVERY step must name the component AND its file path. Plan only steps that STILL NEED TO BE DONE.
- DO NOT invent component names or file paths not listed in DISCOVERED COMPONENTS
- test_strategy, security_considerations, error_handling: populate from patterns above — do NOT leave empty{"" if not is_upgrade else chr(10) + "- MIGRATION SEQUENCE is reference data from automated scanning. Critically evaluate each rule:" + chr(10) + "  - If JIRA comments indicate a rule was already applied, EXCLUDE it from the plan" + chr(10) + "  - If a rule has 0 occurrences, it may already be migrated — verify against comments" + chr(10) + "  - Only include rules that represent ACTUAL remaining work" + chr(10) + "- State exact from_version and to_version from the task description (not ranges)" + chr(10) + "- Order migration_sequence by severity (breaking first, then deprecated, then recommended)"}

Generate the plan now:"""

        return prompt

    def _format_extract_facts(self) -> str:
        """Format key facts from the Extract phase for the LLM prompt.

        Includes technology versions, system containers, and key dependencies
        so the agent knows the ACTUAL current state of the codebase.
        """
        facts = self.extract_facts
        if not facts:
            return "  (no extract facts available)"

        parts = []

        # System overview
        system = facts.get("system", {})
        stats = system.get("statistics", {})
        if stats:
            parts.append(
                f"System: {system.get('name', '?')} — "
                f"{stats.get('total_files', '?')} files, "
                f"{stats.get('total_lines', '?')} lines"
            )

        # Containers (system structure)
        containers = facts.get("containers", [])
        if containers:
            lines = []
            for c in containers:
                name = c.get("name", "?")
                tech = c.get("technology", "?")
                version = c.get("version", "")
                ver_str = f" {version}" if version else ""
                lines.append(f"  - {name} ({tech}{ver_str})")
            parts.append("Containers:\n" + "\n".join(lines))

        # Technology versions (CRITICAL for upgrade tasks)
        tech_versions = facts.get("tech_versions", [])
        if tech_versions:
            lines = []
            for t in tech_versions:
                name = t.get("technology", "?")
                version = t.get("version", "?")
                category = t.get("category", "")
                cat_str = f" [{category}]" if category else ""
                lines.append(f"  - {name} {version}{cat_str}")
            parts.append("Current Technology Versions:\n" + "\n".join(lines))

        # Key dependencies (top 20 by relevance)
        deps = facts.get("dependencies", [])
        if deps:
            # Show a compact summary
            dep_count = len(deps)
            # Group by type if possible
            runtime = [d for d in deps if d.get("scope") in ("runtime", "compile", "implementation", "")]
            dev = [d for d in deps if d.get("scope") in ("dev", "devDependencies", "test", "testImplementation")]
            lines = [f"  Total: {dep_count} dependencies"]
            # Show first 15 runtime deps compactly
            for d in runtime[:15]:
                name = d.get("name", "?")
                version = d.get("version", "")
                ver_str = f" {version}" if version else ""
                lines.append(f"  - {name}{ver_str}")
            if len(runtime) > 15:
                lines.append(f"  ... and {len(runtime) - 15} more runtime dependencies")
            parts.append("Key Dependencies:\n" + "\n".join(lines))

        # Build system
        build = facts.get("build_system", [])
        if build:
            lines = []
            for b in build[:5]:
                name = b.get("tool", b.get("name", "?"))
                version = b.get("version", "")
                ver_str = f" {version}" if version else ""
                lines.append(f"  - {name}{ver_str}")
            parts.append("Build System:\n" + "\n".join(lines))

        if not parts:
            return "  (no extract facts available)"

        return "\n".join(parts)

    def _format_architecture_analysis(self) -> str:
        """Format the full architecture analysis for the LLM prompt.

        Includes executive summary, macro architecture, quality assessment,
        and system statistics — so the agent understands the codebase it
        is planning changes for.
        """
        arch = self.analyzed_architecture
        if not arch:
            return "  (no architecture analysis available)"

        parts = []

        # Executive summary
        summary = arch.get("executive_summary", "")
        if summary:
            parts.append(f"Summary: {summary}")

        # Macro architecture
        macro = arch.get("macro_architecture", {})
        if macro:
            style = macro.get("style", "Unknown")
            reasoning = macro.get("reasoning", "")
            deploy = macro.get("deployment_model", "")
            comm = macro.get("communication_pattern", "")
            line = f"Style: {style}"
            if deploy:
                line += f", Deployment: {deploy}"
            if comm:
                line += f", Communication: {comm}"
            parts.append(line)
            if reasoning:
                parts.append(f"Details: {reasoning[:500]}")

        # Quality assessment
        quality = arch.get("architecture_quality", {})
        if quality:
            grade = quality.get("overall_grade", "?")
            soc = quality.get("separation_of_concerns", "?")
            coupling = quality.get("coupling_assessment", "?")
            violations = quality.get("layer_violations_count", 0)
            rpc = quality.get("relations_per_component", 0)
            parts.append(
                f"Quality: Grade {grade}, Separation: {soc}, "
                f"Coupling: {coupling}, Layer Violations: {violations}, "
                f"Relations/Component: {rpc}"
            )

        # Statistics
        stats = arch.get("statistics", {})
        if stats:
            parts.append(
                f"Scale: {stats.get('total_components', '?')} components, "
                f"{stats.get('total_relations', '?')} relations, "
                f"{stats.get('total_interfaces', '?')} interfaces, "
                f"{stats.get('containers_analyzed', '?')} containers"
            )

        # Top recommendations
        recs = arch.get("top_recommendations", [])
        if recs:
            parts.append("Recommendations:\n" + "\n".join(f"  - {r}" for r in recs[:5]))

        return "\n".join(f"  {p}" for p in parts) if parts else "  (no architecture analysis available)"

    def _format_supplementary_context(self) -> str:
        """Format supplementary files (requirements, logs, reference) for LLM prompt."""
        if not self.supplementary_context:
            return ""

        sections = []
        labels = {
            "requirements": "REQUIREMENTS DOCUMENTS",
            "logs": "APPLICATION LOGS",
            "reference": "REFERENCE MATERIALS",
        }

        for category, content in self.supplementary_context.items():
            label = labels.get(category, category.upper())
            sections.append(f"\n{label}:\n{content}")

        return "\n".join(sections)

    @staticmethod
    def _format_triage_context(triage_context: dict | None) -> str:
        """Format triage phase output for LLM prompt.

        Includes the full triage analysis: classification, big picture,
        scope, context boundaries, architecture notes.  The Plan agent
        should read and understand this before building its plan.
        """
        if not triage_context:
            return ""

        parts = []

        # Classification
        ctype = triage_context.get("classification_type", "")
        conf = triage_context.get("classification_confidence", 0)
        if ctype:
            parts.append(f"CLASSIFICATION: {ctype} (confidence: {conf})")

        # Big Picture — the most important context for understanding the task
        big_picture = triage_context.get("big_picture", "")
        if big_picture:
            parts.append(f"BIG PICTURE (read this first — explains what this task is about):\n{big_picture}")

        # Scope
        scope = triage_context.get("scope_boundary", "")
        if scope:
            parts.append(f"SCOPE BOUNDARY (what is IN and OUT of this task):\n{scope}")

        # Classification Assessment (evidence for/against)
        assessment = triage_context.get("classification_assessment", "")
        if assessment:
            parts.append(f"CLASSIFICATION ASSESSMENT:\n{assessment}")

        # Context Boundaries — risks, constraints, dependencies
        boundaries = triage_context.get("context_boundaries", [])
        if boundaries:
            lines = []
            for b in boundaries:
                sev = b.get("severity", "info").upper()
                cat = b.get("category", "").replace("_", " ").title()
                text = b.get("boundary", "")
                sources = b.get("source_facts", [])
                line = f"  [{sev}] {cat}: {text}"
                if sources:
                    line += f"\n    Sources: {', '.join(sources[:5])}"
                lines.append(line)
            parts.append("CONTEXT BOUNDARIES (risks, constraints — plan must address these):\n" + "\n".join(lines))

        # Affected components from triage
        components = triage_context.get("affected_components", [])
        if components:
            parts.append("TRIAGE-IDENTIFIED COMPONENTS:\n" + "\n".join(f"  - {c}" for c in components))

        # Architecture Walkthrough
        arch_notes = triage_context.get("architecture_notes", "")
        if arch_notes:
            parts.append(f"ARCHITECTURE WALKTHROUGH (where does this piece fit?):\n{arch_notes}")

        # Anticipated Questions — developer concerns already answered by triage
        questions = triage_context.get("anticipated_questions", [])
        if questions:
            lines = []
            for q in questions:
                if isinstance(q, dict):
                    lines.append(f"  Q: {q.get('question', '')}\n  A: {q.get('answer', '')}")
            if lines:
                parts.append(
                    "ANTICIPATED QUESTIONS (developer concerns — your plan should address these):\n"
                    + "\n".join(lines)
                )

        if not parts:
            return ""

        return (
            "\n\nTRIAGE ANALYSIS (from Triage Phase). "
            "READ THIS CAREFULLY — it defines the scope, constraints, and context for your plan.\n"
            "Your plan MUST be consistent with this analysis. Do NOT plan work that is OUT of scope.\n"
            "Do NOT ignore BLOCKING boundaries — your plan must address them.\n\n"
            + "\n\n".join(parts)
        )

    @staticmethod
    def _format_list(items: list) -> str:
        """Format list as numbered items."""
        if not items:
            return "  (none)"
        return "\n".join(f"  {i + 1}. {item}" for i, item in enumerate(items))

    @staticmethod
    def _format_components(components: list) -> str:
        """Format components with file paths for Phase 5 resolution."""
        if not components:
            return "  (none discovered)"

        lines = []
        for comp in components[:15]:  # Slightly higher limit — file paths are critical
            file_path = comp.get("file_path", "")
            file_info = f", file: {file_path}" if file_path else ""
            lines.append(
                f"  - {comp['name']} (ID: {comp['id']}, "
                f"stereotype: {comp['stereotype']}, layer: {comp['layer']}{file_info}, "
                f"relevance: {comp['relevance_score']}, change_type: {comp['change_type']})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_interfaces(interfaces: list) -> str:
        """Format interfaces."""
        if not interfaces:
            return "  (none discovered)"

        lines = []
        for iface in interfaces[:10]:
            lines.append(
                f"  - {iface.get('method', '')} {iface.get('path', '')} "
                f"(implemented_by: {iface.get('implemented_by', '')})"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_dependencies(dependencies: list) -> str:
        """Format dependencies."""
        if not dependencies:
            return "  (none discovered)"

        lines = []
        for dep in dependencies[:10]:
            lines.append(f"  - {dep['from_component']} → {dep['to_component']} ({dep['relation_type']})")
        return "\n".join(lines)

    @staticmethod
    def _format_test_patterns(patterns: list) -> str:
        """Format test patterns."""
        if not patterns:
            return "  (none found)"

        lines = []
        for p in patterns[:5]:
            lines.append(
                f"  - {p['name']} ({p['framework']}, {p['test_type']}, "
                f"relevance: {p['relevance_score']})\n"
                f"    File: {p['file_path']}\n"
                f"    Pattern: {p['pattern_description']}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_security_patterns(patterns: list) -> str:
        """Format security patterns."""
        if not patterns:
            return "  (none found)"

        lines = []
        for p in patterns[:5]:
            lines.append(f"  - {p['security_type']} in {p['class_name']}\n    Recommendation: {p['recommendation']}")
        return "\n".join(lines)

    @staticmethod
    def _format_validation_patterns(patterns: list) -> str:
        """Format validation patterns."""
        if not patterns:
            return "  (none found)"

        lines = []
        for p in patterns[:5]:
            lines.append(
                f"  - {p['validation_type']} on {p['target_class']}\n    Recommendation: {p['recommendation']}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_error_patterns(patterns: list) -> str:
        """Format error patterns."""
        if not patterns:
            return "  (none found)"

        lines = []
        for p in patterns[:5]:
            lines.append(
                f"  - {p['exception_class']} ({p['handling_type']})\n    Recommendation: {p['recommendation']}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_migration_sequence(sequence: list) -> str:
        """Format migration sequence for LLM prompt."""
        if not sequence:
            return "  (none)"

        lines = []
        for i, step in enumerate(sequence, 1):
            severity = step.get("severity", "unknown")
            affected_files = step.get("affected_files", [])
            file_count = len(affected_files)

            lines.append(
                f"  {i}. [{severity.upper()}] {step.get('title', '')}\n"
                f"     Rule: {step.get('rule_id', '')}\n"
                f"     Occurrences: {step.get('occurrences', 0)} in {file_count} files\n"
                f"     Effort: {step.get('estimated_effort_minutes', 0)} min\n"
                f"     Steps: {'; '.join(step.get('migration_steps', []))}"
            )

            # Show affected files (first 10 for brevity)
            if affected_files:
                files_to_show = affected_files[:10]
                files_str = ", ".join(files_to_show)
                if file_count > 10:
                    files_str += f", ... ({file_count - 10} more)"
                lines.append(f"     Affected Files: {files_str}")

            schematic = step.get("schematic")
            if schematic:
                lines.append(f"     Schematic: {schematic}")
        return "\n".join(lines)

    @staticmethod
    def _format_verification_commands(commands: list) -> str:
        """Format verification commands for LLM prompt."""
        if not commands:
            return "  (none)"
        return "\n".join(f"  - {cmd}" for cmd in commands)

    @staticmethod
    def _format_compatibility_report(compat: dict) -> str:
        """Format dependency compatibility report for LLM prompt."""
        checks = compat.get("checks", [])
        if not checks:
            return ""

        lines = ["\nDEPENDENCY COMPATIBILITY:"]
        status_icons = {
            "compatible": "OK",
            "needs_bump": "BUMP",
            "conflict": "CONFLICT",
            "unknown": "??",
        }
        for c in checks:
            icon = status_icons.get(c.get("status", ""), "??")
            lines.append(
                f"  [{icon}] {c['name']}: current={c.get('current_version', '?')} "
                f"required={c.get('required_spec', '?')}"
            )
            if c.get("message"):
                lines.append(f"         {c['message']}")

        warnings = compat.get("warnings", [])
        if warnings:
            lines.append("\nCOMPATIBILITY WARNINGS:")
            for w in warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)

    @staticmethod
    def _repair_truncated_json(content: str) -> str:
        """Repair truncated JSON by closing open structures.

        The on-prem LLM sometimes truncates output at the token limit,
        leaving unclosed arrays, objects, or strings. This method closes
        them to produce valid (but incomplete) JSON.
        """
        content = content.rstrip()

        # Track open structures
        in_string = False
        escape_next = False
        stack = []  # Track open { and [

        for ch in content:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ("{", "["):
                stack.append(ch)
            elif ch == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif ch == "]" and stack and stack[-1] == "[":
                stack.pop()

        # If we're inside a string, close it
        if in_string:
            content += '"'

        # Close trailing comma before closing brackets
        content = re.sub(r",\s*$", "", content)

        # Close open structures in reverse order
        for opener in reversed(stack):
            content += "]" if opener == "[" else "}"

        return content

    def _plan_from_dict(self, plan_json: dict, task: "TaskInput") -> "ImplementationPlan":
        """Build ImplementationPlan from a parsed JSON dict."""
        if not isinstance(plan_json, dict):
            raise ValueError(f"Expected dict, got {type(plan_json).__name__}")

        if "development_plan" not in plan_json:
            plan_json = {"development_plan": plan_json}

        if "understanding" not in plan_json:
            plan_json["understanding"] = {
                "summary": task.summary,
                "requirements": [],
                "acceptance_criteria": task.acceptance_criteria,
                "technical_notes": task.technical_notes,
            }

        # Coerce string values to dicts — on-prem LLM sometimes returns strings
        # instead of dicts for structured fields (MEMORY.md item 13)
        understanding_raw = plan_json.get("understanding") or {}
        if isinstance(understanding_raw, str):
            understanding_raw = {"summary": understanding_raw}

        development_plan_raw = plan_json.get("development_plan") or {}
        if isinstance(development_plan_raw, str):
            development_plan_raw = {"raw": development_plan_raw}

        return ImplementationPlan(
            task_id=task.task_id,
            source_files=[task.source_file],
            understanding=understanding_raw,
            development_plan=development_plan_raw,
        )

    @staticmethod
    def _extract_json(content: str) -> dict:
        """Extract JSON from LLM response."""
        content = content.strip()

        if not content:
            raise ValueError("Cannot extract JSON from empty response")

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        if not content:
            raise ValueError("Response contained only markdown fencing, no JSON content")

        import re as _re

        # Use strict=False to accept control characters (raw newlines/tabs)
        # inside JSON string values — common with on-prem LLMs.
        try:
            return json.loads(content, strict=False)
        except json.JSONDecodeError:
            pass

        # Strip trailing text after last }
        last_brace = content.rfind("}")
        if last_brace > 0 and last_brace < len(content) - 1:
            try:
                return json.loads(content[: last_brace + 1], strict=False)
            except json.JSONDecodeError:
                pass

        # Fix missing commas between properties (LLM omits them)
        fixed = _re.sub(r'"\s*\n(\s*)"', r'",\n\1"', content)
        fixed = _re.sub(r'}\s*\n(\s*)"', r'},\n\1"', fixed)
        fixed = _re.sub(r']\s*\n(\s*)"', r'],\n\1"', fixed)
        fixed = _re.sub(r'(true|false|null|\d+)\s*\n(\s*)"', r'\1,\n\2"', fixed)
        if fixed != content:
            try:
                return json.loads(fixed, strict=False)
            except json.JSONDecodeError:
                content = fixed  # Use for further repair

        # LLM may truncate output at token limit — attempt repair before giving up
        try:
            repaired = PlanGeneratorStage._repair_truncated_json(content)
            return json.loads(repaired, strict=False)
        except Exception as e:
            logger.error("[Stage4] Failed to parse JSON (repair also failed): %s", e)
            logger.error("[Stage4] Content (first 500 chars): %s", content[:500])
            raise
