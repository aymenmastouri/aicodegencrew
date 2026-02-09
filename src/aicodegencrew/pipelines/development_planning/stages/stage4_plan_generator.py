"""
Stage 4: Plan Generator

Uses LLM to synthesize all previous stage outputs into a complete implementation plan.

This is the ONLY stage that uses LLM.

Duration: 15-30 seconds (single LLM call)
"""

import os
import json
from typing import Dict, Any

from ..schemas import TaskInput, ImplementationPlan
from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class PlanGeneratorStage:
    """
    Generate implementation plan using LLM (single call).
    """

    def __init__(self, analyzed_architecture: dict = None):
        """
        Initialize plan generator.

        Args:
            analyzed_architecture: analyzed_architecture.json (from Phase 2)
        """
        self.analyzed_architecture = analyzed_architecture or {}
        self.llm = self._create_llm()

    def _create_llm(self):
        """Create OpenAI-compatible LLM client."""
        from openai import OpenAI

        provider = os.getenv("LLM_PROVIDER", "onprem")
        self._model = os.getenv("MODEL", "gpt-oss-120b")
        api_base = os.getenv("API_BASE", "http://sov-ai-platform.nue.local.vm:4000/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key")

        client = OpenAI(base_url=api_base, api_key=api_key)

        logger.info(f"[Stage4] Created LLM: {provider}/{self._model}")
        return client

    def run(
        self,
        task: TaskInput,
        discovery_result: Dict[str, Any],
        pattern_result: Dict[str, Any],
    ) -> ImplementationPlan:
        """
        Generate implementation plan using LLM.

        Args:
            task: Task input (from Stage 1)
            discovery_result: Component discovery (from Stage 2)
            pattern_result: Pattern matching (from Stage 3)

        Returns:
            ImplementationPlan
        """
        logger.info(f"[Stage4] Generating plan with LLM for task: {task.task_id}")

        # Build prompt
        prompt = self._build_prompt(task, discovery_result, pattern_result)

        # LLM call
        try:
            response = self.llm.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=8000,
            )
            plan_json = self._extract_json(response.choices[0].message.content)

            # Validate structure
            if not isinstance(plan_json, dict):
                raise ValueError("LLM did not return valid JSON")

            # Ensure required keys
            if "development_plan" not in plan_json:
                plan_json = {"development_plan": plan_json}

            if "understanding" not in plan_json:
                plan_json["understanding"] = {
                    "summary": task.summary,
                    "requirements": [],
                    "acceptance_criteria": task.acceptance_criteria,
                    "technical_notes": task.technical_notes,
                }

            # Add metadata
            plan_json["task_id"] = task.task_id
            plan_json["source_files"] = [task.source_file]

            # Create ImplementationPlan
            plan = ImplementationPlan(
                task_id=task.task_id,
                source_files=[task.source_file],
                understanding=plan_json.get("understanding", {}),
                development_plan=plan_json.get("development_plan", {}),
            )

            logger.info(f"[Stage4] Generated plan successfully")

            return plan

        except Exception as e:
            logger.error(f"[Stage4] LLM plan generation failed: {e}")
            raise

    def _build_prompt(
        self,
        task: TaskInput,
        discovery: Dict[str, Any],
        patterns: Dict[str, Any],
    ) -> str:
        """Build prompt for LLM."""

        # Extract architecture context
        arch_style = self.analyzed_architecture.get("macro_architecture", {}).get("style", "Unknown")
        arch_quality = self.analyzed_architecture.get("architecture_quality", {}).get("overall_grade", "C")

        prompt = f"""You are a senior software architect creating an evidence-based implementation plan.

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
"""

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
"""

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

    @staticmethod
    def _format_list(items: list) -> str:
        """Format list as numbered items."""
        if not items:
            return "  (none)"
        return "\n".join(f"  {i+1}. {item}" for i, item in enumerate(items))

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
            lines.append(
                f"  - {dep['from_component']} → {dep['to_component']} "
                f"({dep['relation_type']})"
            )
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
            lines.append(
                f"  - {p['security_type']} in {p['class_name']}\n"
                f"    Recommendation: {p['recommendation']}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_validation_patterns(patterns: list) -> str:
        """Format validation patterns."""
        if not patterns:
            return "  (none found)"

        lines = []
        for p in patterns[:5]:
            lines.append(
                f"  - {p['validation_type']} on {p['target_class']}\n"
                f"    Recommendation: {p['recommendation']}"
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
                f"  - {p['exception_class']} ({p['handling_type']})\n"
                f"    Recommendation: {p['recommendation']}"
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
            affected_files = step.get('affected_files', [])
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
    def _extract_json(content: str) -> dict:
        """Extract JSON from LLM response."""
        # Remove markdown code blocks if present
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"[Stage4] Failed to parse JSON: {e}")
            logger.error(f"[Stage4] Content: {content[:500]}")
            raise
