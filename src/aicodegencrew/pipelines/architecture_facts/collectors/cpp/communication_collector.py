"""C++ Communication Specialist — ZeroMQ, gRPC, Boost.Asio, MQTT."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawCommunicationFact


class CppCommunicationCollector(DimensionCollector):
    DIMENSION = "communication_patterns"

    ZEROMQ_PATTERN = re.compile(r'#include\s*[<"]zmq')
    GRPC_CLIENT_PATTERN = re.compile(r'#include\s*[<"]grpc|grpc::')
    BOOST_ASIO_PATTERN = re.compile(r'#include\s*[<"]boost/asio')
    MQTT_PATTERN = re.compile(r'#include\s*[<"]mqtt|mosquitto')
    WEBSOCKET_PATTERN = re.compile(r'#include\s*[<"](?:boost/beast/websocket|websocketpp)')

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_patterns()
        self._log_end()
        return self.output

    def _collect_patterns(self):
        patterns = [
            (self.ZEROMQ_PATTERN, "message_queue", "zeromq"),
            (self.GRPC_CLIENT_PATTERN, "grpc_client", "grpc"),
            (self.BOOST_ASIO_PATTERN, "rest_client", "boost_asio"),
            (self.MQTT_PATTERN, "message_queue", "mqtt"),
            (self.WEBSOCKET_PATTERN, "websocket", "cpp_websocket"),
        ]

        tech_files: dict[str, int] = {}
        for ext in ("*.cpp", "*.h", "*.hpp"):
            for path in self._find_files(ext):
                content = self._read_file_content(path)
                for regex, pattern_type, tech in patterns:
                    if regex.search(content):
                        tech_files[tech] = tech_files.get(tech, 0) + 1

        pattern_map = {
            "zeromq": ("message_queue", "both"),
            "grpc": ("grpc_client", "client"),
            "boost_asio": ("rest_client", "both"),
            "mqtt": ("message_queue", "both"),
            "cpp_websocket": ("websocket", "both"),
        }

        for tech, count in tech_files.items():
            ptype, direction = pattern_map.get(tech, ("rest_client", "both"))
            fact = RawCommunicationFact(
                name=f"{tech}-usage",
                pattern_type=ptype,
                technology=tech,
                direction=direction,
                container_hint=self.container_id,
            )
            fact.metadata["file_count"] = count
            fact.add_evidence("(aggregated)", 0, 0, f"{tech} in {count} C++ files")
            self.output.add_fact(fact)
