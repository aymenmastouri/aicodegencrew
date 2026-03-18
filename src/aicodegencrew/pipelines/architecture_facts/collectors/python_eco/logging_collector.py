"""Python Logging Specialist — logging config, structlog, health checks."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawLoggingFact


class PythonLoggingCollector(DimensionCollector):
    DIMENSION = "logging_observability"

    LOGGING_CONFIG_PATTERN = re.compile(r"logging\.(?:basicConfig|config\.(?:dictConfig|fileConfig))")
    STRUCTLOG_PATTERN = re.compile(r"structlog\.|import structlog")
    HEALTH_ENDPOINT_PATTERN = re.compile(r'@(?:app|router)\.\w+\s*\(\s*["\']\/health["\']')
    PROMETHEUS_PATTERN = re.compile(r"from prometheus_client|import prometheus_client|Counter\(|Histogram\(|Gauge\(")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_logging_patterns()
        self._log_end()
        return self.output

    def _collect_logging_patterns(self):
        logging_files = 0
        structlog_files = 0
        prometheus_files = 0

        for path in self._find_files("*.py"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            if self.LOGGING_CONFIG_PATTERN.search(content):
                logging_files += 1
                line_num = next((i for i, l in enumerate(lines, 1) if "logging." in l and "Config" in l), 1)
                fact = RawLoggingFact(
                    name=f"logging-config:{path.stem}",
                    observability_type="logging_config",
                    framework="python_logging",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 5, "Python logging configuration")
                self.output.add_fact(fact)

            if self.STRUCTLOG_PATTERN.search(content):
                structlog_files += 1

            if self.HEALTH_ENDPOINT_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "/health" in l), 1)
                fact = RawLoggingFact(
                    name=f"health-endpoint:{path.stem}",
                    observability_type="health_check",
                    framework="fastapi" if "fastapi" in content.lower() else "flask",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 5, "Health check endpoint")
                self.output.add_fact(fact)

            if self.PROMETHEUS_PATTERN.search(content):
                prometheus_files += 1

        if structlog_files:
            fact = RawLoggingFact(
                name="structlog-usage",
                observability_type="logging_config",
                framework="structlog",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = structlog_files
            fact.add_evidence("(aggregated)", 0, 0, f"structlog in {structlog_files} Python files")
            self.output.add_fact(fact)

        if prometheus_files:
            fact = RawLoggingFact(
                name="prometheus-client-usage",
                observability_type="metrics_endpoint",
                framework="prometheus_client",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = prometheus_files
            fact.add_evidence("(aggregated)", 0, 0, f"prometheus_client in {prometheus_files} Python files")
            self.output.add_fact(fact)
