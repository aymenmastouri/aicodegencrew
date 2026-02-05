"""
Architecture Model Builder - Normalizes and deduplicates collector outputs.

This is NOT a collector. This is the normalization layer that:
1. Deduplicates components from multiple collectors
2. Normalizes IDs to stable canonical format
3. Resolves relationships across collectors
4. Assigns layers to components
5. Merges evidence

Pipeline:
    Index → Collectors (parallel) → Raw Facts → Model Builder → Canonical JSON

Collectors sammeln.
Mapper verbindet.
Builder schreibt das Modell.
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from enum import Enum

# Import from new location (fact_adapter has the legacy types)
from .collectors.fact_adapter import (
    CollectedComponent,
    CollectedInterface,
    CollectedRelation,
    CollectedEvidence,
)
from ...shared.utils.logger import logger


# =============================================================================
# Canonical ID Generation
# =============================================================================

class CanonicalIdGenerator:
    """
    Generates stable, hierarchical IDs for architecture elements.
    
    Format:
        {type}.{container}.{module}.{name}
    
    Examples:
        component.backend.workflow.WorkflowController
        interface.backend.rest.POST_workflow_create
        container.backend
        table.database.DOCUMENT
    """
    
    @staticmethod
    def for_component(container: str, module: str, name: str, stereotype: str) -> str:
        """Generate canonical ID for a component."""
        # Clean and normalize parts
        container = CanonicalIdGenerator._normalize(container) or "unknown"
        module = CanonicalIdGenerator._normalize_module(module) or "core"
        name = CanonicalIdGenerator._normalize(name)
        
        return f"component.{container}.{module}.{name}"
    
    @staticmethod
    def for_interface(container: str, iface_type: str, method: str, path: str) -> str:
        """Generate canonical ID for an interface."""
        container = CanonicalIdGenerator._normalize(container) or "unknown"
        iface_type = CanonicalIdGenerator._normalize(iface_type) or "unknown"
        
        # For REST: method + path
        if iface_type.lower() == "rest" and method and path:
            path_normalized = CanonicalIdGenerator._normalize_path(path)
            return f"interface.{container}.rest.{method}_{path_normalized}"
        
        # For routes
        if iface_type.lower() == "route" and path:
            path_normalized = CanonicalIdGenerator._normalize_path(path)
            return f"interface.{container}.route.{path_normalized}"
        
        # Fallback
        return f"interface.{container}.{iface_type}.{CanonicalIdGenerator._hash(f'{method}{path}')[:8]}"
    
    @staticmethod
    def for_container(name: str, technology: str) -> str:
        """Generate canonical ID for a container."""
        name = CanonicalIdGenerator._normalize(name) or "unknown"
        return f"container.{name}"
    
    @staticmethod
    def for_table(schema: str, name: str) -> str:
        """Generate canonical ID for a database table."""
        schema = CanonicalIdGenerator._normalize(schema) or "default"
        name = CanonicalIdGenerator._normalize(name)
        return f"table.{schema}.{name}"
    
    @staticmethod
    def for_evidence(file_path: str, line_start: int, line_end: int) -> str:
        """Generate canonical ID for evidence."""
        # Use hash of file+lines for stability
        content = f"{file_path}:{line_start}-{line_end}"
        return f"ev.{CanonicalIdGenerator._hash(content)[:12]}"
    
    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize a string to valid ID segment."""
        if not value:
            return ""
        # Convert CamelCase to snake_case, remove special chars
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return re.sub(r'[^a-z0-9_]', '_', s2.lower()).strip('_')
    
    @staticmethod
    def _normalize_module(module: str) -> str:
        """Normalize module path to ID segment."""
        if not module:
            return ""
        # Take last 2-3 significant parts
        parts = module.replace('/', '.').replace('\\', '.').split('.')
        # Filter out common non-meaningful parts
        skip = {'com', 'org', 'de', 'example', 'main', 'java', 'src', 'app'}
        meaningful = [p for p in parts if p.lower() not in skip and p]
        return '_'.join(meaningful[-3:]) if meaningful else ""
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize URL path to ID segment."""
        if not path:
            return "root"
        # Remove leading slash, replace special chars
        normalized = path.lstrip('/').replace('/', '_').replace('{', '').replace('}', '')
        normalized = re.sub(r'[^a-z0-9_]', '_', normalized.lower())
        return normalized[:50] or "root"  # Limit length
    
    @staticmethod
    def _hash(value: str) -> str:
        """Generate short hash for uniqueness."""
        return hashlib.md5(value.encode()).hexdigest()


# =============================================================================
# Layer Classification
# =============================================================================

class ArchitectureLayer(Enum):
    """Architecture layers for component classification."""
    PRESENTATION = "presentation"
    APPLICATION = "application"
    DOMAIN = "domain"
    DATA_ACCESS = "dataaccess"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class LayerClassifier:
    """Classifies components into architecture layers based on stereotypes."""
    
    LAYER_MAPPING = {
        # Presentation layer
        "controller": ArchitectureLayer.PRESENTATION,
        "component": ArchitectureLayer.PRESENTATION,  # Angular/React components
        "module": ArchitectureLayer.PRESENTATION,
        "directive": ArchitectureLayer.PRESENTATION,
        "pipe": ArchitectureLayer.PRESENTATION,
        
        # Application layer
        "service": ArchitectureLayer.APPLICATION,
        "facade": ArchitectureLayer.APPLICATION,
        "usecase": ArchitectureLayer.APPLICATION,
        
        # Domain layer
        "entity": ArchitectureLayer.DOMAIN,
        "aggregate": ArchitectureLayer.DOMAIN,
        "value_object": ArchitectureLayer.DOMAIN,
        "domain_service": ArchitectureLayer.DOMAIN,
        
        # Data access layer
        "repository": ArchitectureLayer.DATA_ACCESS,
        "dao": ArchitectureLayer.DATA_ACCESS,
        "mapper": ArchitectureLayer.DATA_ACCESS,
        "database_migration": ArchitectureLayer.DATA_ACCESS,
        "database_schema": ArchitectureLayer.DATA_ACCESS,
        "sql_script": ArchitectureLayer.DATA_ACCESS,
        
        # Infrastructure layer
        "configuration": ArchitectureLayer.INFRASTRUCTURE,
        "dockerfile": ArchitectureLayer.INFRASTRUCTURE,
        "compose_service": ArchitectureLayer.INFRASTRUCTURE,
        "k8s_deployment": ArchitectureLayer.INFRASTRUCTURE,
        "ci_pipeline": ArchitectureLayer.INFRASTRUCTURE,
        "design_pattern": ArchitectureLayer.INFRASTRUCTURE,
        "architecture_style": ArchitectureLayer.INFRASTRUCTURE,
    }
    
    @classmethod
    def classify(cls, stereotype: str) -> ArchitectureLayer:
        """Classify a component by its stereotype."""
        normalized = stereotype.lower().replace('-', '_').replace(' ', '_')
        return cls.LAYER_MAPPING.get(normalized, ArchitectureLayer.UNKNOWN)


# =============================================================================
# Canonical Model Classes
# =============================================================================

@dataclass
class CanonicalComponent:
    """A deduplicated, normalized component."""
    id: str
    name: str
    container_id: str
    stereotype: str
    layer: str
    module: str
    file_paths: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)  # Original collector IDs
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "container": self.container_id,
            "stereotype": self.stereotype,
            "layer": self.layer,
            "module": self.module,
            "file_paths": self.file_paths,
            "evidence_ids": self.evidence_ids,
            "tags": self.tags,
        }


@dataclass
class CanonicalInterface:
    """A deduplicated, normalized interface."""
    id: str
    container_id: str
    type: str
    path: Optional[str]
    method: Optional[str]
    implemented_by: str  # Canonical component ID
    evidence_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "container": self.container_id,
            "type": self.type,
            "path": self.path,
            "method": self.method,
            "implemented_by": self.implemented_by,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class CanonicalRelation:
    """A normalized relationship between components."""
    from_id: str  # Canonical component ID
    to_id: str    # Canonical component ID
    type: str
    evidence_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "type": self.type,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class CanonicalContainer:
    """A normalized container."""
    id: str
    name: str
    type: str
    technology: str
    category: str
    root_path: str
    evidence_ids: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "technology": self.technology,
            "category": self.category,
            "root_path": self.root_path,
            "evidence_ids": self.evidence_ids,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


# =============================================================================
# Architecture Model Builder
# =============================================================================

class ArchitectureModelBuilder:
    """
    Builds a canonical architecture model from raw collector outputs.
    
    Responsibilities:
    1. Deduplication - merge same components from different collectors
    2. ID Normalization - stable, hierarchical IDs
    3. Relationship Resolution - connect hints to real relations
    4. Layer Assignment - classify by stereotype
    5. Evidence Merging - consolidate evidence references
    """
    
    def __init__(self, system_name: str):
        self.system_name = system_name
        
        # Raw inputs (from collectors)
        self._raw_containers: List[Dict] = []
        self._raw_components: List[CollectedComponent] = []
        self._raw_interfaces: List[CollectedInterface] = []
        self._raw_relations: List[CollectedRelation] = []
        self._raw_evidence: Dict[str, CollectedEvidence] = {}
        
        # Canonical outputs
        self.containers: Dict[str, CanonicalContainer] = {}
        self.components: Dict[str, CanonicalComponent] = {}
        self.interfaces: Dict[str, CanonicalInterface] = {}
        self.relations: List[CanonicalRelation] = []
        self.evidence: Dict[str, Dict] = {}
        
        # Mapping tables
        self._old_to_new_component_id: Dict[str, str] = {}
        self._old_to_new_evidence_id: Dict[str, str] = {}
        self._name_to_component_id: Dict[str, str] = {}  # For deduplication
    
    def add_containers(self, containers: List[Dict], evidence: Dict[str, CollectedEvidence]):
        """Add raw container data from ContainerDetector."""
        self._raw_containers.extend(containers)
        self._raw_evidence.update(evidence)
    
    def add_collector_output(
        self,
        components: List[CollectedComponent],
        interfaces: List[CollectedInterface],
        relations: List[CollectedRelation],
        evidence: Dict[str, CollectedEvidence],
    ):
        """Add raw output from a collector."""
        self._raw_components.extend(components)
        self._raw_interfaces.extend(interfaces)
        self._raw_relations.extend(relations)
        self._raw_evidence.update(evidence)
    
    def build(self) -> 'ArchitectureModel':
        """
        Build the canonical architecture model.
        
        Order matters:
        1. Evidence (needed for all other elements)
        2. Containers (needed for component IDs)
        3. Components (main deduplication)
        4. Interfaces (reference components)
        5. Relations (connect components)
        """
        logger.info("[ModelBuilder] Building canonical architecture model...")
        logger.info(f"[ModelBuilder] Raw inputs: {len(self._raw_containers)} containers, "
                   f"{len(self._raw_components)} components, "
                   f"{len(self._raw_interfaces)} interfaces, "
                   f"{len(self._raw_relations)} relations, "
                   f"{len(self._raw_evidence)} evidence items")
        
        # Step 1: Normalize evidence
        self._normalize_evidence()
        logger.info(f"[ModelBuilder] Step 1: Normalized {len(self.evidence)} evidence items")
        
        # Step 2: Normalize containers
        self._normalize_containers()
        logger.info(f"[ModelBuilder] Step 2: Normalized {len(self.containers)} containers")
        
        # Step 3: Deduplicate and normalize components
        self._normalize_components()
        logger.info(f"[ModelBuilder] Step 3: Normalized {len(self.components)} components "
                   f"(deduped from {len(self._raw_components)})")
        
        # Step 4: Normalize interfaces
        self._normalize_interfaces()
        logger.info(f"[ModelBuilder] Step 4: Normalized {len(self.interfaces)} interfaces")
        
        # Step 5: Resolve relations
        self._resolve_relations()
        logger.info(f"[ModelBuilder] Step 5: Resolved {len(self.relations)} relations")
        
        # Build the model
        model = ArchitectureModel(
            system_name=self.system_name,
            containers=self.containers,
            components=self.components,
            interfaces=self.interfaces,
            relations=self.relations,
            evidence=self.evidence,
        )
        
        logger.info("[ModelBuilder] Canonical model built successfully")
        return model
    
    def _normalize_evidence(self):
        """Normalize all evidence with stable IDs."""
        for old_id, ev in self._raw_evidence.items():
            # Parse line range - support both old 'lines' format and new line_start/line_end
            if hasattr(ev, 'line_start') and hasattr(ev, 'line_end'):
                line_start = ev.line_start if ev.line_start else 1
                line_end = ev.line_end if ev.line_end else line_start
            elif hasattr(ev, 'lines') and ev.lines:
                lines = ev.lines.split('-')
                line_start = int(lines[0]) if lines[0].isdigit() else 1
                line_end = int(lines[-1]) if lines[-1].isdigit() else line_start
            else:
                line_start = 1
                line_end = 1
            
            # Generate canonical ID
            new_id = CanonicalIdGenerator.for_evidence(ev.path, line_start, line_end)
            
            # Store mapping
            self._old_to_new_evidence_id[old_id] = new_id
            
            # Store normalized evidence
            self.evidence[new_id] = {
                "id": new_id,
                "path": ev.path,
                "lines": f"{line_start}-{line_end}",
                "reason": ev.reason,
                "chunk_id": ev.chunk_id,
            }
    
    def _normalize_containers(self):
        """Normalize containers with stable IDs."""
        for raw in self._raw_containers:
            canonical_id = CanonicalIdGenerator.for_container(
                raw.get("name", raw.get("id", "unknown")),
                raw.get("technology", "unknown")
            )
            
            # Map old evidence IDs to new
            evidence_ids = [
                self._old_to_new_evidence_id.get(eid, eid)
                for eid in raw.get("evidence", [])
            ]
            
            self.containers[canonical_id] = CanonicalContainer(
                id=canonical_id,
                name=raw.get("name", raw.get("id", "unknown")),
                type=raw.get("type", "application"),
                technology=raw.get("technology", "unknown"),
                category=raw.get("category", "unknown"),
                root_path=raw.get("root_path", "."),
                evidence_ids=evidence_ids,
                metadata={
                    k: v for k, v in raw.items()
                    if k not in ("id", "name", "type", "technology", "category", "root_path", "evidence")
                }
            )
    
    def _normalize_components(self):
        """Deduplicate and normalize components."""
        # Group by deduplication key (name + container)
        groups: Dict[str, List[CollectedComponent]] = {}
        
        for comp in self._raw_components:
            # Create deduplication key
            dedup_key = f"{comp.container}:{comp.name}"
            
            if dedup_key not in groups:
                groups[dedup_key] = []
            groups[dedup_key].append(comp)
        
        # Merge each group into one canonical component
        for dedup_key, group in groups.items():
            # Take first as base
            base = group[0]
            
            # Find canonical container ID
            container_canonical_id = None
            for cid in self.containers:
                if base.container in cid or cid.endswith(f".{base.container}"):
                    container_canonical_id = cid
                    break
            if not container_canonical_id:
                container_canonical_id = f"container.{CanonicalIdGenerator._normalize(base.container)}"
            
            # Generate canonical ID
            canonical_id = CanonicalIdGenerator.for_component(
                base.container,
                base.module or "",
                base.name,
                base.stereotype
            )
            
            # Classify layer
            layer = LayerClassifier.classify(base.stereotype)
            
            # Merge all file paths
            file_paths = list(set(c.file_path for c in group if c.file_path))
            
            # Merge all evidence IDs (map to new IDs)
            evidence_ids = []
            for comp in group:
                for eid in comp.evidence_ids:
                    new_eid = self._old_to_new_evidence_id.get(eid, eid)
                    if new_eid not in evidence_ids:
                        evidence_ids.append(new_eid)
            
            # Merge all tags (handle missing tags attribute)
            tags = list(set(tag for comp in group for tag in getattr(comp, 'tags', [])))
            
            # Store old IDs for relation resolution
            source_ids = [c.id for c in group]
            
            # Create canonical component
            self.components[canonical_id] = CanonicalComponent(
                id=canonical_id,
                name=base.name,
                container_id=container_canonical_id,
                stereotype=base.stereotype,
                layer=layer.value,
                module=base.module or "",
                file_paths=file_paths,
                evidence_ids=evidence_ids,
                tags=tags,
                source_ids=source_ids,
            )
            
            # Update mapping tables
            for comp in group:
                self._old_to_new_component_id[comp.id] = canonical_id
            self._name_to_component_id[base.name] = canonical_id
    
    def _normalize_interfaces(self):
        """Normalize interfaces with stable IDs."""
        seen_ids: Set[str] = set()
        
        for iface in self._raw_interfaces:
            # Get interface type (support both 'type' and 'interface_type' attributes)
            iface_type = getattr(iface, 'type', None) or getattr(iface, 'interface_type', 'unknown')
            iface_path = getattr(iface, 'path', None) or getattr(iface, 'endpoint', '')
            
            # Generate canonical ID
            canonical_id = CanonicalIdGenerator.for_interface(
                iface.container,
                iface_type,
                iface.method,
                iface_path
            )
            
            # Handle duplicates
            if canonical_id in seen_ids:
                continue
            seen_ids.add(canonical_id)
            
            # Find canonical container ID
            container_canonical_id = None
            for cid in self.containers:
                if iface.container in cid:
                    container_canonical_id = cid
                    break
            if not container_canonical_id:
                container_canonical_id = f"container.{CanonicalIdGenerator._normalize(iface.container)}"
            
            # Resolve implemented_by to canonical component ID
            implemented_by_hint = getattr(iface, 'implemented_by', '') or ''
            implemented_by = self._resolve_component_ref(implemented_by_hint) if implemented_by_hint else None
            
            # Map evidence IDs
            evidence_ids = [
                self._old_to_new_evidence_id.get(eid, eid)
                for eid in iface.evidence_ids
            ]
            
            self.interfaces[canonical_id] = CanonicalInterface(
                id=canonical_id,
                container_id=container_canonical_id,
                type=iface_type,
                path=iface_path,
                method=iface.method,
                implemented_by=implemented_by,
                evidence_ids=evidence_ids,
            )
    
    def _resolve_relations(self):
        """Resolve relation hints into canonical relations."""
        seen: Set[Tuple[str, str, str]] = set()
        
        for rel in self._raw_relations:
            # Get relation type (support both 'type' and 'relation_type' attributes)
            rel_type = getattr(rel, 'type', None) or getattr(rel, 'relation_type', 'uses')
            
            # Resolve from/to to canonical IDs
            from_id = self._resolve_component_ref(rel.from_id)
            to_id = self._resolve_component_ref(rel.to_id)
            
            # Skip if we couldn't resolve
            if not from_id or not to_id:
                continue
            
            # Skip self-references
            if from_id == to_id:
                continue
            
            # Skip duplicates
            key = (from_id, to_id, rel_type)
            if key in seen:
                continue
            seen.add(key)
            
            # Map evidence IDs
            evidence_ids = [
                self._old_to_new_evidence_id.get(eid, eid)
                for eid in rel.evidence_ids
            ]
            
            self.relations.append(CanonicalRelation(
                from_id=from_id,
                to_id=to_id,
                type=rel_type,
                evidence_ids=evidence_ids,
            ))
    
    def _resolve_component_ref(self, ref: str) -> Optional[str]:
        """Resolve a component reference to canonical ID."""
        # Direct mapping from old ID
        if ref in self._old_to_new_component_id:
            return self._old_to_new_component_id[ref]
        
        # By name
        if ref in self._name_to_component_id:
            return self._name_to_component_id[ref]
        
        # Already canonical?
        if ref in self.components:
            return ref
        
        return None


# =============================================================================
# Architecture Model (Result)
# =============================================================================

class ArchitectureModel:
    """
    The canonical architecture model.
    
    This is the single source of truth after normalization.
    All dimension writers read from this model.
    """
    
    def __init__(
        self,
        system_name: str,
        containers: Dict[str, CanonicalContainer],
        components: Dict[str, CanonicalComponent],
        interfaces: Dict[str, CanonicalInterface],
        relations: List[CanonicalRelation],
        evidence: Dict[str, Dict],
        dependencies: List[Dict] = None,
        workflows: List[Dict] = None,
    ):
        self.system_name = system_name
        self.containers = containers
        self.components = components
        self.interfaces = interfaces
        self.relations = relations
        self.evidence = evidence
        self.dependencies = dependencies or []
        self.workflows = workflows or []
    
    def get_components_by_layer(self, layer: str) -> List[CanonicalComponent]:
        """Get all components in a specific layer."""
        return [c for c in self.components.values() if c.layer == layer]
    
    def get_components_by_stereotype(self, stereotype: str) -> List[CanonicalComponent]:
        """Get all components with a specific stereotype."""
        return [c for c in self.components.values() if c.stereotype == stereotype]
    
    def get_components_for_container(self, container_id: str) -> List[CanonicalComponent]:
        """Get all components belonging to a container."""
        return [c for c in self.components.values() if c.container_id == container_id]
    
    def get_relations_from(self, component_id: str) -> List[CanonicalRelation]:
        """Get all relations originating from a component."""
        return [r for r in self.relations if r.from_id == component_id]
    
    def get_relations_to(self, component_id: str) -> List[CanonicalRelation]:
        """Get all relations pointing to a component."""
        return [r for r in self.relations if r.to_id == component_id]
    
    def get_statistics(self) -> Dict:
        """Get model statistics."""
        layer_counts = {}
        for comp in self.components.values():
            layer_counts[comp.layer] = layer_counts.get(comp.layer, 0) + 1
        
        stereotype_counts = {}
        for comp in self.components.values():
            stereotype_counts[comp.stereotype] = stereotype_counts.get(comp.stereotype, 0) + 1
        
        return {
            "system_name": self.system_name,
            "containers": len(self.containers),
            "components": len(self.components),
            "interfaces": len(self.interfaces),
            "relations": len(self.relations),
            "evidence": len(self.evidence),
            "dependencies": len(self.dependencies),
            "workflows": len(self.workflows),
            "by_layer": layer_counts,
            "by_stereotype": stereotype_counts,
        }
