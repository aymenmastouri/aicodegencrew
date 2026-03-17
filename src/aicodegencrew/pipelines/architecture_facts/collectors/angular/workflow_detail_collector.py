"""Angular Workflow Detail Specialist — Extracts TypeScript workflow and state machine facts.

Detects:
- XState (createMachine, useMachine)
- NgRx Effects/Reducers
- RxJS Flow Patterns (complex pipe chains)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..workflow_collector import RawWorkflow


class AngularWorkflowDetailCollector(DimensionCollector):
    """Extracts TypeScript/Angular workflow facts."""

    DIMENSION = "workflows"

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
        """Collect TypeScript-based workflows (XState, NgRx, RxJS)."""
        self._log_start()

        ts_files = [f for f in self._find_files("*.ts") if ".spec." not in str(f)]

        logger.info(f"[AngularWorkflowDetailCollector] Scanning {len(ts_files)} TypeScript files for workflows")

        for ts_file in ts_files:
            content = self._read_file_content(ts_file)
            if not content:
                continue

            self._check_xstate(ts_file, content)
            self._check_ngrx(ts_file, content)
            self._check_rxjs_flows(ts_file, content)

        # Add all to output
        for workflow in self._workflows.values():
            self.output.add_fact(workflow)

        self._log_end()
        return self.output

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
        logger.debug(f"[AngularWorkflowDetailCollector] Found XState: {machine_name} ({len(states)} states)")

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
        logger.debug(f"[AngularWorkflowDetailCollector] Found NgRx: {name} ({len(actions)} actions)")

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
        logger.debug(f"[AngularWorkflowDetailCollector] Found RxJS Flow: {name}")
