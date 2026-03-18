"""Angular Logging Specialist — Console patterns, error handlers, HTTP interceptors."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawLoggingFact


class AngularLoggingCollector(DimensionCollector):
    DIMENSION = "logging_observability"

    ERROR_HANDLER_PATTERN = re.compile(r"(?:implements|extends)\s+ErrorHandler")
    HTTP_INTERCEPTOR_PATTERN = re.compile(r"(?:implements)\s+HttpInterceptor")
    LOGGING_SERVICE_PATTERN = re.compile(r"class\s+\w*(?:Log|Logger)\w*Service", re.IGNORECASE)

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_logging_patterns()
        self._log_end()
        return self.output

    def _collect_logging_patterns(self):
        for path in self._find_files("*.ts"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            if self.ERROR_HANDLER_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "ErrorHandler" in l), 1)
                fact = RawLoggingFact(
                    name=f"error-handler:{path.stem}",
                    observability_type="logging_config",
                    framework="angular",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, line_num, line_num + 5, f"Angular ErrorHandler: {path.stem}")
                self.output.add_fact(fact)

            if self.HTTP_INTERCEPTOR_PATTERN.search(content) and any("log" in l.lower() for l in lines):
                line_num = next((i for i, l in enumerate(lines, 1) if "HttpInterceptor" in l), 1)
                fact = RawLoggingFact(
                    name=f"logging-interceptor:{path.stem}",
                    observability_type="log_usage",
                    framework="angular",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, line_num, line_num + 10, f"HTTP logging interceptor: {path.stem}")
                self.output.add_fact(fact)

            if self.LOGGING_SERVICE_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "class" in l and "Log" in l), 1)
                fact = RawLoggingFact(
                    name=f"logging-service:{path.stem}",
                    observability_type="logging_config",
                    framework="angular",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, line_num, line_num + 5, f"Custom logging service: {path.stem}")
                self.output.add_fact(fact)
