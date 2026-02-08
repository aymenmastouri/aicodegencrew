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
from ...shared.utils.logger import setup_logger

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
        """Create LLM instance."""
        from langchain_openai import ChatOpenAI

        provider = os.getenv("LLM_PROVIDER", "onprem")
        model = os.getenv("MODEL", "gpt-oss-120b")
        api_base = os.getenv("API_BASE", "http://sov-ai-platform.nue.local.vm:4000/v1")
        api_key = os.getenv("OPENAI_API_KEY", "dummy-key")

        llm = ChatOpenAI(
            model=model,
            base_url=api_base,
            api_key=api_key,
            temperature=0.2,
            max_tokens=8000,  # Allow long plans
        )

        # Set context window AFTER construction
        context_window = int(os.getenv("MAX_LLM_INPUT_TOKENS", "100000"))
        llm.context_window_size = context_window

        logger.info(f"[Stage4] Created LLM: {provider}/{model}")
        return llm

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
            response = self.llm.invoke(prompt)
            plan_json = self._extract_json(response.content)

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

DISCOVERED COMPONENTS:
{self._format_components(discovery.get("affected_components", []))}

DISCOVERED INTERFACES:
{self._format_interfaces(discovery.get("interfaces", []))}

DISCOVERED DEPENDENCIES:
{self._format_dependencies(discovery.get("dependencies", []))}

SIMILAR TEST PATTERNS (from 925 existing tests):
{self._format_test_patterns(patterns.get("test_patterns", []))}

SECURITY PATTERNS (from 143 security configs):
{self._format_security_patterns(patterns.get("security_patterns", []))}

VALIDATION PATTERNS (from 149 validation rules):
{self._format_validation_patterns(patterns.get("validation_patterns", []))}

ERROR HANDLING PATTERNS (from 23 error handlers):
{self._format_error_patterns(patterns.get("error_patterns", []))}

ARCHITECTURE CONTEXT:
- Style: {arch_style}
- Quality Grade: {arch_quality}

TASK:
Create a COMPLETE implementation plan as JSON following this structure:

{{
  "development_plan": {{
    "affected_components": [...],  // Use discovered components above
    "interfaces": [...],  // Use discovered interfaces above
    "dependencies": [...],  // Use discovered dependencies above

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
      "test_patterns": "925 tests from architecture_facts.json",
      "security": "143 security details from architecture_facts.json",
      "validation": "149 validation patterns from architecture_facts.json",
      "error_handling": "23 error patterns from architecture_facts.json",
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
- Implementation steps must be concrete and actionable

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
