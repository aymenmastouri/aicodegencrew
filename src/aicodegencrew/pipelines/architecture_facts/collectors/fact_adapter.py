"""
Fact Adapter - Converts new RawFact types to legacy Collected* types.

This adapter bridges the gap between:
- NEW: RawFact, RawComponent, RawInterface, etc. (from new collectors)
- OLD: CollectedComponent, CollectedInterface, etc. (used by model_builder)

This allows incremental migration without breaking existing code.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from .base import (
    RawFact,
    RawComponent,
    RawInterface,
    RawContainer,
    RawEntity,
    RawRuntimeFact,
    RawInfraFact,
    RelationHint,
    RawEvidence,
)
from ....shared.utils.logger import logger


# =============================================================================
# Legacy Types (for backward compatibility with model_builder)
# =============================================================================

@dataclass
class CollectedEvidence:
    """Evidence that a component/interface was found in the code."""
    path: str
    line_start: int
    line_end: int
    reason: str
    chunk_id: Optional[str] = None

@dataclass 
class CollectedComponent:
    """A component collected from source code."""
    id: str
    container: str
    name: str
    stereotype: str  # controller, service, repository, entity, etc.
    file_path: str
    evidence_ids: List[str] = field(default_factory=list)
    module: str = ""  # Package/module path
    tags: List[str] = field(default_factory=list)  # Optional tags
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CollectedInterface:
    """An interface (API endpoint, route, etc.) collected from source code."""
    id: str
    container: str
    name: str
    interface_type: str  # rest_endpoint, route, listener, etc.
    endpoint: str
    method: str = "GET"
    implemented_by: str = ""  # Component that implements this interface
    evidence_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CollectedRelation:
    """A relation between two components."""
    from_id: str
    to_id: str
    relation_type: str  # uses, implements, inherits, etc.
    evidence_ids: List[str] = field(default_factory=list)


class FactAdapter:
    """
    Converts new collector outputs to legacy format.
    
    Usage:
        adapter = FactAdapter()
        
        # Convert components
        for raw in raw_components:
            collected = adapter.to_collected_component(raw, container_id)
        
        # Convert interfaces
        for raw in raw_interfaces:
            collected = adapter.to_collected_interface(raw, container_id)
    """
    
    def __init__(self, repo_path: Path = None):
        self.repo_path = repo_path
        self._component_counter = 0
        self._interface_counter = 0
        self._evidence_counter = 0
    
    def to_collected_component(
        self,
        raw: RawFact,
        container_id: str = "unknown",
    ) -> CollectedComponent:
        """
        Convert a RawFact (typically RawComponent) to CollectedComponent.
        
        Args:
            raw: The raw fact from new collector
            container_id: Container this component belongs to
        """
        self._component_counter += 1
        
        # Determine stereotype
        stereotype = "component"
        if hasattr(raw, 'component_type'):
            stereotype = raw.component_type
        elif hasattr(raw, 'fact_type'):
            stereotype = raw.fact_type
        elif hasattr(raw, 'stereotype'):
            stereotype = raw.stereotype
        
        # Get file path
        file_path = ""
        if hasattr(raw, 'file_path') and raw.file_path:
            file_path = str(raw.file_path)
        
        # Get module
        module = ""
        if hasattr(raw, 'module') and raw.module:
            module = raw.module
        elif hasattr(raw, 'package') and raw.package:
            module = raw.package
        elif file_path:
            # Derive from file path
            module = self._extract_module_from_path(file_path)
        
        # Get evidence IDs
        evidence_ids = []
        if hasattr(raw, 'evidence') and raw.evidence:
            evidence_ids = [self._make_evidence_id(raw.evidence)]
        
        # Get tags and add to metadata
        tags = []
        if hasattr(raw, 'tags') and raw.tags:
            tags = raw.tags
        if hasattr(raw, 'stereotype'):
            tags.append(raw.stereotype)
        
        return CollectedComponent(
            id=f"comp_{self._component_counter}_{raw.name}",
            name=raw.name,
            container=container_id,
            stereotype=stereotype,
            file_path=file_path,
            module=module,
            evidence_ids=evidence_ids,
            metadata={"tags": tags} if tags else {},
        )
    
    def to_collected_interface(
        self,
        raw: RawFact,
        container_id: str = "unknown",
    ) -> CollectedInterface:
        """
        Convert a RawFact (typically RawInterface) to CollectedInterface.
        """
        self._interface_counter += 1
        
        # Determine type
        iface_type = "rest"
        if hasattr(raw, 'interface_type'):
            iface_type = raw.interface_type
        elif hasattr(raw, 'fact_type'):
            iface_type = raw.fact_type
        elif hasattr(raw, 'type'):
            iface_type = raw.type
        
        # Get path
        path = ""
        if hasattr(raw, 'path') and raw.path:
            path = raw.path
        elif hasattr(raw, 'endpoint') and raw.endpoint:
            path = raw.endpoint
        
        # Get method
        method = ""
        if hasattr(raw, 'method') and raw.method:
            method = raw.method
        elif hasattr(raw, 'http_method') and raw.http_method:
            method = raw.http_method
        
        # Get implemented_by
        implemented_by = ""
        if hasattr(raw, 'implemented_by') and raw.implemented_by:
            implemented_by = raw.implemented_by
        elif hasattr(raw, 'component') and raw.component:
            implemented_by = raw.component
        elif hasattr(raw, 'controller') and raw.controller:
            implemented_by = raw.controller
        
        # Get evidence IDs
        evidence_ids = []
        if hasattr(raw, 'evidence') and raw.evidence:
            evidence_ids = [self._make_evidence_id(raw.evidence)]
        
        return CollectedInterface(
            id=f"iface_{self._interface_counter}_{raw.name}",
            name=raw.name,
            container=container_id,
            interface_type=iface_type,
            endpoint=path,
            method=method or "GET",
            evidence_ids=evidence_ids,
            metadata={"implemented_by": implemented_by} if implemented_by else {},
        )
    
    def to_collected_relation(
        self,
        hint: RelationHint,
    ) -> CollectedRelation:
        """
        Convert a RelationHint to CollectedRelation.
        """
        # Get from_id (could be name or ID)
        from_id = hint.from_name
        to_id = hint.to_name
        
        # Evidence
        evidence_ids = []
        if hasattr(hint, 'evidence') and hint.evidence:
            evidence_ids = [self._make_evidence_id(hint.evidence)]
        
        return CollectedRelation(
            from_id=from_id,
            to_id=to_id,
            type=hint.relation_type,
            evidence_ids=evidence_ids,
        )
    
    def to_collected_evidence(
        self,
        raw: RawEvidence,
    ) -> CollectedEvidence:
        """
        Convert a RawEvidence to CollectedEvidence.
        """
        return CollectedEvidence(
            path=str(raw.file_path),
            line_start=raw.line_start,
            line_end=raw.line_end,
            reason=raw.reason,
            chunk_id=getattr(raw, 'chunk_id', None),
        )
    
    def raw_evidence_to_dict(self, raw: RawEvidence) -> Dict:
        """Convert RawEvidence to dictionary for evidence map."""
        ev_id = self._make_evidence_id(raw)
        return {
            "id": ev_id,
            "path": str(raw.file_path),
            "lines": f"{raw.line_start}-{raw.line_end}",
            "reason": raw.reason,
            "chunk_id": getattr(raw, 'chunk_id', None),
        }
    
    def _make_evidence_id(self, evidence: RawEvidence) -> str:
        """Create an evidence ID from RawEvidence."""
        self._evidence_counter += 1
        if hasattr(evidence, 'file_path'):
            path_part = Path(evidence.file_path).stem[:20]
            return f"ev_{self._evidence_counter}_{path_part}"
        return f"ev_{self._evidence_counter}"
    
    def _extract_module_from_path(self, file_path: str) -> str:
        """Extract module name from file path."""
        path = Path(file_path)
        
        # For Java: com/example/module/Class.java -> com.example.module
        if '.java' in file_path:
            parts = path.parent.parts
            # Find 'src/main/java' or similar and take everything after
            try:
                if 'java' in parts:
                    idx = parts.index('java')
                    return '.'.join(parts[idx+1:])
            except ValueError:
                pass
            return '.'.join(parts[-3:]) if len(parts) >= 3 else '.'.join(parts)
        
        # For TypeScript: src/app/module/component.ts -> app.module
        if '.ts' in file_path:
            parts = path.parent.parts
            # Find 'src' and take everything after
            try:
                if 'src' in parts:
                    idx = parts.index('src')
                    return '.'.join(parts[idx+1:])
            except ValueError:
                pass
            return '.'.join(parts[-2:]) if len(parts) >= 2 else path.parent.name
        
        return path.parent.name


class DimensionResultsAdapter:
    """
    Converts DimensionResults (from new orchestrator) to legacy format.
    
    This allows the existing ArchitectureModelBuilder to work with
    the new collector architecture.
    """
    
    def __init__(self, repo_path: Path = None):
        self.repo_path = repo_path
        self.fact_adapter = FactAdapter(repo_path)
    
    def convert(self, results) -> Dict[str, Any]:
        """
        Convert DimensionResults to format expected by ArchitectureModelBuilder.
        
        Args:
            results: DimensionResults from CollectorOrchestrator
        
        Returns:
            Dictionary with:
            - containers: List[Dict]
            - components: List[CollectedComponent]
            - interfaces: List[CollectedInterface]
            - relations: List[CollectedRelation]
            - evidence: Dict[str, CollectedEvidence]
        """
        # Convert containers
        containers = []
        for c in results.containers:
            containers.append({
                "id": c.get("name", "unknown"),
                "name": c.get("name", "unknown"),
                "technology": c.get("technology", "unknown"),
                "category": c.get("category", "unknown"),
                "root_path": c.get("root_path", "."),
                "type": c.get("category", "application"),
                "evidence": [],
            })
        
        # Convert components
        components = []
        for raw in results.components:
            # Determine container
            container_id = self._find_container_for_fact(raw, results.containers)
            comp = self.fact_adapter.to_collected_component(raw, container_id)
            components.append(comp)
        
        # Also convert entities to components
        for raw in results.entities:
            container_id = self._find_container_for_fact(raw, results.containers)
            comp = self.fact_adapter.to_collected_component(raw, container_id)
            comp.stereotype = "entity"
            components.append(comp)
        
        # Also convert runtime facts to components
        for raw in results.runtime:
            container_id = self._find_container_for_fact(raw, results.containers)
            comp = self.fact_adapter.to_collected_component(raw, container_id)
            comp.stereotype = getattr(raw, 'fact_type', 'scheduler')
            components.append(comp)
        
        # Also convert infrastructure facts to components
        for raw in results.infrastructure:
            comp = self.fact_adapter.to_collected_component(raw, "infrastructure")
            comp.stereotype = getattr(raw, 'fact_type', 'configuration')
            components.append(comp)
        
        # Convert interfaces
        interfaces = []
        for raw in results.interfaces:
            container_id = self._find_container_for_fact(raw, results.containers)
            iface = self.fact_adapter.to_collected_interface(raw, container_id)
            interfaces.append(iface)
        
        # Convert relations
        relations = []
        for hint in results.relation_hints:
            if isinstance(hint, dict):
                # Already a dict
                rel = CollectedRelation(
                    from_id=hint.get("from_name", hint.get("from", "")),
                    to_id=hint.get("to_name", hint.get("to", "")),
                    relation_type=hint.get("relation_type", hint.get("type", "uses")),
                    evidence_ids=hint.get("evidence_ids", []),
                )
            else:
                # RelationHint object
                rel = self.fact_adapter.to_collected_relation(hint)
            relations.append(rel)
        
        # Convert evidence
        evidence = {}
        for key, raw_ev in results.evidence.items():
            if isinstance(raw_ev, dict):
                # Already dict format - parse lines string if present
                lines_str = raw_ev.get("lines", "1-1")
                if "-" in str(lines_str):
                    parts = str(lines_str).split("-")
                    line_start = int(parts[0])
                    line_end = int(parts[1]) if len(parts) > 1 else line_start
                else:
                    line_start = int(lines_str) if lines_str else 1
                    line_end = line_start
                ev = CollectedEvidence(
                    path=raw_ev.get("path", raw_ev.get("file_path", "")),
                    line_start=raw_ev.get("line_start", line_start),
                    line_end=raw_ev.get("line_end", line_end),
                    reason=raw_ev.get("reason", ""),
                    chunk_id=raw_ev.get("chunk_id"),
                )
            else:
                ev = self.fact_adapter.to_collected_evidence(raw_ev)
            evidence[key] = ev
        
        return {
            "containers": containers,
            "components": components,
            "interfaces": interfaces,
            "relations": relations,
            "evidence": evidence,
        }
    
    def _find_container_for_fact(self, fact: RawFact, containers: List[Dict]) -> str:
        """Find which container a fact belongs to based on file path or container_hint."""
        # First check if fact has explicit container_hint
        if hasattr(fact, 'container_hint') and fact.container_hint:
            # Return the container_hint value (e.g., "frontend", "backend")
            hint = fact.container_hint.lower()
            for container in containers:
                if container.get("name", "").lower() == hint:
                    return container.get("name")
            # If hint doesn't match any container, still use it
            return fact.container_hint
        
        if not hasattr(fact, 'file_path') or not fact.file_path:
            # Default to first container or unknown
            return containers[0].get("name", "unknown") if containers else "unknown"
        
        file_path = str(fact.file_path)
        
        # Check each container's root_path
        for container in containers:
            root = container.get("root_path", "")
            if root and root in file_path:
                return container.get("name", "unknown")
        
        # Try to detect by technology markers in path
        file_lower = file_path.lower()
        for container in containers:
            tech = container.get("technology", "").lower()
            name = container.get("name", "").lower()
            
            # Spring Boot: .java files in backend
            if tech == "spring boot" and ".java" in file_lower:
                if "backend" in file_lower or name in file_lower:
                    return container.get("name", "backend")
            
            # Angular: .ts files (not spec.ts) in frontend
            if tech == "angular" and ".ts" in file_lower and ".spec.ts" not in file_lower:
                if "frontend" in file_lower or "src/app" in file_lower or name in file_lower:
                    return container.get("name", "frontend")
        
        # Default
        return containers[0].get("name", "unknown") if containers else "unknown"
