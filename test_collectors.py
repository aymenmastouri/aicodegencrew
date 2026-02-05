"""Test script for CollectorOrchestrator."""
from pathlib import Path
from aicodegencrew.pipelines.architecture_facts.collectors.orchestrator import CollectorOrchestrator

repo = Path('C:/uvz')
print(f'Testing CollectorOrchestrator on {repo}')

orch = CollectorOrchestrator(repo)
results = orch.run_all()

stats = results.get_statistics()
print('\n=== Collector Statistics ===')
for k, v in stats.items():
    print(f'  {k}: {v}')

print('\n=== Containers ===')
for c in results.containers:
    print(f"  {c['name']} ({c['technology']}) - {c['type']}")

print('\n=== Components (first 20) ===')
for comp in results.components[:20]:
    print(f"  {comp.name} [{comp.stereotype}]")

print('\n=== Dependencies (first 20) ===')
for dep in results.dependencies[:20]:
    print(f"  {dep.name} ({dep.version})")

print('\n=== Workflows ===')
for wf in results.workflows:
    states = getattr(wf, 'states', [])
    actions = getattr(wf, 'actions', [])
    print(f"  {wf.name} [{wf.workflow_type}] - {len(states)} states, {len(actions)} actions")
