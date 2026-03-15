"""Upgrade Rules Engine for Development Planning Pipeline."""

from .angular import ANGULAR_UPGRADE_RULES
from .base import CodePattern, UpgradeImpact, UpgradeRule, UpgradeRuleSet
from .engine import UpgradeRulesEngine
from .java import JAVA_UPGRADE_RULES
from .playwright import PLAYWRIGHT_UPGRADE_RULES
from .spring import SPRING_UPGRADE_RULES

__all__ = [
    "ANGULAR_UPGRADE_RULES",
    "JAVA_UPGRADE_RULES",
    "PLAYWRIGHT_UPGRADE_RULES",
    "SPRING_UPGRADE_RULES",
    "CodePattern",
    "UpgradeImpact",
    "UpgradeRule",
    "UpgradeRuleSet",
    "UpgradeRulesEngine",
]
