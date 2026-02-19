"""
Stage 4: Plan Generator

Uses CrewAI Agent with MCPs to synthesize all previous stage outputs into a complete implementation plan.

MCPs Available:
- Sequential Thinking: Complex multi-step reasoning
- Memory: Learn from past mistakes
- Brave Search: Fetch current documentation
- Playwright: Web scraping for migration guides

Duration: 15-30 seconds (single agent task)
"""

import json
import os
import re
from typing import Any

from crewai import Agent, Crew, Process, Task

from ....shared.mcp import get_phase4_mcps
from ....shared.utils.logger import setup_logger
from ....shared.utils.llm_factory import create_llm
from ..schemas import ImplementationPlan, TaskInput

logger = setup_logger(__name__)


class PlanGeneratorStage:
    """
    Generate implementation plan using CrewAI Agent with MCPs.
    """

    def __init__(self, analyzed_architecture: dict = None, supplementary_context: dict = None):
        """
        Initialize plan generator.

        Args:
            analyzed_architecture: analyzed_architecture.json (from Phase 2)
            supplementary_context: Additional context by category
                {"requirements": "...", "logs": "...", "reference": "..."}
        """
        self.analyzed_architecture = analyzed_architecture or {}
        self.supplementary_context = supplementary_context or {}
        self._model = os.getenv("MODEL", "gpt-4o-mini")
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """Create planning agent with MCPs.

        MCPs provide tools automatically - no need to list them in prompts.
        CrewAI handles tool discovery and makes them available to the agent.
        """
        mcps = get_phase4_mcps()
        llm = create_llm()

        agent = Agent(
            role="Senior Software Architect & Development Planner",
            goal=(
                "Create evidence-based implementation plans grounded in discovered "
                "components, architecture facts, and best practices. "
                "Use your available tools when you need external information."
            ),
            backstory=(
                "You are a pragmatic software architect with 15+ years of experience. "
                "You plan upgrades, bugfixes, features, and refactorings for large enterprise "
                "codebases. You ALWAYS: (1) analyze discovered components first, "
                "(2) use your tools to search for current best practices when needed, "
                "(3) produce complete, actionable plans with file-level granularity."
            ),
            llm=llm,
            mcps=mcps,
            allow_delegation=False,
            verbose=True,
            max_iter=15,
            respect_context_window=True,
        )

        logger.info(f"[Stage4] Created planning agent with {len(mcps)} MCPs")
        return agent

    def run(
        self,
        task: TaskInput,
        discovery_result: dict[str, Any],
        pattern_result: dict[str, Any],
    ) -> ImplementationPlan:
        """
        Generate implementation plan using CrewAI agent with MCPs.

        Args:
            task: Task input (from Stage 1)
            discovery_result: Component discovery (from Stage 2)
            pattern_result: Pattern matching (from Stage 3)

        Returns:
            ImplementationPlan
        """
        logger.info(f"[Stage4] Generating plan with agent+MCPs for task: {task.task_id}")

        # Build task description
        description = self._build_task_description(task, discovery_result, pattern_result)
        expected = f"ImplementationPlan JSON object with task_id={task.task_id}, understanding, and development_plan sections"

        # Create CrewAI task (no output_pydantic — on-prem LLMs can truncate output,
        # causing CrewAI to raise ValidationError before our repair code runs).
        # Paths 2 and 3 below handle JSON parsing from json_dict / raw string.
        planning_task = Task(
            name=f"Plan: {task.summary[:50]}",  # Task name from input
            description=description,
            expected_output=expected,
            agent=self.agent,
        )

        # Run crew
        try:
            crew = Crew(
                agents=[self.agent],
                tasks=[planning_task],
                process=Process.sequential,
                verbose=False,
            )

            result = crew.kickoff()

            # CrewAI kickoff() returns CrewOutput with .pydantic, .json_dict, .raw
            plan = None

            # Path 1: Pydantic attribute present on result (rare — some CrewAI versions populate it)
            if hasattr(result, "pydantic") and isinstance(getattr(result, "pydantic", None), ImplementationPlan):
                plan = result.pydantic
                logger.info("[Stage4] Got plan from CrewOutput.pydantic")

            # Path 2: JSON dict available on CrewOutput
            elif hasattr(result, "json_dict") and result.json_dict:
                plan_json = result.json_dict
                plan = self._plan_from_dict(plan_json, task)
                logger.info("[Stage4] Got plan from CrewOutput.json_dict")

            # Path 3: Parse from raw string output
            else:
                raw = str(result).strip()
                if not raw:
                    raise ValueError(
                        "Agent returned empty result — check LLM connectivity "
                        "and ensure the model is responding."
                    )
                plan_json = self._extract_json(raw)
                plan = self._plan_from_dict(plan_json, task)
                logger.info("[Stage4] Got plan from CrewOutput.raw (parsed JSON)")

            logger.info("[Stage4] Generated plan successfully")

            return plan

        except Exception as e:
            logger.error(f"[Stage4] Agent plan generation failed: {e}")
            raise

    def _build_task_description(
        self,
        task: TaskInput,
        discovery: dict[str, Any],
        patterns: dict[str, Any],
    ) -> str:
        """Build task description for CrewAI agent."""

        # Extract architecture context
        arch_style = self.analyzed_architecture.get("macro_architecture", {}).get("style", "Unknown")
        arch_quality = self.analyzed_architecture.get("architecture_quality", {}).get("overall_grade", "C")

        prompt = f"""Create an evidence-based implementation plan for the task below.

Use the discovered components, architecture context, and patterns provided.
If you need current documentation or best practices, use your available tools.

TASK TYPE: {task.task_type}

TASK:
Task ID: {task.task_id}
Summary: {task.summary}
Description: {task.description}
Acceptance Criteria:
{self._format_list(task.acceptance_criteria)}

Labels: {", ".join(task.labels)}
Technical Notes (including JIRA comments):
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

ARCHITECTURE CONTEXT:
- Style: {arch_style}
- Quality Grade: {arch_quality}
{self._format_supplementary_context()}"""

        # Inject upgrade assessment if available
        upgrade = patterns.get("upgrade_assessment", {})
        if upgrade.get("is_upgrade"):
            summary = upgrade.get("summary", {})
            context = upgrade.get("upgrade_context", {})
            prompt += f"""
UPGRADE ASSESSMENT (from automated code scan):
Framework: {context.get("framework", "Unknown")}
Current Version: {context.get("current_version", "Unknown")}
Target Version: {context.get("target_version", "Unknown")}
Breaking Changes: {summary.get("breaking_changes", 0)}
Deprecated APIs: {summary.get("deprecated_apis", 0)}
Total Affected Files: {summary.get("total_affected_files", 0)}
Estimated Effort: {summary.get("estimated_effort_hours", 0)} hours

MIGRATION SEQUENCE (ordered by severity):
{self._format_migration_sequence(upgrade.get("migration_sequence", []))}

VERIFICATION COMMANDS:
{self._format_verification_commands(upgrade.get("verification_commands", []))}
{self._format_compatibility_report(upgrade.get("compatibility_report", {}))}"""

        # Build JSON schema section based on task type
        upgrade = patterns.get("upgrade_assessment", {})
        is_upgrade = upgrade.get("is_upgrade", False)

        upgrade_plan_schema = ""
        if is_upgrade:
            upgrade_plan_schema = """
    "upgrade_plan": {{
      "framework": "{upgrade.get('upgrade_context', {{}}).get('framework', 'Angular')}",
      "from_version": "{upgrade.get('upgrade_context', {{}}).get('current_version', 'unknown')}",
      "to_version": "{upgrade.get('upgrade_context', {{}}).get('target_version', 'unknown')}",
      "migration_sequence": [
        {{
          "rule_id": "rule ID from MIGRATION SEQUENCE above",
          "title": "Title",
          "severity": "breaking|deprecated|recommended",
          "migration_steps": ["Step 1", "Step 2"],
          "affected_files": ["file1.ts", "file2.ts"],
          "estimated_effort_minutes": <number>,
          "schematic": "ng generate command (if applicable)"
        }}
      ],
      "verification_commands": ["command 1", "command 2"],
      "total_estimated_effort_hours": <number>,
      "pre_migration_checks": ["Check 1", "Check 2"],
      "post_migration_checks": ["Check 1", "Check 2"]
    }},"""

        prompt += f"""
TASK:
Create a COMPLETE implementation plan as JSON following this structure:

{{
  "development_plan": {{
    "affected_components": [...],  // Use discovered components above
    "interfaces": [...],  // Use discovered interfaces above
    "dependencies": [...],  // Use discovered dependencies above
{upgrade_plan_schema}
    "implementation_steps": [
      "1. Concrete step (in ComponentName)",
      "2. Concrete step (in ComponentName)"
    ],

    "test_strategy": {{
      "unit_tests": ["Test description"],
      "integration_tests": ["Test description"],
      "similar_patterns": [...]  // Use test patterns above
    }},

    "security_considerations": [...],  // Use security patterns above
    "validation_strategy": [...],  // Use validation patterns above
    "error_handling": [...],  // Use error patterns above

    "architecture_context": {{
      "style": "{arch_style}",
      "layer_pattern": "Controller → Service → Repository",
      "quality_grade": "{arch_quality}",
      "layer_compliance": ["Check if changes follow layered architecture"]
    }},

    "estimated_complexity": "Low|Medium|High",
    "complexity_reasoning": "Reasoning...",
    "estimated_files_changed": <number>,
    "risks": ["Risk 1", "Risk 2"],

    "evidence_sources": {{
      "components": "architecture_facts.json",
      "test_patterns": "architecture_facts.json",
      "security": "architecture_facts.json",
      "validation": "architecture_facts.json",
      "error_handling": "architecture_facts.json",
      "architecture": "analyzed_architecture.json",
      "semantic_search": "ChromaDB"
    }}
  }}
}}

IMPORTANT:
- Return ONLY valid JSON (no markdown, no explanations)
- Use ONLY the components, patterns, and context provided above
- DO NOT invent new components or patterns
- ALL recommendations must reference the patterns above
- Implementation steps must be concrete and actionable{"" if not is_upgrade else chr(10) + "- For upgrade tasks: include ALL data from MIGRATION SEQUENCE above (rule_id, title, severity, migration_steps, affected_files, estimated_effort_minutes, schematic)" + chr(10) + "- Copy affected_files arrays from MIGRATION SEQUENCE - do NOT leave them empty" + chr(10) + "- Order migration_sequence by severity (breaking first, then deprecated, then recommended)"}

Generate the plan now:"""

        return prompt

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
    def _format_list(items: list) -> str:
        """Format list as numbered items."""
        if not items:
            return "  (none)"
        return "\n".join(f"  {i + 1}. {item}" for i, item in enumerate(items))

    @staticmethod
    def _format_components(components: list) -> str:
        """Format components."""
        if not components:
            return "  (none discovered)"

        lines = []
        for comp in components[:10]:  # Limit for token efficiency
            lines.append(
                f"  - {comp['name']} (ID: {comp['id']}, "
                f"stereotype: {comp['stereotype']}, layer: {comp['layer']}, "
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
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ('{', '['):
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()

        # If we're inside a string, close it
        if in_string:
            content += '"'

        # Close trailing comma before closing brackets
        content = re.sub(r',\s*$', '', content)

        # Close open structures in reverse order
        for opener in reversed(stack):
            content += ']' if opener == '[' else '}'

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

        return ImplementationPlan(
            task_id=task.task_id,
            source_files=[task.source_file],
            understanding=plan_json.get("understanding", {}),
            development_plan=plan_json.get("development_plan", {}),
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

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"[Stage4] Failed to parse JSON: {e}")
            logger.error(f"[Stage4] Content (first 500 chars): {content[:500]}")
            raise
