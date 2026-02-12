"""Endpoint Flow Builder - Constructs evidence-based workflow chains.

Deterministically builds endpoint -> controller -> service -> repository call chains
from collected components, interfaces, and relations.

NO LLM. Only evidence-based construction from Phase 1 facts.
"""

from ...shared.utils.logger import logger
from .collectors.fact_adapter import CollectedComponent, CollectedEvidence, CollectedInterface, CollectedRelation


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

    # REST interface type patterns (case-insensitive)
    REST_TYPES = {"rest", "rest_endpoint", "rest-endpoint", "openapi_endpoint", "openapi-endpoint"}

    def __init__(
        self,
        components: list[CollectedComponent],
        interfaces: list[CollectedInterface],
        relations: list[CollectedRelation],
        evidence: dict[str, CollectedEvidence],
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
        self.component_by_id: dict[str, CollectedComponent] = {c.id: c for c in components}
        self.component_by_name: dict[str, CollectedComponent] = {c.name: c for c in components}
        # Also index by lowercase name for fuzzy matching
        self.component_by_name_lower: dict[str, CollectedComponent] = {c.name.lower(): c for c in components}
        # Reverse lookup: adapter ID -> component name
        self._id_to_name: dict[str, str] = {c.id: c.name for c in components}

        # Index relations by from_id (raw component NAME, since RelationHints use names)
        self.relations_from: dict[str, list[CollectedRelation]] = {}
        for rel in relations:
            if rel.from_id not in self.relations_from:
                self.relations_from[rel.from_id] = []
            self.relations_from[rel.from_id].append(rel)

        # Also index by lowercase for fuzzy matching
        self.relations_from_lower: dict[str, list[CollectedRelation]] = {}
        for rel in relations:
            key = rel.from_id.lower()
            if key not in self.relations_from_lower:
                self.relations_from_lower[key] = []
            self.relations_from_lower[key].append(rel)

        logger.info(
            f"[EndpointFlowBuilder] Initialized with {len(components)} components, "
            f"{len(interfaces)} interfaces, {len(relations)} relations"
        )

    def build_flows(self) -> list[dict]:
        """
        Build all endpoint flows.

        Returns:
            List of endpoint flow dictionaries
        """
        flows = []
        rest_count = 0

        for interface in self.interfaces:
            # Support both 'type' and 'interface_type' attributes (case-insensitive)
            iface_type = getattr(interface, "type", None) or getattr(interface, "interface_type", "")
            if not iface_type:
                continue

            # Check if it's a REST-type interface
            if iface_type.lower().replace("-", "_") not in self.REST_TYPES:
                continue

            rest_count += 1
            flow = self._build_single_flow(interface)
            if flow and len(flow["chain"]) >= 1:  # Include even single-step flows
                flows.append(flow)

        logger.info(f"[EndpointFlowBuilder] Found {rest_count} REST interfaces, built {len(flows)} endpoint flows")
        return flows

    def _find_controller(self, interface: CollectedInterface) -> CollectedComponent | None:
        """
        Find the controller/implementer for an interface.

        Tries multiple strategies:
        1. implemented_by attribute (direct match)
        2. implemented_by_hint attribute
        3. Partial name match
        4. Find by stereotype (controller, rest_interface)
        """
        # Try implemented_by or implemented_by_hint
        controller_name = (
            getattr(interface, "implemented_by", "") or getattr(interface, "implemented_by_hint", "") or ""
        )

        if controller_name:
            # Try exact match
            controller = self.component_by_name.get(controller_name)
            if controller:
                return controller

            # Try case-insensitive match
            controller = self.component_by_name_lower.get(controller_name.lower())
            if controller:
                return controller

            # Try by ID
            controller = self.component_by_id.get(controller_name)
            if controller:
                return controller

        # Try to find controller by stereotype matching the path
        iface_path = getattr(interface, "path", "") or ""
        if iface_path:
            # Extract possible controller name from path (e.g., /api/users -> Users, User)
            path_parts = [p for p in iface_path.split("/") if p and not p.startswith("{")]
            if path_parts:
                last_part = path_parts[-1] if path_parts else ""
                # Try to find a controller with matching name
                for comp in self.components:
                    if comp.stereotype in ("controller", "rest_interface"):
                        comp_name_lower = comp.name.lower()
                        if last_part.lower() in comp_name_lower:
                            return comp

        return None

    def _build_single_flow(self, interface: CollectedInterface) -> dict | None:
        """
        Build a single endpoint flow.

        Args:
            interface: REST interface to build flow for

        Returns:
            Endpoint flow dictionary or None
        """
        # Find implementing controller
        controller = self._find_controller(interface)

        if not controller:
            # Log at debug level to avoid spam
            iface_id = getattr(interface, "id", "unknown")
            logger.debug(f"[EndpointFlowBuilder] No controller found for interface: {iface_id}")
            return None

        # Build call chain starting from controller
        chain = [controller.id]
        visited = {controller.id}
        evidence_ids = list(getattr(interface, "evidence_ids", []))

        # Follow relations through layers: controller -> service -> repository
        self._follow_chain(controller.id, chain, visited, evidence_ids, max_depth=5)

        # Create flow ID
        iface_id = getattr(interface, "id", "unknown")
        flow_id = f"flow_{iface_id}"

        # Get path - support both 'path' and 'endpoint' attributes
        iface_path = getattr(interface, "path", None) or getattr(interface, "endpoint", "UNKNOWN")
        iface_method = getattr(interface, "method", "UNKNOWN")

        # Build flow dictionary
        flow = {
            "id": flow_id,
            "interface_id": iface_id,
            "path": iface_path or "UNKNOWN",
            "method": iface_method or "UNKNOWN",
            "chain": chain,
            "evidence": evidence_ids,
        }

        return flow

    def _follow_chain(
        self,
        component_id: str,
        chain: list[str],
        visited: set[str],
        evidence_ids: list[str],
        max_depth: int,
    ):
        """
        Recursively follow dependency relations to build call chain.

        Args:
            component_id: Current component to explore (adapter ID like comp_1_Name)
            chain: Chain being built (modified in-place)
            visited: Set of visited component IDs
            evidence_ids: List of evidence IDs (modified in-place)
            max_depth: Maximum recursion depth
        """
        if max_depth <= 0:
            return

        # Relations use raw names as from_id/to_id, so look up by component NAME
        component_name = self._id_to_name.get(component_id, component_id)

        # Try exact match first, then case-insensitive
        relations = self.relations_from.get(component_name, [])
        if not relations:
            relations = self.relations_from_lower.get(component_name.lower(), [])

        # Prioritize relations based on stereotype progression:
        # controller -> service -> repository -> entity
        stereotype_priority = {
            "controller": 0,
            "rest_interface": 0,
            "service": 1,
            "adapter": 2,
            "repository": 3,
            "entity": 4,
            "component": 5,
        }

        # Sort relations by target stereotype priority
        # Note: rel.to_id is a raw component NAME, so look up by name
        sorted_relations = []
        for rel in relations:
            # Try exact match first
            target_component = self.component_by_name.get(rel.to_id)
            if not target_component:
                # Try case-insensitive
                target_component = self.component_by_name_lower.get(rel.to_id.lower())

            if target_component and target_component.id not in visited:
                priority = stereotype_priority.get(target_component.stereotype, 99)
                sorted_relations.append((priority, rel, target_component))

        sorted_relations.sort(key=lambda x: x[0])

        # Follow the most relevant relations
        for _priority, rel, target_component in sorted_relations[:3]:  # Limit to top 3 relations per level
            if target_component.id not in visited:
                visited.add(target_component.id)
                chain.append(target_component.id)

                # Safely extend evidence_ids
                rel_evidence = getattr(rel, "evidence_ids", [])
                if rel_evidence:
                    evidence_ids.extend(rel_evidence)

                # Recursively follow from this component
                self._follow_chain(target_component.id, chain, visited, evidence_ids, max_depth - 1)

                # Only follow one main path per component to avoid explosion
                break
