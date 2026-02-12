"""Quality gate tool for validation and quality checks."""

import json
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..models.analysis_schema import ArchitectureAnalysis
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class QualityGateInput(BaseModel):
    """Input schema for QualityGateTool."""

    analysis_path: str = Field(..., description="Path to analysis JSON")
    output_path: str = Field(..., description="Path to save quality report")
    min_evidence_count: int = Field(default=1, description="Minimum evidence items required")


class QualityGateTool(BaseTool):
    name: str = "quality_gate"
    description: str = (
        "Validates analysis JSON against schema, checks evidence requirements, "
        "verifies required sections, and generates quality report."
    )
    args_schema: type[BaseModel] = QualityGateInput

    def _run(
        self,
        analysis_path: str,
        output_path: str,
        min_evidence_count: int = 1,
    ) -> dict[str, Any]:
        """Run quality gate checks.

        Args:
            analysis_path: Path to analysis JSON
            output_path: Path for quality report
            min_evidence_count: Minimum evidence required

        Returns:
            Quality gate result dictionary
        """
        try:
            # Load analysis JSON
            with open(analysis_path, encoding="utf-8") as f:
                analysis_dict = json.load(f)

            # Run checks
            checks = []

            # Check 1: Schema validation
            schema_check = self._check_schema(analysis_dict)
            checks.append(schema_check)

            # Check 2: Evidence requirements
            evidence_check = self._check_evidence(analysis_dict, min_evidence_count)
            checks.append(evidence_check)

            # Check 3: Required sections
            sections_check = self._check_required_sections(analysis_dict)
            checks.append(sections_check)

            # Check 4: Technology detection
            tech_check = self._check_technologies(analysis_dict)
            checks.append(tech_check)

            # Calculate overall status
            passed = sum(1 for c in checks if c["status"] == "pass")
            failed = len(checks) - passed
            overall_status = "PASS" if failed == 0 else "FAIL"

            # Generate report
            report = self._generate_report(checks, overall_status, passed, failed)

            # Save Markdown report
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)

            # Generate and save HTML report
            html_report = self._generate_html_report(checks, overall_status, passed, failed)
            if html_report:
                html_file = output_file.parent / "quality-report.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_report)

            logger.info(
                f"Quality gate {overall_status}: {passed}/{len(checks)} checks passed. Report saved to: {output_file}"
            )

            return {
                "success": True,
                "overall_status": overall_status,
                "passed": passed,
                "failed": failed,
                "checks": checks,
                "report_path": str(output_file),
            }

        except Exception as e:
            logger.error(f"Error in quality gate: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _check_schema(self, analysis_dict: dict[str, Any]) -> dict[str, Any]:
        """Check schema validation.

        Args:
            analysis_dict: Analysis dictionary

        Returns:
            Check result
        """
        try:
            # Validate using Pydantic model
            ArchitectureAnalysis(**analysis_dict)

            return {
                "name": "Schema Validation",
                "status": "pass",
                "message": "Analysis JSON conforms to schema",
            }
        except Exception as e:
            return {
                "name": "Schema Validation",
                "status": "fail",
                "message": f"Schema validation failed: {e!s}",
            }

    def _check_evidence(
        self,
        analysis_dict: dict[str, Any],
        min_evidence_count: int,
    ) -> dict[str, Any]:
        """Check evidence requirements.

        Args:
            analysis_dict: Analysis dictionary
            min_evidence_count: Minimum evidence count

        Returns:
            Check result
        """
        technologies = analysis_dict.get("technologies", [])
        project_units = analysis_dict.get("project_units", [])

        issues = []

        # Check technologies
        for tech in technologies:
            evidence = tech.get("evidence", [])
            if len(evidence) < min_evidence_count:
                issues.append(
                    f"Technology '{tech.get('name')}' has {len(evidence)} evidence items "
                    f"(minimum: {min_evidence_count})"
                )

        # Check project units
        for unit in project_units:
            evidence = unit.get("evidence", [])
            if len(evidence) < min_evidence_count:
                issues.append(
                    f"Project unit '{unit.get('name')}' has {len(evidence)} evidence items "
                    f"(minimum: {min_evidence_count})"
                )

        if issues:
            return {
                "name": "Evidence Requirements",
                "status": "fail",
                "message": f"{len(issues)} evidence requirement violations",
                "details": issues,
            }
        else:
            return {
                "name": "Evidence Requirements",
                "status": "pass",
                "message": "All items have sufficient evidence",
            }

    def _check_required_sections(self, analysis_dict: dict[str, Any]) -> dict[str, Any]:
        """Check required sections.

        Args:
            analysis_dict: Analysis dictionary

        Returns:
            Check result
        """
        required_fields = [
            "repo_name",
            "repo_path",
            "analysis_timestamp",
            "summary",
        ]

        missing = []
        for field in required_fields:
            if not analysis_dict.get(field):
                missing.append(field)

        if missing:
            return {
                "name": "Required Sections",
                "status": "fail",
                "message": f"Missing required fields: {', '.join(missing)}",
            }
        else:
            return {
                "name": "Required Sections",
                "status": "pass",
                "message": "All required sections present",
            }

    def _check_technologies(self, analysis_dict: dict[str, Any]) -> dict[str, Any]:
        """Check technology detection.

        Args:
            analysis_dict: Analysis dictionary

        Returns:
            Check result
        """
        technologies = analysis_dict.get("technologies", [])

        if not technologies:
            return {
                "name": "Technology Detection",
                "status": "fail",
                "message": "No technologies detected",
            }
        else:
            return {
                "name": "Technology Detection",
                "status": "pass",
                "message": f"Detected {len(technologies)} technologies",
            }

    def _generate_report(
        self,
        checks: list[dict[str, Any]],
        overall_status: str,
        passed: int,
        failed: int,
    ) -> str:
        """Generate quality report.

        Args:
            checks: List of check results
            overall_status: Overall status
            passed: Number of passed checks
            failed: Number of failed checks

        Returns:
            Markdown report
        """
        report_lines = [
            "# Quality Gate Report",
            "",
            f"**Overall Status:** {overall_status}",
            f"**Checks Passed:** {passed}/{passed + failed}",
            "",
            "## Check Results",
            "",
        ]

        for check in checks:
            status_icon = "[PASS]" if check["status"] == "pass" else "[FAIL]"
            report_lines.append(f"### {status_icon} {check['name']}")
            report_lines.append("")
            report_lines.append(f"**Status:** {check['status'].upper()}")
            report_lines.append(f"**Message:** {check['message']}")

            if check.get("details"):
                report_lines.append("")
                report_lines.append("**Details:**")
                for detail in check["details"]:
                    report_lines.append(f"- {detail}")

            report_lines.append("")

        markdown_report = "\n".join(report_lines)
        return markdown_report

    def _generate_html_report(
        self,
        checks: list[dict[str, Any]],
        overall_status: str,
        passed: int,
        failed: int,
    ) -> str:
        """Generate HTML quality report using Jinja2.

        Args:
            checks: List of check results
            overall_status: Overall status
            passed: Number of passed checks
            failed: Number of failed checks

        Returns:
            HTML report or empty string on error
        """
        try:
            from pathlib import Path

            from jinja2 import Environment, FileSystemLoader, select_autoescape

            # Setup Jinja2 environment
            templates_path = Path(__file__).parent.parent / "archscan" / "templates"
            if not templates_path.exists():
                return ""

            env = Environment(
                loader=FileSystemLoader(str(templates_path)),
                autoescape=select_autoescape(["html", "xml"]),
            )

            template = env.get_template("quality-report.html.j2")
            html_content = template.render(
                overall_status=overall_status,
                passed=passed,
                failed=failed,
                checks=checks,
            )

            return html_content
        except Exception:
            return ""
