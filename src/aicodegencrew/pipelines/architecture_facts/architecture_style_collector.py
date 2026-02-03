"""Architecture Style Collector - Detects architecture styles and design patterns.

Detects:
- Architecture Styles: Microservices, Monolith, Layered, Hexagonal
- Design Patterns: Repository, Factory, Singleton, Strategy, Builder, Adapter
- Module structure analysis
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


class ArchitectureStyleCollector(BaseCollector):
    """Collects architecture style and design pattern facts."""
    
    def __init__(self, project_root: Path, container_id: str = "backend"):
        super().__init__(project_root, container_id)
        self._component_counter = 0
        self._detected_patterns: Set[str] = set()
        self._detected_styles: Set[str] = set()
        
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """Collect all architecture style and design pattern facts."""
        self._analyze_folder_structure()
        self._detect_design_patterns()
        self._detect_architecture_styles()
        
        return self.components, self.interfaces, self.relations, self.evidence
    
    def _create_component(self, name: str, stereotype: str, file_path: str, 
                         evidence_ids: List[str]) -> CollectedComponent:
        """Create a component."""
        cid = f"cmp_arch_{self._component_counter:04d}"
        self._component_counter += 1
        
        component = CollectedComponent(
            id=cid,
            container=self.container_id,
            name=name,
            stereotype=stereotype,
            file_path=file_path,
            evidence_ids=evidence_ids,
            module=self._derive_module_from_path(file_path)
        )
        self.components.append(component)
        return component
    
    def _analyze_folder_structure(self):
        """Analyze folder structure for architecture indicators."""
        self._layer_folders = defaultdict(list)
        self._pattern_folders = defaultdict(list)
        self._module_count = 0
        self._service_modules = []
        
        java_dirs = list(self.repo_path.rglob("src/main/java"))
        
        for java_dir in java_dirs:
            if not java_dir.exists():
                continue
                
            for subdir in java_dir.rglob("*"):
                if not subdir.is_dir():
                    continue
                    
                dir_name = subdir.name.lower()
                
                # Layer detection
                if dir_name in ["controller", "controllers", "rest", "api", "web", "endpoint", "endpoints"]:
                    self._layer_folders["controller"].append(subdir)
                elif dir_name in ["service", "services", "usecase", "usecases", "application"]:
                    self._layer_folders["service"].append(subdir)
                elif dir_name in ["repository", "repositories", "dao", "daos", "persistence"]:
                    self._layer_folders["repository"].append(subdir)
                elif dir_name in ["entity", "entities", "model", "models", "domain"]:
                    self._layer_folders["entity"].append(subdir)
                    
                # Pattern folder detection
                if dir_name in ["factory", "factories"]:
                    self._pattern_folders["factory"].append(subdir)
                elif dir_name in ["strategy", "strategies"]:
                    self._pattern_folders["strategy"].append(subdir)
                elif dir_name in ["adapter", "adapters"]:
                    self._pattern_folders["adapter"].append(subdir)
                elif dir_name in ["port", "ports"]:
                    self._pattern_folders["port"].append(subdir)
                elif dir_name in ["builder", "builders"]:
                    self._pattern_folders["builder"].append(subdir)
                elif dir_name == "module":
                    # Count modules for monolith detection
                    self._module_count = len(list(subdir.iterdir()))
        
        # Detect service modules (microservices indicator)
        for pom in self.repo_path.rglob("pom.xml"):
            if pom.parent != self.repo_path:  # Not root pom
                self._service_modules.append(pom.parent)
        
        for gradle in self.repo_path.rglob("build.gradle"):
            if gradle.parent != self.repo_path:
                self._service_modules.append(gradle.parent)
    
    def _detect_design_patterns(self):
        """Detect design patterns from code analysis."""
        java_files = list(self.repo_path.rglob("*.java"))
        
        pattern_evidence = defaultdict(list)
        
        for java_file in java_files:
            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore')
                rel_path = str(java_file.relative_to(self.repo_path))
            except Exception:
                continue
            
            # Repository Pattern
            if re.search(r'@Repository|extends\s+(Jpa|Crud|Mongo)Repository|interface\s+\w+Repository', content):
                pattern_evidence["repository"].append((rel_path, "Repository annotation or interface"))
            
            # Factory Pattern
            if re.search(r'class\s+\w*Factory|Factory\s*{|create\w+\s*\([^)]*\)\s*{[^}]*new\s+\w+', content, re.DOTALL):
                pattern_evidence["factory"].append((rel_path, "Factory class with create methods"))
            
            # Singleton Pattern
            if re.search(r'private\s+static\s+\w+\s+instance|getInstance\s*\(\s*\)|@Singleton', content):
                pattern_evidence["singleton"].append((rel_path, "Singleton getInstance pattern"))
            
            # Strategy Pattern
            if re.search(r'interface\s+\w*Strategy|implements\s+\w*Strategy|class\s+\w*Strategy', content):
                pattern_evidence["strategy"].append((rel_path, "Strategy interface or implementation"))
            
            # Builder Pattern
            if re.search(r'@Builder|class\s+\w*Builder|\.build\(\)|Builder\s*{', content):
                pattern_evidence["builder"].append((rel_path, "Builder pattern or Lombok @Builder"))
            
            # Adapter Pattern
            if re.search(r'class\s+\w*Adapter|implements\s+\w*Port|Adapter\s+implements', content):
                pattern_evidence["adapter"].append((rel_path, "Adapter class implementing port"))
            
            # Observer Pattern
            if re.search(r'@EventListener|ApplicationListener|Observer|implements\s+\w*Listener', content):
                pattern_evidence["observer"].append((rel_path, "Observer/Event listener pattern"))
            
            # Decorator Pattern
            if re.search(r'class\s+\w*Decorator|Decorator\s+implements|@Decorator', content):
                pattern_evidence["decorator"].append((rel_path, "Decorator pattern"))
        
        # Also check folder-based patterns
        for pattern, folders in self._pattern_folders.items():
            for folder in folders:
                java_count = len(list(folder.glob("*.java")))
                if java_count > 0:
                    rel_path = str(folder.relative_to(self.repo_path))
                    pattern_evidence[pattern].append((rel_path, f"Folder '{folder.name}' with {java_count} Java files"))
        
        # Create components for detected patterns (minimum 2 occurrences)
        for pattern, evidences in pattern_evidence.items():
            if len(evidences) >= 2:
                self._detected_patterns.add(pattern)
                evidence_ids = []
                for path, reason in evidences[:10]:  # Limit to 10 evidence items
                    eid = self._add_evidence(path, 1, 50, f"{pattern.title()} Pattern: {reason}", prefix="ev_pat")
                    evidence_ids.append(eid)
                
                self._create_component(
                    name=f"{pattern}_pattern",
                    stereotype="design_pattern",
                    file_path=evidences[0][0],
                    evidence_ids=evidence_ids,
                )
    
    def _detect_architecture_styles(self):
        """Detect architecture styles based on structure analysis."""
        
        # Layered Architecture Detection
        layer_count = sum(1 for layer in ["controller", "service", "repository"] 
                        if self._layer_folders.get(layer))
        
        if layer_count >= 2:
            self._detected_styles.add("layered")
            evidence_ids = []
            
            for layer, folders in self._layer_folders.items():
                for folder in folders[:3]:
                    rel_path = str(folder.relative_to(self.repo_path))
                    eid = self._add_evidence(rel_path, 1, 1, 
                                            f"Layered Architecture: {layer} layer folder", 
                                            prefix="ev_arch")
                    evidence_ids.append(eid)
            
            self._create_component(
                name="layered_architecture",
                stereotype="architecture_style",
                file_path=str(list(self._layer_folders.values())[0][0].relative_to(self.repo_path)),
                evidence_ids=evidence_ids[:10],
            )
        
        # Microservices Detection
        if self._is_microservices():
            self._detected_styles.add("microservices")
            evidence_ids = []
            
            for svc in self._service_modules[:5]:
                rel_path = str(svc.relative_to(self.repo_path))
                eid = self._add_evidence(rel_path, 1, 1, 
                                        f"Microservice module: {svc.name}", 
                                        prefix="ev_arch")
                evidence_ids.append(eid)
            
            self._create_component(
                name="microservices_architecture",
                stereotype="architecture_style",
                file_path=str(self._service_modules[0].relative_to(self.repo_path)) if self._service_modules else "",
                evidence_ids=evidence_ids,
            )
        
        # Monolith Detection
        elif self._is_monolith():
            self._detected_styles.add("modular_monolith")
            evidence_ids = []
            
            # Find module folder
            for java_dir in self.repo_path.rglob("src/main/java"):
                module_dir = None
                for subdir in java_dir.rglob("module"):
                    if subdir.is_dir():
                        module_dir = subdir
                        break
                
                if module_dir:
                    for mod in list(module_dir.iterdir())[:5]:
                        if mod.is_dir():
                            rel_path = str(mod.relative_to(self.repo_path))
                            eid = self._add_evidence(rel_path, 1, 1, 
                                                    f"Monolith module: {mod.name}", 
                                                    prefix="ev_arch")
                            evidence_ids.append(eid)
            
            if evidence_ids:
                self._create_component(
                    name="modular_monolith_architecture",
                    stereotype="architecture_style",
                    file_path=evidence_ids[0] if evidence_ids else "",
                    evidence_ids=evidence_ids,
                )
        
        # Hexagonal/Ports-Adapters Detection
        if self._pattern_folders.get("port") and self._pattern_folders.get("adapter"):
            self._detected_styles.add("hexagonal")
            evidence_ids = []
            
            for folder in self._pattern_folders["port"][:2] + self._pattern_folders["adapter"][:2]:
                rel_path = str(folder.relative_to(self.repo_path))
                eid = self._add_evidence(rel_path, 1, 1, 
                                        f"Hexagonal Architecture: {folder.name} folder", 
                                        prefix="ev_arch")
                evidence_ids.append(eid)
            
            self._create_component(
                name="hexagonal_architecture",
                stereotype="architecture_style",
                file_path=str(self._pattern_folders["port"][0].relative_to(self.repo_path)),
                evidence_ids=evidence_ids,
            )
        elif "adapter" in self._detected_patterns:
            # Adapter pattern detected without explicit ports folder
            self._detected_styles.add("ports_adapters")
    
    def _is_microservices(self) -> bool:
        """Check if project appears to be microservices architecture."""
        # Multiple independent service modules with their own pom.xml/build.gradle
        if len(self._service_modules) >= 3:
            return True
        
        # Check for Spring Cloud / service discovery
        for pom in self.repo_path.rglob("pom.xml"):
            try:
                content = pom.read_text(encoding='utf-8', errors='ignore')
                if any(indicator in content for indicator in [
                    "spring-cloud", "eureka", "consul", "netflix", 
                    "spring-boot-starter-web-services", "feign"
                ]):
                    return True
            except Exception:
                continue
        
        return False
    
    def _is_monolith(self) -> bool:
        """Check if project appears to be monolithic architecture."""
        # Single deployable with multiple internal modules
        if self._module_count >= 3:
            return True
        
        # Check for WAR packaging (traditional monolith)
        for pom in self.repo_path.rglob("pom.xml"):
            try:
                content = pom.read_text(encoding='utf-8', errors='ignore')
                if "<packaging>war</packaging>" in content:
                    return True
            except Exception:
                continue
        
        return False
