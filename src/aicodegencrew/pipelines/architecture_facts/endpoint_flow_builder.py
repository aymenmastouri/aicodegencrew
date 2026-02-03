"""Endpoint Flow Builder - Constructs evidence-based workflow chains.

Deterministically builds endpoint → controller → service → repository call chains
from collected components, interfaces, and relations.

NO LLM. Only evidence-based construction from Phase 1 facts.
"""

from typing import List, Dict, Set, Tuple
from pathlib import Path

from .base_collector import CollectedComponent, CollectedInterface, CollectedRelation, CollectedEvidence
from ...shared.utils.logger import logger


class EndpointFlowBuilder:
    """
    Builds endpoint flows (runtime workflows) from collected facts.

    For each REST interface:
    1. Find implementing controller
    2. Follow relations to find service calls
    3. Follow relations to find repository calls
    4. Construct evidence-based chain

    Example flow:
    - Interface: POST /workflow/create
    - Controller: WorkflowController.create()
    - Service: WorkflowService.createWorkflow()
    - Repository: WorkflowRepository.save()
    - Chain: [workflow_controller, workflow_service, workflow_repository]
    """

    def __init__(
        self,
        components: List[CollectedComponent],
        interfaces: List[CollectedInterface],
        relations: List[CollectedRelation],
        evidence: Dict[str, CollectedEvidence],
    ):
        """
        Initialize the endpoint flow builder.

        Args:
            components: All collected components
            interfaces: All collected interfaces
            relations: All collected relations
            evidence: Evidence map
        """
        self.components = components
        self.interfaces = interfaces
        self.relations = relations
        self.evidence = evidence

        # Build lookup indices
        self.component_by_id: Dict[str, CollectedComponent] = {
            c.id: c for c in components
        }
        self.component_by_name: Dict[str, CollectedComponent] = {
            c.name: c for c in components
        }
        self.relations_from: Dict[str, List[CollectedRelation]] = {}
        for rel in relations:
            if rel.from_id not in self.relations_from:
                self.relations_from[rel.from_id] = []
            self.relations_from[rel.from_id].append(rel)

        logger.info(f"[EndpointFlowBuilder] Initialized with {len(components)} components, "
                   f"{len(interfaces)} interfaces, {len(relations)} relations")

    def build_flows(self) -> List[Dict]:
        """
        Build all endpoint flows.

        Returns:
            List of endpoint flow dictionaries
        """
        flows = []

        for interface in self.interfaces:
            if interface.type != "REST":
                continue  # Only process REST interfaces for now

            flow = self._build_single_flow(interface)
            if flow and len(flow["chain"]) > 1:  # Only include if chain has multiple steps
                flows.append(flow)

        logger.info(f"[EndpointFlowBuilder] Built {len(flows)} endpoint flows")
        return flows

    def _build_single_flow(self, interface: CollectedInterface) -> Dict:
        """
        Build a single endpoint flow.

        Args:
            interface: REST interface to build flow for

        Returns:
            Endpoint flow dictionary or None
        """
        # Find implementing controller
        controller_name = interface.implemented_by
        controller = self.component_by_name.get(controller_name)

        if not controller:
            # Try finding by ID
            controller = self.component_by_id.get(controller_name)

        if not controller:
            logger.debug(f"[EndpointFlowBuilder] Controller not found for interface {interface.id}: {controller_name}")
            return None

        # Build call chain starting from controller
        chain = [controller.id]
        visited = {controller.id}
        evidence_ids = list(interface.evidence_ids)  # Start with interface evidence

        # Follow relations through layers: controller → service → repository
        self._follow_chain(controller.id, chain, visited, evidence_ids, max_depth=5)

        # Create flow ID
        flow_id = f"flow_{interface.id}"

        # Build flow dictionary
        flow = {
            "id": flow_id,
            "interface_id": interface.id,
            "path": interface.path or "UNKNOWN",
            "method": interface.method or "UNKNOWN",
            "chain": chain,
            "evidence": evidence_ids,
        }

        return flow

    def _follow_chain(
        self,
        component_id: str,
        chain: List[str],
        visited: Set[str],
        evidence_ids: List[str],
        max_depth: int,
    ):
        """
        Recursively follow dependency relations to build call chain.

        Args:
            component_id: Current component to explore
            chain: Chain being built (modified in-place)
            visited: Set of visited component IDs
            evidence_ids: List of evidence IDs (modified in-place)
            max_depth: Maximum recursion depth
        """
        if max_depth <= 0:
            return

        # Get all relations from this component
        relations = self.relations_from.get(component_id, [])

        # Prioritize relations based on stereotype progression:
        # controller → service → repository → entity
        stereotype_priority = {
            "controller": 0,
            "service": 1,
            "repository": 2,
            "entity": 3,
            "component": 4,
        }

        # Sort relations by target stereotype priority
        sorted_relations = []
        for rel in relations:
            target_component = self.component_by_id.get(rel.to_id)
            if target_component and target_component.id not in visited:
                priority = stereotype_priority.get(target_component.stereotype, 99)
                sorted_relations.append((priority, rel, target_component))

        sorted_relations.sort(key=lambda x: x[0])

        # Follow the most relevant relations
        for priority, rel, target_component in sorted_relations[:3]:  # Limit to top 3 relations per level
            if target_component.id not in visited:
                visited.add(target_component.id)
                chain.append(target_component.id)
                evidence_ids.extend(rel.evidence_ids)

                # Recursively follow from this component
                self._follow_chain(
                    target_component.id,
                    chain,
                    visited,
                    evidence_ids,
                    max_depth - 1
                )

                # Only follow one main path per component to avoid explosion
                break
