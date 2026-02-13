# End-to-End Tests - AI SDLC Pipeline

This directory contains comprehensive end-to-end tests for the AI-powered SDLC pipeline, validating the complete workflow from code indexing to architecture synthesis.

## Structure

```
tests/e2e/
+-- README.md                           # This file
+-- conftest.py                         # Pytest fixtures & utilities
+-- test_phase1_facts_extraction.py     # Phase 1 E2E tests (deterministic)
+-- test_phase2_synthesis.py            # Phase 2 E2E tests (LLM synthesis)
+-- test_full_workflow.py               # Complete workflow tests
+-- fixtures/                           # Test data & sample projects
|   +-- sample_project/                 # Minimal test project
|   |   +-- backend/                    # Java Spring Backend
|   |   +-- frontend/                   # Angular Frontend
|   +-- expected_outputs/               # Expected test results
|       +-- architecture_facts.json     # Expected Phase 1 output
|       +-- c4_container.md             # Expected Phase 2 output
+-- helpers/                            # Validation utilities
    +-- __init__.py
    +-- facts_validator.py              # Validate architecture_facts.json
    +-- evidence_validator.py           # Validate evidence_map.json
    +-- synthesis_validator.py          # Validate Phase 2 outputs
```

## Test Coverage

### Phase 1: Architecture Facts Extraction (Deterministic)
- **test_phase1_facts_extraction.py**
  - Container detection (Spring Boot, Angular, Docker, etc.)
  - Component extraction (Java classes, Angular components)
  - Interface detection (REST endpoints, routes)
  - Relation inference (imports, dependencies)
  - Evidence collection (file paths, line ranges)
  - JSON schema validation
  - Evidence integrity (all IDs valid, line ranges accurate)

### Phase 2: Architecture Synthesis (LLM)
- **test_phase2_synthesis.py**
  - C4 diagram generation (context, container, component)
  - arc42 documentation generation
  - Quality gate validation
  - Evidence-first compliance (no hallucinations)
  - FileReadTool integration (can read architecture_facts.json)

### Full Workflow
- **test_full_workflow.py**
  - End-to-end: Phase 0 -> Phase 1 -> Phase 2
  - Data flow validation (outputs become inputs)
  - Error handling & recovery
  - Performance benchmarks

## Running Tests

### Run All E2E Tests
```bash
pytest tests/e2e/ -v
```

### Run Specific Test Suite
```bash
# Phase 1 only (fast, deterministic)
pytest tests/e2e/test_phase1_facts_extraction.py -v

# Phase 2 only (slow, LLM required)
pytest tests/e2e/test_phase2_synthesis.py -v

# Full workflow (slowest, complete validation)
pytest tests/e2e/test_full_workflow.py -v
```

### Run with Coverage
```bash
pytest tests/e2e/ --cov=src/aicodegencrew --cov-report=html
```

### Run with Different Configurations
```bash
# Skip slow tests
pytest tests/e2e/ -v -m "not slow"

# Run only smoke tests
pytest tests/e2e/ -v -m "smoke"

# Parallel execution (faster)
pytest tests/e2e/ -v -n auto
```

## Test Fixtures

### `temp_workspace` (conftest.py)
Creates isolated temporary workspace for each test with cleanup.

```python
def test_example(temp_workspace):
    # temp_workspace is a Path object
    project_root = temp_workspace / "project"
    # ... test logic ...
    # Automatically cleaned up after test
```

### `sample_project` (conftest.py)
Provides a minimal Spring Boot + Angular project for testing.

```python
def test_with_sample(sample_project):
    # sample_project contains:
    # - backend/ (Java Spring classes)
    # - frontend/ (Angular components)
    # - knowledge/ (output directory)
```

### `orchestrator` (conftest.py)
Pre-configured orchestrator instance for running phases.

```python
def test_run_phase(orchestrator, sample_project):
    result = orchestrator.run_phase("facts_extraction", sample_project)
    assert result.success
```

## Validation Helpers

### `FactsValidator` (helpers/facts_validator.py)
```python
from tests.e2e.helpers import FactsValidator

validator = FactsValidator(facts_path="knowledge/architecture/architecture_facts.json")

# Schema validation
assert validator.validate_schema()

# Evidence integrity
assert validator.validate_evidence_integrity()

# ID uniqueness
duplicates = validator.find_duplicate_ids()
assert len(duplicates) == 0

# Relations consistency
assert validator.validate_relations()
```

