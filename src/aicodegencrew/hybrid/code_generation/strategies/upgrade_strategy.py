"""Upgrade strategy: schematics, config changes, version bumps, migration tracking.

Implements all 3 pipeline hooks for task_type="upgrade":
1. enrich_plan     — dependency compatibility validation
2. pre_execute     — run schematics, apply config changes, bump versions
3. enrich_verification — error clusters + deprecation warnings + migration completeness
"""

from __future__ import annotations

import json
import os
import platform
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from ....shared.utils.logger import setup_logger
from .base import (
    PlanEnrichment,
    PreExecutionResult,
    PreExecutionStep,
    TaskTypeStrategy,
    VerificationEnrichment,
    register_strategy,
)

logger = setup_logger(__name__)

SCHEMATIC_WHITELIST = {"ng", "npx", "npm", "openrewrite"}
SCHEMATIC_TIMEOUT = 300  # seconds


@register_strategy("upgrade")
class UpgradeStrategy(TaskTypeStrategy):
    """Strategy for framework upgrade tasks.

    Handles Angular, Spring, and other framework upgrades with:
    - Dependency compatibility validation (plan enrichment)
    - Deterministic pre-execution (schematics, config changes, version bumps)
    - Rich verification (error clustering, deprecation parsing, migration completeness)
    """

    # ── Hook 1: Plan enrichment (dependency compatibility) ───────────────

    def enrich_plan(self, plan_data: dict, facts: dict) -> PlanEnrichment:
        """Validate required_dependencies against actual repo versions."""
        upgrade_plan = plan_data.get("upgrade_plan", {})
        if not upgrade_plan:
            return PlanEnrichment()

        rule_sets = self._load_rule_sets(facts, upgrade_plan)
        if not rule_sets:
            return PlanEnrichment()

        checks = self._validate_dependencies(facts, rule_sets)
        warnings = [c["message"] for c in checks if c["status"] == "conflict"]

        return PlanEnrichment(
            compatibility_checks=checks,
            warnings=warnings,
            additional_context={
                "is_feasible": not any(c["status"] == "conflict" for c in checks),
                "needs_bump_count": sum(1 for c in checks if c["status"] == "needs_bump"),
            },
        )

    def _load_rule_sets(self, facts: dict, upgrade_plan: dict) -> list:
        """Load applicable UpgradeRuleSets from the upgrade rules engine."""
        try:
            from ...development_planning.upgrade_rules import UpgradeRulesEngine

            framework = upgrade_plan.get("framework", "")
            from_version = upgrade_plan.get("from_version", "")
            to_version = upgrade_plan.get("to_version", "")

            if not all([framework, from_version, to_version]):
                return []

            engine = UpgradeRulesEngine(facts=facts)
            return engine.get_applicable_rules(framework, from_version, to_version)
        except Exception as e:
            logger.warning("[UpgradeStrategy] Failed to load rule sets: %s", e)
            return []

    def _validate_dependencies(self, facts: dict, rule_sets: list) -> list[dict]:
        """Check required_dependencies against actual versions in facts."""
        # Extract current dependency versions from architecture facts
        tech_versions = {}
        for container in facts.get("containers", []):
            metadata = container.get("metadata", {})
            for dep_name, dep_version in metadata.get("dependencies", {}).items():
                tech_versions[dep_name.lower()] = str(dep_version)

        # Also check top-level tech_versions
        for entry in facts.get("tech_versions", []):
            name = entry.get("name", "").lower()
            version = entry.get("version", "")
            if name and version:
                tech_versions[name] = str(version)

        checks: list[dict] = []
        for rule_set in rule_sets:
            required = getattr(rule_set, "required_dependencies", {}) or {}
            for dep_name, required_spec in required.items():
                current = tech_versions.get(dep_name.lower(), "")
                status, message = self._check_semver(current, required_spec)
                checks.append(
                    {
                        "name": dep_name,
                        "current_version": current or "unknown",
                        "required_spec": required_spec,
                        "status": status,
                        "message": message,
                    }
                )

        return checks

    @staticmethod
    def _check_semver(current: str, spec: str) -> tuple[str, str]:
        """Check if current version satisfies required spec.

        Returns (status, message) where status is one of:
        - "compatible": current satisfies spec
        - "needs_bump": current is below spec, bump needed
        - "conflict": versions are incompatible (major mismatch)
        - "unknown": can't determine (missing version info)
        """
        if not current:
            return "unknown", f"Current version unknown, requires {spec}"

        # Extract numeric parts from version strings
        def extract_version(v: str) -> tuple[int, ...]:
            cleaned = re.sub(r"^[~^>=<]*", "", v.strip())
            parts = re.findall(r"\d+", cleaned)
            return tuple(int(p) for p in parts) if parts else (0,)

        try:
            current_parts = extract_version(current)
            spec_parts = extract_version(spec)

            # Simple comparison: if current major matches or exceeds spec
            if current_parts >= spec_parts:
                return "compatible", f"{current} satisfies {spec}"

            # Check if it's just a minor/patch bump needed
            if current_parts[0] == spec_parts[0]:
                return "needs_bump", f"{current} → {spec} (minor/patch bump needed)"

            # Major version mismatch — incompatible, flag as conflict
            return "conflict", f"{current} → {spec} (major version conflict)"

        except (ValueError, IndexError):
            return "unknown", f"Could not parse versions: current={current}, spec={spec}"

    # ── Hook 2: Pre-execution (schematics, configs, bumps) ──────────────

    def pre_execute(
        self,
        plan: Any,
        staging: dict[str, dict],
        repo_path: str,
        dry_run: bool = False,
    ) -> PreExecutionResult:
        """Execute deterministic upgrade steps before LLM."""
        upgrade_plan = getattr(plan, "upgrade_plan", None) or {}
        if not upgrade_plan:
            return PreExecutionResult()

        steps: list[PreExecutionStep] = []
        migration_seq = upgrade_plan.get("migration_sequence", [])

        # 1. Schematics (subprocess)
        steps.extend(self._run_schematics(migration_seq, repo_path, dry_run, staging))

        # 2. Config changes (JSON edits from UpgradeRule.config_changes)
        rule_sets = self._load_rule_sets_from_plan(plan)
        steps.extend(self._apply_config_changes(rule_sets, repo_path, staging, dry_run))

        # 3. Version bumps (from required_dependencies)
        steps.extend(self._apply_version_bumps(upgrade_plan, repo_path, staging, dry_run))

        return PreExecutionResult(
            steps=steps,
            total_files_modified=sum(len(s.modified_files) for s in steps if s.success),
            errors=[s.error for s in steps if not s.success and s.error],
        )

    def _load_rule_sets_from_plan(self, plan: Any) -> list:
        """Load rule sets using plan's upgrade_plan metadata."""
        upgrade_plan = getattr(plan, "upgrade_plan", None) or {}
        facts_data: dict = {}
        # Architecture context may carry facts reference
        arch_ctx = getattr(plan, "architecture_context", {}) or {}
        facts_data = arch_ctx.get("_facts", {}) or {}

        return self._load_rule_sets(facts_data, upgrade_plan)

    def _run_schematics(
        self,
        migration_seq: list,
        repo_path: str,
        dry_run: bool,
        staging: dict[str, dict],
    ) -> list[PreExecutionStep]:
        """Run whitelisted schematics from migration sequence."""
        steps: list[PreExecutionStep] = []

        for entry in migration_seq:
            schematic = entry.get("schematic") if isinstance(entry, dict) else None
            if not schematic:
                continue

            rule_id = entry.get("rule_id", "unknown") if isinstance(entry, dict) else "unknown"

            if not self._validate_command(schematic):
                steps.append(
                    PreExecutionStep(
                        step_type="schematic",
                        rule_id=rule_id,
                        description=f"Skipped (not whitelisted): {schematic}",
                        success=False,
                        error=f"Command not in whitelist: {schematic.split()[0] if schematic.split() else 'empty'}",
                    )
                )
                continue

            if dry_run:
                steps.append(
                    PreExecutionStep(
                        step_type="schematic",
                        rule_id=rule_id,
                        description=f"[DRY RUN] Would run: {schematic}",
                        success=True,
                    )
                )
                continue

            step = self._run_single_schematic(schematic, rule_id, repo_path, staging)
            steps.append(step)

        return steps

    def _run_single_schematic(
        self,
        command: str,
        rule_id: str,
        repo_path: str,
        staging: dict[str, dict],
    ) -> PreExecutionStep:
        """Run a single schematic command and capture modified files."""
        before_snapshot = self._snapshot_tree(repo_path)

        try:
            # Build safe argument list — no shell=True to prevent injection
            if platform.system() == "Windows":
                cmd_args = ["cmd", "/d", "/s", "/c", command]
            else:
                cmd_args = shlex.split(command)
            result = subprocess.run(
                cmd_args,
                shell=False,
                cwd=repo_path,
                capture_output=True,
                timeout=SCHEMATIC_TIMEOUT,
            )
            output = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")

            modified = self._capture_modified(before_snapshot, repo_path, staging)

            if result.returncode == 0:
                return PreExecutionStep(
                    step_type="schematic",
                    rule_id=rule_id,
                    description=f"Ran: {command}",
                    success=True,
                    modified_files=modified,
                    output=output[:2000],
                )
            else:
                return PreExecutionStep(
                    step_type="schematic",
                    rule_id=rule_id,
                    description=f"Failed: {command}",
                    success=False,
                    modified_files=modified,
                    error=stderr[:1000] or output[:1000],
                    output=output[:2000],
                )
        except subprocess.TimeoutExpired:
            return PreExecutionStep(
                step_type="schematic",
                rule_id=rule_id,
                description=f"Timeout: {command}",
                success=False,
                error=f"Command timed out after {SCHEMATIC_TIMEOUT}s",
            )
        except Exception as e:
            return PreExecutionStep(
                step_type="schematic",
                rule_id=rule_id,
                description=f"Error: {command}",
                success=False,
                error=str(e),
            )

    # Shell metacharacters that indicate injection or command chaining
    _SHELL_METACHAR_RE = re.compile(r"[;&|`$\(\)\{\}<>!]")

    @classmethod
    def _validate_command(cls, command: str) -> bool:
        """Check if command is safe to execute.

        Validates:
        1. Starts with a whitelisted tool
        2. Contains no shell metacharacters (&&, ;, |, backticks, $(), etc.)
        """
        if not command or not command.strip():
            return False
        # Block shell metacharacters to prevent injection
        if cls._SHELL_METACHAR_RE.search(command):
            logger.warning("[UpgradeStrategy] Blocked command with shell metacharacters: %s", command[:100])
            return False
        parts = command.strip().split()
        tool = parts[0].lower()
        return tool in SCHEMATIC_WHITELIST

    def _apply_config_changes(
        self,
        rule_sets: list,
        repo_path: str,
        staging: dict[str, dict],
        dry_run: bool,
    ) -> list[PreExecutionStep]:
        """Apply deterministic config changes from upgrade rules."""
        steps: list[PreExecutionStep] = []

        for rule_set in rule_sets:
            rules = getattr(rule_set, "rules", []) or []
            for rule in rules:
                config_changes = getattr(rule, "config_changes", []) or []
                rule_id = getattr(rule, "id", "unknown")
                for change in config_changes:
                    if dry_run:
                        steps.append(
                            PreExecutionStep(
                                step_type="config_change",
                                rule_id=rule_id,
                                description=f"[DRY RUN] {getattr(change, 'description', 'config change')}",
                                success=True,
                            )
                        )
                        continue
                    step = self._apply_single_config(change, rule_id, repo_path, staging)
                    steps.append(step)

        return steps

    def _apply_single_config(
        self,
        change: Any,
        rule_id: str,
        repo_path: str,
        staging: dict[str, dict],
    ) -> PreExecutionStep:
        """Apply a single ConfigChange to a file."""
        file_glob = getattr(change, "file_glob", "")
        operation = str(getattr(change, "operation", "")).lower()
        json_path = getattr(change, "json_path", "")
        value = getattr(change, "value", None)
        description = getattr(change, "description", "") or f"{operation} {json_path}"
        condition_regex = getattr(change, "condition_regex", "")

        # Find matching files
        repo = Path(repo_path)
        matching_files = list(repo.glob(file_glob))
        if not matching_files:
            # Try recursive glob
            matching_files = list(repo.glob(f"**/{file_glob}"))

        if not matching_files:
            return PreExecutionStep(
                step_type="config_change",
                rule_id=rule_id,
                description=f"No files matched: {file_glob}",
                success=False,
                error=f"Glob '{file_glob}' matched no files",
            )

        modified_files: list[str] = []
        errors: list[str] = []

        for file_path in matching_files:
            rel_path = str(file_path.relative_to(repo)).replace("\\", "/")

            # Read file content (from staging or disk)
            content = self._read_file(rel_path, repo_path, staging)
            if content is None:
                errors.append(f"Could not read {rel_path}")
                continue

            # Only apply to JSON files
            if file_path.suffix.lower() not in (".json",):
                errors.append(f"Config change only supports JSON files, got: {rel_path}")
                continue

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                errors.append(f"Invalid JSON in {rel_path}")
                continue

            # Check condition regex if specified
            if condition_regex:
                current_val = self._json_path_get(data, json_path)
                if current_val is not None and not re.search(condition_regex, str(current_val)):
                    continue  # Condition not met, skip

            # Apply operation
            if operation == "set":
                self._json_path_set(data, json_path, value)
            elif operation == "delete":
                self._json_path_delete(data, json_path)
            elif operation == "rename_key":
                self._json_path_rename(data, json_path, value)
            else:
                errors.append(f"Unknown operation: {operation}")
                continue

            new_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            self._stage_file(rel_path, new_content, staging)
            modified_files.append(rel_path)

        success = len(modified_files) > 0 and len(errors) == 0
        return PreExecutionStep(
            step_type="config_change",
            rule_id=rule_id,
            description=description,
            success=success,
            modified_files=modified_files,
            error="; ".join(errors) if errors else "",
        )

    def _apply_version_bumps(
        self,
        upgrade_plan: dict,
        repo_path: str,
        staging: dict[str, dict],
        dry_run: bool,
    ) -> list[PreExecutionStep]:
        """Apply version bumps from required_dependencies."""
        required_deps = upgrade_plan.get("required_dependencies", {})
        if not required_deps:
            return []

        steps: list[PreExecutionStep] = []
        for dep_name, spec in required_deps.items():
            if dry_run:
                steps.append(
                    PreExecutionStep(
                        step_type="version_bump",
                        rule_id=f"dep-{dep_name}",
                        description=f"[DRY RUN] Would bump {dep_name} to {spec}",
                        success=True,
                    )
                )
                continue

            # Determine if npm or gradle dependency
            step = self._bump_npm_dep(dep_name, spec, repo_path, staging)
            if step.success or step.modified_files:
                steps.append(step)
            else:
                # Try gradle
                gradle_step = self._bump_gradle_dep(dep_name, spec, repo_path, staging)
                steps.append(gradle_step)

        return steps

    def _bump_npm_dep(
        self,
        name: str,
        spec: str,
        repo_path: str,
        staging: dict[str, dict],
    ) -> PreExecutionStep:
        """Bump an npm dependency in package.json."""
        repo = Path(repo_path)
        # Search for package.json files (root + frontend subdirs)
        pkg_files = list(repo.glob("**/package.json"))
        # Filter out node_modules
        pkg_files = [p for p in pkg_files if "node_modules" not in str(p)]

        modified: list[str] = []
        for pkg_path in pkg_files:
            rel_path = str(pkg_path.relative_to(repo)).replace("\\", "/")
            content = self._read_file(rel_path, repo_path, staging)
            if content is None:
                continue

            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue

            changed = False
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                deps = data.get(section, {})
                if name in deps:
                    deps[name] = spec
                    changed = True

            if changed:
                new_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
                self._stage_file(rel_path, new_content, staging)
                modified.append(rel_path)

        return PreExecutionStep(
            step_type="version_bump",
            rule_id=f"dep-{name}",
            description=f"Bump {name} to {spec}",
            success=len(modified) > 0,
            modified_files=modified,
            error="" if modified else f"Dependency '{name}' not found in any package.json",
        )

    def _bump_gradle_dep(
        self,
        name: str,
        spec: str,
        repo_path: str,
        staging: dict[str, dict],
    ) -> PreExecutionStep:
        """Bump a Gradle dependency in build.gradle / build.gradle.kts."""
        repo = Path(repo_path)
        gradle_files = list(repo.glob("**/build.gradle")) + list(repo.glob("**/build.gradle.kts"))
        gradle_files = [p for p in gradle_files if ".gradle" not in str(p.parent)]

        modified: list[str] = []
        for gradle_path in gradle_files:
            rel_path = str(gradle_path.relative_to(repo)).replace("\\", "/")
            content = self._read_file(rel_path, repo_path, staging)
            if content is None:
                continue

            # Replace version in dependency declarations
            # Matches patterns like: implementation 'group:name:version'
            # and implementation("group:name:version")
            escaped_name = re.escape(name)
            pattern = rf"({escaped_name}):[\d.]+[^'\"]*"
            new_content, count = re.subn(pattern, rf"\1:{spec}", content)

            if count > 0:
                self._stage_file(rel_path, new_content, staging)
                modified.append(rel_path)

        return PreExecutionStep(
            step_type="version_bump",
            rule_id=f"dep-{name}",
            description=f"Bump {name} to {spec} (Gradle)",
            success=len(modified) > 0,
            modified_files=modified,
            error="" if modified else f"Dependency '{name}' not found in Gradle files",
        )

    # ── JSON path helpers ────────────────────────────────────────────────

    @staticmethod
    def _json_path_get(data: dict, path: str) -> Any:
        """Get value at dot-separated JSON path."""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    @staticmethod
    def _json_path_set(data: dict, path: str, value: Any) -> None:
        """Set value at dot-separated JSON path, creating intermediates."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    @staticmethod
    def _json_path_delete(data: dict, path: str) -> None:
        """Delete key at dot-separated JSON path."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]

    @staticmethod
    def _json_path_rename(data: dict, path: str, new_key: Any) -> None:
        """Rename key at dot-separated JSON path."""
        if not isinstance(new_key, str):
            return
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return
        old_key = keys[-1]
        if isinstance(current, dict) and old_key in current:
            current[new_key] = current.pop(old_key)

    # ── File/staging helpers ─────────────────────────────────────────────

    @staticmethod
    def _read_file(
        rel_path: str,
        repo_path: str,
        staging: dict[str, dict],
    ) -> str | None:
        """Read file content from staging dict or disk."""
        if rel_path in staging:
            return staging[rel_path].get("content", "")

        full_path = Path(repo_path) / rel_path
        if full_path.exists():
            try:
                return full_path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    @staticmethod
    def _stage_file(
        rel_path: str,
        content: str,
        staging: dict[str, dict],
        action: str = "modify",
    ) -> None:
        """Add or update file in staging dict."""
        if rel_path in staging:
            staging[rel_path]["content"] = content
        else:
            staging[rel_path] = {
                "content": content,
                "original_content": "",
                "action": action,
                "language": "other",
            }

    @staticmethod
    def _snapshot_tree(root: str) -> dict[str, float]:
        """Take a snapshot of file modification times for change detection."""
        snapshot: dict[str, float] = {}
        root_path = Path(root)
        skip_dirs = {"node_modules", ".git", "dist", "build", "__pycache__", ".cache", ".venv", "venv", "site-packages"}

        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                dirnames[:] = [d for d in dirnames if d not in skip_dirs]
                for fname in filenames:
                    full = Path(dirpath) / fname
                    rel = str(full.relative_to(root_path)).replace("\\", "/")
                    snapshot[rel] = full.stat().st_mtime
        except Exception:
            pass

        return snapshot

    def _capture_modified(
        self,
        before_snapshot: dict[str, float],
        repo_path: str,
        staging: dict[str, dict],
    ) -> list[str]:
        """Compare before/after snapshots and stage modified files."""
        after_snapshot = self._snapshot_tree(repo_path)
        modified: list[str] = []

        for rel_path, mtime in after_snapshot.items():
            before_mtime = before_snapshot.get(rel_path)
            if before_mtime is None or mtime > before_mtime:
                # File was created or modified
                full_path = Path(repo_path) / rel_path
                try:
                    content = full_path.read_text(encoding="utf-8")
                    action = "create" if before_mtime is None else "modify"
                    self._stage_file(rel_path, content, staging, action=action)
                    modified.append(rel_path)
                except Exception:
                    pass

        return modified

    # ── Hook 3: Verification (migration completeness) ────────────────────

    def enrich_verification(
        self,
        build_result: Any,
        staging: dict[str, dict],
        plan: Any,
        raw_build_outputs: list[str],
        pre_execution_result: PreExecutionResult | None = None,
    ) -> VerificationEnrichment:
        """Error clusters + deprecation warnings + migration completeness."""
        return VerificationEnrichment(
            error_clusters=self._cluster_errors(build_result),
            deprecation_warnings=self._parse_deprecations(raw_build_outputs),
            task_specific={
                "migration_completeness": self._compute_migration_completeness(plan, staging),
            },
            pre_execution_summary=self._summarize_pre_execution(pre_execution_result),
        )

    def _parse_deprecations(self, raw_outputs: list[str]) -> list[dict]:
        """Extract deprecation warnings from raw build output."""
        deprecations: list[dict] = []
        seen: set[str] = set()

        patterns = [
            re.compile(r"(?:DEPRECATED|deprecated|Deprecation)\s*:?\s*(.+)", re.IGNORECASE),
            re.compile(r"warning\s+NG\d+:\s*(.+)", re.IGNORECASE),  # Angular deprecations
            re.compile(r"\[WARNING\]\s*(.+?deprecated.+)", re.IGNORECASE),  # Maven/Gradle
        ]

        for output in raw_outputs:
            # Strip ANSI codes
            clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
            for line in clean.splitlines():
                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        msg = match.group(1).strip()
                        if msg and msg not in seen:
                            seen.add(msg)
                            deprecations.append(
                                {
                                    "message": msg,
                                    "source_line": line.strip()[:200],
                                }
                            )

        return deprecations

    def _compute_migration_completeness(
        self,
        plan: Any,
        staging: dict[str, dict],
    ) -> dict:
        """Estimate migration completeness based on plan vs staged files."""
        upgrade_plan = getattr(plan, "upgrade_plan", None) or {}
        migration_seq = upgrade_plan.get("migration_sequence", [])
        if not migration_seq:
            return {"status": "no_migration_sequence"}

        total_rules = len(migration_seq)
        staged_files = set(staging.keys())

        rules_with_staged_files = 0
        for entry in migration_seq:
            if not isinstance(entry, dict):
                continue
            affected = entry.get("affected_files", [])
            if any(f.replace("\\", "/") in staged_files for f in affected):
                rules_with_staged_files += 1

        completeness = rules_with_staged_files / total_rules if total_rules > 0 else 0.0

        return {
            "total_rules": total_rules,
            "rules_with_staged_changes": rules_with_staged_files,
            "completeness_ratio": round(completeness, 2),
            "status": ("complete" if completeness >= 1.0 else "partial" if completeness > 0 else "not_started"),
        }

    @staticmethod
    def _summarize_pre_execution(
        result: PreExecutionResult | None,
    ) -> dict:
        """Summarize pre-execution results for the report."""
        if result is None:
            return {}

        by_type: dict[str, dict] = {}
        for step in result.steps:
            if step.step_type not in by_type:
                by_type[step.step_type] = {"total": 0, "success": 0, "failed": 0, "files": []}
            entry = by_type[step.step_type]
            entry["total"] += 1
            if step.success:
                entry["success"] += 1
            else:
                entry["failed"] += 1
            entry["files"].extend(step.modified_files)

        return {
            "total_steps": len(result.steps),
            "total_files_modified": result.total_files_modified,
            "errors": result.errors,
            "by_type": by_type,
        }
