"""Python Security Specialist — Extracts Python security facts.

Detects:
- Django @login_required, @permission_required
- Flask-Login current_user.is_authenticated
- FastAPI Depends(get_current_user)
- DRF permission_classes
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawSecurityDetail


class PythonSecurityCollector(DimensionCollector):
    """Extracts Python security facts."""

    DIMENSION = "security_details"

    # Python security patterns
    PY_LOGIN_REQUIRED = re.compile(r"@login_required")
    PY_PERMISSION_REQUIRED = re.compile(r"@permission_required\s*\(\s*['\"]([^'\"]+)['\"]")
    PY_FLASK_LOGIN = re.compile(r"@login_required|current_user\.is_authenticated")
    PY_FASTAPI_DEPENDS = re.compile(r"Depends\s*\(\s*(get_current_user|get_current_active_user|verify_token|auth_required)")
    PY_DRF_PERMISSION = re.compile(r"permission_classes\s*=\s*\[([^\]]+)\]")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python security facts."""
        self._log_start()
        self._collect_python_security()
        self._log_end()
        return self.output

    def _collect_python_security(self):
        """Collect Python security: Django @login_required, @permission_required, Flask-Login, FastAPI Depends, DRF permission_classes."""
        py_files = [f for f in self._find_files("*.py") if ".spec." not in str(f)]

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Quick skip: no security indicators
            if not any(kw in content for kw in ("login_required", "permission_required", "permission_classes", "Depends", "get_current_user", "is_authenticated")):
                continue

            rel_path = self._relative_path(py_file)
            class_match = re.search(r"class\s+(\w+)", content)
            class_name = class_match.group(1) if class_match else py_file.stem

            # Django @login_required
            for match in self.PY_LOGIN_REQUIRED.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                # Find the function/method after the decorator
                func_match = re.search(r"def\s+(\w+)", content[match.end():match.end() + 200])
                method_name = func_match.group(1) if func_match else ""

                fact = RawSecurityDetail(
                    name=f"{class_name}.{method_name}" if method_name else class_name,
                    security_type="authentication",
                    roles=[],
                    method=method_name,
                    class_name=class_name,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "django", "mechanism": "login_required"},
                )
                fact.add_evidence(path=rel_path, line_start=line_num, line_end=line_num + 3, reason=f"@login_required: {method_name}")
                self.output.add_fact(fact)

            # Django @permission_required
            for match in self.PY_PERMISSION_REQUIRED.finditer(content):
                permission = match.group(1)
                line_num = content[: match.start()].count("\n") + 1
                func_match = re.search(r"def\s+(\w+)", content[match.end():match.end() + 200])
                method_name = func_match.group(1) if func_match else ""

                fact = RawSecurityDetail(
                    name=f"{class_name}.{method_name}" if method_name else class_name,
                    security_type="authorization",
                    roles=[permission],
                    method=method_name,
                    class_name=class_name,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "django", "mechanism": "permission_required"},
                )
                fact.add_evidence(path=rel_path, line_start=line_num, line_end=line_num + 3, reason=f"@permission_required('{permission}')")
                self.output.add_fact(fact)

            # FastAPI Depends(get_current_user)
            for match in self.PY_FASTAPI_DEPENDS.finditer(content):
                dep_func = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}.{dep_func}",
                    security_type="authentication",
                    roles=[],
                    method="",
                    class_name=class_name,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "fastapi", "mechanism": "dependency_injection", "dependency": dep_func},
                )
                fact.add_evidence(path=rel_path, line_start=line_num, line_end=line_num + 3, reason=f"FastAPI auth dependency: Depends({dep_func})")
                self.output.add_fact(fact)

            # DRF permission_classes
            for match in self.PY_DRF_PERMISSION.finditer(content):
                perms_str = match.group(1)
                permissions = [p.strip() for p in perms_str.split(",") if p.strip()]
                line_num = content[: match.start()].count("\n") + 1

                fact = RawSecurityDetail(
                    name=f"{class_name}_permissions",
                    security_type="authorization",
                    roles=permissions,
                    method="",
                    class_name=class_name,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "django_rest_framework", "mechanism": "permission_classes"},
                )
                fact.add_evidence(path=rel_path, line_start=line_num, line_end=line_num + 3, reason=f"DRF permission_classes: {permissions}")
                self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
