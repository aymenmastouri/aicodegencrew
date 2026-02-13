"""Central path constants for all SDLC phases.

Single source of truth — every pipeline, crew, and backend service
imports from here instead of hardcoding directory names.
"""

# Phase output directories (relative to project root)
PHASE_DIRS: dict[str, str] = {
    "discover": "knowledge/discover",
    "extract": "knowledge/extract",
    "analyze": "knowledge/analyze",
    "document": "knowledge/document",
    "plan": "knowledge/plan",
    "implement": "knowledge/implement",
    "verify": "knowledge/verify",
    "deliver": "knowledge/deliver",
}

# Frequently-used file paths
PHASE1_FACTS = "knowledge/extract/architecture_facts.json"
PHASE1_EVIDENCE = "knowledge/extract/evidence_map.json"
PHASE2_ANALYSIS = "knowledge/analyze/analyzed_architecture.json"

# ChromaDB lives inside discover phase
CHROMA_DIR = "knowledge/discover"
