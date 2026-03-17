"""C/C++ Workflow Specialist — Extracts C/C++ workflow and state machine facts.

Detects:
- Enum-based finite state machines (enum class State/Status)
- Switch/case on state variables
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..workflow_collector import RawWorkflow


class CppWorkflowCollector(DimensionCollector):
    """Extracts C/C++ workflow and state machine facts."""

    DIMENSION = "workflows"

    # C/C++ FSM patterns
    CPP_ENUM_STATE_PATTERN = re.compile(r"enum\s+(?:class\s+)?(\w*(?:State|Status)\w*)\s*\{", re.IGNORECASE)
    ENUM_VALUES_PATTERN = re.compile(r"^\s*([A-Z][A-Z0-9_]+)(?:\s*\(|\s*,|\s*;|\s*$)", re.MULTILINE)

    # Switch on action/state
    SWITCH_PATTERN = re.compile(r"switch\s*\(\s*(\w*(?:action|state|status|type)\w*)\s*\)", re.IGNORECASE)
    CASE_PATTERN = re.compile(r"case\s+(?:\w+\.)?([A-Z][A-Z0-9_]+)\s*:", re.MULTILINE)

    def __init__(self, repo_path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._workflows: dict[str, RawWorkflow] = {}

    def collect(self) -> CollectorOutput:
        """Collect C/C++ workflows: Enum-based FSMs, switch/case on state variables."""
        self._log_start()

        cpp_files = []
        for pattern in ["*.cpp", "*.cc", "*.cxx", "*.hpp", "*.h"]:
            cpp_files.extend(self._find_files(pattern))

        for cpp_file in cpp_files:
            content = self._read_file_content(cpp_file)
            if not content:
                continue

            rel_path = self._relative_path(cpp_file)

            # Enum-based state machines
            for match in self.CPP_ENUM_STATE_PATTERN.finditer(content):
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
                states = self.ENUM_VALUES_PATTERN.findall(enum_body)
                states = [s for s in states if s not in ("INSTANCE", "LOG", "LOGGER")]

                if len(states) < 2:
                    continue

                workflow = RawWorkflow(
                    name=enum_name,
                    workflow_type="enum_based",
                    states=states,
                    container_hint=self.container_id,
                    file_path=rel_path,
                )
                line_num = content[: match.start()].count("\n") + 1
                workflow.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + len(states) + 5,
                    reason=f"C/C++ State Enum: {enum_name} ({len(states)} states)",
                )
                self._workflows[f"cpp_enum_{enum_name}"] = workflow

            # Switch on state variable
            for switch_match in self.SWITCH_PATTERN.finditer(content):
                switch_var = switch_match.group(1).lower()
                if "state" not in switch_var and "status" not in switch_var:
                    continue

                # Get class name context
                class_match = re.search(r"class\s+(\w+)", content[:switch_match.start()])
                class_name = class_match.group(1) if class_match else cpp_file.stem

                if any(class_name in key for key in self._workflows):
                    continue

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
                states = list(set(self.CASE_PATTERN.findall(switch_block)))

                if len(states) < 2:
                    continue

                workflow = RawWorkflow(
                    name=class_name,
                    workflow_type="custom",
                    states=states,
                    container_hint=self.container_id,
                    file_path=rel_path,
                )
                line_num = content[: switch_match.start()].count("\n") + 1
                workflow.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 20,
                    reason=f"C/C++ FSM: {class_name} ({len(states)} states)",
                )
                self._workflows[f"cpp_fsm_{class_name}"] = workflow

        # Add all to output
        for workflow in self._workflows.values():
            self.output.add_fact(workflow)

        self._log_end()
        return self.output
