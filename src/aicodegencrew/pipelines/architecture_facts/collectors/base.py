"""
Base classes for dimension collectors.

Design Principles:
1. Each collector extracts ONE dimension
2. No collector thinks or summarizes
3. All deliver structured facts with evidence
4. IDs are assigned by the Model Builder, not collectors
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum

from ....shared.utils.logger import logger


# =============================================================================
# Fact Types
# =============================================================================

class FactType(Enum):
    """Types of facts that can be collected."""
    SYSTEM = "system"
    CONTAINER = "container"
    COMPONENT = "component"
    INTERFACE = "interface"
    RELATION = "relation"
    DATA_MODEL = "data_model"
    RUNTIME = "runtime"
    INFRASTRUCTURE = "infrastructure"
    DEPENDENCY = "dependency"
    WORKFLOW = "workflow"
    EVIDENCE = "evidence"


@dataclass
class RawEvidence:
    """
    Evidence linking a fact back to source code.
    
    This is CRITICAL - every fact must have evidence.
    """
    path: str  # Relative file path
    line_start: int
    line_end: int
    reason: str  # Why this is evidence
    snippet: Optional[str] = None  # Optional code snippet
    
    def to_dict(self) -> Dict:
        result = {
            "path": self.path,
            "lines": f"{self.line_start}-{self.line_end}",
            "reason": self.reason,
        }
        if self.snippet:
            result["snippet"] = self.snippet
        return result


@dataclass
class RawFact:
    """
    Base class for all raw facts.
    
    NO ID - the Model Builder assigns canonical IDs.
    """
    name: str
    evidence: List[RawEvidence] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_evidence(self, path: str, line_start: int, line_end: int, 
                     reason: str, snippet: Optional[str] = None):
        """Add evidence for this fact."""
        self.evidence.append(RawEvidence(
            path=path,
            line_start=line_start,
            line_end=line_end,
            reason=reason,
            snippet=snippet,
        ))


@dataclass
class RawComponent(RawFact):
    """A component fact (controller, service, repository, etc.)."""
    stereotype: str = ""  # controller, service, repository, entity, etc.
    container_hint: str = ""  # Which container this likely belongs to
    module: str = ""  # Package/module path
    file_path: str = ""  # Source file
    layer_hint: Optional[str] = None  # presentation, application, domain, data_access


@dataclass
class RawInterface(RawFact):
    """An interface fact (REST endpoint, route, listener, etc.)."""
    type: str = ""  # rest_endpoint, route, scheduler, listener, graphql
    path: Optional[str] = None  # URL path or route
    method: Optional[str] = None  # HTTP method
    implemented_by_hint: str = ""  # Component name that implements this
    container_hint: str = ""


@dataclass
class RelationHint:
    """
    A hint about a relationship between components.
    
    Uses NAMES, not IDs. Model Builder resolves to actual components.
    """
    from_name: str
    to_name: str
    type: str = "uses"  # uses, calls, extends, implements, produces, consumes
    evidence: List[RawEvidence] = field(default_factory=list)
    confidence: float = 1.0
    # Disambiguation hints
    from_file_hint: Optional[str] = None
    to_file_hint: Optional[str] = None
    from_stereotype_hint: Optional[str] = None
    to_stereotype_hint: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            "from": self.from_name,
            "to": self.to_name,
            "type": self.type,
            "confidence": self.confidence,
        }
        if self.from_file_hint:
            result["from_file"] = self.from_file_hint
        if self.to_file_hint:
            result["to_file"] = self.to_file_hint
        if self.from_stereotype_hint:
            result["from_stereotype"] = self.from_stereotype_hint
        if self.to_stereotype_hint:
            result["to_stereotype"] = self.to_stereotype_hint
        if self.evidence:
            result["evidence"] = [e.to_dict() for e in self.evidence]
        return result


@dataclass  
class RawContainer(RawFact):
    """A container fact (deployable unit)."""
    type: str = ""  # backend, frontend, database, batch, external
    technology: str = ""  # Spring Boot, Angular, PostgreSQL, etc.
    root_path: str = ""  # Root directory
    category: str = ""  # application, datastore, infrastructure


@dataclass
class RawEntity(RawFact):
    """A data model entity (table, JPA entity, etc.)."""
    type: str = ""  # table, entity, view
    schema: Optional[str] = None
    columns: List[Dict] = field(default_factory=list)
    constraints: List[Dict] = field(default_factory=list)


@dataclass
class RawRuntimeFact(RawFact):
    """A runtime behavior fact (scheduler, async, workflow)."""
    type: str = ""  # scheduler, async, workflow_trigger, background_job
    schedule: Optional[str] = None  # Cron expression
    trigger: Optional[str] = None


@dataclass
class RawInfraFact(RawFact):
    """An infrastructure fact (Docker, K8s, CI)."""
    type: str = ""  # dockerfile, k8s_deployment, ci_pipeline, config_file
    category: str = ""  # container, orchestration, ci_cd, configuration


# =============================================================================
# Collector Output
# =============================================================================

@dataclass
class CollectorOutput:
    """Output from a dimension collector."""
    dimension: str  # Which JSON file this feeds
    facts: List[RawFact] = field(default_factory=list)
    relations: List[RelationHint] = field(default_factory=list)
    
    def add_fact(self, fact: RawFact):
        self.facts.append(fact)
    
    def add_relation(self, relation: RelationHint):
        self.relations.append(relation)
    
    @property
    def fact_count(self) -> int:
        return len(self.facts)
    
    @property
    def relation_count(self) -> int:
        return len(self.relations)


# =============================================================================
# Base Collector
# =============================================================================

class DimensionCollector(ABC):
    """
    Base class for all dimension collectors.
    
    Each collector:
    1. Scans specific file types
    2. Extracts facts for ONE dimension
    3. Creates evidence links
    4. Returns structured output (no IDs)
    """
    
    # Override in subclass
    DIMENSION: str = "unknown"
    
    # Directories to skip
    SKIP_DIRS: Set[str] = {
        'node_modules', '.git', '__pycache__', 'dist', 'build', 
        'target', '.venv', 'venv', '.idea', '.gradle', 'out'
    }
    
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.output = CollectorOutput(dimension=self.DIMENSION)
        self._file_cache: Dict[Path, List[str]] = {}
    
    @abstractmethod
    def collect(self) -> CollectorOutput:
        """
        Collect facts for this dimension.
        
        Returns:
            CollectorOutput with facts and relation hints
        """
        pass
    
    # =========================================================================
    # File Utilities
    # =========================================================================
    
    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        return bool(set(path.parts) & self.SKIP_DIRS)
    
    def _find_files(self, pattern: str, root: Optional[Path] = None) -> List[Path]:
        """Find files matching glob pattern."""
        search_root = root or self.repo_path
        files = []
        for path in search_root.rglob(pattern):
            if path.is_file() and not self._should_skip(path):
                files.append(path)
        return files
    
    def _read_file(self, path: Path) -> List[str]:
        """Read file lines (cached)."""
        if path not in self._file_cache:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    self._file_cache[path] = f.readlines()
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")
                self._file_cache[path] = []
        return self._file_cache[path]
    
    def _read_file_content(self, path: Path) -> str:
        """Read file as single string."""
        return ''.join(self._read_file(path))
    
    def _relative_path(self, path: Path) -> str:
        """Get path relative to repo root."""
        try:
            return str(path.relative_to(self.repo_path))
        except ValueError:
            return str(path)
    
    def _find_line_number(self, lines: List[str], search: str) -> int:
        """Find line number containing search string."""
        for i, line in enumerate(lines, 1):
            if search in line:
                return i
        return 1
    
    def _extract_snippet(self, lines: List[str], start: int, end: int, 
                         max_lines: int = 10) -> str:
        """Extract code snippet."""
        actual_end = min(end, start + max_lines)
        snippet_lines = lines[start-1:actual_end]
        return ''.join(snippet_lines).strip()
    
    # =========================================================================
    # Evidence Helpers
    # =========================================================================
    
    def _create_evidence(self, path: Path, line_start: int, line_end: int,
                         reason: str, include_snippet: bool = False) -> RawEvidence:
        """Create an evidence record."""
        rel_path = self._relative_path(path)
        snippet = None
        if include_snippet:
            lines = self._read_file(path)
            snippet = self._extract_snippet(lines, line_start, line_end)
        
        return RawEvidence(
            path=rel_path,
            line_start=line_start,
            line_end=line_end,
            reason=reason,
            snippet=snippet,
        )
    
    # =========================================================================
    # Name/Module Utilities
    # =========================================================================
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a name (CamelCase to snake_case style comparison)."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _derive_module(self, file_path: str) -> str:
        """Derive module/package from file path."""
        if not file_path:
            return ""
        parts = file_path.replace("\\", "/").split("/")
        
        # Find start after src/main/java or src/app
        start_idx = 0
        for i, p in enumerate(parts):
            if p in ("java", "kotlin", "app") and i > 0:
                start_idx = i + 1
                break
        
        # Get directory parts (exclude file)
        dir_parts = parts[start_idx:-1] if start_idx < len(parts) - 1 else parts[:-1]
        
        # Filter non-module parts
        skip = {"src", "main", "test", "resources", "lib", "shared"}
        filtered = [p for p in dir_parts if p and p.lower() not in skip]
        
        return ".".join(filtered) if filtered else ""
    
    # =========================================================================
    # Logging
    # =========================================================================
    
    def _log_start(self):
        """Log collector start."""
        logger.info(f"[{self.__class__.__name__}] Starting collection...")
    
    def _log_end(self):
        """Log collector results."""
        logger.info(f"[{self.__class__.__name__}] Collected: "
                   f"{self.output.fact_count} facts, "
                   f"{self.output.relation_count} relations")
