"""Configuration Collector — Config files, env vars, profiles, feature flags.

Delegates to ecosystem specialists for framework-specific config extraction,
plus cross-cutting .env and Docker env detection.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawConfigFact


class ConfigurationCollector(DimensionCollector):
    DIMENSION = "configuration"

    ENV_LINE_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]+)\s*=", re.MULTILINE)

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()

        # Cross-cutting: .env files
        self._collect_env_files()
        # Cross-cutting: Docker ENV/ARG
        self._collect_docker_env()

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

    def _collect_env_files(self):
        for pattern in (".env", ".env.*", "*.env"):
            for path in self._find_files(pattern):
                if path.name.startswith(".env") or path.name.endswith(".env"):
                    content = self._read_file_content(path)
                    keys = self.ENV_LINE_PATTERN.findall(content)
                    if keys:
                        rel = self._relative_path(path)
                        fact = RawConfigFact(
                            name=f"env:{path.name}",
                            config_type="env_variable",
                            format="env",
                            file_path=rel,
                            key_count=len(keys),
                        )
                        fact.add_evidence(rel, 1, min(len(keys), 20), f"{len(keys)} environment variables")
                        self.output.add_fact(fact)

    def _collect_docker_env(self):
        for path in self._find_files("Dockerfile*"):
            content = self._read_file_content(path)
            lines = content.splitlines()
            env_lines = [i for i, l in enumerate(lines, 1) if l.strip().startswith(("ENV ", "ARG "))]
            if env_lines:
                rel = self._relative_path(path)
                fact = RawConfigFact(
                    name=f"docker-env:{path.name}",
                    config_type="env_variable",
                    format="dockerfile",
                    file_path=rel,
                    key_count=len(env_lines),
                )
                fact.add_evidence(rel, env_lines[0], env_lines[-1], f"{len(env_lines)} Docker ENV/ARG declarations")
                self.output.add_fact(fact)
