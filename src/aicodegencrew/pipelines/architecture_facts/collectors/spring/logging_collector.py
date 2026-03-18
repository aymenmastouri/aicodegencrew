"""Spring Logging Specialist — Actuator, Micrometer, SLF4J patterns."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawLoggingFact


class SpringLoggingCollector(DimensionCollector):
    DIMENSION = "logging_observability"

    ACTUATOR_PATTERN = re.compile(r"management\.(endpoints|endpoint|health|metrics|info)")
    SLF4J_PATTERN = re.compile(r"@Slf4j|LoggerFactory\.getLogger|private\s+(?:static\s+)?(?:final\s+)?Logger")
    MICROMETER_PATTERN = re.compile(r"MeterRegistry|@Timed|@Counted|Counter\.builder|Timer\.builder")
    HEALTH_INDICATOR_PATTERN = re.compile(r"(?:implements|extends)\s+\w*HealthIndicator")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_actuator_config()
        self._collect_logging_usage()
        self._collect_health_indicators()
        self._log_end()
        return self.output

    def _collect_actuator_config(self):
        for pattern in ("application.yml", "application.yaml", "application.properties"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                if self.ACTUATOR_PATTERN.search(content):
                    rel = self._relative_path(path)
                    lines = content.splitlines()
                    actuator_lines = [i for i, l in enumerate(lines, 1) if "management." in l or "actuator" in l.lower()]
                    fact = RawLoggingFact(
                        name="spring-actuator",
                        observability_type="metrics_endpoint",
                        framework="spring_actuator",
                        file_path=rel,
                        container_hint=self.container_id,
                    )
                    start = actuator_lines[0] if actuator_lines else 1
                    fact.add_evidence(rel, start, start + 5, "Spring Actuator management endpoints configured")
                    self.output.add_fact(fact)

                # Micrometer in config
                if "micrometer" in content.lower() or "metrics" in content.lower():
                    micrometer_lines = [i for i, l in enumerate(lines, 1) if "micrometer" in l.lower() or "metrics.export" in l]
                    if micrometer_lines:
                        rel = self._relative_path(path)
                        fact = RawLoggingFact(
                            name="spring-micrometer-config",
                            observability_type="metrics_endpoint",
                            framework="micrometer",
                            file_path=rel,
                            container_hint=self.container_id,
                        )
                        fact.add_evidence(rel, micrometer_lines[0], micrometer_lines[0] + 5, "Micrometer metrics configuration")
                        self.output.add_fact(fact)

    def _collect_logging_usage(self):
        # Count SLF4J/Micrometer usage across Java files (sample — don't scan every file)
        slf4j_count = 0
        micrometer_count = 0
        for path in self._find_files("*.java"):
            content = self._read_file_content(path)
            if self.SLF4J_PATTERN.search(content):
                slf4j_count += 1
            if self.MICROMETER_PATTERN.search(content):
                micrometer_count += 1

        if slf4j_count:
            fact = RawLoggingFact(
                name="slf4j-usage",
                observability_type="log_usage",
                framework="slf4j",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = slf4j_count
            fact.add_evidence("(aggregated)", 0, 0, f"SLF4J logging in {slf4j_count} Java files")
            self.output.add_fact(fact)

        if micrometer_count:
            fact = RawLoggingFact(
                name="micrometer-usage",
                observability_type="metrics_endpoint",
                framework="micrometer",
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = micrometer_count
            fact.add_evidence("(aggregated)", 0, 0, f"Micrometer metrics in {micrometer_count} Java files")
            self.output.add_fact(fact)

    def _collect_health_indicators(self):
        for path in self._find_files("*.java"):
            content = self._read_file_content(path)
            if self.HEALTH_INDICATOR_PATTERN.search(content):
                rel = self._relative_path(path)
                lines = content.splitlines()
                line_num = next((i for i, l in enumerate(lines, 1) if "HealthIndicator" in l), 1)
                class_name = path.stem
                fact = RawLoggingFact(
                    name=f"health-indicator:{class_name}",
                    observability_type="health_check",
                    framework="spring_actuator",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 5, f"Custom health indicator: {class_name}")
                self.output.add_fact(fact)
