"""Angular Communication Specialist — HttpClient, WebSocket, SSE, RxJS event patterns."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawCommunicationFact


class AngularCommunicationCollector(DimensionCollector):
    DIMENSION = "communication_patterns"

    HTTP_CLIENT_PATTERN = re.compile(r"HttpClient|this\.http\.")
    WEBSOCKET_PATTERN = re.compile(r"WebSocket|webSocket\(|WebSocketSubject")
    SSE_PATTERN = re.compile(r"EventSource|fromEvent\(.*,\s*['\"]message['\"]")
    SUBJECT_EVENT_BUS_PATTERN = re.compile(r"class\s+\w*(?:Event|Message|Notification)\w*Service")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_patterns()
        self._log_end()
        return self.output

    def _collect_patterns(self):
        http_client_count = 0
        for path in self._find_files("*.ts"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            if self.HTTP_CLIENT_PATTERN.search(content):
                http_client_count += 1

            if self.WEBSOCKET_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "WebSocket" in l or "webSocket" in l), 1)
                fact = RawCommunicationFact(
                    name=f"websocket:{path.stem}",
                    pattern_type="websocket",
                    technology="rxjs_websocket",
                    direction="both",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, line_num, line_num + 5, "Angular WebSocket connection")
                self.output.add_fact(fact)

            if self.SSE_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "EventSource" in l), 1)
                fact = RawCommunicationFact(
                    name=f"sse:{path.stem}",
                    pattern_type="sse",
                    technology="event_source",
                    direction="consumer",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, line_num, line_num + 3, "Server-Sent Events consumer")
                self.output.add_fact(fact)

            if self.SUBJECT_EVENT_BUS_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "class" in l and ("Event" in l or "Message" in l)), 1)
                fact = RawCommunicationFact(
                    name=f"event-bus:{path.stem}",
                    pattern_type="event_bus",
                    technology="rxjs_subject",
                    direction="both",
                    file_path=rel,
                    container_hint=self.container_id or "frontend",
                )
                fact.add_evidence(rel, line_num, line_num + 5, f"RxJS event bus service: {path.stem}")
                self.output.add_fact(fact)

        if http_client_count:
            fact = RawCommunicationFact(
                name="angular-http-client",
                pattern_type="rest_client",
                technology="angular_http",
                direction="client",
                container_hint=self.container_id or "frontend",
            )
            fact.metadata["file_count"] = http_client_count
            fact.add_evidence("(aggregated)", 0, 0, f"Angular HttpClient in {http_client_count} files")
            self.output.add_fact(fact)
