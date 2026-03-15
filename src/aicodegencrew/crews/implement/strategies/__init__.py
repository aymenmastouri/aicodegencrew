"""Task-type strategies for pipeline behavior customization."""

# Import strategies to trigger @register_strategy decorators
from . import upgrade_strategy  # noqa: F401
from .base import (
    DefaultStrategy,
    ErrorCluster,
    PlanEnrichment,
    PreExecutionResult,
    PreExecutionStep,
    TaskTypeStrategy,
    VerificationEnrichment,
    get_strategy,
    register_strategy,
)

__all__ = [
    "DefaultStrategy",
    "ErrorCluster",
    "PlanEnrichment",
    "PreExecutionResult",
    "PreExecutionStep",
    "TaskTypeStrategy",
    "VerificationEnrichment",
    "get_strategy",
    "register_strategy",
]
