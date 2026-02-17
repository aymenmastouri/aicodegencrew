# Task-Type-Aware Pipeline — Strategy Architecture

**Status**: Approved
**Author**: Aymen Mastouri
**Date**: 2026-02-17
**Phase**: 5 (Plan) + 6 (Implement)

---

## 1. Problem Statement

Phase 6 (implement) is 100% LLM-generated code. For many task types, a significant
portion of the work is **deterministic** and should happen **before** the LLM touches
anything. Currently, the pipeline has no mechanism to adapt its behavior based on task
type — no pre-execution, no task-specific validation, no specialized reporting.

**Upgrade** is just one example. The same pattern applies to:

| Task Type     | Deterministic Work                                      |
|---------------|---------------------------------------------------------|
| **Upgrade**   | Schematics (`ng update`), config changes, version bumps |
| **Migration** | Codemods (`sass-migrator`, `eslint --fix`), config edits|
| **Refactoring** | AST-based codemods, linting auto-fixes               |
| **Feature**   | Scaffolding (`ng generate`, Spring Initializr)          |
| **Security**  | Dependency patching, CVE resolution                     |

## 2. Solution Overview

A **Strategy pattern** where each task type registers its own behavior for **3 pipeline
hooks**. The core pipeline dispatches to the right strategy — no `if task_type == "upgrade"`
anywhere.

```
                        TaskTypeStrategy (ABC)
                        ┌─────────────────────────┐
                        │ enrich_plan()            │  ← Phase 5: validate feasibility
                        │ pre_execute()            │  ← Phase 6: deterministic pre-LLM
                        │ enrich_verification()    │  ← Phase 6: rich post-build report
                        └─────────┬───────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
    UpgradeStrategy      MigrationStrategy     DefaultStrategy
    (schematics,         (codemods,            (no-op for
     dep compat,          tool runs,            feature/bugfix)
     migration track)     config edits)
```

## 3. Registry

Strategies auto-register via decorator. No manual configuration.

```python
@register_strategy("upgrade")     → UpgradeStrategy
@register_strategy("migration")   → MigrationStrategy  (future)
@register_strategy("refactoring") → RefactoringStrategy (future)
@register_strategy("feature")     → DefaultStrategy
@register_strategy("bugfix")      → DefaultStrategy
```

Lookup with fallback:

```python
strategy = get_strategy(plan.task_type)  # never raises
```

Unknown task types fall back to `DefaultStrategy` (no-op for hooks 1 & 2, universal
error clustering for hook 3).

## 4. Pipeline Integration

### 4.1 Phase 5 — Plan Enrichment (Stage 3)

After `UpgradeRulesEngine.scan_and_assess()` in `stage3_pattern_matcher.py`:

```python
strategy = get_strategy("upgrade")
enrichment = strategy.enrich_plan(plan_data, facts)
assessment["compatibility_report"] = { ... }
```

**Output**: `compatibility_report` dict added to `upgrade_assessment` in pattern result.

### 4.2 Phase 5 — Prompt Enrichment (Stage 4)

In `stage4_plan_generator.py`, the `compatibility_report` checks are formatted into the
LLM prompt so the planning agent knows about dependency conflicts before generating
the plan.

### 4.3 Phase 6 — Pre-Execution (`crew.py:run()`)

After preflight, before the build-fix loop:

```python
strategy = get_strategy(plan.task_type)
det_result = strategy.pre_execute(plan, staging, repo_path, dry_run)
```

For upgrades, this runs schematics, applies config changes, and bumps dependency
versions — all deterministically. Results are staged in the shared `staging` dict,
so the LLM sees them during code generation.

### 4.4 Phase 6 — Verification Enrichment (`crew.py:run()`)

After the build-fix loop:

```python
rich_report = strategy.enrich_verification(
    build_result, staging, plan, raw_build_outputs, det_result,
)
```

Produces error clusters, deprecation warnings, and task-specific metrics (e.g.,
migration completeness for upgrades).

### 4.5 No Hardcoded if/else

The core pipeline (`crew.py`) never checks `task_type` directly. All task-type-specific
behavior lives in strategy classes.

## 5. Data Flow

```
Phase 5 (Plan):
  Stage 3 → strategy.enrich_plan() → compatibility_report in assessment
  Stage 4 → formats compatibility_report into LLM prompt

Phase 6 (Implement):
  crew.py:run()
    ├── Preflight (unchanged)
    ├── strategy.pre_execute()     → deterministic changes in staging
    ├── Build-Fix Loop (unchanged, collects raw_build_outputs)
    ├── strategy.enrich_verification() → rich_report
    └── OutputWriter.run(rich_verification=rich_report.to_dict())
```

