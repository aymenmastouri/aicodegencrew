"""Python Communication Specialist — Celery, Django signals, WebSocket, HTTP clients."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawCommunicationFact


class PythonCommunicationCollector(DimensionCollector):
    DIMENSION = "communication_patterns"

    CELERY_TASK_PATTERN = re.compile(r"@(?:shared_task|app\.task|celery\.task)")
    CELERY_SEND_PATTERN = re.compile(r"\.delay\(|\.apply_async\(|send_task\(")
    DJANGO_SIGNAL_PATTERN = re.compile(r"(?:Signal\(\)|@receiver|\.connect\(|\.send\(|\.send_robust\()")
    WEBSOCKET_PATTERN = re.compile(r"WebSocket|websocket|channels\.|@channel_layer")
    HTTP_CLIENT_PATTERN = re.compile(r"requests\.(?:get|post|put|delete|patch)|httpx\.\w+Client|aiohttp\.ClientSession")
    REDIS_PUBSUB_PATTERN = re.compile(r"\.pubsub\(\)|\.publish\(|\.subscribe\(")
    KAFKA_PATTERN = re.compile(r"KafkaProducer|KafkaConsumer|confluent_kafka")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_patterns()
        self._log_end()
        return self.output

    def _collect_patterns(self):
        for path in self._find_files("*.py"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            # Celery tasks
            if self.CELERY_TASK_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "@" in l and "task" in l.lower()), 1)
                fact = RawCommunicationFact(
                    name=f"celery-worker:{path.stem}",
                    pattern_type="message_queue",
                    technology="celery",
                    direction="consumer",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "Celery task consumer")
                self.output.add_fact(fact)

            if self.CELERY_SEND_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if ".delay(" in l or ".apply_async(" in l), 1)
                fact = RawCommunicationFact(
                    name=f"celery-producer:{path.stem}",
                    pattern_type="message_queue",
                    technology="celery",
                    direction="producer",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "Celery task producer")
                self.output.add_fact(fact)

            # Django signals
            if self.DJANGO_SIGNAL_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "Signal" in l or "@receiver" in l or ".send(" in l), 1)
                direction = "consumer" if "@receiver" in content or ".connect(" in content else "producer"
                if ("@receiver" in content or ".connect(" in content) and ".send(" in content:
                    direction = "both"
                fact = RawCommunicationFact(
                    name=f"django-signal:{path.stem}",
                    pattern_type="event_bus",
                    technology="django_signals",
                    direction=direction,
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"Django signal: {direction}")
                self.output.add_fact(fact)

            # WebSocket
            if self.WEBSOCKET_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "websocket" in l.lower() or "channel" in l.lower()), 1)
                fact = RawCommunicationFact(
                    name=f"websocket:{path.stem}",
                    pattern_type="websocket",
                    technology="python_websocket",
                    direction="both",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "WebSocket handler")
                self.output.add_fact(fact)

            # HTTP client
            if self.HTTP_CLIENT_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "requests." in l or "httpx." in l or "aiohttp" in l), 1)
                tech = "httpx" if "httpx" in content else "aiohttp" if "aiohttp" in content else "requests"
                fact = RawCommunicationFact(
                    name=f"http-client:{path.stem}",
                    pattern_type="rest_client",
                    technology=tech,
                    direction="client",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"HTTP client: {tech}")
                self.output.add_fact(fact)

            # Redis pub/sub
            if self.REDIS_PUBSUB_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "pubsub" in l or "publish" in l or "subscribe" in l), 1)
                fact = RawCommunicationFact(
                    name=f"redis-pubsub:{path.stem}",
                    pattern_type="message_queue",
                    technology="redis_pubsub",
                    direction="both",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "Redis pub/sub")
                self.output.add_fact(fact)

            # Kafka
            if self.KAFKA_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "Kafka" in l or "confluent" in l), 1)
                direction = "producer" if "KafkaProducer" in content else "consumer" if "KafkaConsumer" in content else "both"
                fact = RawCommunicationFact(
                    name=f"kafka:{path.stem}",
                    pattern_type="message_queue",
                    technology="kafka",
                    direction=direction,
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"Kafka: {direction}")
                self.output.add_fact(fact)
