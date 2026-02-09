"""Upgrade Rules Engine for Development Planning Pipeline."""

from .engine import UpgradeRulesEngine
from .base import UpgradeRule, UpgradeRuleSet, UpgradeImpact, CodePattern
from .angular import ANGULAR_UPGRADE_RULES
from .spring import SPRING_UPGRADE_RULES
from .java import JAVA_UPGRADE_RULES
from .playwright import PLAYWRIGHT_UPGRADE_RULES

__all__ = [
    "UpgradeRulesEngine",
    "UpgradeRule",
    "UpgradeRuleSet",
    "UpgradeImpact",
    "CodePattern",
    "ANGULAR_UPGRADE_RULES",
    "SPRING_UPGRADE_RULES",
    "JAVA_UPGRADE_RULES",
    "PLAYWRIGHT_UPGRADE_RULES",
]
