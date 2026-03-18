"""Angular Configuration Specialist — environment.ts, angular.json, proxy configs."""

from __future__ import annotations

from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawConfigFact


class AngularConfigurationCollector(DimensionCollector):
    DIMENSION = "configuration"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_environment_files()
        self._collect_angular_json()
        self._collect_proxy_config()
        self._log_end()
        return self.output

    def _collect_environment_files(self):
        for path in self._find_files("environment*.ts"):
            content = self._read_file_content(path)
            lines = content.splitlines()
            rel = self._relative_path(path)

            # Count exported properties
            key_count = sum(1 for l in lines if ":" in l and not l.strip().startswith("//"))

            env_name = path.stem.replace("environment.", "").replace("environment", "default")
            fact = RawConfigFact(
                name=f"angular-env:{env_name}",
                config_type="profile" if env_name != "default" else "config_file",
                format="typescript",
                file_path=rel,
                key_count=key_count,
                container_hint=self.container_id or "frontend",
            )
            fact.metadata["environment"] = env_name
            fact.add_evidence(rel, 1, min(len(lines), 20), f"Angular environment: {key_count} config keys")
            self.output.add_fact(fact)

    def _collect_angular_json(self):
        for path in self._find_files("angular.json"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            fact = RawConfigFact(
                name="angular-json",
                config_type="config_file",
                format="json",
                file_path=rel,
                key_count=len(lines),
                container_hint=self.container_id or "frontend",
            )
            fact.add_evidence(rel, 1, min(len(lines), 20), "Angular workspace configuration")
            self.output.add_fact(fact)

    def _collect_proxy_config(self):
        for pattern in ("proxy.conf.json", "proxy.conf.js", "proxy.conf.mjs"):
            for path in self._find_files(pattern):
                rel = self._relative_path(path)
                fact = RawConfigFact(
                    name=f"proxy-config:{path.name}",
                    config_type="config_file",
                    format="json",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, 1, 10, "Angular dev proxy configuration")
                self.output.add_fact(fact)
