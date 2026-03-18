"""Logging & Observability Collector — Logging config, tracing, metrics, health checks.

Delegates to ecosystem specialists for framework-specific logging extraction,
plus cross-cutting detection of logging configuration files.
"""

from __future__ import annotations

from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawLoggingFact


class LoggingObservabilityCollector(DimensionCollector):
    DIMENSION = "logging_observability"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()

        # Cross-cutting: common logging config files
        self._collect_logging_configs()

        # Delegate to ecosystem specialists
        from ....shared.ecosystems import EcosystemRegistry
        registry = EcosystemRegistry()
        for eco in registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output

    def _collect_logging_configs(self):
        config_files = {
            "logback.xml": ("logback", "xml"),
            "logback-spring.xml": ("logback", "xml"),
            "log4j2.xml": ("log4j2", "xml"),
            "log4j2.yml": ("log4j2", "yaml"),
            "log4j.properties": ("log4j", "properties"),
            "logging.conf": ("python_logging", "ini"),
            "logging.ini": ("python_logging", "ini"),
            ".logging": ("generic", "text"),
        }
        for filename, (framework, fmt) in config_files.items():
            for path in self._find_files(filename):
                content = self._read_file_content(path)
                lines = content.splitlines()
                rel = self._relative_path(path)
                fact = RawLoggingFact(
                    name=f"logging-config:{path.name}",
                    observability_type="logging_config",
                    framework=framework,
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, 1, min(len(lines), 20), f"Logging config: {framework}")
                self.output.add_fact(fact)

        # Prometheus/Grafana configs
        for pattern in ("prometheus.yml", "prometheus.yaml", "grafana*.json"):
            for path in self._find_files(pattern):
                rel = self._relative_path(path)
                fact = RawLoggingFact(
                    name=f"metrics-config:{path.name}",
                    observability_type="metrics_endpoint",
                    framework="prometheus" if "prometheus" in path.name else "grafana",
                    file_path=rel,
                )
                fact.add_evidence(rel, 1, 10, f"Metrics config: {path.name}")
                self.output.add_fact(fact)

        # OpenTelemetry config
        for pattern in ("otel-*.yml", "otel-*.yaml", "opentelemetry*.yml", "opentelemetry*.yaml"):
            for path in self._find_files(pattern):
                rel = self._relative_path(path)
                fact = RawLoggingFact(
                    name=f"tracing-config:{path.name}",
                    observability_type="tracing",
                    framework="opentelemetry",
                    file_path=rel,
                )
                fact.add_evidence(rel, 1, 10, f"OpenTelemetry config: {path.name}")
                self.output.add_fact(fact)
