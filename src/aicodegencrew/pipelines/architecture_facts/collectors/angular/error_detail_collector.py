"""Angular Error Handling Specialist — Extracts Angular error handling facts.

Detects:
- Angular ErrorHandler implementations
- HTTP interceptors with error handling (catchError)
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawErrorHandlingFact


class AngularErrorDetailCollector(DimensionCollector):
    """Extracts Angular error handling facts."""

    DIMENSION = "error_handling"

    # Angular patterns
    ANGULAR_ERROR_HANDLER_PATTERN = re.compile(r"(?:implements|extends)\s+ErrorHandler")
    ANGULAR_INTERCEPTOR_PATTERN = re.compile(r"(?:implements\s+HttpInterceptor|HttpInterceptorFn)")
    ANGULAR_CATCH_ERROR_PATTERN = re.compile(r"catchError\s*\(")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Angular error handling facts."""
        self._log_start()
        self._collect_angular_error_handling()
        self._log_end()
        return self.output

    def _collect_angular_error_handling(self):
        """Collect Angular error handling patterns."""
        ts_files = [f for f in self._find_files("*.ts") if ".spec." not in str(f)]

        for ts_file in ts_files:
            try:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            class_match = re.search(r"(?:class|const)\s+(\w+)", content)
            class_name = class_match.group(1) if class_match else ts_file.stem

            # Angular ErrorHandler
            if self.ANGULAR_ERROR_HANDLER_PATTERN.search(content):
                line_num = content[: self.ANGULAR_ERROR_HANDLER_PATTERN.search(content).start()].count("\n") + 1

                fact = RawErrorHandlingFact(
                    name=class_name,
                    handling_type="angular_error_handler",
                    exception_class="",
                    http_status="",
                    handler_method="handleError",
                    file_path=self._relative_path(ts_file),
                    container_hint="frontend",
                )
                fact.add_evidence(
                    path=self._relative_path(ts_file),
                    line_start=line_num,
                    line_end=line_num + 30,
                    reason=f"Angular ErrorHandler: {class_name}",
                )
                self.output.add_fact(fact)

            # HTTP Interceptors (error handling)
            if self.ANGULAR_INTERCEPTOR_PATTERN.search(content):
                has_error_handling = self.ANGULAR_CATCH_ERROR_PATTERN.search(content)
                if has_error_handling:
                    line_num = content[: self.ANGULAR_INTERCEPTOR_PATTERN.search(content).start()].count("\n") + 1

                    fact = RawErrorHandlingFact(
                        name=class_name,
                        handling_type="http_interceptor",
                        exception_class="HttpErrorResponse",
                        http_status="",
                        handler_method="intercept",
                        file_path=self._relative_path(ts_file),
                        container_hint="frontend",
                    )
                    fact.add_evidence(
                        path=self._relative_path(ts_file),
                        line_start=line_num,
                        line_end=line_num + 30,
                        reason=f"HTTP error interceptor: {class_name}",
                    )
                    self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
