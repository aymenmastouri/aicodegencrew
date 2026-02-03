"""Test the _summarize_facts function for compact output."""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aicodegencrew.crews.architecture_synthesis.crew import _summarize_facts


def test_summarize_facts_is_compact():
    """Verify that facts summary stays under 4000 chars for LLM context."""
    facts_path = Path(__file__).parent.parent / "knowledge" / "architecture" / "architecture_facts.json"
    
    if not facts_path.exists():
        print(f"SKIP: {facts_path} not found")
        return
    
    with open(facts_path, 'r', encoding='utf-8') as f:
        facts = json.load(f)
    
    # Load evidence map if available
    evidence_path = facts_path.parent / "evidence_map.json"
    evidence_map = {}
    if evidence_path.exists():
        with open(evidence_path, 'r', encoding='utf-8') as f:
            evidence_map = json.load(f)
    
    summary = _summarize_facts(facts, evidence_map)
    
    print(f"Components in facts: {len(facts.get('components', []))}")
    print(f"Summary length: {len(summary)} chars")
    print(f"Summary lines: {len(summary.splitlines())}")
    print(f"Target: < 4000 chars")
    print("---")
    print(summary)
    print("---")
    
    # Assert compact size
    assert len(summary) < 4000, f"Summary too large: {len(summary)} chars (max 4000)"
    print("\n[PASS] Summary is compact enough for LLM context")


if __name__ == "__main__":
    test_summarize_facts_is_compact()
