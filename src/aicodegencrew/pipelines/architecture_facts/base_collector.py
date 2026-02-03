"""Base class for architecture fact collectors."""

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field

from ...shared.utils.logger import logger


@dataclass
class CollectedEvidence:
    """Evidence collected during scanning."""
    id: str
    path: str
    lines: str
    reason: str
    chunk_id: Optional[str] = None


@dataclass
class CollectedComponent:
    """Component collected during scanning."""
    id: str
    container: str
    name: str
    stereotype: str
    file_path: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0.0-1.0 certainty of detection
    layer: Optional[str] = None  # "presentation", "business", "data", "infrastructure"
    module: Optional[str] = None  # Module/package grouping
    tags: List[str] = field(default_factory=list)  # Flexible metadata


@dataclass
class CollectedInterface:
    """Interface collected during scanning."""
    id: str
    container: str
    type: str
    path: Optional[str]
    method: Optional[str]
    implemented_by: str
    evidence_ids: List[str] = field(default_factory=list)


@dataclass
class CollectedRelation:
    """Relation collected during scanning."""
    from_id: str
    to_id: str
    type: str = "uses"
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0.0-1.0 certainty of relation
    description: Optional[str] = None  # Optional description of the relation


class BaseCollector(ABC):
    """Base class for all architecture fact collectors."""
    
    def __init__(self, repo_path: Path, container_id: str):
        self.repo_path = repo_path
        self.container_id = container_id
        self.evidence: Dict[str, CollectedEvidence] = {}
        self.components: List[CollectedComponent] = []
        self.interfaces: List[CollectedInterface] = []
        self.relations: List[CollectedRelation] = []
        self._evidence_counter = 0
        self._used_component_ids: Set[str] = set()  # Track used IDs to avoid duplicates
    
    def _next_evidence_id(self, prefix: str = "ev") -> str:
        """Generate next evidence ID."""
        self._evidence_counter += 1
        return f"{prefix}_{self._evidence_counter:04d}"
    
    def _add_evidence(self, path: str, line_start: int, line_end: int, reason: str, prefix: str = "ev") -> str:
        """Add evidence and return its ID."""
        ev_id = self._next_evidence_id(prefix)
        rel_path = str(Path(path).relative_to(self.repo_path)) if Path(path).is_absolute() else path
        self.evidence[ev_id] = CollectedEvidence(
            id=ev_id,
            path=rel_path,
            lines=f"{line_start}-{line_end}",
            reason=reason
        )
        return ev_id
    
    def _make_component_id(self, name: str, file_path: Optional[str] = None) -> str:
        """Create a unique component ID from class name.
        
        If the ID already exists and file_path is provided, appends a suffix
        derived from the file path to ensure uniqueness.
        
        NOTE: This method registers the ID. Use _get_component_id_base() for lookups.
        """
        # Convert CamelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        base_id = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Check for duplicates and make unique if needed
        if base_id not in self._used_component_ids:
            self._used_component_ids.add(base_id)
            return base_id
        
        # ID already exists - need to make it unique
        if file_path:
            # Extract a suffix from the file path (e.g., ".xnp" from "file.xnp.ts")
            path_parts = Path(file_path).stem.split('.')
            if len(path_parts) > 1:
                suffix = path_parts[-1]  # e.g., "xnp"
                unique_id = f"{base_id}_{suffix}"
                if unique_id not in self._used_component_ids:
                    self._used_component_ids.add(unique_id)
                    return unique_id
        
        # Fallback: add numeric suffix
        counter = 2
        while f"{base_id}_{counter}" in self._used_component_ids:
            counter += 1
        unique_id = f"{base_id}_{counter}"
        self._used_component_ids.add(unique_id)
        return unique_id
    
    def _get_component_id_base(self, name: str) -> str:
        """Get the base component ID from class name (for lookups, no registration).
        
        Use this when you need to look up an existing component by name,
        not when creating new components.
        """
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _read_file_lines(self, file_path: Path) -> List[str]:
        """Read file and return lines."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.readlines()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []
    
    def _find_files(self, pattern: str, root: Optional[Path] = None) -> List[Path]:
        """Find files matching pattern."""
        search_root = root or self.repo_path
        files = []
        for path in search_root.rglob(pattern):
            if path.is_file():
                files.append(path)
        return files
    
    @abstractmethod
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """
        Collect facts from the repository.
        
        Returns:
            Tuple of (components, interfaces, relations, evidence)
        """
        pass
