"""Central path constants for all SDLC phases.

Single source of truth — every pipeline, crew, and backend service
imports from here instead of hardcoding directory names.
"""

# Phase output directories (relative to project root)
PHASE_DIRS: dict[str, str] = {
    "phase0_indexing": "knowledge/phase0_indexing",
    "phase1_architecture_facts": "knowledge/phase1_facts",
    "phase2_architecture_analysis": "knowledge/phase2_analysis",
    "phase3_architecture_synthesis": "knowledge/phase3_synthesis",
    "phase4_development_planning": "knowledge/phase4_planning",
    "phase5_code_generation": "knowledge/phase5_codegen",
    "phase6_test_generation": "knowledge/phase6_testing",
    "phase7_review_deploy": "knowledge/phase7_deployment",
}

# Frequently-used file paths
PHASE1_FACTS = "knowledge/phase1_facts/architecture_facts.json"
PHASE1_EVIDENCE = "knowledge/phase1_facts/evidence_map.json"
PHASE2_ANALYSIS = "knowledge/phase2_analysis/analyzed_architecture.json"

# ChromaDB lives inside phase0
CHROMA_DIR = "knowledge/phase0_indexing"
