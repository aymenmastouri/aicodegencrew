"""Central path constants for all SDLC phases.

Single source of truth — every pipeline, crew, and backend service
imports from here instead of hardcoding directory names.

All paths are RELATIVE to the project root (CWD).
The target repository (repo_path) is only used as INPUT for analysis.
Phase outputs always go into the PROJECT's knowledge/ directory.
"""

from pathlib import Path

# Phase output directories (relative to project root)
PHASE_DIRS: dict[str, str] = {
    "discover": "knowledge/discover",
    "extract": "knowledge/extract",
    "analyze": "knowledge/analyze",
    "document": "knowledge/document",
    "triage": "knowledge/triage",
    "plan": "knowledge/plan",
    "implement": "knowledge/implement",
    "verify": "knowledge/verify",
    "deliver": "knowledge/deliver",
}

# Frequently-used file paths (relative to project root)
KNOWLEDGE_DIR = Path("knowledge")
PHASE1_FACTS = "knowledge/extract/architecture_facts.json"
PHASE1_EVIDENCE = "knowledge/extract/evidence_map.json"
PHASE2_ANALYSIS = "knowledge/analyze/analyzed_architecture.json"

# ChromaDB lives inside discover phase
CHROMA_DIR = "knowledge/discover"

# Discover phase artifacts (new in v0.6)
DISCOVER_SYMBOLS = "knowledge/discover/symbols.jsonl"
DISCOVER_EVIDENCE = "knowledge/discover/evidence.jsonl"
DISCOVER_MANIFEST = "knowledge/discover/repo_manifest.json"
