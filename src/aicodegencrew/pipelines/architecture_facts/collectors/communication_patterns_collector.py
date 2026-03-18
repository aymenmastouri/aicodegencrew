"""Communication Patterns Collector — Message queues, events, WebSockets, REST clients.

Delegates to ecosystem specialists for framework-specific communication patterns,
plus cross-cutting detection of messaging infrastructure config.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawCommunicationFact


class CommunicationPatternsCollector(DimensionCollector):
    DIMENSION = "communication_patterns"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()

        # Cross-cutting: messaging infrastructure configs
        self._collect_messaging_configs()

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

    def _collect_messaging_configs(self):
        """Detect messaging infrastructure from config files."""
        # Kafka configs
        for pattern in ("kafka*.properties", "kafka*.yml", "kafka*.yaml"):
            for path in self._find_files(pattern):
                rel = self._relative_path(path)
                fact = RawCommunicationFact(
                    name=f"kafka-config:{path.name}",
                    pattern_type="message_queue",
                    technology="kafka",
                    direction="both",
                    file_path=rel,
                )
                fact.add_evidence(rel, 1, 10, f"Kafka configuration: {path.name}")
                self.output.add_fact(fact)

        # RabbitMQ configs
        for pattern in ("rabbitmq*.conf", "rabbitmq*.yml", "rabbitmq*.yaml"):
            for path in self._find_files(pattern):
                rel = self._relative_path(path)
                fact = RawCommunicationFact(
                    name=f"rabbitmq-config:{path.name}",
                    pattern_type="message_queue",
                    technology="rabbitmq",
                    direction="both",
                    file_path=rel,
                )
                fact.add_evidence(rel, 1, 10, f"RabbitMQ configuration: {path.name}")
                self.output.add_fact(fact)

        # Docker-compose: detect messaging services
        for path in self._find_files("docker-compose*.yml"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            for tech, images in [("kafka", ["kafka", "confluent"]), ("rabbitmq", ["rabbitmq"]), ("redis", ["redis"]), ("nats", ["nats"])]:
                for img in images:
                    pattern = re.compile(rf"image:\s*.*{img}", re.IGNORECASE)
                    for m in pattern.finditer(content):
                        line_num = content[:m.start()].count("\n") + 1
                        fact = RawCommunicationFact(
                            name=f"messaging-infra:{tech}",
                            pattern_type="message_queue",
                            technology=tech,
                            direction="both",
                            file_path=rel,
                        )
                        fact.add_evidence(rel, line_num, line_num + 3, f"Docker Compose: {tech} service")
                        self.output.add_fact(fact)
