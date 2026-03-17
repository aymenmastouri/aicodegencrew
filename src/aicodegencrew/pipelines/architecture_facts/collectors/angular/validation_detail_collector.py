"""Angular Validation Specialist — Extracts Angular form validator facts.

Detects:
- Angular Validators (required, minLength, maxLength, min, max, pattern, email)
- FormControl validator assignments
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawValidationRule


class AngularValidationDetailCollector(DimensionCollector):
    """Extracts Angular form validation facts."""

    DIMENSION = "validation"

    # Angular Validators
    ANGULAR_VALIDATOR_PATTERN = re.compile(
        r"Validators\s*\.\s*(required|minLength|maxLength|min|max|pattern|email|nullValidator)"
        r"(?:\s*\(\s*([^)]*)\s*\))?"
    )
    ANGULAR_FORMCONTROL_PATTERN = re.compile(
        r"['\"]([\w]+)['\"].*?(?:new\s+FormControl|FormBuilder.*?)\s*\([^)]*\[([^\]]+)\]", re.DOTALL
    )

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Angular form validator facts."""
        self._log_start()
        self._collect_angular_validation()
        self._log_end()
        return self.output

    def _collect_angular_validation(self):
        """Collect Angular form validators."""
        ts_files = [f for f in self._find_files("*.ts") if ".spec." not in str(f)]

        for ts_file in ts_files:
            try:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if "Validators" not in content:
                continue

            class_match = re.search(r"(?:class|const)\s+(\w+)", content)
            component_name = class_match.group(1) if class_match else ts_file.stem

            for match in self.ANGULAR_VALIDATOR_PATTERN.finditer(content):
                validator_type = match.group(1)
                params = match.group(2) or ""
                line_num = content[: match.start()].count("\n") + 1

                fact = RawValidationRule(
                    name=f"{component_name}.{validator_type}",
                    validation_type=f"angular_{validator_type}",
                    constraint=params.strip(),
                    target_class=component_name,
                    target_field="",
                    file_path=self._relative_path(ts_file),
                    container_hint="frontend",
                )
                fact.add_evidence(
                    path=self._relative_path(ts_file),
                    line_start=line_num,
                    line_end=line_num + 3,
                    reason=f"Angular Validators.{validator_type} in {component_name}",
                )
                self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
