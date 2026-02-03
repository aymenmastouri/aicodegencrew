"""
Validator for Phase 2 synthesis outputs.

Validates:
- Evidence-first compliance (no hallucinations)
- Completeness (all containers/components present)
- Mermaid syntax validity
- arc42 documentation structure
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple


class SynthesisValidator:
    """Validate Phase 2 synthesis outputs against architecture facts."""
    
    def __init__(
        self,
        facts_path: str | Path,
        c4_path: str | Path,
        arc42_path: str | Path
    ):
        """
        Initialize validator.
        
        Args:
            facts_path: Path to architecture_facts.json
            c4_path: Path to c4/ directory
            arc42_path: Path to arc42/ directory
        """
        self.facts_path = Path(facts_path)
        self.c4_path = Path(c4_path)
        self.arc42_path = Path(arc42_path)
        
        self.facts = self._load_facts()
        self.valid_container_ids = self._extract_container_ids()
        self.valid_component_ids = self._extract_component_ids()
    
    def _load_facts(self) -> Dict[str, Any]:
        """Load architecture facts."""
        with open(self.facts_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _extract_container_ids(self) -> Set[str]:
        """Extract valid container IDs from facts."""
        return {c.get("id") for c in self.facts.get("containers", [])}
    
    def _extract_component_ids(self) -> Set[str]:
        """Extract valid component IDs from facts."""
        return {c.get("id") for c in self.facts.get("components", [])}
    
    def validate_no_hallucinations(self) -> Tuple[bool, List[str]]:
        """
        Validate no invented containers/components in C4 diagrams.
        
        Returns:
            Tuple of (is_valid, list_of_hallucinated_elements)
        """
        hallucinations = []
        
        # Check C4 container diagram
        container_file = self.c4_path / "c4-container.md"
        if container_file.exists():
            content = container_file.read_text(encoding='utf-8')
            
            # Extract container references from Mermaid
            # Pattern: Container(id, "name", ...)
            container_pattern = r'Container(?:Db|Queue)?\(([a-zA-Z0-9_-]+),'
            mentioned_containers = set(re.findall(container_pattern, content))
            
            # Check for invalid containers
            invalid = mentioned_containers - self.valid_container_ids
            for container_id in invalid:
                hallucinations.append(f"C4 Container: {container_id} not in facts")
        
        # Check C4 component diagrams
        for component_file in self.c4_path.glob("c4-components-*.md"):
            content = component_file.read_text(encoding='utf-8')
            
            # Pattern: Component(id, "name", ...)
            component_pattern = r'Component\(([a-zA-Z0-9_.-]+),'
            mentioned_components = set(re.findall(component_pattern, content))
            
            # Check for invalid components (allow some flexibility for formatting)
            for component_id in mentioned_components:
                # Normalize ID (remove quotes, spaces)
                normalized_id = component_id.strip('"').strip()
                if normalized_id and normalized_id not in self.valid_component_ids:
                    # Check if it's a partial match (sometimes IDs are truncated)
                    if not any(normalized_id in valid_id for valid_id in self.valid_component_ids):
                        hallucinations.append(
                            f"C4 Component: {normalized_id} not in facts ({component_file.name})"
                        )
        
        return (len(hallucinations) == 0, hallucinations)
    
    def validate_completeness(self) -> Tuple[bool, List[str]]:
        """
        Validate all containers from facts are present in C4 diagrams.
        
        Returns:
            Tuple of (is_complete, list_of_missing_containers)
        """
        missing = []
        
        # Check C4 container diagram
        container_file = self.c4_path / "c4-container.md"
        if not container_file.exists():
            return (False, ["C4 container diagram not found"])
        
        content = container_file.read_text(encoding='utf-8')
        
        # Extract mentioned containers
        container_pattern = r'Container(?:Db|Queue)?\(([a-zA-Z0-9_-]+),'
        mentioned_containers = set(re.findall(container_pattern, content))
        
        # Find missing containers
        for container_id in self.valid_container_ids:
            if container_id not in mentioned_containers:
                missing.append(f"Container missing in C4: {container_id}")
        
        return (len(missing) == 0, missing)
    
    def validate_mermaid_syntax(self) -> Tuple[bool, List[str]]:
        """
        Validate Mermaid syntax in C4 diagrams.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for md_file in self.c4_path.glob("*.md"):
            content = md_file.read_text(encoding='utf-8')
            
            # Check for mermaid code blocks
            if "```mermaid" not in content:
                errors.append(f"{md_file.name}: No mermaid code block found")
                continue
            
            # Extract mermaid blocks
            mermaid_blocks = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)
            
            for i, block in enumerate(mermaid_blocks):
                # Check for C4 diagram type
                if not any(keyword in block for keyword in ["C4Context", "C4Container", "C4Component"]):
                    errors.append(f"{md_file.name} block {i+1}: Not a C4 diagram")
                
                # Check for basic syntax elements
                if "title" not in block:
                    errors.append(f"{md_file.name} block {i+1}: Missing title")
                
                # Check for balanced parentheses
                if block.count("(") != block.count(")"):
                    errors.append(f"{md_file.name} block {i+1}: Unbalanced parentheses")
        
        return (len(errors) == 0, errors)
    
    def validate_arc42_structure(self) -> Tuple[bool, List[str]]:
        """
        Validate arc42 documentation structure.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Expected chapters
        expected_chapters = [
            "01-introduction.md",
            "03-context.md",
            "05-building-blocks.md",
        ]
        
        for chapter in expected_chapters:
            chapter_file = self.arc42_path / chapter
            if not chapter_file.exists():
                errors.append(f"Missing chapter: {chapter}")
                continue
            
            content = chapter_file.read_text(encoding='utf-8')
            
            # Check for markdown heading
            if not content.strip().startswith("#"):
                errors.append(f"{chapter}: No markdown heading")
            
            # Check for evidence references
            if "Evidence" not in content and "ev_" not in content:
                errors.append(f"{chapter}: No evidence references found")
        
        return (len(errors) == 0, errors)
    
    def validate_unknown_markers(self) -> List[str]:
        """
        Find sections marked as UNKNOWN.
        
        Returns:
            List of UNKNOWN markers (informational, not an error)
        """
        unknown_markers = []
        
        for arc42_file in self.arc42_path.glob("*.md"):
            content = arc42_file.read_text(encoding='utf-8')
            
            if "UNKNOWN" in content:
                # Extract lines with UNKNOWN
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if "UNKNOWN" in line:
                        unknown_markers.append(f"{arc42_file.name}:{i}: {line.strip()}")
        
        return unknown_markers
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get validation summary.
        
        Returns:
            Dict with validation results
        """
        no_hallucinations, hallucinations = self.validate_no_hallucinations()
        is_complete, missing = self.validate_completeness()
        mermaid_valid, mermaid_errors = self.validate_mermaid_syntax()
        arc42_valid, arc42_errors = self.validate_arc42_structure()
        unknown_markers = self.validate_unknown_markers()
        
        return {
            "no_hallucinations": no_hallucinations,
            "hallucinations_found": hallucinations,
            "completeness": is_complete,
            "missing_elements": missing,
            "mermaid_syntax_valid": mermaid_valid,
            "mermaid_errors": mermaid_errors,
            "arc42_structure_valid": arc42_valid,
            "arc42_errors": arc42_errors,
            "unknown_markers_count": len(unknown_markers),
            "unknown_markers": unknown_markers[:5],  # First 5 for brevity
        }
