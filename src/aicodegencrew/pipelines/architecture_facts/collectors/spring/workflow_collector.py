"""Spring Workflow Specialist — Extracts Java/Spring workflow and state machine facts.

Detects:
- Spring State Machine (@EnableStateMachine)
- Camunda/Flowable (@ProcessEngine, @Deployment)
- Custom StateMachines (*StateMachine.java with switch logic)
- Status/State Enums (Enum*Status, Enum*State)
- Business Flow Services (*WorkflowService, *ProcessService)
- Service Orchestration (Saga, Pipeline, Chain patterns)
- Action Dispatch patterns
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..workflow_collector import RawWorkflow


class SpringWorkflowCollector(DimensionCollector):
    """Extracts Java/Spring workflow and state machine facts."""

    DIMENSION = "workflows"

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

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._workflows: dict[str, RawWorkflow] = {}

    def collect(self) -> CollectorOutput:
        """Collect Java-based workflows and state machines."""
        self._log_start()

        java_files = self._find_files("*.java")

        logger.info(f"[SpringWorkflowCollector] Scanning {len(java_files)} Java files for workflows")

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

        # Add all to output
        for workflow in self._workflows.values():
            self.output.add_fact(workflow)

        self._log_end()
        return self.output

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
        logger.debug(f"[SpringWorkflowCollector] Found Spring StateMachine: {class_name}")

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
        logger.debug(f"[SpringWorkflowCollector] Found {workflow_type.title()}: {class_name}")

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
            f"[SpringWorkflowCollector] Found Custom StateMachine: {class_name} ({len(states)} states, {len(actions)} actions)"
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
            logger.debug(f"[SpringWorkflowCollector] Found Status Enum: {enum_name} ({len(states)} states)")

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

        # Also look for common workflow method names (Java method signature)
        for pattern in [r"(?:public|protected|private)\s+\w+\s+(approve|reject|submit|cancel|complete|start|pause|resume)\s*\("]:
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
        logger.debug(f"[SpringWorkflowCollector] Found Workflow Service: {class_name} ({len(actions)} actions)")

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
        logger.debug(f"[SpringWorkflowCollector] Found Orchestration: {class_name} ({len(service_calls)} calls)")

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
        logger.debug(f"[SpringWorkflowCollector] Found Action Dispatcher: {class_name}")
