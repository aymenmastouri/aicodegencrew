"""
Phase 2: Architecture Analysis Crew

Multi-agent analysis using 4 specialized agents:
- Technical Architect: Architecture styles, patterns, layers
- Functional Analyst: Domain model, capabilities, entities
- Quality Analyst: Technical debt, risks, quality attributes
- Synthesis Lead: Merges all analyses into unified model

Input: architecture_facts.json + ChromaDB (RAG)
Output: analyzed_architecture.json
"""

from .crew import ArchitectureAnalysisCrew
from .mapreduce_crew import MapReduceAnalysisCrew
from .tools import FactsQueryTool, RAGQueryTool, StereotypeListTool

__all__ = [
    "ArchitectureAnalysisCrew",
    "MapReduceAnalysisCrew",
    "FactsQueryTool",
    "RAGQueryTool",
    "StereotypeListTool",
]
