"""Data models for the enhanced Discover phase.

Shared by symbol extractor, evidence store, manifest builder, and budget engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


@dataclass
class SymbolRecord:
    """One extracted symbol (class, method, function, endpoint, interface)."""

    symbol: str
    kind: str  # class, method, function, interface, endpoint, decorator
    path: str  # relative file path
    line: int
    end_line: int = 0
    language: str = ""
    refs: list[str] = field(default_factory=list)  # referenced symbols
    module: str = ""  # top-level directory / module name

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceRecord:
    """One chunk with traceability metadata."""

    chunk_id: str
    path: str
    type: str  # code, doc, config
    module: str
    start_line: int
    end_line: int
    hash: str  # content hash
    symbols: list[str] = field(default_factory=list)
    language: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModuleStats:
    """Stats for a single top-level module/directory."""

    name: str
    file_count: int = 0
    extensions: dict[str, int] = field(default_factory=dict)


@dataclass
class RepoManifest:
    """Repository-level manifest with stats, frameworks, and noise folders."""

    repo_root: str
    commit: str = ""
    stats: dict[str, int] = field(default_factory=dict)
    modules: list[dict] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    noise_folders: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
