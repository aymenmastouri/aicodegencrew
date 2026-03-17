"""Python Error Handling Specialist — Extracts Python error handling facts.

Detects:
- Custom exception classes
- Flask @app.errorhandler(code)
- Django middleware process_exception
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawErrorHandlingFact


class PythonErrorCollector(DimensionCollector):
    """Extracts Python error handling facts."""

    DIMENSION = "error_handling"

    # Python patterns
    PYTHON_CUSTOM_EXCEPTION = re.compile(
        r"class\s+(\w+(?:Error|Exception))\s*\(\s*(\w+(?:Error|Exception)?)\s*\)"
    )
    FLASK_ERROR_HANDLER = re.compile(r"@\w+\.errorhandler\s*\(\s*(\d+|\w+)\s*\)")
    DJANGO_PROCESS_EXCEPTION = re.compile(r"def\s+(process_exception)\s*\(")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python error handling facts."""
        self._log_start()
        self._collect_python_error_handling()
        self._log_end()
        return self.output

    def _collect_python_error_handling(self):
        """Collect Python error handling: custom exceptions, Flask errorhandler, Django middleware."""
        py_files = [f for f in self._find_files("*.py") if ".spec." not in str(f)]

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_path = self._relative_path(py_file)
            class_match = re.search(r"class\s+(\w+)", content)
            file_class_name = class_match.group(1) if class_match else py_file.stem

            # Custom exception classes
            for match in self.PYTHON_CUSTOM_EXCEPTION.finditer(content):
                exc_name = match.group(1)
                parent = match.group(2)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawErrorHandlingFact(
                    name=exc_name,
                    handling_type="custom_exception",
                    exception_class=parent,
                    http_status="",
                    handler_method="",
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "python"},
                )
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Custom exception: {exc_name} extends {parent}",
                )
                self.output.add_fact(fact)

            # Flask @app.errorhandler(code)
            for match in self.FLASK_ERROR_HANDLER.finditer(content):
                error_code = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Find handler function name
                func_match = re.search(r"def\s+(\w+)", content[match.end():match.end() + 200])
                handler_name = func_match.group(1) if func_match else "handler"

                fact = RawErrorHandlingFact(
                    name=f"{file_class_name}.{handler_name}",
                    handling_type="exception_handler",
                    exception_class=error_code,
                    http_status=error_code if error_code.isdigit() else "",
                    handler_method=handler_name,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "flask", "mechanism": "errorhandler"},
                )
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Flask errorhandler({error_code}): {handler_name}",
                )
                self.output.add_fact(fact)

            # Django middleware process_exception
            if self.DJANGO_PROCESS_EXCEPTION.search(content):
                match = self.DJANGO_PROCESS_EXCEPTION.search(content)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawErrorHandlingFact(
                    name=f"{file_class_name}.process_exception",
                    handling_type="exception_handler",
                    exception_class="Exception",
                    http_status="",
                    handler_method="process_exception",
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"framework": "django", "mechanism": "middleware"},
                )
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Django middleware: {file_class_name}.process_exception",
                )
                self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
