"""Spring Communication Specialist — Kafka, RabbitMQ, Spring Events, REST clients, WebSocket."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawCommunicationFact


class SpringCommunicationCollector(DimensionCollector):
    DIMENSION = "communication_patterns"

    KAFKA_LISTENER_PATTERN = re.compile(r'@KafkaListener\s*\(.*?topics?\s*=\s*["\{]([^"\}]+)')
    KAFKA_TEMPLATE_PATTERN = re.compile(r"KafkaTemplate|kafkaTemplate\.send")
    RABBIT_LISTENER_PATTERN = re.compile(r'@RabbitListener\s*\(.*?queues?\s*=\s*"([^"]+)')
    RABBIT_TEMPLATE_PATTERN = re.compile(r"RabbitTemplate|rabbitTemplate\.convertAndSend")
    EVENT_LISTENER_PATTERN = re.compile(r"@EventListener|ApplicationEventPublisher|publishEvent\(")
    REST_TEMPLATE_PATTERN = re.compile(r"RestTemplate|WebClient\.(?:create|builder)|\.exchange\(|\.retrieve\(")
    WEBSOCKET_PATTERN = re.compile(r"@EnableWebSocket|WebSocketHandler|SimpMessagingTemplate|@MessageMapping")
    JMS_PATTERN = re.compile(r"@JmsListener|JmsTemplate")
    FEIGN_PATTERN = re.compile(r"@FeignClient")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_patterns()
        self._log_end()
        return self.output

    def _collect_patterns(self):
        for path in self._find_files("*.java"):
            content = self._read_file_content(path)
            rel = self._relative_path(path)
            lines = content.splitlines()

            # Kafka consumer
            for m in self.KAFKA_LISTENER_PATTERN.finditer(content):
                topic = m.group(1)
                line_num = content[:m.start()].count("\n") + 1
                fact = RawCommunicationFact(
                    name=f"kafka-consumer:{topic}",
                    pattern_type="message_queue",
                    technology="kafka",
                    direction="consumer",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.metadata["topic"] = topic
                fact.add_evidence(rel, line_num, line_num + 3, f"@KafkaListener: topic={topic}")
                self.output.add_fact(fact)

            # Kafka producer
            if self.KAFKA_TEMPLATE_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "KafkaTemplate" in l or "kafkaTemplate" in l), 1)
                fact = RawCommunicationFact(
                    name=f"kafka-producer:{path.stem}",
                    pattern_type="message_queue",
                    technology="kafka",
                    direction="producer",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "KafkaTemplate producer")
                self.output.add_fact(fact)

            # RabbitMQ consumer
            for m in self.RABBIT_LISTENER_PATTERN.finditer(content):
                queue = m.group(1)
                line_num = content[:m.start()].count("\n") + 1
                fact = RawCommunicationFact(
                    name=f"rabbit-consumer:{queue}",
                    pattern_type="message_queue",
                    technology="rabbitmq",
                    direction="consumer",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.metadata["queue"] = queue
                fact.add_evidence(rel, line_num, line_num + 3, f"@RabbitListener: queue={queue}")
                self.output.add_fact(fact)

            # RabbitMQ producer
            if self.RABBIT_TEMPLATE_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "RabbitTemplate" in l or "rabbitTemplate" in l), 1)
                fact = RawCommunicationFact(
                    name=f"rabbit-producer:{path.stem}",
                    pattern_type="message_queue",
                    technology="rabbitmq",
                    direction="producer",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "RabbitTemplate producer")
                self.output.add_fact(fact)

            # Spring Events
            if self.EVENT_LISTENER_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "@EventListener" in l or "publishEvent" in l), 1)
                direction = "consumer" if "@EventListener" in content else "producer"
                if "publishEvent" in content and "@EventListener" in content:
                    direction = "both"
                fact = RawCommunicationFact(
                    name=f"spring-events:{path.stem}",
                    pattern_type="event_bus",
                    technology="spring_events",
                    direction=direction,
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"Spring Events: {direction}")
                self.output.add_fact(fact)

            # REST client (RestTemplate/WebClient)
            if self.REST_TEMPLATE_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "RestTemplate" in l or "WebClient" in l), 1)
                tech = "webclient" if "WebClient" in content else "rest_template"
                fact = RawCommunicationFact(
                    name=f"rest-client:{path.stem}",
                    pattern_type="rest_client",
                    technology=tech,
                    direction="client",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"REST client: {tech}")
                self.output.add_fact(fact)

            # Feign client
            for m in self.FEIGN_PATTERN.finditer(content):
                line_num = content[:m.start()].count("\n") + 1
                fact = RawCommunicationFact(
                    name=f"feign-client:{path.stem}",
                    pattern_type="rest_client",
                    technology="feign",
                    direction="client",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"@FeignClient: {path.stem}")
                self.output.add_fact(fact)

            # WebSocket
            if self.WEBSOCKET_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "WebSocket" in l or "@MessageMapping" in l), 1)
                fact = RawCommunicationFact(
                    name=f"websocket:{path.stem}",
                    pattern_type="websocket",
                    technology="spring_websocket",
                    direction="both",
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, "Spring WebSocket")
                self.output.add_fact(fact)

            # JMS
            if self.JMS_PATTERN.search(content):
                line_num = next((i for i, l in enumerate(lines, 1) if "Jms" in l), 1)
                direction = "consumer" if "@JmsListener" in content else "producer"
                fact = RawCommunicationFact(
                    name=f"jms:{path.stem}",
                    pattern_type="message_queue",
                    technology="jms",
                    direction=direction,
                    file_path=rel,
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, line_num, line_num + 3, f"JMS: {direction}")
                self.output.add_fact(fact)
