"""Task-type strategies for pipeline behavior customization."""

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

# Import strategies to trigger @register_strategy decorators
from . import upgrade_strategy  # noqa: F401

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
