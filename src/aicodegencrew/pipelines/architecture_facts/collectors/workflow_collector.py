"""
WorkflowCollector - Extracts workflow, state machine, and business flow facts.

Detects:
1. BPMN Workflows (*.bpmn, *.bpmn20.xml)
2. Camunda/Flowable (@ProcessEngine, @Deployment)
3. Spring State Machine (@EnableStateMachine)
4. XState (createMachine, useMachine)
5. Custom StateMachines (*StateMachine.java with switch logic)
6. Status/State Enums (Enum*Status, Enum*State)
7. Business Flow Services (*WorkflowService, *ProcessService)
8. NgRx Effects/Reducers
9. RxJS Flow Patterns

Output -> workflows.json
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

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
    Collects workflow and state machine facts from multiple sources.
    """

    DIMENSION = "workflows"

    # Skip directories
    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # === BPMN Patterns ===
    BPMN_EXTENSIONS = ["*.bpmn", "*.bpmn20.xml", "*.bpmn2"]

    # === Java/Spring Patterns ===
    STATEMACHINE_CLASS_PATTERN = re.compile(r"class\s+(\w*StateMachine\w*)", re.IGNORECASE)
    STATUS_ENUM_PATTERN = re.compile(
        r"enum\s+(Enum\w*(?:Status|State)\w*|(?:Status|State)\w*Enum|\w+Status|\w+State)\s*\{", re.IGNORECASE
    )
    ENUM_VALUES_PATTERN = re.compile(r"^\s*([A-Z][A-Z0-9_]+)(?:\s*\(|\s*,|\s*;|\s*$)", re.MULTILINE)

    # Spring State Machine
    SPRING_STATEMACHINE_PATTERN = re.compile(r"@EnableStateMachine|StateMachineConfig|StateMachineBuilder")

    # Camunda/Flowable
    CAMUNDA_PATTERN = re.compile(r"@ProcessEngine|@Deployment|ProcessEngineConfiguration|RuntimeService|TaskService")
    FLOWABLE_PATTERN = re.compile(r"org\.flowable\.|FlowableEngine|ProcessEngine")

    # Workflow/Process Services
    WORKFLOW_SERVICE_PATTERN = re.compile(
        r"class\s+(\w*(?:Workflow|Process|Flow|Orchestrat)(?:Service|Handler|Manager|Executor|or)\w*)"
    )

    # Service orchestration patterns
    ORCHESTRATION_PATTERN = re.compile(
        r"class\s+(\w*(?:Orchestrat|Coordinat|Saga|Pipeline|Chain)(?:or|ion|Service|Handler)\w*)"
    )

    # Transition methods
    TRANSITION_METHOD_PATTERN = re.compile(
        r"(?:public|private|protected)\s+\w+\s+(transition|handle|change|update|set|move)(\w*Status|\w*State)\s*\(",
        re.IGNORECASE,
    )

    # Action dispatch patterns
    ACTION_DISPATCH_PATTERN = re.compile(
        r"(?:dispatch|execute|perform|process|handle)(?:Action|Command|Event)\s*\([^)]*(\w+Action|\w+Command)[^)]*\)",
        re.IGNORECASE,
    )

    # Switch on action/state
    SWITCH_PATTERN = re.compile(r"switch\s*\(\s*(\w*(?:action|state|status|type)\w*)\s*\)", re.IGNORECASE)
    CASE_PATTERN = re.compile(r"case\s+(?:\w+\.)?([A-Z][A-Z0-9_]+)\s*:", re.MULTILINE)

    # Chain/Pipeline patterns
    CHAIN_PATTERN = re.compile(r"\.(?:then|andThen|chain|pipe|next)\s*\(", re.IGNORECASE)

    # === TypeScript/Angular Patterns ===
    XSTATE_PATTERN = re.compile(r"createMachine|useMachine|interpret\s*\(|Machine\s*\(")
    XSTATE_STATE_PATTERN = re.compile(r"states\s*:\s*\{([^}]+)\}")

    # NgRx
    NGRX_EFFECT_PATTERN = re.compile(r"createEffect|@Effect|ofType\s*\(")
    NGRX_REDUCER_PATTERN = re.compile(r"createReducer|on\s*\(\s*\w+Actions\.")
    NGRX_ACTION_PATTERN = re.compile(r'createAction\s*\(\s*[\'"]([^\'"]+)[\'"]')

    # RxJS Flow patterns
    RXJS_FLOW_PATTERN = re.compile(r"\.pipe\s*\([^)]*(?:switchMap|mergeMap|concatMap|exhaustMap)[^)]*\)")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._workflows: dict[str, RawWorkflow] = {}

    def collect(self) -> CollectorOutput:
        """Collect all workflow facts."""
        self._log_start()

        # 1. BPMN files
        self._collect_bpmn_workflows()

        # 2. Java/Spring workflows
        self._collect_java_workflows()

        # 3. TypeScript/Angular workflows
        self._collect_typescript_workflows()

        # Add all to output
        for workflow in self._workflows.values():
            self.output.add_fact(workflow)

        self._log_end()
        return self.output

    # =========================================================================
    # BPMN Collection
    # =========================================================================

    def _collect_bpmn_workflows(self):
        """Parse BPMN files for process definitions."""
        for ext in self.BPMN_EXTENSIONS:
            for bpmn_file in self.repo_path.rglob(ext):
                if self._should_skip(bpmn_file):
                    continue
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

    # =========================================================================
    # Java/Spring Collection
    # =========================================================================

    def _collect_java_workflows(self):
        """Collect Java-based workflows and state machines."""
        java_files = self._find_files("*.java")

        logger.info(f"[WorkflowCollector] Scanning {len(java_files)} Java files for workflows")

        for java_file in java_files:
            content = self._read_file_content(java_file)
            if not content:
                continue

            # Check for different workflow types
            self._check_spring_statemachine(java_file, content)
            self._check_camunda_flowable(java_file, content)
            self._check_custom_statemachine(java_file, content)
            self._check_status_enum(java_file, content)
            self._check_workflow_service(java_file, content)
            self._check_service_orchestration(java_file, content)
            self._check_action_dispatch(java_file, content)

    def _check_spring_statemachine(self, file_path: Path, content: str):
        """Check for Spring State Machine."""
        if not self.SPRING_STATEMACHINE_PATTERN.search(content):
            return

        class_match = re.search(r"class\s+(\w+)", content)
        class_name = class_match.group(1) if class_match else file_path.stem

        # Extract states from builder
        states = []
        state_match = re.search(r"\.states\(\)\s*\.(?:initial|state|end)\((\w+\.\w+)\)", content)
        if state_match:
            states.append(state_match.group(1))

        # Find all enum references that look like states
        for match in re.finditer(r"States\.(\w+)|(\w+State)\.\w+", content):
            state = match.group(1) or match.group(2)
            if state and state not in states:
                states.append(state)

        workflow = RawWorkflow(
            name=class_name,
            workflow_type="spring_statemachine",
            states=states,
            container_hint=self.container_id,
            file_path=self._relative_path(file_path),
        )
        workflow.add_evidence(
            path=self._relative_path(file_path), line_start=1, line_end=50, reason=f"Spring State Machine: {class_name}"
        )

        self._workflows[f"spring_sm_{class_name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found Spring StateMachine: {class_name}")

    def _check_camunda_flowable(self, file_path: Path, content: str):
        """Check for Camunda or Flowable usage."""
        is_camunda = self.CAMUNDA_PATTERN.search(content)
        is_flowable = self.FLOWABLE_PATTERN.search(content)

        if not (is_camunda or is_flowable):
            return

        class_match = re.search(r"class\s+(\w+)", content)
        class_name = class_match.group(1) if class_match else file_path.stem

        workflow_type = "camunda" if is_camunda else "flowable"

        workflow = RawWorkflow(
            name=class_name,
            workflow_type=workflow_type,
            container_hint=self.container_id,
            file_path=self._relative_path(file_path),
        )
        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=1,
            line_end=30,
            reason=f"{workflow_type.title()} integration: {class_name}",
        )

        self._workflows[f"{workflow_type}_{class_name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found {workflow_type.title()}: {class_name}")

    def _check_custom_statemachine(self, file_path: Path, content: str):
        """Check for custom state machine implementations."""
        # Look for *StateMachine classes
        class_match = self.STATEMACHINE_CLASS_PATTERN.search(content)
        if not class_match:
            return

        class_name = class_match.group(1)

        # Extract states from switch statements
        states = set()
        actions = set()

        # Find switch on action/state
        for switch_match in self.SWITCH_PATTERN.finditer(content):
            switch_var = switch_match.group(1).lower()

            # Get the switch block
            switch_start = switch_match.end()
            brace_count = 0
            switch_end = switch_start
            for i, char in enumerate(content[switch_start:], switch_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        switch_end = i
                        break

            switch_block = content[switch_start:switch_end]

            # Extract case values
            for case_match in self.CASE_PATTERN.finditer(switch_block):
                case_value = case_match.group(1)
                if "action" in switch_var:
                    actions.add(case_value)
                else:
                    states.add(case_value)

        # Also look for enum references in the file
        for enum_ref in re.finditer(r"Enum\w*(?:Status|State)\.(\w+)", content):
            states.add(enum_ref.group(1))

        workflow = RawWorkflow(
            name=class_name,
            workflow_type="custom",
            states=list(states),
            actions=list(actions),
            container_hint=self.container_id,
            file_path=self._relative_path(file_path),
        )

        line_num = content[: class_match.start()].count("\n") + 1
        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=line_num,
            line_end=line_num + 100,
            reason=f"Custom StateMachine: {class_name}",
        )

        self._workflows[f"custom_sm_{class_name}"] = workflow
        logger.debug(
            f"[WorkflowCollector] Found Custom StateMachine: {class_name} ({len(states)} states, {len(actions)} actions)"
        )

    def _check_status_enum(self, file_path: Path, content: str):
        """Check for status/state enums that define workflow states."""
        for match in self.STATUS_ENUM_PATTERN.finditer(content):
            enum_name = match.group(1)

            # Get enum body
            enum_start = match.end()
            brace_count = 1
            enum_end = enum_start
            for i, char in enumerate(content[enum_start:], enum_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        enum_end = i
                        break

            enum_body = content[enum_start:enum_end]

            # Extract enum values
            states = []
            for value_match in self.ENUM_VALUES_PATTERN.finditer(enum_body):
                value = value_match.group(1)
                if value not in ("INSTANCE", "LOG", "LOGGER"):  # Skip common non-state fields
                    states.append(value)

            if len(states) < 2:  # Need at least 2 states to be interesting
                continue

            workflow = RawWorkflow(
                name=enum_name,
                workflow_type="enum_based",
                states=states,
                container_hint=self.container_id,
                file_path=self._relative_path(file_path),
            )

            line_num = content[: match.start()].count("\n") + 1
            workflow.add_evidence(
                path=self._relative_path(file_path),
                line_start=line_num,
                line_end=line_num + len(states) + 5,
                reason=f"Status Enum: {enum_name} ({len(states)} states)",
            )

            self._workflows[f"enum_{enum_name}"] = workflow
            logger.debug(f"[WorkflowCollector] Found Status Enum: {enum_name} ({len(states)} states)")

    def _check_workflow_service(self, file_path: Path, content: str):
        """Check for workflow/process service classes."""
        match = self.WORKFLOW_SERVICE_PATTERN.search(content)
        if not match:
            return

        class_name = match.group(1)

        # Check if already captured as StateMachine
        if any(class_name in key for key in self._workflows):
            return

        # Find transition methods
        actions = []
        for method_match in self.TRANSITION_METHOD_PATTERN.finditer(content):
            method_name = method_match.group(1) + method_match.group(2)
            actions.append(method_name)

        # Also look for common workflow method names
        for pattern in [r"def\s+(approve|reject|submit|cancel|complete|start|pause|resume)\s*\("]:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                actions.append(m.group(1))

        workflow = RawWorkflow(
            name=class_name,
            workflow_type="business_flow",
            actions=actions,
            container_hint=self.container_id,
            file_path=self._relative_path(file_path),
        )

        line_num = content[: match.start()].count("\n") + 1
        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=line_num,
            line_end=line_num + 50,
            reason=f"Workflow Service: {class_name}",
        )

        self._workflows[f"service_{class_name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found Workflow Service: {class_name} ({len(actions)} actions)")

    def _check_service_orchestration(self, file_path: Path, content: str):
        """Check for service orchestration patterns."""
        match = self.ORCHESTRATION_PATTERN.search(content)
        if not match:
            return

        class_name = match.group(1)

        # Check if already captured
        if any(class_name in key for key in self._workflows):
            return

        # Find service calls (method calls on injected services)
        service_calls = []
        service_call_pattern = re.compile(
            r"(?:this\.)?(\w+Service|\w+Repository|\w+Client)\s*\.\s*(\w+)\s*\(", re.IGNORECASE
        )
        for m in service_call_pattern.finditer(content):
            service_calls.append(f"{m.group(1)}.{m.group(2)}")

        # Find chain/pipeline patterns
        chain_count = len(self.CHAIN_PATTERN.findall(content))

        # Detect saga pattern (compensating transactions)
        has_saga = bool(re.search(r"compensat|rollback|undo|revert", content, re.IGNORECASE))

        workflow = RawWorkflow(
            name=class_name,
            workflow_type="service_orchestration",
            actions=list(set(service_calls))[:20],  # Limit
            container_hint=self.container_id,
            file_path=self._relative_path(file_path),
        )

        workflow.metadata["chain_count"] = chain_count
        if has_saga:
            workflow.tags.append("saga")
            workflow.metadata["has_compensating_transactions"] = True

        line_num = content[: match.start()].count("\n") + 1
        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=line_num,
            line_end=line_num + 50,
            reason=f"Service Orchestration: {class_name} ({len(service_calls)} service calls)",
        )

        self._workflows[f"orchestration_{class_name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found Orchestration: {class_name} ({len(service_calls)} calls)")

    def _check_action_dispatch(self, file_path: Path, content: str):
        """Check for action/command dispatch patterns (custom workflow engine)."""
        # Look for action dispatch methods
        dispatch_matches = list(self.ACTION_DISPATCH_PATTERN.finditer(content))
        if len(dispatch_matches) < 2:  # Need multiple dispatches to be interesting
            return

        # Get class name
        class_match = re.search(r"class\s+(\w+)", content)
        if not class_match:
            return

        class_name = class_match.group(1)

        # Check if already captured
        if any(class_name in key for key in self._workflows):
            return

        # Extract action types
        actions = []
        for m in dispatch_matches:
            actions.append(m.group(1))

        # Also check for action enum/constant references
        action_ref_pattern = re.compile(r"(\w+Action|\w+Command)\.(\w+)", re.IGNORECASE)
        for m in action_ref_pattern.finditer(content):
            actions.append(f"{m.group(1)}.{m.group(2)}")

        workflow = RawWorkflow(
            name=class_name,
            workflow_type="action_dispatcher",
            actions=list(set(actions))[:20],
            container_hint=self.container_id,
            file_path=self._relative_path(file_path),
        )

        line_num = content[: class_match.start()].count("\n") + 1
        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=line_num,
            line_end=line_num + 50,
            reason=f"Action Dispatcher: {class_name} ({len(actions)} actions)",
        )

        self._workflows[f"dispatcher_{class_name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found Action Dispatcher: {class_name}")

    # =========================================================================
    # TypeScript/Angular Collection
    # =========================================================================

    def _collect_typescript_workflows(self):
        """Collect TypeScript-based workflows (XState, NgRx, RxJS)."""
        ts_files = [f for f in self._find_files("*.ts") if ".spec." not in str(f)]

        logger.info(f"[WorkflowCollector] Scanning {len(ts_files)} TypeScript files for workflows")

        for ts_file in ts_files:
            content = self._read_file_content(ts_file)
            if not content:
                continue

            self._check_xstate(ts_file, content)
            self._check_ngrx(ts_file, content)
            self._check_rxjs_flows(ts_file, content)

    def _check_xstate(self, file_path: Path, content: str):
        """Check for XState state machines."""
        if not self.XSTATE_PATTERN.search(content):
            return

        # Find machine name
        machine_match = re.search(r"(?:const|let|var)\s+(\w+)\s*=\s*createMachine", content)
        machine_name = machine_match.group(1) if machine_match else file_path.stem

        # Extract states
        states = []
        state_block_match = re.search(r"states\s*:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", content)
        if state_block_match:
            state_block = state_block_match.group(1)
            for state_match in re.finditer(r"(\w+)\s*:\s*\{", state_block):
                states.append(state_match.group(1))

        workflow = RawWorkflow(
            name=machine_name,
            workflow_type="xstate",
            states=states,
            container_hint=self.container_id or "frontend",
            file_path=self._relative_path(file_path),
        )

        line_num = content[: content.find("createMachine")].count("\n") + 1 if "createMachine" in content else 1
        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=line_num,
            line_end=line_num + 50,
            reason=f"XState Machine: {machine_name}",
        )

        self._workflows[f"xstate_{machine_name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found XState: {machine_name} ({len(states)} states)")

    def _check_ngrx(self, file_path: Path, content: str):
        """Check for NgRx effects/reducers."""
        has_effects = self.NGRX_EFFECT_PATTERN.search(content)
        has_reducer = self.NGRX_REDUCER_PATTERN.search(content)

        if not (has_effects or has_reducer):
            return

        # Determine type
        if "effects" in str(file_path).lower() or has_effects:
            workflow_type = "ngrx_effects"
        else:
            workflow_type = "ngrx_reducer"

        # Extract action names
        actions = []
        for match in self.NGRX_ACTION_PATTERN.finditer(content):
            actions.append(match.group(1))

        # Also look for ofType references
        for match in re.finditer(r"ofType\s*\(\s*(\w+Actions\.\w+)", content):
            actions.append(match.group(1))

        # Get class/const name
        name_match = re.search(r"(?:class|const)\s+(\w+)", content)
        name = name_match.group(1) if name_match else file_path.stem

        workflow = RawWorkflow(
            name=name,
            workflow_type=workflow_type,
            actions=list(set(actions)),
            container_hint=self.container_id or "frontend",
            file_path=self._relative_path(file_path),
        )

        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=1,
            line_end=50,
            reason=f"NgRx {workflow_type.replace('_', ' ').title()}: {name}",
        )

        self._workflows[f"ngrx_{name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found NgRx: {name} ({len(actions)} actions)")

    def _check_rxjs_flows(self, file_path: Path, content: str):
        """Check for complex RxJS flow patterns."""
        # Only capture if it looks like a significant flow (multiple operators)
        pipe_count = content.count(".pipe(")
        if pipe_count < 3:  # Need multiple pipes to be interesting
            return

        # Check for flow operators
        flow_operators = ["switchMap", "mergeMap", "concatMap", "exhaustMap", "flatMap"]
        operator_count = sum(content.count(op) for op in flow_operators)

        if operator_count < 2:
            return

        # Get service name
        name_match = re.search(r"class\s+(\w*(?:Service|Effects?|Handler)\w*)", content)
        if not name_match:
            return

        name = name_match.group(1)

        # Skip if already captured
        if any(name in key for key in self._workflows):
            return

        workflow = RawWorkflow(
            name=name,
            workflow_type="rxjs_flow",
            container_hint=self.container_id or "frontend",
            file_path=self._relative_path(file_path),
            metadata={"pipe_count": pipe_count, "flow_operators": operator_count},
        )

        workflow.add_evidence(
            path=self._relative_path(file_path),
            line_start=1,
            line_end=30,
            reason=f"RxJS Flow: {name} ({operator_count} flow operators)",
        )

        self._workflows[f"rxjs_{name}"] = workflow
        logger.debug(f"[WorkflowCollector] Found RxJS Flow: {name}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)

    def _read_file_content(self, file_path: Path) -> str | None:
        """Read file content safely."""
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

    def _relative_path(self, file_path: Path) -> str:
        """Get relative path from repo root."""
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
