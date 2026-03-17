"""Spring Interface Detail Specialist — Extracts Java-specific interface facts.

Detects:
- @Scheduled methods (cron, fixedRate)
- Message listeners (@KafkaListener, @RabbitListener)
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawInterface


class SpringInterfaceDetailCollector(DimensionCollector):
    """Extracts Java-specific interface facts: schedulers and message listeners."""

    DIMENSION = "interfaces"

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect scheduler and message listener interface facts."""
        self._log_start()

        self._collect_schedulers()
        self._collect_listeners()

        self._log_end()
        return self.output

    def _collect_schedulers(self):
        """Collect @Scheduled methods."""
        SCHEDULED_PATTERN = re.compile(r"@Scheduled\s*\(([^)]+)\)")
        METHOD_PATTERN = re.compile(r"(?:public|private|protected)?\s*(?:void|[\w<>]+)\s+(\w+)\s*\(")

        java_files = self._find_files("*.java")

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for match in SCHEDULED_PATTERN.finditer(content):
                config = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                method_search = METHOD_PATTERN.search(content[match.end() : match.end() + 200])
                method_name = method_search.group(1) if method_search else "unknown"

                cron_match = re.search(r'cron\s*=\s*["\']([^"\']+)["\']', config)
                rate_match = re.search(r"fixedRate\s*=\s*(\d+)", config)

                scheduler = RawInterface(
                    name=method_name,
                    type="scheduler",
                    path=None,
                    method=None,
                    implemented_by_hint=java_file.stem,
                    container_hint=self.container_id,
                )

                if cron_match:
                    scheduler.metadata["cron"] = cron_match.group(1)
                if rate_match:
                    scheduler.metadata["fixed_rate_ms"] = int(rate_match.group(1))

                rel_path = self._relative_path(java_file)
                scheduler.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 3, reason=f"@Scheduled: {method_name}"
                )

                self.output.add_fact(scheduler)

    def _collect_listeners(self):
        """Collect message listeners (Kafka, RabbitMQ)."""
        KAFKA_LISTENER = re.compile(r"@KafkaListener\s*\(([^)]+)\)")
        RABBIT_LISTENER = re.compile(r"@RabbitListener\s*\(([^)]+)\)")

        java_files = self._find_files("*.java")

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for match in KAFKA_LISTENER.finditer(content):
                self._extract_listener(match, content, java_file, "kafka_listener")

            for match in RABBIT_LISTENER.finditer(content):
                self._extract_listener(match, content, java_file, "rabbit_listener")

    def _extract_listener(self, match, content: str, file_path: Path, listener_type: str):
        """Extract a message listener."""
        config = match.group(1)
        line_num = content[: match.start()].count("\n") + 1

        METHOD_PATTERN = re.compile(r"(?:public|private|protected)?\s*(?:void|[\w<>]+)\s+(\w+)\s*\(")
        method_search = METHOD_PATTERN.search(content[match.end() : match.end() + 200])
        method_name = method_search.group(1) if method_search else "unknown"

        topic_match = re.search(r'topics?\s*=\s*["\']([^"\']+)["\']', config)
        queue_match = re.search(r'queues?\s*=\s*["\']([^"\']+)["\']', config)

        listener = RawInterface(
            name=method_name,
            type=listener_type,
            path=topic_match.group(1) if topic_match else (queue_match.group(1) if queue_match else None),
            method=None,
            implemented_by_hint=file_path.stem,
            container_hint=self.container_id,
        )

        rel_path = self._relative_path(file_path)
        listener.add_evidence(
            path=rel_path, line_start=line_num, line_end=line_num + 5, reason=f"Message listener: {method_name}"
        )

        self.output.add_fact(listener)
