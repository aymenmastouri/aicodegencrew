"""Documentation Quality Gate Tool - Validates Phase 2 outputs against evidence-first principles.

This tool enforces:
1. Evidence ID coverage (minimum 30%)
2. No invented facts (all claims must exist in architecture_facts.json)
3. No generic phrases ("UNKNOWN (no evidence extracted)")
4. Runtime workflow evidence traceability
5. Required chapters present
"""

import json
import re
from pathlib import Path
from typing import Type, Dict, List, Any, Optional, Set
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocQualityGateInput(BaseModel):
    """Input schema for DocQualityGateTool."""
    docs_dir: str = Field(..., description="Directory containing generated docs (e.g., knowledge/architecture/arc42)")
    facts_path: str = Field(..., description="Path to architecture_facts.json")
    output_path: str = Field(..., description="Path to save quality report")
    min_evidence_coverage: float = Field(default=0.30, description="Minimum evidence ID coverage (0.0-1.0)")


class DocQualityGateTool(BaseTool):
    """
    Quality gate for generated architecture documentation.

    Validates:
    - Evidence ID presence and coverage
    - No invented components/relations (all must exist in facts)
    - No banned phrases like "UNKNOWN (no evidence extracted)"
    - Required chapters exist
    - Runtime workflows have evidence
    """

    name: str = "doc_quality_gate"
    description: str = (
        "Validates generated architecture documentation against facts. "
        "Checks evidence coverage, detects invented claims, enforces evidence-first compliance."
    )
    args_schema: Type[BaseModel] = DocQualityGateInput

    # Banned phrases that indicate facts were not consulted
    BANNED_PHRASES = [
        "UNKNOWN (no evidence extracted)",
        "no evidence extracted",
        "not extracted from code",
        "no facts available",
        "keine Fakten extrahiert",
    ]

    # Generic filler phrases that lack specificity
    GENERIC_PHRASES = [
        "provides functionality",
        "handles requests",
        "manages data",
        "implements logic",
        "orchestrates",
        "coordinates",
    ]

    def _run(
        self,
        docs_dir: str,
        facts_path: str,
        output_path: str,
        min_evidence_coverage: float = 0.30,
    ) -> str:
        """
        Run quality gate checks on generated documentation.

        Args:
            docs_dir: Directory with generated docs
            facts_path: Path to architecture_facts.json
            output_path: Where to save report
            min_evidence_coverage: Minimum evidence coverage (default 30%)

        Returns:
            JSON string with validation results
        """
        try:
            docs_path = Path(docs_dir)
            facts_file = Path(facts_path)

            if not docs_path.exists():
                return json.dumps({"error": f"Docs directory not found: {docs_dir}", "status": "FAIL"})

            if not facts_file.exists():
                return json.dumps({"error": f"Facts file not found: {facts_path}", "status": "FAIL"})

            # Load facts
            with open(facts_file, 'r', encoding='utf-8') as f:
                facts = json.load(f)

            # Run checks
            checks = []

            # Check 1: Evidence ID coverage
            coverage_check = self._check_evidence_coverage(docs_path, facts, min_evidence_coverage)
            checks.append(coverage_check)

            # Check 2: Banned phrases
            banned_check = self._check_banned_phrases(docs_path)
            checks.append(banned_check)

            # Check 3: Invented facts detection
            invented_check = self._check_invented_facts(docs_path, facts)
            checks.append(invented_check)

            # Check 4: Required chapters
            required_check = self._check_required_chapters(docs_path)
            checks.append(required_check)

            # Check 5: Generic content detection
            generic_check = self._check_generic_content(docs_path)
            checks.append(generic_check)

            # Calculate overall status
            passed = sum(1 for c in checks if c["status"] == "PASS")
            failed = len(checks) - passed
            overall_status = "PASS" if failed == 0 else "FAIL"

            # Generate report
            report = self._generate_report(checks, overall_status, passed, failed)

            # Save report
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"Quality gate {overall_status}: {passed}/{len(checks)} checks passed")

            result = {
                "status": overall_status,
                "passed": passed,
                "failed": failed,
                "total_checks": len(checks),
                "checks": checks,
                "report_path": str(output_file),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Quality gate error: {e}")
            return json.dumps({"error": str(e), "status": "ERROR"})

    def _check_evidence_coverage(
        self,
        docs_path: Path,
        facts: Dict,
        min_coverage: float
    ) -> Dict[str, Any]:
        """Check evidence ID coverage in documentation."""
        # Extract all evidence IDs from facts
        available_evidence = set()

        for component in facts.get("components", []):
            available_evidence.update(component.get("evidence", []))

        for interface in facts.get("interfaces", []):
            available_evidence.update(interface.get("evidence", []))

        for relation in facts.get("relations", []):
            available_evidence.update(relation.get("evidence", []))

        for container in facts.get("containers", []):
            available_evidence.update(container.get("evidence", []))

        # Extract evidence IDs referenced in docs
        referenced_evidence = set()
        evidence_pattern = re.compile(r'\[?ev_[a-z_]+_\d+\]?')

        for doc_file in docs_path.rglob("*.md"):
            content = doc_file.read_text(encoding='utf-8')
            matches = evidence_pattern.findall(content)
            for match in matches:
                ev_id = match.strip('[]')
                referenced_evidence.add(ev_id)

        # Calculate coverage
        if len(available_evidence) == 0:
            coverage = 0.0
        else:
            coverage = len(referenced_evidence) / len(available_evidence)

        if coverage >= min_coverage:
            return {
                "name": "Evidence ID Coverage",
                "status": "PASS",
                "message": f"Evidence coverage: {coverage:.1%} (threshold: {min_coverage:.1%})",
                "details": {
                    "available": len(available_evidence),
                    "referenced": len(referenced_evidence),
                    "coverage": coverage,
                }
            }
        else:
            return {
                "name": "Evidence ID Coverage",
                "status": "FAIL",
                "message": f"Evidence coverage too low: {coverage:.1%} (required: {min_coverage:.1%})",
                "details": {
                    "available": len(available_evidence),
                    "referenced": len(referenced_evidence),
                    "coverage": coverage,
                }
            }

    def _check_banned_phrases(self, docs_path: Path) -> Dict[str, Any]:
        """Check for banned phrases that indicate facts not consulted."""
        violations = []

        for doc_file in docs_path.rglob("*.md"):
            content = doc_file.read_text(encoding='utf-8')

            for phrase in self.BANNED_PHRASES:
                if phrase.lower() in content.lower():
                    count = content.lower().count(phrase.lower())
                    violations.append(f"{doc_file.name}: '{phrase}' appears {count} times")

        if violations:
            return {
                "name": "Banned Phrases Check",
                "status": "FAIL",
                "message": f"Found {len(violations)} banned phrase violations",
                "details": violations[:10],  # Limit to first 10
            }
        else:
            return {
                "name": "Banned Phrases Check",
                "status": "PASS",
                "message": "No banned phrases found",
            }

    def _check_invented_facts(self, docs_path: Path, facts: Dict) -> Dict[str, Any]:
        """Check for component/relation claims not present in facts."""
        # Build set of known component names and IDs
        known_components = set()
        for comp in facts.get("components", []):
            known_components.add(comp.get("name", "").lower())
            known_components.add(comp.get("id", "").lower())

        # Pattern to detect component references (CamelCase class names)
        component_pattern = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+(?:Controller|Service|Repository|Impl|Entity)?)\b')

        violations = []

        for doc_file in docs_path.rglob("*.md"):
            content = doc_file.read_text(encoding='utf-8')

            # Find potential component references
            matches = component_pattern.findall(content)
            for match in matches:
                if match.lower() not in known_components and len(violations) < 20:
                    # Check if it's a common word (not a component)
                    if match not in ["Unknown", "Request", "Response", "Exception", "Error"]:
                        violations.append(f"{doc_file.name}: References '{match}' (not in facts)")

        if len(violations) > 5:  # Allow some false positives
            return {
                "name": "Invented Facts Detection",
                "status": "WARN",
                "message": f"Found {len(violations)} potential invented component references",
                "details": violations[:10],
            }
        else:
            return {
                "name": "Invented Facts Detection",
                "status": "PASS",
                "message": "No significant invented facts detected",
            }

    def _check_required_chapters(self, docs_path: Path) -> Dict[str, Any]:
        """Check that required arc42 chapters exist."""
        required_files = [
            "01-introduction.md",
            "02-constraints.md",
            "03-context.md",
            "04-solution-strategy.md",
            "05-building-blocks.md",
            "06-runtime-view.md",
            "07-deployment.md",
            "08-crosscutting.md",
            "09-decisions.md",
            "10-quality.md",
            "11-risks.md",
            "12-glossary.md",
        ]

        missing = []
        for filename in required_files:
            file_path = docs_path / filename
            if not file_path.exists():
                missing.append(filename)

        if missing:
            return {
                "name": "Required Chapters",
                "status": "FAIL",
                "message": f"Missing {len(missing)} required chapters",
                "details": missing,
            }
        else:
            return {
                "name": "Required Chapters",
                "status": "PASS",
                "message": "All required chapters present",
            }

    def _check_generic_content(self, docs_path: Path) -> Dict[str, Any]:
        """Check for excessive generic/filler content."""
        generic_count = 0
        total_sentences = 0

        for doc_file in docs_path.rglob("*.md"):
            content = doc_file.read_text(encoding='utf-8')

            # Count sentences (approximate)
            sentences = re.split(r'[.!?]+', content)
            total_sentences += len(sentences)

            # Count generic phrases
            for phrase in self.GENERIC_PHRASES:
                generic_count += content.lower().count(phrase.lower())

        if total_sentences == 0:
            generic_ratio = 0.0
        else:
            generic_ratio = generic_count / total_sentences

        if generic_ratio > 0.15:  # More than 15% generic
            return {
                "name": "Generic Content Check",
                "status": "WARN",
                "message": f"High generic content ratio: {generic_ratio:.1%}",
                "details": {
                    "generic_phrases": generic_count,
                    "total_sentences": total_sentences,
                    "ratio": generic_ratio,
                }
            }
        else:
            return {
                "name": "Generic Content Check",
                "status": "PASS",
                "message": f"Generic content ratio acceptable: {generic_ratio:.1%}",
            }

    def _generate_report(
        self,
        checks: List[Dict[str, Any]],
        overall_status: str,
        passed: int,
        failed: int,
    ) -> str:
        """Generate quality gate report."""
        lines = [
            "# Documentation Quality Gate Report",
            "",
            f"**Overall Status**: {overall_status}",
            f"**Checks Passed**: {passed}/{passed + failed}",
            "",
            "## Check Results",
            "",
        ]

        for check in checks:
            status_icon = "✅" if check["status"] == "PASS" else ("⚠️" if check["status"] == "WARN" else "❌")
            lines.append(f"### {status_icon} {check['name']}")
            lines.append("")
            lines.append(f"**Status**: {check['status']}")
            lines.append(f"**Message**: {check['message']}")

            if check.get("details"):
                lines.append("")
                lines.append("**Details**:")
                details = check["details"]
                if isinstance(details, list):
                    for detail in details[:10]:  # Limit details
                        lines.append(f"- {detail}")
                elif isinstance(details, dict):
                    for key, value in details.items():
                        lines.append(f"- {key}: {value}")

            lines.append("")

        return "\n".join(lines)
