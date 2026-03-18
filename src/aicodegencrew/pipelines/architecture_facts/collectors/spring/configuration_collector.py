"""Spring Configuration Specialist — application.yml, profiles, @ConfigurationProperties."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawConfigFact


class SpringConfigurationCollector(DimensionCollector):
    DIMENSION = "configuration"

    VALUE_PATTERN = re.compile(r'@Value\s*\(\s*"([^"]+)"\s*\)')
    CONFIG_PROPS_PATTERN = re.compile(r'@ConfigurationProperties\s*\(\s*(?:prefix\s*=\s*)?"([^"]+)"')
    PROFILE_PATTERN = re.compile(r"application[_-](\w+)\.(yml|yaml|properties)")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_app_configs()
        self._collect_config_annotations()
        self._log_end()
        return self.output

    def _collect_app_configs(self):
        for pattern in ("application.yml", "application.yaml", "application.properties", "application-*.yml", "application-*.yaml", "application-*.properties", "bootstrap.yml", "bootstrap.yaml"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                lines = content.splitlines()
                rel = self._relative_path(path)

                # Detect profile
                profile_match = self.PROFILE_PATTERN.search(path.name)
                profile = profile_match.group(1) if profile_match else "default"

                # Count non-empty, non-comment lines as key proxies
                key_count = sum(1 for l in lines if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("---"))

                config_type = "profile" if profile != "default" else "config_file"
                fmt = "yaml" if path.suffix in (".yml", ".yaml") else "properties"

                fact = RawConfigFact(
                    name=f"spring-config:{path.name}",
                    config_type=config_type,
                    format=fmt,
                    file_path=rel,
                    key_count=key_count,
                    container_hint=self.container_id,
                )
                fact.metadata["profile"] = profile
                fact.add_evidence(rel, 1, min(len(lines), 30), f"Spring config: {key_count} entries, profile={profile}")
                self.output.add_fact(fact)

    def _collect_config_annotations(self):
        for path in self._find_files("*.java"):
            content = self._read_file_content(path)

            # @ConfigurationProperties
            for m in self.CONFIG_PROPS_PATTERN.finditer(content):
                prefix = m.group(1)
                rel = self._relative_path(path)
                lines = content[:m.start()].count("\n") + 1
                fact = RawConfigFact(
                    name=f"config-props:{prefix}",
                    config_type="config_file",
                    format="annotation",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.metadata["prefix"] = prefix
                fact.add_evidence(rel, lines, lines + 3, f"@ConfigurationProperties(prefix=\"{prefix}\")")
                self.output.add_fact(fact)

            # Count @Value usages per file
            values = self.VALUE_PATTERN.findall(content)
            if values:
                rel = self._relative_path(path)
                fact = RawConfigFact(
                    name=f"value-injection:{path.stem}",
                    config_type="env_variable",
                    format="annotation",
                    file_path=rel,
                    key_count=len(values),
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, 1, 10, f"{len(values)} @Value injections")
                self.output.add_fact(fact)
