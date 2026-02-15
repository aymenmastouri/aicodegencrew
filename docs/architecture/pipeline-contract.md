# Pipeline Contract

Central runtime contract for phases, presets, and status normalization across CLI, orchestrator, and dashboard backend.

**File:** `src/aicodegencrew/pipeline_contract.py`

> **Reference Diagrams:**
> - [pipeline-flow.drawio](../diagrams/pipeline-flow.drawio) - End-to-end SDLC phase flow
> - [orchestration-state.drawio](../diagrams/orchestration-state.drawio) - Phase state lifecycle
> - [dashboard-architecture.drawio](../diagrams/dashboard-architecture.drawio) - Frontend/backend execution monitoring

## Why This Exists

Before the contract, phase and run status logic existed in multiple places:
- `orchestrator.py`
- `cli.py`
- `ui/backend/services/phase_runner.py`
- `ui/backend/services/pipeline_executor.py`

Each module had slightly different status terms and mapping rules. This caused drift and fragile behavior (for example, the same run being interpreted differently by orchestrator and dashboard).

The pipeline contract provides one place for:
- Phase and preset definition merging
- Status normalization
- Run outcome computation
- Shared phase context shape

## Core Responsibilities

### 1. Unified Status Vocabulary

The contract defines canonical status groups:

| Domain | Values |
|--------|--------|
| Phase result (orchestrator) | `success`, `partial`, `skipped`, `failed` |
| Phase progress (UI/API) | `pending`, `running`, `completed`, `partial`, `skipped`, `failed` |
| Pipeline phase card status | `idle`, `ready`, `planned`, plus progress states |
| Run outcome | `success`, `all_skipped`, `partial`, `failed` |

Key helpers:
- `normalize_phase_result_status()`
- `normalize_phase_progress_status()`
- `normalize_pipeline_phase_status()`
- `compute_run_outcome()`

### 2. Merge Static + Runtime Definitions

`PipelineContract` merges:
- static structural metadata from `phase_registry.py`
- runtime config from `config/phases_config.yaml`

This keeps one runtime view of:
- phase order and enablement
- dependencies
- phase config payload
- presets (legacy list and rich object formats)

### 3. Typed Runtime Model

The contract exposes:
- `PhaseDefinition`
- `PresetDefinition`
- `PipelineContract`
- `PhaseContext`

`PhaseContext` is the shared execution payload between phases and includes:
- `run_id`
- requested/resolved phases
- current phase
- artifacts and per-phase metrics
- execution errors

## Integration Points

### Orchestrator

`src/aicodegencrew/orchestrator.py` now uses the contract for:
- resolving phases and presets
- dependency list lookup
- status normalization and mapping to `phase_state.json`
- metric status consistency
- run outcome calculation
- optional `pipeline_context` in `context` property

### CLI

`src/aicodegencrew/cli.py` uses the contract for:
- validating explicit phase IDs
- validating preset names
- resolving default enabled phases

### Dashboard Backend: Phase Runner

`ui/backend/services/phase_runner.py` now reads phases/presets from `PipelineContract` and resolves phase status through normalized status mapping.

### Dashboard Backend: Pipeline Executor

`ui/backend/services/pipeline_executor.py` now uses central status helpers for:
- phase progress counting
- completion percentage semantics
- external state normalization
- run outcome computation

## Status Mapping Rules

### Phase Result Normalization

Incoming status tokens are normalized to the phase-result domain. Examples:
- `completed`, `success`, `ok`, `dry_run` -> `success`
- `partial`, `degraded` -> `partial`
- `skip`, `up_to_date`, `noop` -> `skipped`
- `error`, `failure`, `cancelled` -> `failed`

### Phase State Mapping (`logs/phase_state.json`)

When a phase completes in orchestrator:
- `success` -> `completed`
- `partial` -> `partial`
- `skipped` -> `skipped`
- `failed` -> `failed`

### Run Outcome

`compute_run_outcome()` semantics:
1. Any failed phase -> `failed`
2. All skipped -> `all_skipped`
3. Mix of completed/partial and skipped -> `partial`
4. Otherwise -> `success`

## Config Precedence

### Source of Truth by Concern

| Concern | Primary Source |
|---------|----------------|
| Outputs, cleanup targets, resettable flag | `phase_registry.py` |
| Runtime enable/disable, order, presets, phase config | `phases_config.yaml` |

### Dependency Drift Detection

If dependencies differ between registry and YAML, the contract logs a warning so drift is visible while still allowing runtime behavior from YAML.

## Backward Compatibility

The contract keeps compatibility with:
- legacy preset format (`preset: [phase_a, phase_b]`)
- existing phase state file values
- existing run outcome values used in UI
- existing orchestrator `context` keys (`phases`, `knowledge`, `shared`)

`context` now adds `pipeline_context` without removing old keys.

## How To Extend

### Add a New Status Alias

Update normalization in:
- `normalize_phase_result_status()` and/or
- `normalize_phase_progress_status()`

Then add tests under `tests/test_pipeline_contract.py`.

### Add a New Phase

1. Add phase descriptor to `src/aicodegencrew/phase_registry.py`
2. Add runtime section to `config/phases_config.yaml`
3. Register executable in `src/aicodegencrew/cli.py`
4. Optionally include in presets

No additional status glue is required in backend services.

## Test Coverage

Contract-specific tests are in:
- `tests/test_pipeline_contract.py`

Cross-module behavior is validated by:
- `tests/test_cli_orchestrator.py`
- `tests/test_orchestrator_protocol.py`
- `tests/test_progress_and_ux.py`
- `tests/test_reset_and_history.py`
- `tests/test_api_integration.py`

