"""
ComponentCollector - Aggregates component facts from specialists.

This is an AGGREGATOR that:
1. Receives container info from orchestrator
2. Runs specialists based on container technology
3. Merges all component facts

Container-Aware:
- Spring specialists run in containers with type="backend"
- Angular specialists run in containers with type="frontend"
- Each specialist searches in the container's root_path

Output → components.json
"""

from pathlib import Path
from typing import Dict, List, Optional

from .base import DimensionCollector, CollectorOutput, RawComponent, RawFact
from .spring import SpringRestCollector, SpringServiceCollector, SpringRepositoryCollector
from .angular import AngularModuleCollector, AngularComponentCollector, AngularServiceCollector
from ....shared.utils.logger import logger


class ComponentCollector(DimensionCollector):
    """
    Aggregates component facts from technology-specific specialists.
    
    Uses container information to determine:
    - Which specialists to run
    - Where to search (container root paths)
    """
    
    DIMENSION = "components"
    
    def __init__(self, repo_path: Path, containers: List[Dict] = None):
        """
        Initialize with container context.
        
        Args:
            repo_path: Repository root
            containers: List of detected containers with technology and root_path
        """
        super().__init__(repo_path)
        self.containers = containers or []
    
    def collect(self) -> CollectorOutput:
        """Collect components from all relevant specialists."""
        self._log_start()
        
        # Collect from Spring containers
        spring_containers = self._get_containers_by_technology("Spring Boot")
        for container in spring_containers:
            self._collect_spring_components(container)
        
        # Collect from Angular containers
        angular_containers = self._get_containers_by_technology("Angular")
        for container in angular_containers:
            self._collect_angular_components(container)
        
        # Fallback: if no containers, detect and run anyway
        if not spring_containers and not angular_containers:
            self._fallback_detection()
        
        self._log_end()
        return self.output
    
    def _get_containers_by_technology(self, technology: str) -> List[Dict]:
        """Get containers matching a technology."""
        return [c for c in self.containers if c.get("technology") == technology]
    
    def _get_container_root(self, container: Dict) -> Path:
        """Get the root path for a container."""
        root_path = container.get("root_path", "")
        if root_path and root_path != ".":
            return self.repo_path / root_path
        return self.repo_path
    
    def _collect_spring_components(self, container: Dict):
        """Run Spring specialists for a container."""
        container_root = self._get_container_root(container)
        container_name = container.get("name", "backend")
        
        logger.info(f"[ComponentCollector] Running Spring specialists for '{container_name}' in {container_root}")
        
        # Controllers
        rest_collector = SpringRestCollector(container_root, container_id=container_name)
        rest_output = rest_collector.collect()
        self._merge_output(rest_output)
        
        # Services
        service_collector = SpringServiceCollector(container_root, container_id=container_name)
        service_output = service_collector.collect()
        self._merge_output(service_output)
        
        # Repositories
        repo_collector = SpringRepositoryCollector(container_root, container_id=container_name)
        repo_output = repo_collector.collect()
        self._merge_output(repo_output)
    
    def _collect_angular_components(self, container: Dict):
        """Run Angular specialists for a container."""
        container_root = self._get_container_root(container)
        container_name = container.get("name", "frontend")
        
        logger.info(f"[ComponentCollector] Running Angular specialists for '{container_name}' in {container_root}")
        
        # Modules
        module_collector = AngularModuleCollector(container_root, container_id=container_name)
        module_output = module_collector.collect()
        self._merge_output(module_output)
        
        # Components
        component_collector = AngularComponentCollector(container_root, container_id=container_name)
        component_output = component_collector.collect()
        self._merge_output(component_output)
        
        # Services
        service_collector = AngularServiceCollector(container_root, container_id=container_name)
        service_output = service_collector.collect()
        self._merge_output(service_output)
    
    def _fallback_detection(self):
        """Fallback: detect technologies without container info."""
        logger.info("[ComponentCollector] No containers provided, running fallback detection...")
        
        # Detect Spring
        if self._detect_spring():
            logger.info("[ComponentCollector] Detected Spring Boot, running specialists...")
            self._collect_spring_components({"name": "backend", "root_path": ""})
        
        # Detect Angular - search in subdirectories too
        angular_root = self._find_angular_root()
        if angular_root:
            logger.info(f"[ComponentCollector] Detected Angular in {angular_root}")
            self._collect_angular_components({"name": "frontend", "root_path": str(angular_root.relative_to(self.repo_path))})
    
    def _detect_spring(self) -> bool:
        """Detect if project has Spring Boot."""
        # Check Maven
        for pom in self.repo_path.rglob("pom.xml"):
            if "node_modules" in str(pom) or "deployment" in str(pom):
                continue
            try:
                content = pom.read_text(encoding='utf-8', errors='ignore')
                if "spring-boot" in content.lower():
                    return True
            except:
                continue
        
        # Check Gradle
        for gradle in list(self.repo_path.rglob("build.gradle")) + list(self.repo_path.rglob("build.gradle.kts")):
            if "node_modules" in str(gradle) or "deployment" in str(gradle) or "buildSrc" in str(gradle):
                continue
            try:
                content = gradle.read_text(encoding='utf-8', errors='ignore')
                if "org.springframework.boot" in content or "spring-boot" in content.lower():
                    return True
            except:
                continue
        
        return False
    
    def _find_angular_root(self) -> Optional[Path]:
        """Find Angular root directory (looks in subdirectories)."""
        # Check root
        if (self.repo_path / "angular.json").exists():
            return self.repo_path
        
        # Check common subdirectories
        for subdir in ["frontend", "client", "web", "ui", "angular"]:
            angular_json = self.repo_path / subdir / "angular.json"
            if angular_json.exists():
                return angular_json.parent
        
        # Search deeper
        for angular_json in self.repo_path.rglob("angular.json"):
            if "node_modules" not in str(angular_json) and "deployment" not in str(angular_json):
                return angular_json.parent
        
        return None
    
    def _merge_output(self, other: CollectorOutput):
        """Merge another collector's output into this one (only RawComponent facts)."""
        for fact in other.facts:
            # Only add actual components, not interfaces
            if isinstance(fact, RawComponent):
                self.output.add_fact(fact)
        
        for relation in other.relations:
            self.output.add_relation(relation)
