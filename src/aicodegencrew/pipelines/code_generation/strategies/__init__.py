"""Code generation strategies per task type."""

from .base import BaseStrategy
from .upgrade_strategy import UpgradeStrategy
from .feature_strategy import FeatureStrategy
from .bugfix_strategy import BugfixStrategy
from .refactoring_strategy import RefactoringStrategy

STRATEGY_MAP = {
    "upgrade": UpgradeStrategy,
    "feature": FeatureStrategy,
    "bugfix": BugfixStrategy,
    "refactoring": RefactoringStrategy,
}

__all__ = [
    "BaseStrategy",
    "UpgradeStrategy",
    "FeatureStrategy",
    "BugfixStrategy",
    "RefactoringStrategy",
    "STRATEGY_MAP",
]
