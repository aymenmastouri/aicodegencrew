"""
Validator for evidence_map.json.

Validates:
- File path existence
- Line range accuracy
- Evidence ID uniqueness
- Cross-references with architecture_facts.json
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Any


class EvidenceValidator:
    """Validate evidence_map.json integrity."""
    
    def __init__(self, evidence_path: str | Path, project_root: str | Path):
        """
        Initialize validator.
        
        Args:
            evidence_path: Path to evidence_map.json
            project_root: Root directory of analyzed project
        """
        self.evidence_path = Path(evidence_path)
        self.project_root = Path(project_root)
        self.evidence_map = self._load_evidence()
    
    def _load_evidence(self) -> Dict[str, Any]:
        """Load and parse evidence JSON."""
        if not self.evidence_path.exists():
            raise FileNotFoundError(f"Evidence file not found: {self.evidence_path}")
        
        with open(self.evidence_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_file_paths(self) -> List[str]:
        """
        Validate all evidence file paths exist.
        
        Returns:
            List of missing file paths (empty if all valid)
        """
        missing_files = []
        
        for evidence_id, evidence in self.evidence_map.items():
            file_path = evidence.get("file_path")
            if not file_path:
                missing_files.append(f"{evidence_id}: No file_path")
                continue
            
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(f"{evidence_id}: {file_path} not found")
        
        return missing_files
    
    def validate_line_ranges(self) -> List[str]:
        """
        Validate line ranges are within file bounds.
        
        Returns:
            List of invalid line ranges (empty if all valid)
        """
        invalid_ranges = []
        
        for evidence_id, evidence in self.evidence_map.items():
            file_path = evidence.get("file_path")
            start_line = evidence.get("start_line")
            end_line = evidence.get("end_line")
            
            if not file_path or start_line is None or end_line is None:
                continue
            
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    total_lines = sum(1 for _ in f)
                
                if start_line < 1:
                    invalid_ranges.append(f"{evidence_id}: start_line < 1 ({start_line})")
                if end_line > total_lines:
                    invalid_ranges.append(
                        f"{evidence_id}: end_line ({end_line}) > total lines ({total_lines})"
                    )
                if start_line > end_line:
                    invalid_ranges.append(
                        f"{evidence_id}: start_line ({start_line}) > end_line ({end_line})"
                    )
            except Exception as e:
                invalid_ranges.append(f"{evidence_id}: Error reading file: {e}")
        
        return invalid_ranges
    
    def validate_evidence_ids_unique(self) -> bool:
        """
        Validate all evidence IDs are unique.
        
        Returns:
            True if all IDs are unique
        """
        # JSON keys are inherently unique, but check for consistency
        return len(self.evidence_map) == len(set(self.evidence_map.keys()))
    
    def get_evidence_ids(self) -> Set[str]:
        """
        Get all evidence IDs.
        
        Returns:
            Set of evidence IDs
        """
        return set(self.evidence_map.keys())
    
    def validate_cross_references(self, facts_path: str | Path) -> List[str]:
        """
        Validate all evidence IDs referenced in facts exist in evidence map.
        
        Args:
            facts_path: Path to architecture_facts.json
            
        Returns:
            List of missing evidence IDs (empty if all valid)
        """
        missing_evidence = []
        
        # Load facts
        with open(facts_path, 'r', encoding='utf-8') as f:
            facts = json.load(f)
        
        valid_evidence_ids = self.get_evidence_ids()
        
        # Check all evidence_ids in facts
        for container in facts.get("containers", []):
            for ev_id in container.get("evidence_ids", []):
                if ev_id not in valid_evidence_ids:
                    missing_evidence.append(f"Container {container['id']}: {ev_id}")
        
        for component in facts.get("components", []):
            for ev_id in component.get("evidence_ids", []):
                if ev_id not in valid_evidence_ids:
                    missing_evidence.append(f"Component {component['id']}: {ev_id}")
        
        for interface in facts.get("interfaces", []):
            for ev_id in interface.get("evidence_ids", []):
                if ev_id not in valid_evidence_ids:
                    missing_evidence.append(f"Interface {interface['id']}: {ev_id}")
        
        return missing_evidence
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get validation summary.
        
        Returns:
            Dict with validation results
        """
        return {
            "total_evidence": len(self.evidence_map),
            "evidence_ids_unique": self.validate_evidence_ids_unique(),
            "missing_files": len(self.validate_file_paths()),
            "invalid_line_ranges": len(self.validate_line_ranges()),
        }