### `EvidenceValidator` (helpers/evidence_validator.py)
```python
from tests.e2e.helpers import EvidenceValidator

validator = EvidenceValidator(
    evidence_path="knowledge/architecture/evidence_map.json",
    project_root="/path/to/project"
)

# Line range validation
assert validator.validate_line_ranges()

# File existence
assert validator.validate_file_paths()
```

### `SynthesisValidator` (helpers/synthesis_validator.py)
```python
from tests.e2e.helpers import SynthesisValidator

validator = SynthesisValidator(
    facts_path="knowledge/architecture/architecture_facts.json",
    c4_path="knowledge/architecture/c4/",
    arc42_path="knowledge/architecture/arc42/"
)

# Evidence-first compliance
assert validator.validate_no_hallucinations()

# Completeness (all containers/components present)
assert validator.validate_completeness()

# Mermaid syntax
assert validator.validate_mermaid_syntax()
```

## Known Issues & Expected Failures

### Phase 1 Known Issues
1. **Duplicate Component IDs**: Parser treats keywords as class names
   - Example: "is", "for", "with" appear multiple times
   - Status: Low priority, documented in `test_known_issues.py`

2. **REST Endpoint Detection**: SpringCollector misses multi-line annotations
   - Example: Only 2 endpoints found, expected 50+
   - Status: Medium priority, workaround available

### Phase 2 Known Issues (FIXED)
1. ~~**FileReadTool Missing**: Agents couldn't access architecture_facts.json~~ FIXED
   - Solution: Added FileReadTool to all agents
   - Status: RESOLVED in agents.py + tasks.py

## Test Metrics & Benchmarks

### Performance Expectations
- **Extract** (scan): ~30-40 seconds for 557 components
- **Document** (document): ~2-5 minutes (LLM dependent)
- **Full Workflow**: ~3-6 minutes

### Quality Thresholds
- Evidence coverage: >=95% (all facts have evidence IDs)
- ID uniqueness: >=98% (max 10 known duplicates)
- Relation consistency: 100% (all relation IDs valid)
- Synthesis completeness: 100% (no missing containers)

## Debugging Failed Tests

### Enable Debug Logging
```bash
pytest tests/e2e/ -v --log-cli-level=DEBUG
```

### Preserve Test Artifacts
```python
# In conftest.py, disable cleanup:
@pytest.fixture
def temp_workspace(tmp_path, request):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    yield workspace
    # Comment out cleanup for debugging:
    # shutil.rmtree(workspace)
```

### Inspect Generated Files
```python
def test_debug_output(temp_workspace):
    # ... run test ...
    facts_path = temp_workspace / "knowledge" / "architecture" / "architecture_facts.json"
    print(f"\nGenerated facts: {facts_path}")
    print(facts_path.read_text())
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      
      - name: Run E2E Tests
        run: pytest tests/e2e/ -v --cov=src/aicodegencrew
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

## Writing New E2E Tests

### Template
```python
import pytest
from pathlib import Path
from tests.e2e.helpers import FactsValidator

@pytest.mark.e2e
@pytest.mark.slow
def test_new_feature(temp_workspace, orchestrator):
    """
    Test description: What this test validates.
    
    Given: Initial state
    When: Action performed
    Then: Expected outcome
    """
    # Arrange
    project_root = temp_workspace / "project"
    project_root.mkdir(parents=True)
    
    # Act
    result = orchestrator.run_phase("phase_name", project_root)
    
    # Assert
    assert result.success
    
    # Validate outputs
    validator = FactsValidator(
        facts_path=project_root / "knowledge" / "architecture" / "architecture_facts.json"
    )
    assert validator.validate_schema()
```

### Best Practices
1. Use descriptive test names: `test_phase1_extracts_all_spring_controllers`
2. Follow AAA pattern: Arrange, Act, Assert
3. Use fixtures for setup/teardown
4. Add docstrings with Given/When/Then format
5. Mark slow tests: `@pytest.mark.slow`
6. Mark smoke tests: `@pytest.mark.smoke`
7. Use validation helpers instead of manual checks
8. Clean up temporary resources
9. Test both success and failure scenarios
10. Use parametrize for multiple scenarios

## Resources

- **pytest Documentation**: https://docs.pytest.org/
- **CrewAI Testing**: https://docs.crewai.com/testing/
- **Test Pyramids**: Unit (70%) -> Integration (20%) -> E2E (10%)
- **Evidence-First Architecture**: [AI_SDLC_ARCHITECTURE.md](../../AI_SDLC_ARCHITECTURE.md)

## Support

If tests fail unexpectedly:
1. Check logs: `logs/` directory
2. Review generated files: `knowledge/architecture/`
3. Run validation scripts: `tests/e2e/helpers/`
4. See known issues above
5. File bug report with test output + generated files
