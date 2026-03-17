"""Python Validation Specialist — Extracts Python validation facts.

Detects:
- Pydantic BaseModel with field validators
- Marshmallow Schema classes
- Django Forms (Form, ModelForm)
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawValidationRule


class PythonValidationCollector(DimensionCollector):
    """Extracts Python validation facts."""

    DIMENSION = "validation"

    # Python validation patterns
    PYDANTIC_MODEL_PATTERN = re.compile(r"class\s+(\w+)\s*\(\s*(?:BaseModel|BaseSettings)\s*\)")
    PYDANTIC_FIELD_VALIDATOR = re.compile(r"@(?:field_validator|validator)\s*\(\s*['\"](\w+)['\"]")
    MARSHMALLOW_SCHEMA_PATTERN = re.compile(r"class\s+(\w+)\s*\(\s*(?:Schema|ma\.Schema)\s*\)")
    DJANGO_FORM_PATTERN = re.compile(r"class\s+(\w+)\s*\(\s*(?:forms\.Form|forms\.ModelForm|ModelForm|Form)\s*\)")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python validation facts."""
        self._log_start()
        self._collect_python_validation()
        self._log_end()
        return self.output

    def _collect_python_validation(self):
        """Collect Python validation: Pydantic BaseModel, Marshmallow Schema, Django Forms."""
        py_files = [f for f in self._find_files("*.py") if ".spec." not in str(f)]

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_path = self._relative_path(py_file)

            # Pydantic models with field validators
            for match in self.PYDANTIC_MODEL_PATTERN.finditer(content):
                class_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Find field validators in the class body
                class_start = match.end()
                next_class = re.search(r"^class\s+\w+", content[class_start:], re.MULTILINE)
                class_body = content[class_start:class_start + next_class.start()] if next_class else content[class_start:]

                validators = self.PYDANTIC_FIELD_VALIDATOR.findall(class_body)

                fact = RawValidationRule(
                    name=class_name,
                    validation_type="model_validation",
                    constraint=f"{len(validators)} field validators" if validators else "",
                    target_class=class_name,
                    target_field="",
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "pydantic", "validated_fields": validators},
                )
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Pydantic model: {class_name}",
                )
                self.output.add_fact(fact)

            # Marshmallow schemas
            for match in self.MARSHMALLOW_SCHEMA_PATTERN.finditer(content):
                class_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawValidationRule(
                    name=class_name,
                    validation_type="schema_validation",
                    constraint="",
                    target_class=class_name,
                    target_field="",
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "marshmallow"},
                )
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Marshmallow schema: {class_name}",
                )
                self.output.add_fact(fact)

            # Django forms
            for match in self.DJANGO_FORM_PATTERN.finditer(content):
                class_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawValidationRule(
                    name=class_name,
                    validation_type="form_validation",
                    constraint="",
                    target_class=class_name,
                    target_field="",
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "django"},
                )
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Django form: {class_name}",
                )
                self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
