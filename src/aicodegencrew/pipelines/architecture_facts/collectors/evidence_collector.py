"""
EvidenceCollector - Aggregates all evidence into a map.

This collector:
1. Takes output from all other collectors
2. Builds a unified evidence map
3. Links evidence to facts

Output → evidence.json
"""

from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, field

from .base import DimensionCollector, CollectorOutput, RawEvidence, RawFact
from ....shared.utils.logger import logger


@dataclass
class EvidenceEntry:
    """An entry in the evidence map."""
    path: str
    line_start: int
    line_end: int
    reason: str
    fact_refs: List[str] = field(default_factory=list)  # Facts that reference this evidence
    snippet: str = ""


class EvidenceCollector(DimensionCollector):
    """
    Aggregates evidence from all collectors into a unified map.
    """
    
    DIMENSION = "evidence"
    
    def __init__(self, repo_path: Path):
        super().__init__(repo_path)
        self._evidence_map: Dict[str, EvidenceEntry] = {}
    
    def collect(self) -> CollectorOutput:
        """This collector doesn't scan - it aggregates."""
        self._log_start()
        # No direct collection - use add_from_output instead
        self._log_end()
        return self.output
    
    def add_from_output(self, collector_output: CollectorOutput, fact_prefix: str = ""):
        """
        Add evidence from another collector's output.
        
        Args:
            collector_output: Output from another collector
            fact_prefix: Prefix to identify which collector (e.g., "spring_rest")
        """
        for fact in collector_output.facts:
            fact_id = f"{fact_prefix}:{fact.name}" if fact_prefix else fact.name
            
            for ev in fact.evidence:
                key = f"{ev.path}:{ev.line_start}-{ev.line_end}"
                
                if key not in self._evidence_map:
                    self._evidence_map[key] = EvidenceEntry(
                        path=ev.path,
                        line_start=ev.line_start,
                        line_end=ev.line_end,
                        reason=ev.reason,
                        snippet=ev.snippet or "",
                    )
                
                self._evidence_map[key].fact_refs.append(fact_id)
    
    def build_evidence_map(self) -> Dict[str, Dict]:
        """
        Build the final evidence map.
        
        Returns:
            Dictionary mapping evidence keys to evidence entries
        """
        result = {}
        
        for key, entry in self._evidence_map.items():
            result[key] = {
                "path": entry.path,
                "lines": f"{entry.line_start}-{entry.line_end}",
                "reason": entry.reason,
                "referenced_by": entry.fact_refs,
            }
            if entry.snippet:
                result[key]["snippet"] = entry.snippet
        
        return result
    
    def get_evidence_for_file(self, file_path: str) -> List[Dict]:
        """Get all evidence entries for a specific file."""
        results = []
        for key, entry in self._evidence_map.items():
            if entry.path == file_path or file_path in entry.path:
                results.append({
                    "lines": f"{entry.line_start}-{entry.line_end}",
                    "reason": entry.reason,
                    "referenced_by": entry.fact_refs,
                })
        return sorted(results, key=lambda x: int(x["lines"].split("-")[0]))
    
    def get_statistics(self) -> Dict:
        """Get evidence statistics."""
        files: Set[str] = set()
        total_lines = 0
        
        for entry in self._evidence_map.values():
            files.add(entry.path)
            total_lines += entry.line_end - entry.line_start + 1
        
        return {
            "total_evidence": len(self._evidence_map),
            "files_with_evidence": len(files),
            "total_lines_covered": total_lines,
            "facts_referenced": sum(len(e.fact_refs) for e in self._evidence_map.values()),
        }
