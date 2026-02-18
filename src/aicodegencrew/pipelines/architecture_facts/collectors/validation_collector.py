"""
ValidationCollector - Extracts validation rules from DTOs, entities, and custom validators.

Detects:
- Bean Validation annotations: @Valid, @NotNull, @NotBlank, @Size, @Pattern, @Min, @Max
- Custom validators (implements ConstraintValidator<...>)
- DTO field -> validation rule mapping
- Angular form validators (Validators.required, Validators.pattern, etc.)

Output -> validation dimension
"""

import re
from pathlib import Path

from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawValidationRule


class ValidationCollector(DimensionCollector):
    """Collects validation rule facts from Java/Kotlin and TypeScript sources."""

    DIMENSION = "validation"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # Java Bean Validation annotations
    VALIDATION_ANNOTATIONS = {
        "@NotNull": "not_null",
        "@NotBlank": "not_blank",
        "@NotEmpty": "not_empty",
        "@Size": "size",
        "@Min": "min",
        "@Max": "max",
        "@Pattern": "pattern",
        "@Email": "email",
        "@Positive": "positive",
        "@PositiveOrZero": "positive_or_zero",
        "@Negative": "negative",
        "@NegativeOrZero": "negative_or_zero",
        "@Past": "past",
        "@PastOrPresent": "past_or_present",
        "@Future": "future",
        "@FutureOrPresent": "future_or_present",
        "@Digits": "digits",
        "@DecimalMin": "decimal_min",
        "@DecimalMax": "decimal_max",
    }

    # Pattern for annotation with optional parameters
    ANNOTATION_PATTERN = re.compile(
        r"(@(?:NotNull|NotBlank|NotEmpty|Size|Min|Max|Pattern|Email|"
        r"Positive(?:OrZero)?|Negative(?:OrZero)?|Past(?:OrPresent)?|"
        r"Future(?:OrPresent)?|Digits|DecimalMin|DecimalMax|Valid)"
        r"(?:\s*\(([^)]*)\))?)",
        re.MULTILINE,
    )

    # Field following annotation
    FIELD_PATTERN = re.compile(
        r"(?:private|protected|public)?\s*(?:final\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*[;=]", re.MULTILINE
    )

    # Method parameter with @Valid
    VALID_PARAM_PATTERN = re.compile(r"@Valid\s+(?:@\w+(?:\([^)]*\))?\s+)*(\w+)\s+(\w+)", re.MULTILINE)

    # Custom validator
    CUSTOM_VALIDATOR_PATTERN = re.compile(
        r"class\s+(\w+)\s+implements\s+ConstraintValidator\s*<\s*(\w+)\s*,\s*(\w+)\s*>"
    )

    # Class pattern
    CLASS_PATTERN = re.compile(r"class\s+(\w+)")

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
        """Collect all validation facts."""
        self._log_start()

        self._collect_java_validation()
        self._collect_angular_validation()

        self._log_end()
        return self.output

    def _collect_java_validation(self):
        """Collect Bean Validation annotations from Java/Kotlin files."""
        java_files = self._find_files("*.java") + self._find_files("*.kt")

        logger.info(f"[ValidationCollector] Scanning {len(java_files)} Java/Kotlin files")

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Skip files without validation imports
            if "javax.validation" not in content and "jakarta.validation" not in content and "@Valid" not in content:
                continue

            class_match = self.CLASS_PATTERN.search(content)
            class_name = class_match.group(1) if class_match else java_file.stem

            # Find validation annotations on fields
            lines = content.split("\n")
            for i, line in enumerate(lines):
                for ann_match in self.ANNOTATION_PATTERN.finditer(line):
                    annotation = ann_match.group(1).split("(")[0]  # e.g. @NotNull
                    params = ann_match.group(2) or ""
                    validation_type = self.VALIDATION_ANNOTATIONS.get(annotation, annotation.lstrip("@").lower())

                    # Find the field this annotation applies to
                    field_name = ""
                    for j in range(i, min(i + 5, len(lines))):
                        field_match = self.FIELD_PATTERN.search(lines[j])
                        if field_match:
                            field_name = field_match.group(2)
                            break

                    fact = RawValidationRule(
                        name=f"{class_name}.{field_name}" if field_name else f"{class_name}.{validation_type}",
                        validation_type=validation_type,
                        constraint=params.strip(),
                        target_class=class_name,
                        target_field=field_name,
                        file_path=self._relative_path(java_file),
                        container_hint=self.container_id,
                    )
                    fact.add_evidence(
                        path=self._relative_path(java_file),
                        line_start=i + 1,
                        line_end=i + 3,
                        reason=f"{annotation} on {class_name}.{field_name}",
                    )
                    self.output.add_fact(fact)

            # @Valid on method parameters (controller endpoints)
            for match in self.VALID_PARAM_PATTERN.finditer(content):
                param_type = match.group(1)
                param_name = match.group(2)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawValidationRule(
                    name=f"{class_name}.@Valid_{param_name}",
                    validation_type="valid",
                    constraint="",
                    target_class=class_name,
                    target_field=param_name,
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                    metadata={"param_type": param_type},
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 3,
                    reason=f"@Valid on parameter {param_name} ({param_type})",
                )
                self.output.add_fact(fact)

            # Custom ConstraintValidator implementations
            for match in self.CUSTOM_VALIDATOR_PATTERN.finditer(content):
                validator_name = match.group(1)
                annotation_name = match.group(2)
                target_type = match.group(3)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawValidationRule(
                    name=validator_name,
                    validation_type="custom",
                    constraint=f"Annotation: {annotation_name}, Target: {target_type}",
                    target_class=target_type,
                    target_field="",
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                    metadata={"annotation": annotation_name, "target_type": target_type},
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 30,
                    reason=f"Custom ConstraintValidator: {validator_name} for @{annotation_name}",
                )
                self.output.add_fact(fact)

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

    def _should_skip(self, path: Path) -> bool:
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
