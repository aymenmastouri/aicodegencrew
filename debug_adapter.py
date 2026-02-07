#!/usr/bin/env python
"""Debug the adapter container assignment."""
import sys
sys.path.insert(0, 'src')

from aicodegencrew.pipelines.architecture_facts.collectors.orchestrator import CollectorOrchestrator
from aicodegencrew.pipelines.architecture_facts.collectors.fact_adapter import DimensionResultsAdapter

# Step 1: Run orchestrator
o = CollectorOrchestrator('c:/uvz', 'knowledge/test_run')
o._run_container_collector()
o._run_component_collector()

# Check raw facts
print(f"Raw components: {len(o.results.components)}")
frontend_raw = [c for c in o.results.components if hasattr(c, 'container_hint') and c.container_hint == 'frontend']
print(f"Frontend raw (container_hint): {len(frontend_raw)}")

# Step 2: Adapt
adapter = DimensionResultsAdapter('c:/uvz')
adapted = adapter.convert(o.results)

# Check adapted
frontend = [c for c in adapted['components'] if c.container == 'frontend']
backend = [c for c in adapted['components'] if c.container == 'backend']
print(f"Adapted - Frontend: {len(frontend)}, Backend: {len(backend)}, Total: {len(adapted['components'])}")

# Debug first frontend component if any
if frontend:
    print(f"Example frontend: {frontend[0].name}, container: {frontend[0].container}")
else:
    # Check what containers are assigned
    containers = set(c.container for c in adapted['components'])
    print(f"All containers in adapted: {containers}")
