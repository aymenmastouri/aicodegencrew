"""Python Workflow Specialist — Extracts Python workflow facts.

Detects:
- Celery chain/chord/group patterns
- Airflow DAG definitions and tasks
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..workflow_collector import RawWorkflow


class PythonWorkflowCollector(DimensionCollector):
    """Extracts Python workflow facts."""

    DIMENSION = "workflows"

    # Python workflow patterns
    CELERY_CHAIN_PATTERN = re.compile(r"(?:chain|chord|group)\s*\(")
    AIRFLOW_DAG_PATTERN = re.compile(r"(?:DAG\s*\(|@dag\b)")
    AIRFLOW_TASK_PATTERN = re.compile(r"(?:@task\b|PythonOperator|BashOperator|BranchPythonOperator)")

    def __init__(self, repo_path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._workflows: dict[str, RawWorkflow] = {}

    def collect(self) -> CollectorOutput:
        """Collect Python workflows: Celery chain/chord/group, Airflow DAGs."""
        self._log_start()

        py_files = [f for f in self._find_files("*.py") if ".spec." not in str(f)]

        for py_file in py_files:
            content = self._read_file_content(py_file)
            if not content:
                continue

            rel_path = self._relative_path(py_file)

            # Celery chain/chord/group
            celery_matches = list(self.CELERY_CHAIN_PATTERN.finditer(content))
            if len(celery_matches) >= 2:
                class_match = re.search(r"(?:class|def)\s+(\w+)", content)
                name = class_match.group(1) if class_match else py_file.stem

                if not any(name in key for key in self._workflows):
                    workflow = RawWorkflow(
                        name=name,
                        workflow_type="celery_workflow",
                        container_hint=self.container_id,
                        file_path=rel_path,
                        metadata={"chain_count": len(celery_matches)},
                    )
                    workflow.tags.append("celery")
                    workflow.add_evidence(
                        path=rel_path, line_start=1, line_end=30,
                        reason=f"Celery workflow: {name} ({len(celery_matches)} chains/groups)",
                    )
                    self._workflows[f"celery_{name}"] = workflow

            # Airflow DAGs
            if self.AIRFLOW_DAG_PATTERN.search(content):
                # Find DAG name
                dag_name_match = re.search(r"DAG\s*\(\s*['\"]([^'\"]+)['\"]", content)
                dag_name = dag_name_match.group(1) if dag_name_match else py_file.stem

                # Find tasks
                task_names = []
                for task_match in re.finditer(r"task_id\s*=\s*['\"]([^'\"]+)['\"]", content):
                    task_names.append(task_match.group(1))

                workflow = RawWorkflow(
                    name=dag_name,
                    workflow_type="airflow_dag",
                    states=task_names,
                    container_hint=self.container_id,
                    file_path=rel_path,
                    metadata={"task_count": len(task_names)},
                )
                workflow.tags.append("airflow")
                line_num = content[: self.AIRFLOW_DAG_PATTERN.search(content).start()].count("\n") + 1
                workflow.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 30,
                    reason=f"Airflow DAG: {dag_name} ({len(task_names)} tasks)",
                )
                self._workflows[f"airflow_{dag_name}"] = workflow

        # Add all to output
        for workflow in self._workflows.values():
            self.output.add_fact(workflow)

        self._log_end()
        return self.output
