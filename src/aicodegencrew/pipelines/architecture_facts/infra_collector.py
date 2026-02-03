"""Infrastructure collector for architecture facts.

Extracts:
- Docker/docker-compose: container hints
- Kubernetes/Helm: deployment hints
- CI/CD configs: pipeline hints
- Database migrations: DB container hints
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .base_collector import (
    BaseCollector,
    CollectedComponent,
    CollectedInterface,
    CollectedRelation,
    CollectedEvidence,
)
from ...shared.utils.logger import logger


class InfraCollector(BaseCollector):
    """Collector for infrastructure and deployment configurations."""
    
    # File patterns for different infra types
    DOCKER_FILES = ["Dockerfile", "dockerfile", "Dockerfile.*"]
    COMPOSE_FILES = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    K8S_PATTERNS = ["*.yaml", "*.yml"]
    K8S_DIRS = ["k8s", "kubernetes", "deploy", "manifests", "charts"]
    CI_FILES = [".gitlab-ci.yml", ".github/workflows/*.yml", "Jenkinsfile", "azure-pipelines.yml", ".circleci/config.yml"]
    
    # Kubernetes resource patterns
    K8S_DEPLOYMENT = re.compile(r'kind:\s*Deployment', re.IGNORECASE)
    K8S_SERVICE = re.compile(r'kind:\s*Service', re.IGNORECASE)
    K8S_INGRESS = re.compile(r'kind:\s*Ingress', re.IGNORECASE)
    K8S_CONFIGMAP = re.compile(r'kind:\s*ConfigMap', re.IGNORECASE)
    K8S_SECRET = re.compile(r'kind:\s*Secret', re.IGNORECASE)
    
    # Docker patterns
    DOCKER_FROM = re.compile(r'^FROM\s+([^\s]+)', re.MULTILINE)
    DOCKER_EXPOSE = re.compile(r'^EXPOSE\s+(\d+)', re.MULTILINE)
    
    # Compose service pattern
    COMPOSE_SERVICE = re.compile(r'^  (\w+):\s*$', re.MULTILINE)
    COMPOSE_IMAGE = re.compile(r'image:\s*([^\s]+)')
    COMPOSE_PORT = re.compile(r'ports:\s*\n\s*-\s*["\']?(\d+):(\d+)')
    
    def __init__(self, repo_path: Path, container_id: str = "infrastructure"):
        super().__init__(repo_path, container_id)
        self.detected_containers: List[Dict] = []
    
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """Collect infrastructure architecture facts."""
        logger.info(f"[InfraCollector] Scanning {self.repo_path}")
        
        # Collect Docker facts
        self._collect_docker_facts()
        
        # Collect docker-compose facts
        self._collect_compose_facts()
        
        # Collect Kubernetes facts
        self._collect_k8s_facts()
        
        # Collect CI/CD facts
        self._collect_ci_facts()
        
        # Collect database migration hints
        self._collect_db_hints()
        
        logger.info(f"[InfraCollector] Collected: {len(self.components)} components, {len(self.interfaces)} interfaces")
        logger.info(f"[InfraCollector] Detected containers: {[c['id'] for c in self.detected_containers]}")
        
        return self.components, self.interfaces, self.relations, self.evidence
    
    def get_detected_containers(self) -> List[Dict]:
        """Return containers detected from infrastructure."""
        return self.detected_containers
    
    # Directories to skip during infrastructure scanning
    SKIP_DIRS = {'node_modules', '.git', '__pycache__', 'dist', 'build', 'target', '.venv', 'venv'}
    
    def _should_skip_path(self, file_path: Path) -> bool:
        """Check if path should be skipped (e.g., node_modules)."""
        path_parts = set(file_path.parts)
        return bool(path_parts & self.SKIP_DIRS)
    
    def _collect_docker_facts(self):
        """Collect facts from Dockerfiles."""
        processed_files = set()  # Track processed files to avoid duplicates
        for pattern in self.DOCKER_FILES:
            for dockerfile in self.repo_path.rglob(pattern):
                if not dockerfile.is_file():
                    continue
                # Skip node_modules and other ignored directories
                if self._should_skip_path(dockerfile):
                    continue
                # Skip already processed files
                rel_path = str(dockerfile.relative_to(self.repo_path))
                if rel_path in processed_files:
                    continue
                processed_files.add(rel_path)
                self._process_dockerfile(dockerfile)
    
    def _process_dockerfile(self, file_path: Path):
        """Process a Dockerfile."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Determine container name from directory
        parent_dir = file_path.parent.name
        if parent_dir == str(self.repo_path.name) or parent_dir == '.':
            container_id = "app"
        else:
            container_id = self._make_component_id(parent_dir)
        
        # Extract base image
        base_image = None
        from_match = self.DOCKER_FROM.search(content)
        if from_match:
            base_image = from_match.group(1)
        
        # Extract exposed ports
        ports = self.DOCKER_EXPOSE.findall(content)
        
        ev_id = self._add_evidence(
            rel_path,
            1,
            len(lines),
            f"Dockerfile for {container_id}" + (f" based on {base_image}" if base_image else ""),
            prefix="ev_docker"
        )
        
        # Add as detected container
        tech = self._guess_technology_from_image(base_image) if base_image else "docker"
        self.detected_containers.append({
            "id": container_id,
            "name": parent_dir,
            "type": "application",
            "technology": tech,
            "evidence": [ev_id]
        })
        
        # Add component for Dockerfile - use file path for unique ID
        docker_component_id = self._make_component_id(f"docker_{container_id}", rel_path)
        self.components.append(CollectedComponent(
            id=docker_component_id,
            container=self.container_id,
            name=f"Dockerfile-{parent_dir}",
            stereotype="dockerfile",
            file_path=rel_path,
            evidence_ids=[ev_id]
        ))
    
    def _collect_compose_facts(self):
        """Collect facts from docker-compose files."""
        for pattern in self.COMPOSE_FILES:
            for compose_file in self.repo_path.rglob(pattern):
                if not compose_file.is_file():
                    continue
                self._process_compose_file(compose_file)
    
    def _process_compose_file(self, file_path: Path):
        """Process a docker-compose file."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        # Find services
        in_services = False
        current_service = None
        service_start = 0
        
        for i, line in enumerate(lines, 1):
            if line.strip() == 'services:':
                in_services = True
                continue
            
            if in_services:
                # Check for service definition (indented with 2 spaces, ends with :)
                if line.startswith('  ') and not line.startswith('    ') and ':' in line:
                    # Save previous service
                    if current_service:
                        self._add_compose_service(current_service, service_start, i - 1, rel_path, lines)
                    
                    current_service = line.strip().rstrip(':')
                    service_start = i
                
                # Check if we've left services section
                if not line.startswith(' ') and line.strip() and line.strip() != 'services:':
                    if current_service:
                        self._add_compose_service(current_service, service_start, i - 1, rel_path, lines)
                    in_services = False
                    current_service = None
        
        # Don't forget last service
        if current_service:
            self._add_compose_service(current_service, service_start, len(lines), rel_path, lines)
    
    def _add_compose_service(self, service_name: str, start_line: int, end_line: int, rel_path: str, lines: List[str]):
        """Add a docker-compose service as detected container."""
        service_content = ''.join(lines[start_line - 1:end_line])
        
        # Extract image
        image_match = self.COMPOSE_IMAGE.search(service_content)
        image = image_match.group(1) if image_match else None
        
        ev_id = self._add_evidence(
            rel_path,
            start_line,
            end_line,
            f"docker-compose service '{service_name}'" + (f" using {image}" if image else ""),
            prefix="ev_compose"
        )
        
        # Determine type
        container_type = "application"
        tech = self._guess_technology_from_image(image) if image else "docker"
        
        if any(db in (image or "").lower() for db in ["postgres", "mysql", "mongo", "redis", "elasticsearch"]):
            container_type = "database"
        elif any(mq in (image or "").lower() for mq in ["rabbitmq", "kafka", "activemq"]):
            container_type = "message_broker"
        
        self.detected_containers.append({
            "id": service_name,
            "name": service_name,
            "type": container_type,
            "technology": tech,
            "evidence": [ev_id]
        })
    
    def _collect_k8s_facts(self):
        """Collect facts from Kubernetes manifests."""
        for k8s_dir in self.K8S_DIRS:
            k8s_path = self.repo_path / k8s_dir
            if k8s_path.exists():
                self._scan_k8s_directory(k8s_path)
        
        # Also check for Helm charts
        for chart_yaml in self.repo_path.rglob("Chart.yaml"):
            self._process_helm_chart(chart_yaml.parent)
    
    def _scan_k8s_directory(self, k8s_path: Path):
        """Scan a Kubernetes directory for manifests."""
        for yaml_file in k8s_path.rglob("*.yaml"):
            self._process_k8s_manifest(yaml_file)
        for yml_file in k8s_path.rglob("*.yml"):
            self._process_k8s_manifest(yml_file)
    
    def _process_k8s_manifest(self, file_path: Path):
        """Process a Kubernetes manifest."""
        lines = self._read_file_lines(file_path)
        if not lines:
            return
        
        content = ''.join(lines)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        resource_type = None
        if self.K8S_DEPLOYMENT.search(content):
            resource_type = "deployment"
        elif self.K8S_SERVICE.search(content):
            resource_type = "k8s-service"
        elif self.K8S_INGRESS.search(content):
            resource_type = "ingress"
        elif self.K8S_CONFIGMAP.search(content):
            resource_type = "configmap"
        
        if resource_type:
            ev_id = self._add_evidence(
                rel_path,
                1,
                len(lines),
                f"Kubernetes {resource_type} manifest",
                prefix="ev_k8s"
            )
            
            self.components.append(CollectedComponent(
                id=f"k8s_{file_path.stem}",
                container=self.container_id,
                name=file_path.stem,
                stereotype=resource_type,
                file_path=rel_path,
                evidence_ids=[ev_id]
            ))
    
    def _process_helm_chart(self, chart_path: Path):
        """Process a Helm chart directory."""
        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            return
        
        lines = self._read_file_lines(chart_yaml)
        rel_path = str(chart_yaml.relative_to(self.repo_path))
        
        ev_id = self._add_evidence(
            rel_path,
            1,
            len(lines),
            f"Helm chart at {chart_path.name}",
            prefix="ev_helm"
        )
        
        self.components.append(CollectedComponent(
            id=f"helm_{chart_path.name}",
            container=self.container_id,
            name=chart_path.name,
            stereotype="helm-chart",
            file_path=rel_path,
            evidence_ids=[ev_id]
        ))
    
    def _collect_ci_facts(self):
        """Collect CI/CD configuration facts."""
        ci_patterns = [
            (".gitlab-ci.yml", "gitlab-ci"),
            (".github/workflows", "github-actions"),
            ("Jenkinsfile", "jenkins"),
            ("azure-pipelines.yml", "azure-devops"),
            (".circleci/config.yml", "circleci"),
        ]
        
        for pattern, ci_type in ci_patterns:
            path = self.repo_path / pattern
            if path.exists():
                if path.is_file():
                    self._add_ci_component(path, ci_type)
                elif path.is_dir():
                    for f in path.glob("*.yml"):
                        self._add_ci_component(f, ci_type)
                    for f in path.glob("*.yaml"):
                        self._add_ci_component(f, ci_type)
    
    def _add_ci_component(self, file_path: Path, ci_type: str):
        """Add a CI configuration as component."""
        lines = self._read_file_lines(file_path)
        rel_path = str(file_path.relative_to(self.repo_path))
        
        ev_id = self._add_evidence(
            rel_path,
            1,
            len(lines),
            f"{ci_type} CI/CD configuration",
            prefix="ev_ci"
        )
        
        self.components.append(CollectedComponent(
            id=f"ci_{file_path.stem}",
            container=self.container_id,
            name=file_path.name,
            stereotype=ci_type,
            file_path=rel_path,
            evidence_ids=[ev_id]
        ))
    
    def _collect_db_hints(self):
        """Collect database migration hints."""
        migration_patterns = [
            ("db/migrations", "sql"),
            ("migrations", "sql"),
            ("flyway", "flyway"),
            ("liquibase", "liquibase"),
            ("src/main/resources/db/migration", "flyway"),
        ]
        
        for pattern, db_type in migration_patterns:
            migration_path = self.repo_path / pattern
            if migration_path.exists() and migration_path.is_dir():
                sql_files = list(migration_path.glob("*.sql"))
                if sql_files:
                    ev_id = self._add_evidence(
                        str(migration_path.relative_to(self.repo_path)),
                        1,
                        1,
                        f"Database migrations ({len(sql_files)} files, {db_type})",
                        prefix="ev_db"
                    )
                    
                    self.detected_containers.append({
                        "id": "database",
                        "name": "database",
                        "type": "database",
                        "technology": db_type,
                        "evidence": [ev_id]
                    })
                    break
    
    def _guess_technology_from_image(self, image: str) -> str:
        """Guess technology from Docker image name."""
        if not image:
            return "docker"
        
        image_lower = image.lower()
        
        tech_map = {
            "openjdk": "Java",
            "java": "Java",
            "maven": "Maven/Java",
            "gradle": "Gradle/Java",
            "node": "Node.js",
            "python": "Python",
            "golang": "Go",
            "rust": "Rust",
            "dotnet": ".NET",
            "nginx": "nginx",
            "postgres": "PostgreSQL",
            "mysql": "MySQL",
            "mongo": "MongoDB",
            "redis": "Redis",
            "elasticsearch": "Elasticsearch",
            "rabbitmq": "RabbitMQ",
            "kafka": "Kafka",
        }
        
        for key, tech in tech_map.items():
            if key in image_lower:
                return tech
        
        return image.split("/")[-1].split(":")[0]
