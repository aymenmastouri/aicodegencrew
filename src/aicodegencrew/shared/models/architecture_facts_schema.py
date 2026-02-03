"""Pydantic schemas for Architecture Facts (Phase 1 output).

Phase 1 erzeugt die einzige Architektur-Wahrheit.
Keine Interpretation. Kein LLM. Keine Doku. Nur Fakten + Belege.

Alles, was nicht in Phase 1 steht, darf Phase 2 nicht schreiben.

Output:
- architecture_facts.json: Ground truth about the codebase
- evidence_map.json: Links facts to source code locations
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Evidence Model
# =============================================================================

class EvidenceItem(BaseModel):
    """A single piece of evidence linking a fact to source code."""
    path: str = Field(..., description="Relative file path")
    lines: str = Field(..., description="Line range, e.g. '12-85'")
    reason: str = Field(..., description="Why this is evidence, e.g. '@Service annotated class'")
    chunk_id: Optional[str] = Field(None, description="ChromaDB chunk ID if indexed")


# =============================================================================
# System Model
# =============================================================================

class SystemInfo(BaseModel):
    """High-level system information."""
    id: str = Field(default="system", description="Always 'system'")
    name: str = Field(..., description="Repository/System name")
    domain: str = Field(default="UNKNOWN", description="Business domain (UNKNOWN if not detectable)")


# =============================================================================
# Container Model
# =============================================================================

class Container(BaseModel):
    """A container (deployable unit) - very coarse-grained."""
    id: str = Field(..., description="Unique container ID (e.g., 'backend', 'frontend')")
    name: str = Field(..., description="Container name")
    type: str = Field(default="application", description="Type: application, database, infrastructure")
    technology: str = Field(..., description="Primary technology (e.g., Spring Boot, Angular)")
    evidence: List[str] = Field(..., description="Evidence IDs (minimum 1)")


# =============================================================================
# Component Model
# =============================================================================

class Component(BaseModel):
    """A component within a container - only technically recognizable units."""
    id: str = Field(..., description="Unique component ID")
    container: str = Field(..., description="Parent container ID")
    name: str = Field(..., description="Class/module name (e.g., 'WorkflowServiceImpl')")
    stereotype: str = Field(..., description="Stereotype: controller, service, repository, component, module, etc.")
    file_path: Optional[str] = Field(None, description="Relative file path")
    evidence: List[str] = Field(..., description="Evidence IDs (minimum 1)")


# =============================================================================
# Interface Model
# =============================================================================

class Interface(BaseModel):
    """An explicit interface (REST endpoint, GraphQL, etc.)."""
    id: str = Field(..., description="Unique interface ID")
    container: str = Field(..., description="Container that exposes this interface")
    type: str = Field(..., description="Type: REST, GraphQL, gRPC, Kafka, etc.")
    path: Optional[str] = Field(None, description="URL path pattern (e.g., '/workflow/**')")
    method: Optional[str] = Field(None, description="HTTP method for REST")
    implemented_by: str = Field(..., description="Component name that implements this")
    evidence: List[str] = Field(..., description="Evidence IDs (minimum 1)")


# =============================================================================
# Relation Model
# =============================================================================

class Relation(BaseModel):
    """A relation between components - only 'uses', technically derivable."""
    id: Optional[str] = Field(None, description="Optional relation ID")
    from_id: str = Field(..., alias="from", description="Source component ID")
    to_id: str = Field(..., alias="to", description="Target component ID")
    type: str = Field(default="uses", description="Relation type (always 'uses' for now)")
    method: Optional[str] = Field(None, description="Method name if call relation")
    evidence: List[str] = Field(..., description="Evidence IDs (minimum 1)")
    
    class Config:
        populate_by_name = True


# =============================================================================
# Endpoint Flow Model (NEW - for runtime view evidence)
# =============================================================================

class EndpointFlow(BaseModel):
    """
    Evidence-based workflow: endpoint → controller → service → repository chain.
    Deterministically extracted from code structure (no LLM).
    """
    id: str = Field(..., description="Unique flow ID")
    interface_id: str = Field(..., description="REST interface ID that triggers this flow")
    path: str = Field(..., description="REST path (e.g., '/workflow/create')")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    chain: List[str] = Field(..., description="Component IDs in call order [controller, service, repository, ...]")
    evidence: List[str] = Field(..., description="Evidence IDs proving this flow")

    class Config:
        populate_by_name = True


# =============================================================================
# Architecture Facts (Root Model)
# =============================================================================

class ArchitectureFacts(BaseModel):
    """
    Complete architecture facts extracted from the codebase.
    
    This is the GROUND TRUTH - deterministically extracted, no LLM.
    Every fact has evidence linking back to source code.
    
    Phase 1 does NOT:
    - Use C4 names like "Application Layer"
    - Describe responsibilities
    - Make architecture decisions
    - Define flows
    - Summarize anything
    - Use LLM
    """
    system: SystemInfo = Field(..., description="System information")
    containers: List[Container] = Field(default_factory=list, description="Containers")
    components: List[Component] = Field(default_factory=list, description="Components")
    interfaces: List[Interface] = Field(default_factory=list, description="Interfaces")
    relations: List[Relation] = Field(default_factory=list, description="Relations")
    endpoint_flows: List[EndpointFlow] = Field(default_factory=list, description="Endpoint → Component call chains (for runtime view)")

    def validate_evidence(self, evidence_map: Dict[str, EvidenceItem]) -> List[str]:
        """Validate that all facts have evidence. Returns list of errors."""
        errors = []
        
        for container in self.containers:
            if not container.evidence:
                errors.append(f"Container '{container.id}' has no evidence")
            for ev_id in container.evidence:
                if ev_id not in evidence_map:
                    errors.append(f"Container '{container.id}' references unknown evidence '{ev_id}'")
        
        for component in self.components:
            if not component.evidence:
                errors.append(f"Component '{component.id}' has no evidence")
            for ev_id in component.evidence:
                if ev_id not in evidence_map:
                    errors.append(f"Component '{component.id}' references unknown evidence '{ev_id}'")
        
        for interface in self.interfaces:
            if not interface.evidence:
                errors.append(f"Interface '{interface.id}' has no evidence")
            for ev_id in interface.evidence:
                if ev_id not in evidence_map:
                    errors.append(f"Interface '{interface.id}' references unknown evidence '{ev_id}'")
        
        for relation in self.relations:
            if not relation.evidence:
                errors.append(f"Relation '{relation.from_id}->{relation.to_id}' has no evidence")
            for ev_id in relation.evidence:
                if ev_id not in evidence_map:
                    errors.append(f"Relation references unknown evidence '{ev_id}'")
        
        for flow in self.endpoint_flows:
            if not flow.evidence:
                errors.append(f"EndpointFlow '{flow.id}' has no evidence")
            for ev_id in flow.evidence:
                if ev_id not in evidence_map:
                    errors.append(f"EndpointFlow '{flow.id}' references unknown evidence '{ev_id}'")

        return errors
