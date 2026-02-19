"""Dependency checker — extracted from SDLCOrchestrator._check_dependencies.

Separation of concerns: pure logic class that checks whether a phase's
dependencies are satisfied by prior results or disk artifacts.
Observational ARCH-5 contract violations are logged here (never a hard block).
"""

from pathlib import Path
from typing import Any

from .utils.logger import logger


class DependencyChecker:
    """
    Checks whether a phase's runtime dependencies are satisfied.

    Extracted from SDLCOrchestrator._check_dependencies (ARCH-5).
    Pure logic — no orchestrator state access.

    Usage::

        checker = DependencyChecker(contract, orchestrator.results)
        if not checker.check("plan"):
            # dependencies not met
    """

    # Phase contracts: declared requirements.
    # Used for observational contract violation warnings only — not a hard gate;
    # the actual blocking is handled by get_dependencies() on the contract object.
    PHASE_CONTRACTS: dict[str, dict] = {
        "discover":  {"requires": [],            "provides": ["discover"]},
        "extract":   {"requires": ["discover"],  "provides": ["extract"]},
        "analyze":   {"requires": ["extract"],   "provides": ["analyze"]},
        "document":  {"requires": ["analyze"],   "provides": ["document"]},
        "plan":      {"requires": ["extract"],   "provides": ["plan"]},
        "implement": {"requires": ["plan"],      "provides": ["implement"]},
        "verify":    {"requires": ["implement"], "provides": ["verify"]},
        "deliver":   {"requires": ["implement"], "provides": ["deliver"]},
    }

    def __init__(
        self,
        contract: Any,           # PipelineContract — get_dependencies(phase_id) -> list[str]
        results: dict[str, Any], # dict[phase_id, PhaseResult-like] — .is_success() -> bool
    ) -> None:
        self._contract = contract
        self._results = results

    def check(self, phase_id: str) -> bool:
        """Return True if all dependencies satisfied; log ARCH-5 contract violations.

        Two-tier check:
        1. Did the dependency succeed in *this* run (results dict)?
        2. Do its output files exist on disk from a *previous* run?

        Contract violations (ARCH-5) are logged as warnings but never block execution.
        """
        from ..phase_registry import outputs_exist
        from .validation import PhaseOutputValidator

        dependencies = self._contract.get_dependencies(phase_id)
        validator = PhaseOutputValidator()

        for dep in dependencies:
            # Tier 1: succeeded in this session
            result = self._results.get(dep)
            if result is not None and result.is_success():
                continue

            # Tier 2: output files exist from a previous run (CWD-relative)
            if outputs_exist(dep, Path(".")):
                errors = validator.validate_phase(dep)
                if errors:
                    logger.warning("[DependencyChecker] Dependency %s has validation warnings:", dep)
                    for err in errors[:5]:
                        logger.warning("   - %s", err)
                else:
                    logger.info("[DependencyChecker] Dependency %s satisfied (output valid)", dep)
                continue

            logger.error(
                "[DependencyChecker] Dependency not met: %s requires %s",
                phase_id, dep,
            )
            return False

        # ARCH-5: Log contract violations (observational — not a hard block)
        contract_def = self.PHASE_CONTRACTS.get(phase_id, {})
        for required in contract_def.get("requires", []):
            if required not in self._results and not outputs_exist(required, Path(".")):
                logger.warning(
                    "[DependencyChecker] Contract violation: %s requires '%s' output but it is absent",
                    phase_id, required,
                )

        return True
