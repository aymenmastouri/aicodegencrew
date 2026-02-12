"""
Upgrade Rules Engine.

Orchestrates: detect framework -> select rules -> scan code -> assess impact.
Duration: 3-8 seconds (deterministic).
"""

import re
from typing import Any

from ....shared.utils.logger import setup_logger
from .base import UpgradeImpact, UpgradeRuleSet, UpgradeSeverity
from .scanner import UpgradeCodeScanner

logger = setup_logger(__name__)

_RULE_REGISTRY: dict[str, list] = {}


def register_rules(framework: str, rule_sets: list):
    """Register upgrade rule sets for a framework."""
    _RULE_REGISTRY[framework.lower()] = rule_sets


class UpgradeRulesEngine:
    """Generic upgrade rules engine."""

    def __init__(self, facts: dict, repo_path: str = None):
        self.facts = facts
        self.repo_path = repo_path

        # Auto-register all framework rules on first use
        self._auto_register_rules()

    def detect_upgrade_context(
        self,
        task_description: str,
        task_labels: list[str],
    ) -> dict[str, Any] | None:
        """
        Detect upgrade context (framework + versions).

        Called only when stage1 already classified task_type="upgrade".
        Returns None if framework cannot be identified (no rules to apply).
        Returns dict with framework, current_version, target_version.
        """
        text = f"{task_description} {' '.join(task_labels)}".lower()

        # Must detect a specific framework - otherwise no rules to apply
        framework = self._detect_framework(text)
        if not framework:
            logger.info("[UpgradeEngine] No framework detected, skipping upgrade rules")
            return None

        # Must have registered rules for this framework
        if framework.lower() not in _RULE_REGISTRY:
            logger.info(f"[UpgradeEngine] No rules registered for {framework}")
            return None

        current_version = self._detect_current_version(framework)
        target_version = self._detect_target_version(text)

        logger.info(f"[UpgradeEngine] Detected: {framework} {current_version} -> {target_version}")

        return {
            "framework": framework,
            "current_version": current_version,
            "target_version": target_version,
            "is_upgrade": True,
        }

    def get_applicable_rules(
        self,
        framework: str,
        current_version: str,
        target_version: str,
    ) -> list[UpgradeRuleSet]:
        """Get rule sets applicable for version range."""
        all_rules = _RULE_REGISTRY.get(framework.lower(), [])

        applicable = []
        for rule_set in all_rules:
            if self._version_in_range(
                rule_set.from_version,
                rule_set.to_version,
                current_version,
                target_version,
            ):
                applicable.append(rule_set)

        logger.info(
            f"[UpgradeEngine] {len(applicable)} rule sets applicable "
            f"for {framework} {current_version}->{target_version}"
        )
        return applicable

    def scan_and_assess(self, rule_sets: list[UpgradeRuleSet]) -> dict[str, Any]:
        """Scan codebase and produce impact assessment."""
        if not self.repo_path:
            logger.warning("[UpgradeEngine] No repo_path, returning rules without scan")
            return self._rules_only_assessment(rule_sets)

        frontend_root = self._find_frontend_root()
        scanner = UpgradeCodeScanner(
            repo_path=self.repo_path,
            frontend_root=frontend_root,
        )

        all_impacts = []
        for rule_set in rule_sets:
            impacts = scanner.scan_rules(rule_set)
            all_impacts.extend(impacts)

        # Filter rules with 0 occurrences
        active = [i for i in all_impacts if i.occurrences > 0]

        # Sort: breaking first, then by occurrence count
        severity_order = {
            UpgradeSeverity.BREAKING: 0,
            UpgradeSeverity.DEPRECATED: 1,
            UpgradeSeverity.RECOMMENDED: 2,
            UpgradeSeverity.OPTIONAL: 3,
        }
        active.sort(key=lambda i: (severity_order.get(i.rule.severity, 9), -i.occurrences))

        total_effort = sum(i.estimated_effort_minutes for i in active)
        total_files = len(set(f for i in active for f in i.affected_files))

        logger.info(
            f"[UpgradeEngine] Assessment: {len(active)} rules triggered, "
            f"{total_files} files, ~{round(total_effort / 60, 1)}h effort"
        )

        return {
            "is_upgrade": True,
            "impacts": [self._impact_to_dict(i) for i in active],
            "summary": {
                "total_rules_triggered": len(active),
                "total_occurrences": sum(i.occurrences for i in active),
                "total_affected_files": total_files,
                "estimated_effort_minutes": total_effort,
                "estimated_effort_hours": round(total_effort / 60, 1),
                "breaking_changes": len([i for i in active if i.rule.severity == UpgradeSeverity.BREAKING]),
                "deprecated_apis": len([i for i in active if i.rule.severity == UpgradeSeverity.DEPRECATED]),
            },
            "migration_sequence": [
                {
                    "step": idx + 1,
                    "rule_id": i.rule.id,
                    "title": i.rule.title,
                    "severity": i.rule.severity.value,
                    "occurrences": i.occurrences,
                    "affected_files": i.affected_files[:20],  # Limit to first 20 files
                    "estimated_effort_minutes": i.estimated_effort_minutes,
                    "migration_steps": i.rule.migration_steps,
                    "schematic": i.rule.schematic,
                }
                for idx, i in enumerate(active)
            ],
            "verification_commands": list(set(cmd for rs in rule_sets for cmd in rs.verification_commands)),
        }

    # -- Private helpers --

    @staticmethod
    def _auto_register_rules():
        """Auto-register all framework rules (lazy, once per process)."""
        if not _RULE_REGISTRY:
            from .angular import ANGULAR_UPGRADE_RULES
            from .java import JAVA_UPGRADE_RULES
            from .playwright import PLAYWRIGHT_UPGRADE_RULES
            from .spring import SPRING_UPGRADE_RULES

            register_rules("angular", ANGULAR_UPGRADE_RULES)
            register_rules("spring", SPRING_UPGRADE_RULES)
            register_rules("java", JAVA_UPGRADE_RULES)
            register_rules("playwright", PLAYWRIGHT_UPGRADE_RULES)

            logger.info(
                f"[UpgradeEngine] Registered {len(_RULE_REGISTRY)} frameworks: {', '.join(_RULE_REGISTRY.keys())}"
            )

    def _impact_to_dict(self, impact: UpgradeImpact) -> dict:
        return {
            "rule_id": impact.rule.id,
            "title": impact.rule.title,
            "description": impact.rule.description,
            "severity": impact.rule.severity.value,
            "category": impact.rule.category.value,
            "occurrences": impact.occurrences,
            "affected_files": impact.affected_files[:20],
            "estimated_effort_minutes": impact.estimated_effort_minutes,
            "migration_steps": impact.rule.migration_steps,
            "schematic": impact.rule.schematic,
        }

    def _detect_framework(self, text: str) -> str | None:
        """Detect framework from task text. Returns registered framework name or None."""
        framework_keywords = {
            "angular": ["angular", "ng update", "ng-", "@angular"],
            "spring": ["spring boot", "spring framework", "spring-boot", "spring security"],
            "java": ["java version", "java 17", "java 21", "java 25", "jdk", "openjdk"],
            "playwright": ["playwright", "@playwright", "e2e upgrade", "playwright-bdd"],
            "react": ["react", "react.js", "reactjs", "next.js"],
            "vue": ["vue", "vue.js", "vuejs", "nuxt"],
        }
        for framework, keywords in framework_keywords.items():
            if any(kw in text for kw in keywords):
                return framework

        # Fallback: check containers from architecture facts
        for container in self.facts.get("containers", []):
            tech = (container.get("technology") or "").lower()
            for framework, keywords in framework_keywords.items():
                if any(kw in tech for kw in keywords):
                    return framework
        return None

    def _detect_current_version(self, framework: str) -> str:
        # Strategy 1: Check container.version (primary)
        for container in self.facts.get("containers", []):
            tech = (container.get("technology") or "").lower()
            if framework.lower() in tech:
                version = container.get("version", "")
                if version:
                    return version.split(".")[0]

        # Strategy 2: Fallback to tech_versions
        for tech_ver in self.facts.get("tech_versions", []):
            tech_name = (tech_ver.get("technology") or "").lower()
            if framework.lower() == tech_name:
                version = tech_ver.get("version", "")
                if version:
                    return version.split(".")[0]  # Return major version

        return "unknown"

    def _detect_target_version(self, text: str) -> str:
        patterns = [
            r"(?:to|auf|target|upgrade to|migrate to)\s+v?(\d+)",
            r"version\s+(\d+)",
            r"v(\d+)",
        ]
        versions = []
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                versions.append(match.group(1))
        if versions:
            return max(versions, key=int)
        return "latest"

    def _find_frontend_root(self) -> str:
        for container in self.facts.get("containers", []):
            tech = (container.get("technology") or "").lower()
            if "angular" in tech:
                return container.get("root_path", "frontend")
        return "frontend"

    @staticmethod
    def _version_in_range(
        rule_from: str,
        rule_to: str,
        current: str,
        target: str,
    ) -> bool:
        try:
            rf = int(rule_from)
            int(rule_to)
            cv = int(current.split(".")[0]) if current != "unknown" else 0
            tv = int(target.split(".")[0]) if target not in ("unknown", "latest") else 999
            return rf >= cv and rf <= tv
        except (ValueError, IndexError):
            return True

    def _rules_only_assessment(self, rule_sets: list[UpgradeRuleSet]) -> dict:
        all_rules = [r for rs in rule_sets for r in rs.rules]
        return {
            "is_upgrade": True,
            "impacts": [],
            "summary": {
                "total_rules": len(all_rules),
                "note": "No code scanning (repo_path not available)",
            },
            "migration_sequence": [
                {
                    "step": idx + 1,
                    "rule_id": r.id,
                    "title": r.title,
                    "severity": r.severity.value,
                    "steps": r.migration_steps,
                    "schematic": r.schematic,
                }
                for idx, r in enumerate(all_rules)
            ],
            "verification_commands": list(set(cmd for rs in rule_sets for cmd in rs.verification_commands)),
        }
