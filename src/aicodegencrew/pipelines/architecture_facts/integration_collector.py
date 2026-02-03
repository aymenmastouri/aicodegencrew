"""Integration Collector - Detects cross-container integrations.

Detects:
- REST Clients (RestTemplate, WebClient, Feign)
- Message Queues (Kafka, RabbitMQ)
- Database Connections (JDBC URLs)
- External Service Integrations
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict

from .base_collector import (
    BaseCollector,
    CollectedComponent,
    CollectedInterface,
    CollectedRelation,
    CollectedEvidence,
)


class IntegrationCollector(BaseCollector):
    """Collects cross-container integration facts."""
    
    def __init__(self, project_root: Path, container_id: str = "backend"):
        super().__init__(project_root, container_id)
        self._component_counter = 0
        self._detected_integrations: Dict[str, List[dict]] = defaultdict(list)
        
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """Collect all cross-container integration facts."""
        self._scan_java_files()
        self._scan_config_files()
        self._create_integration_components()
        
        return self.components, self.interfaces, self.relations, self.evidence
    
    def _create_component(self, name: str, stereotype: str, file_path: str, 
                         evidence_ids: List[str], confidence: float = 1.0,
                         tags: List[str] = None) -> CollectedComponent:
        """Create a component."""
        cid = f"cmp_int_{self._component_counter:04d}"
        self._component_counter += 1
        
        component = CollectedComponent(
            id=cid,
            container=self.container_id,
            name=name,
            stereotype=stereotype,
            file_path=file_path,
            evidence_ids=evidence_ids,
            confidence=confidence,
            layer="infrastructure",
            tags=tags or [],
        )
        self.components.append(component)
        return component
    
    def _scan_java_files(self):
        """Scan Java files for integration patterns."""
        java_files = list(self.repo_path.rglob("*.java"))
        
        for java_file in java_files:
            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(java_file.relative_to(self.repo_path))
            except Exception:
                continue
            
            # REST Clients
            self._detect_rest_template(content, rel_path)
            self._detect_webclient(content, rel_path)
            self._detect_feign_client(content, rel_path)
            
            # Message Queues
            self._detect_kafka(content, rel_path)
            self._detect_rabbitmq(content, rel_path)
    
    def _detect_rest_template(self, content: str, file_path: str):
        """Detect RestTemplate usage."""
        if re.search(r'RestTemplate|restTemplate\.get|restTemplate\.post|restTemplate\.exchange', content):
            # Extract target URL if possible
            url_match = re.search(r'@Value\s*\(\s*"\$\{([^}]+)\}"\s*\)[^;]*String\s+(\w*[Uu]rl)', content)
            target = url_match.group(1) if url_match else "external-service"
            
            self._detected_integrations["rest_client"].append({
                "file": file_path,
                "type": "RestTemplate",
                "target": target,
                "confidence": 0.9,
            })
    
    def _detect_webclient(self, content: str, file_path: str):
        """Detect WebClient usage."""
        if re.search(r'WebClient|webClient\.|WebClient\.Builder', content):
            # Extract base URL
            url_match = re.search(r'\.baseUrl\s*\(\s*"([^"]+)"', content)
            target = url_match.group(1) if url_match else "external-service"
            
            self._detected_integrations["rest_client"].append({
                "file": file_path,
                "type": "WebClient",
                "target": target,
                "confidence": 0.9,
            })
    
    def _detect_feign_client(self, content: str, file_path: str):
        """Detect Feign client interfaces."""
        feign_match = re.search(r'@FeignClient\s*\([^)]*name\s*=\s*"([^"]+)"', content)
        if feign_match:
            service_name = feign_match.group(1)
            
            # Extract URL if present
            url_match = re.search(r'@FeignClient\s*\([^)]*url\s*=\s*"([^"]+)"', content)
            target = url_match.group(1) if url_match else service_name
            
            self._detected_integrations["feign_client"].append({
                "file": file_path,
                "type": "FeignClient",
                "service_name": service_name,
                "target": target,
                "confidence": 1.0,  # Feign is explicit
            })
    
    def _detect_kafka(self, content: str, file_path: str):
        """Detect Kafka usage."""
        # Producer
        if re.search(r'KafkaTemplate|kafkaTemplate\.send', content):
            topic_match = re.search(r'@Value\s*\(\s*"\$\{([^}]*topic[^}]*)\}"', content, re.IGNORECASE)
            topic = topic_match.group(1) if topic_match else "kafka-topic"
            
            self._detected_integrations["kafka"].append({
                "file": file_path,
                "type": "KafkaProducer",
                "topic": topic,
                "confidence": 1.0,
            })
        
        # Consumer
        listener_match = re.search(r'@KafkaListener\s*\([^)]*topics\s*=\s*"?\$?\{?([^}"]+)', content)
        if listener_match:
            topic = listener_match.group(1)
            
            self._detected_integrations["kafka"].append({
                "file": file_path,
                "type": "KafkaConsumer",
                "topic": topic,
                "confidence": 1.0,
            })
    
    def _detect_rabbitmq(self, content: str, file_path: str):
        """Detect RabbitMQ usage."""
        if re.search(r'RabbitTemplate|rabbitTemplate\.|@RabbitListener|AmqpTemplate', content):
            exchange_match = re.search(r'@Value\s*\(\s*"\$\{([^}]*exchange[^}]*)\}"', content, re.IGNORECASE)
            exchange = exchange_match.group(1) if exchange_match else "rabbitmq-exchange"
            
            self._detected_integrations["rabbitmq"].append({
                "file": file_path,
                "type": "RabbitMQ",
                "exchange": exchange,
                "confidence": 1.0,
            })
    
    def _scan_config_files(self):
        """Scan configuration files for database connections."""
        config_patterns = [
            "application.properties",
            "application.yml",
            "application.yaml",
            "application-*.properties",
            "application-*.yml",
        ]
        
        for pattern in config_patterns:
            for config_file in self.repo_path.rglob(pattern):
                try:
                    content = config_file.read_text(encoding='utf-8', errors='ignore')
                    rel_path = str(config_file.relative_to(self.repo_path))
                except Exception:
                    continue
                
                self._detect_database_connection(content, rel_path)
    
    def _detect_database_connection(self, content: str, file_path: str):
        """Detect database connection configuration."""
        # JDBC URL patterns
        jdbc_patterns = [
            (r'jdbc:postgresql://([^/\s]+)', "PostgreSQL"),
            (r'jdbc:mysql://([^/\s]+)', "MySQL"),
            (r'jdbc:oracle:thin:@([^/\s]+)', "Oracle"),
            (r'jdbc:sqlserver://([^;/\s]+)', "SQLServer"),
            (r'jdbc:h2:([^;\s]+)', "H2"),
        ]
        
        for pattern, db_type in jdbc_patterns:
            match = re.search(pattern, content)
            if match:
                host = match.group(1)
                
                self._detected_integrations["database"].append({
                    "file": file_path,
                    "type": db_type,
                    "host": host,
                    "confidence": 1.0,
                })
    
    def _create_integration_components(self):
        """Create components from detected integrations."""
        
        # REST Clients
        rest_integrations = self._detected_integrations.get("rest_client", [])
        if rest_integrations:
            evidence_ids = []
            for integration in rest_integrations[:10]:
                eid = self._add_evidence(
                    integration["file"], 1, 50,
                    f"REST Client ({integration['type']}): calls {integration['target']}",
                    prefix="ev_int"
                )
                evidence_ids.append(eid)
            
            self._create_component(
                name="rest_client_integration",
                stereotype="integration",
                file_path=rest_integrations[0]["file"],
                evidence_ids=evidence_ids,
                confidence=min(i["confidence"] for i in rest_integrations),
                tags=["http", "rest", "client"],
            )
        
        # Feign Clients
        feign_integrations = self._detected_integrations.get("feign_client", [])
        for integration in feign_integrations:
            eid = self._add_evidence(
                integration["file"], 1, 50,
                f"Feign Client: {integration['service_name']} -> {integration['target']}",
                prefix="ev_int"
            )
            
            self._create_component(
                name=f"feign_{integration['service_name'].replace('-', '_')}",
                stereotype="integration",
                file_path=integration["file"],
                evidence_ids=[eid],
                confidence=1.0,
                tags=["feign", "http", "client", integration["service_name"]],
            )
        
        # Kafka
        kafka_integrations = self._detected_integrations.get("kafka", [])
        if kafka_integrations:
            evidence_ids = []
            for integration in kafka_integrations[:10]:
                eid = self._add_evidence(
                    integration["file"], 1, 50,
                    f"Kafka {integration['type']}: topic {integration['topic']}",
                    prefix="ev_int"
                )
                evidence_ids.append(eid)
            
            self._create_component(
                name="kafka_integration",
                stereotype="message_queue",
                file_path=kafka_integrations[0]["file"],
                evidence_ids=evidence_ids,
                confidence=1.0,
                tags=["kafka", "messaging", "async"],
            )
        
        # RabbitMQ
        rabbitmq_integrations = self._detected_integrations.get("rabbitmq", [])
        if rabbitmq_integrations:
            evidence_ids = []
            for integration in rabbitmq_integrations[:10]:
                eid = self._add_evidence(
                    integration["file"], 1, 50,
                    f"RabbitMQ: exchange {integration['exchange']}",
                    prefix="ev_int"
                )
                evidence_ids.append(eid)
            
            self._create_component(
                name="rabbitmq_integration",
                stereotype="message_queue",
                file_path=rabbitmq_integrations[0]["file"],
                evidence_ids=evidence_ids,
                confidence=1.0,
                tags=["rabbitmq", "amqp", "messaging"],
            )
        
        # Database Connections
        db_integrations = self._detected_integrations.get("database", [])
        for integration in db_integrations:
            eid = self._add_evidence(
                integration["file"], 1, 20,
                f"Database Connection: {integration['type']} at {integration['host']}",
                prefix="ev_int"
            )
            
            self._create_component(
                name=f"{integration['type'].lower()}_connection",
                stereotype="database_connection",
                file_path=integration["file"],
                evidence_ids=[eid],
                confidence=1.0,
                tags=["database", integration["type"].lower(), "jdbc"],
            )
