import json
from pathlib import Path
from unittest.mock import patch

from aicodegencrew.hybrid.code_generation.crew import ImplementCrew
from aicodegencrew.hybrid.code_generation.output_writer import OutputWriter
from aicodegencrew.hybrid.code_generation.preflight.dependency_graph import (
    DependencyGraphBuilder,
)
from aicodegencrew.hybrid.code_generation.preflight.import_index import ImportIndex
from aicodegencrew.hybrid.code_generation.preflight.task_source_reader import (
    TaskSourceReader,
)
from aicodegencrew.hybrid.code_generation.schemas import (
    CodegenPlanInput,
    ComponentTarget,
    GeneratedFile,
)
from aicodegencrew.hybrid.code_generation.tasks import implement_task
from aicodegencrew.hybrid.code_generation.tools.build_runner_tool import (
    BuildRunnerTool,
    ContainerConfig,
)
from aicodegencrew.hybrid.code_generation.tools.code_reader_tool import CodeReaderTool


def test_output_writer_blocks_prefix_path_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "repo2" / "escape.txt"
    outside.parent.mkdir(parents=True, exist_ok=True)

    writer = OutputWriter(repo_path=str(repo))
    blocked = writer._write_file(
        GeneratedFile(file_path=str(outside), content="secret", action="create")
    )
    assert blocked is False
    assert not outside.exists()

    allowed = writer._write_file(
        GeneratedFile(file_path="src/app.ts", content="export const ok = true;", action="create")
    )
    assert allowed is True
    assert (repo / "src" / "app.ts").exists()


def test_code_reader_rejects_absolute_paths_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    inside = repo / "src" / "component.ts"
    inside.parent.mkdir(parents=True, exist_ok=True)
    inside.write_text("export class Component {}", encoding="utf-8")

    outside = tmp_path / "outside.ts"
    outside.write_text("export const leaked = true", encoding="utf-8")

    tool = CodeReaderTool(repo_path=str(repo))
    inside_result = json.loads(tool._run(str(inside)))
    outside_result = json.loads(tool._run(str(outside)))

    assert "error" not in inside_result
    assert inside_result["language"] == "typescript"
    assert "error" in outside_result


def test_dependency_graph_reads_file_paths_and_from_to_keys(tmp_path: Path) -> None:
    facts_path = tmp_path / "architecture_facts.json"
    facts_path.write_text(
        json.dumps(
            {
                "components": [
                    {"id": "comp.a", "file_paths": ["src/a.ts"]},
                    {"id": "comp.b", "file_paths": ["src/b.ts"]},
                ],
                "relations": [
                    {"from": "comp.a", "to": "comp.b", "type": "uses"}
                ],
            }
        ),
        encoding="utf-8",
    )

    affected = [
        ComponentTarget(id="comp.a", name="A", file_path="src/a.ts"),
        ComponentTarget(id="comp.b", name="B", file_path="src/b.ts"),
    ]
    order = DependencyGraphBuilder(facts_path=str(facts_path)).run(affected, ImportIndex())

    assert "src/a.ts" in order.dependency_graph
    assert "src/b.ts" in order.dependency_graph["src/a.ts"]


def test_build_runner_applies_root_container_staging(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    readme = repo / "README.md"
    readme.write_text("before", encoding="utf-8")

    tool = BuildRunnerTool(
        repo_path=str(repo),
        staging={"README.md": {"content": "after", "action": "modify"}},
    )
    config = ContainerConfig(
        container_id="container.root",
        name="root",
        root_path="",
        build_cwd=".",
        build_command="echo ok",
        build_tool="npm",
    )

    backup = tool._apply_staging(config)
    assert readme.read_text(encoding="utf-8") == "after"
    tool._restore_backup(backup)
    assert readme.read_text(encoding="utf-8") == "before"


def test_build_runner_ignores_outside_repo_staging(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside.ts"
    outside.write_text("before", encoding="utf-8")

    tool = BuildRunnerTool(
        repo_path=str(repo),
        staging={str(outside): {"content": "after", "action": "modify"}},
    )
    config = ContainerConfig(
        container_id="container.root",
        name="root",
        root_path="",
        build_cwd=".",
        build_command="echo ok",
        build_tool="npm",
    )

    backup = tool._apply_staging(config)
    assert backup == {}
    assert outside.read_text(encoding="utf-8") == "before"


def test_verify_builds_baseline_failure_is_not_success(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    facts_path = tmp_path / "architecture_facts.json"
    facts_path.write_text(
        json.dumps(
            {
                "containers": [
                    {
                        "id": "container.app",
                        "name": "app",
                        "type": "backend",
                        "root_path": "src",
                        "metadata": {"build_system": "npm", "language": "typescript"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    plan = CodegenPlanInput(
        task_id="T-1",
        task_type="feature",
        summary="test",
        affected_components=[
            ComponentTarget(id="comp.a", name="A", file_path="src/a.ts"),
        ],
        implementation_steps=["update file"],
    )

    crew = ImplementCrew(repo_path=str(repo), facts_path=str(facts_path))

    def _fake_run(self, container_id: str, baseline: bool = False) -> str:
        return json.dumps(
            {
                "container_id": container_id,
                "container_name": "app",
                "build_tool": "npm",
                "build_command": "npm run build",
                "success": False if baseline else True,
                "exit_code": 1 if baseline else 0,
                "output": "baseline failed" if baseline else "ok",
            }
        )

    with patch.object(BuildRunnerTool, "_run", autospec=True, side_effect=_fake_run):
        result = crew._verify_builds(plan=plan, staging={})

    assert result.all_passed is False
    assert result.total_containers_failed == 1
    assert len(result.container_results) == 1
    assert result.container_results[0].success is False
    assert "Baseline broken" in result.container_results[0].error_summary


def test_task_source_reader_reads_matching_jira_xml(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    xml_path = task_dir / "T-123.xml"
    xml_path.write_text(
        (
            "<rss><channel><item>"
            "<key>T-123</key>"
            "<summary>Implement endpoint</summary>"
            "<description>Must support idempotency key</description>"
            "<priority>High</priority>"
            "<type>Story</type>"
            "<label>backend</label>"
            "<component>api</component>"
            "</item></channel></rss>"
        ),
        encoding="utf-8",
    )

    result = TaskSourceReader(task_input_dir=str(task_dir)).run(task_id="T-123")

    assert result["found"] is True
    assert result["task_id"] == "T-123"
    assert result["summary"] == "Implement endpoint"
    assert result["description"] == "Must support idempotency key"
    assert result["priority"] == "High"
    assert result["jira_type"] == "Story"
    assert result["source_file"].endswith("T-123.xml")
    assert "Summary: Implement endpoint" in result["excerpt"]


def test_task_source_reader_returns_error_without_task_input_dir() -> None:
    result = TaskSourceReader(task_input_dir="").run(task_id="T-123")
    assert result["found"] is False
    assert "TASK_INPUT_DIR is not configured" in result["error"]


def test_implement_task_prompt_requires_task_source_and_evidence() -> None:
    description, _ = implement_task(
        task_id="T-123",
        summary="Implement endpoint",
        description="Use original task intent",
        task_type="feature",
        implementation_steps=["Update handler", "Add test"],
        upgrade_plan=None,
        dependency_order=["src/api/handler.ts"],
        task_source_snapshot="- source_file: inputs/tasks/T-123.xml",
    )

    assert 'read_task_source(task_id="T-123")' in description
    assert "Treat read_plan() and implementation_steps as GUIDANCE" in description
    assert "facts_query and rag_query" in description
    assert "actual task source -> architecture facts -> codebase evidence" in description