## 6. Shared Result Types

All strategies share the same result dataclasses:

| Dataclass              | Purpose                                  |
|------------------------|------------------------------------------|
| `PlanEnrichment`       | Compatibility checks + warnings + context |
| `PreExecutionStep`     | Single deterministic step result          |
| `PreExecutionResult`   | Aggregated pre-execution results          |
| `ErrorCluster`         | Grouped build errors by pattern           |
| `VerificationEnrichment` | Rich verification data                  |

## 7. UpgradeStrategy Details

### 7.1 enrich_plan()

- Loads upgrade rule sets from architecture facts
- Validates `required_dependencies` against actual repo versions (semver)
- Returns compatibility checks: `compatible`, `needs_bump`, `conflict`, `unknown`
- Warnings for conflicts that would block the upgrade

### 7.2 pre_execute()

Three deterministic step types:

1. **Schematics** — Run whitelisted CLI commands (`ng`, `npx`, `npm`, `openrewrite`)
   with subprocess, capture modified files
2. **Config changes** — Apply JSON path operations (set, delete, rename) from
   upgrade rules
3. **Version bumps** — Update dependency versions in `package.json` / `build.gradle`

All changes are staged in the shared `staging` dict. The LLM sees them during
code generation.

**Security**: Commands are validated against `SCHEMATIC_WHITELIST` before execution.
Timeout: 300 seconds per schematic.

### 7.3 enrich_verification()

- **Error clustering**: Group build errors by pattern/root cause (inherited from
  `DefaultStrategy._cluster_errors()`)
- **Deprecation parsing**: Extract deprecation warnings from raw build output
- **Migration completeness**: Re-run `UpgradeCodeScanner` on staged content,
  compare before/after to measure progress
- **Pre-execution summary**: Aggregate step results from pre_execute phase

## 8. DefaultStrategy

No-op for `enrich_plan()` and `pre_execute()`. Error clustering in
`enrich_verification()` is **universal** — it applies to all task types, not just
upgrades. This ensures every task gets build error analysis.

## 9. File Structure

```
hybrid/code_generation/
├── crew.py              (modified: strategy dispatch)
├── schemas.py           (modified: raw_output, rich_verification)
├── output_writer.py     (modified: pass-through rich_verification)
├── strategies/
│   ├── __init__.py      (NEW: exports + auto-register)
│   ├── base.py          (NEW: ABC + DefaultStrategy + registry)
│   └── upgrade_strategy.py (NEW: UpgradeStrategy)
└── ...

hybrid/development_planning/stages/
├── stage3_pattern_matcher.py  (modified: call enrich_plan)
└── stage4_plan_generator.py   (modified: format compat report)
```

## 10. Extensibility

Adding a new task type = **1 new file**, zero changes to core pipeline:

```python
# strategies/migration_strategy.py
@register_strategy("migration")
class MigrationStrategy(TaskTypeStrategy):
    def enrich_plan(self, plan_data, facts):
        # Validate migration path feasibility
        ...
    def pre_execute(self, plan, staging, repo_path, dry_run):
        # Run codemods (sass-migrator, eslint --fix)
        ...
    def enrich_verification(self, ...):
        # Track migration completeness
        ...
```

No changes to `crew.py`, `output_writer.py`, or any core file needed.

## 11. Schema Changes

### ContainerBuildResult

```python
raw_output: str = ""  # Raw build output for report parsing
```

### CodegenReport

```python
rich_verification: dict | None = None  # Strategy-enriched verification report
```

## 12. Verification Plan

1. **Unit tests**: `DefaultStrategy` returns no-op results. `UpgradeStrategy.enrich_plan()`
   with mock facts containing TS 5.4 vs required >=5.6 → `needs_bump`.
2. **Integration**: Run Phase 5+6 on BNUVZ-12529 (Angular 18→19). Check:
   - Plan JSON has `compatibility_report`
   - Logs show strategy pre-execution steps
   - Report JSON has `rich_verification` with error clusters + migration completeness
3. **DefaultStrategy**: Run on a feature task. Verify no pre-execution, but error
   clustering still works in verification.
4. **Registry**: Import strategies module → verify `get_strategy("upgrade")` returns
   `UpgradeStrategy`, `get_strategy("feature")` returns `DefaultStrategy`.
