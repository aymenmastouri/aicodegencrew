"""Writer for architecture facts output files.

Writes:
- knowledge/architecture/architecture_facts.json
- knowledge/architecture/evidence_map.json
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from .base_collector import CollectedEvidence, CollectedComponent, CollectedInterface, CollectedRelation
from ...shared.models.architecture_facts_schema import (
    ArchitectureFacts,
    EvidenceItem,
    SystemInfo,
    Container,
    Component,
    Interface,
    Relation,
)
from ...shared.utils.logger import logger


class FactsWriter:
    """Writes architecture facts to JSON files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _derive_package(self, file_path: str) -> str:
        """Derive package/module from file path."""
        if not file_path:
            return ""
        # Remove file name, get directory path as package
        parts = file_path.replace("\\", "/").split("/")
        # Remove src/main/java, src/app, etc.
        skip_parts = {"src", "main", "java", "app", "lib", "components", "services", "modules"}
        filtered = [p for p in parts[:-1] if p and p.lower() not in skip_parts]
        return ".".join(filtered[-3:]) if filtered else ""
    
    def write(
        self,
        system_name: str,
        containers: List[Dict],
        components: List[CollectedComponent],
        interfaces: List[CollectedInterface],
        relations: List[CollectedRelation],
        endpoint_flows: List[Dict],
        evidence: Dict[str, CollectedEvidence],
    ) -> Dict:
        """
        Write architecture facts and evidence map to JSON files.
        
        Returns:
            Dict with file paths and statistics
        """
        # Build facts model
        facts = {
            "system": {
                "id": "system",
                "name": system_name,
                "domain": "UNKNOWN"
            },
            "containers": containers,
            "components": [
                {
                    "id": c.id,
                    "container": c.container,
                    "name": c.name,
                    "stereotype": c.stereotype,
                    "file_path": c.file_path,
                    "evidence_ids": c.evidence_ids,
                    "confidence": getattr(c, 'confidence', 1.0),
                    "layer": getattr(c, 'layer', None),
                    "module": getattr(c, 'module', None),
                    "package": getattr(c, 'module', None) or self._derive_package(c.file_path),
                    "description": "",  # Populated by Phase 2
                    "tags": getattr(c, 'tags', []),
                }
                for c in components
            ],
            "interfaces": [
                {
                    "id": i.id,
                    "container": i.container,
                    "type": i.type,
                    "path": i.path,
                    "method": i.method,
                    "implemented_by": i.implemented_by,
                    "evidence_ids": i.evidence_ids
                }
                for i in interfaces
            ],
            "relations": [
                {
                    "from": r.from_id,
                    "to": r.to_id,
                    "type": r.type,
                    "evidence_ids": r.evidence_ids,
                    "confidence": getattr(r, 'confidence', 1.0),
                    "description": getattr(r, 'description', None),
                }
                for r in relations
            ],
            "endpoint_flows": endpoint_flows,
            # Evidence array for validation (also in separate evidence_map.json)
            "evidence": [
                {
                    "id": ev_id,
                    "path": ev.path,
                    "lines": ev.lines,
                    "reason": ev.reason
                }
                for ev_id, ev in evidence.items()
            ]
        }
        
        # Build evidence map
        evidence_map = {
            ev_id: {
                "path": ev.path,
                "lines": ev.lines,
                "reason": ev.reason,
                "chunk_id": ev.chunk_id
            }
            for ev_id, ev in evidence.items()
        }
        
        # Validate: every fact must have evidence
        errors = self._validate_evidence(facts, evidence_map)
        if errors:
            logger.warning(f"[FactsWriter] Validation warnings: {len(errors)}")
            for error in errors[:10]:
                logger.warning(f"  - {error}")
        
        # Write files
        facts_path = self.output_dir / "architecture_facts.json"
        evidence_path = self.output_dir / "evidence_map.json"
        
        with open(facts_path, 'w', encoding='utf-8') as f:
            json.dump(facts, f, indent=2, ensure_ascii=False)
        
        with open(evidence_path, 'w', encoding='utf-8') as f:
            json.dump(evidence_map, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[FactsWriter] Written: {facts_path}")
        logger.info(f"[FactsWriter] Written: {evidence_path}")
        
        return {
            "facts_path": str(facts_path),
            "evidence_path": str(evidence_path),
            "statistics": {
                "containers": len(containers),
                "components": len(components),
                "interfaces": len(interfaces),
                "relations": len(relations),
                "endpoint_flows": len(endpoint_flows),
                "evidence_items": len(evidence_map),
                "validation_errors": len(errors)
            }
        }
    
    def _validate_evidence(self, facts: Dict, evidence_map: Dict) -> List[str]:
        """Validate that all facts have valid evidence references."""
        errors = []
        
        for container in facts.get("containers", []):
            if not container.get("evidence"):
                errors.append(f"Container '{container['id']}' has no evidence")
            else:
                for ev_id in container["evidence"]:
                    if ev_id not in evidence_map:
                        errors.append(f"Container '{container['id']}' references unknown evidence '{ev_id}'")
        
        for component in facts.get("components", []):
            if not component.get("evidence"):
                errors.append(f"Component '{component['id']}' has no evidence")
            else:
                for ev_id in component["evidence"]:
                    if ev_id not in evidence_map:
                        errors.append(f"Component '{component['id']}' references unknown evidence '{ev_id}'")
        
        for interface in facts.get("interfaces", []):
            if not interface.get("evidence"):
                errors.append(f"Interface '{interface['id']}' has no evidence")
            else:
                for ev_id in interface["evidence"]:
                    if ev_id not in evidence_map:
                        errors.append(f"Interface '{interface['id']}' references unknown evidence '{ev_id}'")
        
        for relation in facts.get("relations", []):
            if not relation.get("evidence"):
                errors.append(f"Relation '{relation['from']}->{relation['to']}' has no evidence")
            else:
                for ev_id in relation["evidence"]:
                    if ev_id not in evidence_map:
                        errors.append(f"Relation references unknown evidence '{ev_id}'")
        
        return errors
