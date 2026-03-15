# Phase Registry

Single source of truth for static SDLC phase metadata.

**File:** `src/aicodegencrew/phase_registry.py`

> **Reference Diagrams:**
> - [sdlc-overview.drawio](../diagrams/sdlc-overview.drawio) - Full SDLC pipeline overview
> - [layer-architecture.drawio](../diagrams/layer-architecture.drawio) - 4-layer architecture model
> - [pipeline-flow.drawio](../diagrams/pipeline-flow.drawio) - Phase flow with layer context
>
> **Related Docs:**
> - [pipeline-contract.md](./pipeline-contract.md) - Runtime merge layer that combines registry + phases config and normalizes statuses

## PhaseDescriptor Schema

| Field | Type | Description |
|-------|------|-------------|
| `phase_id` | `str` | Unique identifier (e.g. `"extract"`) |
| `display_name` | `str` | Human-readable name |
| `phase_type` | `"pipeline" \| "crew"` | Execution engine: `pipeline` = deterministic + LLM pipeline; `crew` = CrewAI agent loop |
| `order` | `int` | Execution order (0-7) |
| `dependencies` | `tuple[str, ...]` | Phases that must complete first |
| `required` | `bool` | Must-complete phase? |
| `primary_output` | `str` | Path for completion detection (relative to project root) |
| `cleanup_targets` | `tuple[str, ...]` | Paths deleted on reset |
| `resettable` | `bool` | Whether the phase can be reset (False for discover) |

## All 8 Phases

```mermaid
graph LR
    discover["0: Discover<br/>Pipeline"] --> extract["1: Extract<br/>Pipeline"]
    extract --> analyze["2: Analyze<br/>Pipeline"]
    analyze --> document["3: Document<br/>Pipeline"]
    analyze --> triage["4: Triage<br/>Pipeline"]
    analyze --> plan["5: Plan<br/>Pipeline"]
    plan --> implement["6: Implement<br/>Crew"]
    implement --> verify["7: Verify<br/>Crew"]
    verify --> deliver["8: Deliver<br/>Pipeline"]
```

| Phase | Display Name | Type | Dependencies | Required | Resettable |
|-------|--------------|------|--------------|----------|------------|
| `discover` | Repository Indexing | pipeline | - | yes | no |
| `extract` | Architecture Facts Extraction | pipeline | discover | yes | yes |
| `analyze` | Architecture Analysis | pipeline | extract | yes | yes |
| `document` | Architecture Synthesis | pipeline | analyze | no | yes |
| `triage` | Issue Triage | pipeline | extract | no | yes |
| `plan` | Development Planning | pipeline | analyze | no | yes |
| `implement` | Code Generation | crew | plan | no | yes |
| `verify` | Test Generation | crew | implement | no | yes |
| `deliver` | Review and Deploy | pipeline | implement | no | yes |

## Registry vs phases_config.yaml vs PipelineContract

| Concern | Source |
|---------|--------|
| Output paths, cleanup targets, resettable behavior | `phase_registry.py` (structural, static) |
| Enabled/disabled, presets, per-phase runtime config | `phases_config.yaml` (runtime, configurable) |
| Runtime merged model + status vocabulary | `pipeline_contract.py` (contract for orchestrator, CLI, dashboard backend) |

## How to Add a New Phase

1. Add a `PhaseDescriptor` entry to `PHASES` in `phase_registry.py`
2. Add a section in `config/phases_config.yaml` with `enabled`, `order`, `config`
3. Register the phase executable in `cli.py` (`cmd_run()`)
4. Optionally add it to presets in `phases_config.yaml`

## DISCOVER_ARTIFACTS

The phase registry also defines artifact paths for the Discover phase:

```python
DISCOVER_ARTIFACTS = {
    "symbols": "knowledge/discover/symbols.jsonl",
    "evidence": "knowledge/discover/evidence.jsonl",
    "manifest": "knowledge/discover/repo_manifest.json",
}
```

These paths are also available as constants in `shared/paths.py`: `DISCOVER_SYMBOLS`, `DISCOVER_EVIDENCE`, `DISCOVER_MANIFEST`.

## Convenience Functions

| Function | Replaces |
|----------|----------|
| `get_phase(id)` | Direct dict lookups |
| `get_all_phases()` | Sorting phases by order |
| `get_cleanup_targets(id)` | `phase_outputs.get_cleanup_targets()` |
| `get_resettable_phases()` | Hardcoded `!= "discover"` filter |
| `get_dependency_graph()` | YAML loading in `reset_service._load_dependencies()` |
| `outputs_exist(id, base)` | `orchestrator._outputs_exist()` |
| `check_phase_output_exists(id, root)` | `phase_outputs.check_phase_output_exists()` |
