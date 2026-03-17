"""
WorkflowCollector - Thin router that delegates to ecosystem specialists.

Cross-cutting:
- BPMN Workflows (*.bpmn, *.bpmn20.xml, *.bpmn2) — parsed directly

Delegated to ecosystem specialists:
- Java/Spring: SpringWorkflowCollector
- TypeScript/Angular: AngularWorkflowDetailCollector
- Python: PythonWorkflowCollector
- C/C++: CppWorkflowCollector

Output -> workflows.json
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, FactType, RawFact


@dataclass
class RawWorkflow(RawFact):
    """A workflow/state machine fact."""

    workflow_type: str = ""  # bpmn, camunda, spring_statemachine, xstate, custom, ngrx, enum_based
    states: list[str] = field(default_factory=list)
    transitions: list[dict] = field(default_factory=list)  # [{from, to, trigger}]
    actions: list[str] = field(default_factory=list)
    container_hint: str = ""
    file_path: str = ""

    @property
    def fact_type(self) -> str:
        return FactType.WORKFLOW if hasattr(FactType, "WORKFLOW") else "workflow"


class WorkflowCollector(DimensionCollector):
    """
    Thin router that delegates workflow collection to ecosystem specialists.

    Handles BPMN parsing directly (cross-cutting concern), then delegates
    language-specific workflow detection to the appropriate ecosystem.
    """

    DIMENSION = "workflows"

    # Skip directories
    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # === BPMN Patterns ===
    BPMN_EXTENSIONS = ["*.bpmn", "*.bpmn20.xml", "*.bpmn2"]

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._workflows: dict[str, RawWorkflow] = {}
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect all workflow facts via BPMN parsing and ecosystem delegation."""
        self._log_start()

        # 1. BPMN files (cross-cutting, not ecosystem-specific)
        self._collect_bpmn_workflows()

        # 2. Delegate to ecosystem specialists
        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        # 3. Add BPMN workflows to output
        for workflow in self._workflows.values():
            self.output.add_fact(workflow)

        self._log_end()
        return self.output

    # =========================================================================
    # BPMN Collection (cross-cutting)
    # =========================================================================

    def _collect_bpmn_workflows(self):
        """Parse BPMN files for process definitions."""
        for ext in self.BPMN_EXTENSIONS:
            for bpmn_file in self._find_files(ext):
                self._parse_bpmn_file(bpmn_file)

    def _parse_bpmn_file(self, file_path: Path):
        """Parse a BPMN XML file."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Handle namespaces
            ns = {
                "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
                "bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL",
                "camunda": "http://camunda.org/schema/1.0/bpmn",
            }

            # Find process definitions
            processes = root.findall(".//bpmn:process", ns) or root.findall(".//bpmn2:process", ns)
            if not processes:
                # Try without namespace
                processes = root.findall(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}process")

            for process in processes:
                process_id = process.get("id", file_path.stem)
                process_name = process.get("name", process_id)

                # Extract tasks/states
                states = []
                for elem_type in [
                    "userTask",
                    "serviceTask",
                    "scriptTask",
                    "manualTask",
                    "businessRuleTask",
                    "startEvent",
                    "endEvent",
                ]:
                    for elem in process.findall(f".//{{{ns.get('bpmn', '')}}}" + elem_type) or []:
                        state_name = elem.get("name") or elem.get("id")
                        if state_name:
                            states.append(state_name)

                # Extract sequence flows (transitions)
                transitions = []
                for flow in process.findall(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}sequenceFlow") or []:
                    transitions.append(
                        {
                            "from": flow.get("sourceRef", ""),
                            "to": flow.get("targetRef", ""),
                            "trigger": flow.get("name", ""),
                        }
                    )

                workflow = RawWorkflow(
                    name=process_name,
                    workflow_type="bpmn",
                    states=states,
                    transitions=transitions,
                    container_hint=self.container_id,
                    file_path=self._relative_path(file_path),
                )
                workflow.add_evidence(
                    path=self._relative_path(file_path),
                    line_start=1,
                    line_end=10,
                    reason=f"BPMN Process: {process_name}",
                )

                self._workflows[f"bpmn_{process_id}"] = workflow
                logger.debug(f"[WorkflowCollector] Found BPMN: {process_name} ({len(states)} tasks)")

        except ET.ParseError as e:
            logger.warning(f"[WorkflowCollector] Failed to parse BPMN {file_path}: {e}")
        except Exception as e:
            logger.warning(f"[WorkflowCollector] Error processing BPMN {file_path}: {e}")
