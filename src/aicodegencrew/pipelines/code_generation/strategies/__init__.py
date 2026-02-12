"""Code generation strategies per task type."""

from .base import BaseStrategy
from .bugfix_strategy import BugfixStrategy
from .feature_strategy import FeatureStrategy
from .refactoring_strategy import RefactoringStrategy
from .upgrade_strategy import UpgradeStrategy

STRATEGY_MAP = {
    "upgrade": UpgradeStrategy,
    "feature": FeatureStrategy,
    "bugfix": BugfixStrategy,
    "refactoring": RefactoringStrategy,
}

__all__ = [
    "STRATEGY_MAP",
    "BaseStrategy",
    "BugfixStrategy",
    "FeatureStrategy",
    "RefactoringStrategy",
    "UpgradeStrategy",
]
