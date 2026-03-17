"""Python Runtime Specialist — Extracts Python runtime behavior facts.

Detects:
- Celery tasks (@shared_task, @task, @app.task)
- APScheduler scheduled jobs (@scheduler.scheduled_job)
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawRuntimeFact


class PythonRuntimeCollector(DimensionCollector):
    """Extracts Python runtime behavior facts."""

    DIMENSION = "runtime"

    CELERY_TASK_PATTERN = re.compile(r"@(?:shared_task|task|app\.task)\s*(?:\([^)]*\))?")
    APSCHEDULER_PATTERN = re.compile(r"@\w+\.scheduled_job\s*\(\s*['\"](\w+)['\"]")
    PY_METHOD_AFTER_DECORATOR = re.compile(r"def\s+(\w+)\s*\(")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python runtime facts: Celery tasks, APScheduler jobs."""
        self._log_start()

        py_files = self._find_files("*.py")

        for py_file in py_files:
            content = self._read_file_content(py_file)
            if not content:
                continue

            rel_path = self._relative_path(py_file)

            # Celery @task, @shared_task, @app.task
            for match in self.CELERY_TASK_PATTERN.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                func_match = self.PY_METHOD_AFTER_DECORATOR.search(content[match.end():match.end() + 200])
                func_name = func_match.group(1) if func_match else "unknown"

                fact = RawRuntimeFact(
                    name=func_name,
                    type="async",
                    metadata={"framework": "celery", "mechanism": "task_decorator"},
                )
                fact.add_evidence(path=rel_path, line_start=line_num, line_end=line_num + 5, reason=f"Celery task: {func_name}")
                self.output.add_fact(fact)

            # APScheduler @scheduler.scheduled_job('interval', ...)
            for match in self.APSCHEDULER_PATTERN.finditer(content):
                trigger_type = match.group(1)
                line_num = content[: match.start()].count("\n") + 1
                func_match = self.PY_METHOD_AFTER_DECORATOR.search(content[match.end():match.end() + 200])
                func_name = func_match.group(1) if func_match else "unknown"

                fact = RawRuntimeFact(
                    name=func_name,
                    type="scheduler",
                    trigger=trigger_type,
                    metadata={"framework": "apscheduler", "trigger_type": trigger_type},
                )
                fact.add_evidence(path=rel_path, line_start=line_num, line_end=line_num + 5, reason=f"APScheduler job: {func_name} ({trigger_type})")
                self.output.add_fact(fact)

        self._log_end()
        return self.output
