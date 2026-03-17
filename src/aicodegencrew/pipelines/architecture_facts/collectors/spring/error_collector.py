"""Spring Error Handling Specialist — Extracts Java/Kotlin error handling facts.

Detects:
- @ExceptionHandler methods with exception type
- @ControllerAdvice / @RestControllerAdvice classes
- Custom exception classes (extends RuntimeException, etc.)
- ErrorResponse / HTTP status codes in handlers
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawErrorHandlingFact


class SpringErrorCollector(DimensionCollector):
    """Extracts error handling facts from Java/Kotlin sources."""

    DIMENSION = "error_handling"

    # Java patterns
    EXCEPTION_HANDLER_PATTERN = re.compile(
        r"@ExceptionHandler\s*(?:\(\s*(?:value\s*=\s*)?(\w+(?:\.\w+)*)\.class\s*\))?"
    )
    CONTROLLER_ADVICE_PATTERN = re.compile(r"@(ControllerAdvice|RestControllerAdvice)")
    CUSTOM_EXCEPTION_PATTERN = re.compile(
        r"class\s+(\w+Exception|\w+Error)\s+extends\s+(\w+(?:Exception|Error|Throwable))"
    )
    RESPONSE_STATUS_PATTERN = re.compile(r"@ResponseStatus\s*\(\s*(?:value\s*=\s*)?(?:HttpStatus\.)?(\w+)\s*\)")
    HTTP_STATUS_IN_HANDLER = re.compile(r"(?:HttpStatus|ResponseEntity\.status\s*\(\s*HttpStatus)\.(\w+)")
    CLASS_PATTERN = re.compile(r"class\s+(\w+)")
    METHOD_PATTERN = re.compile(r"(?:public|protected|private)\s+\w+(?:<[^>]+>)?\s+(\w+)\s*\(")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect error handling facts from Java/Kotlin files."""
        self._log_start()
        self._collect_java_error_handling()
        self._log_end()
        return self.output

    def _collect_java_error_handling(self):
        """Collect error handling facts from Java/Kotlin files."""
        java_files = self._find_files("*.java") + self._find_files("*.kt")

        logger.info(f"[ErrorHandlingCollector] Scanning {len(java_files)} Java/Kotlin files")

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            class_match = self.CLASS_PATTERN.search(content)
            class_name = class_match.group(1) if class_match else java_file.stem

            # @ControllerAdvice / @RestControllerAdvice classes
            advice_match = self.CONTROLLER_ADVICE_PATTERN.search(content)
            if advice_match:
                advice_type = advice_match.group(1)
                line_num = content[: advice_match.start()].count("\n") + 1

                # Collect all @ExceptionHandler methods within this class
                handlers = list(self.EXCEPTION_HANDLER_PATTERN.finditer(content))
                for handler in handlers:
                    exception_class = handler.group(1) or "Exception"
                    handler_line = content[: handler.start()].count("\n") + 1

                    # Find method name after @ExceptionHandler
                    remaining = content[handler.end() : handler.end() + 300]
                    method_match = self.METHOD_PATTERN.search(remaining)
                    method_name = method_match.group(1) if method_match else "handle"

                    # Find HTTP status
                    handler_block = content[handler.start() : handler.start() + 500]
                    status_match = self.RESPONSE_STATUS_PATTERN.search(handler_block)
                    if not status_match:
                        status_match = self.HTTP_STATUS_IN_HANDLER.search(handler_block)
                    http_status = status_match.group(1) if status_match else ""

                    fact = RawErrorHandlingFact(
                        name=f"{class_name}.{method_name}",
                        handling_type="exception_handler",
                        exception_class=exception_class,
                        http_status=http_status,
                        handler_method=method_name,
                        file_path=self._relative_path(java_file),
                        container_hint=self.container_id,
                        metadata={"advice_class": class_name, "advice_type": advice_type},
                    )
                    fact.add_evidence(
                        path=self._relative_path(java_file),
                        line_start=handler_line,
                        line_end=handler_line + 15,
                        reason=f"@ExceptionHandler({exception_class}) in {class_name}",
                    )
                    self.output.add_fact(fact)

                # Also register the advice class itself
                fact = RawErrorHandlingFact(
                    name=class_name,
                    handling_type="controller_advice",
                    exception_class="",
                    http_status="",
                    handler_method="",
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                    metadata={"handler_count": len(handlers)},
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 10,
                    reason=f"@{advice_type}: {class_name} ({len(handlers)} handlers)",
                )
                self.output.add_fact(fact)

            # Custom exception classes
            for match in self.CUSTOM_EXCEPTION_PATTERN.finditer(content):
                exc_name = match.group(1)
                parent = match.group(2)
                line_num = content[: match.start()].count("\n") + 1

                # Check for @ResponseStatus on the exception
                exc_block = content[max(0, match.start() - 200) : match.start()]
                status_match = self.RESPONSE_STATUS_PATTERN.search(exc_block)
                http_status = status_match.group(1) if status_match else ""

                fact = RawErrorHandlingFact(
                    name=exc_name,
                    handling_type="custom_exception",
                    exception_class=parent,
                    http_status=http_status,
                    handler_method="",
                    file_path=self._relative_path(java_file),
                    container_hint=self.container_id,
                )
                fact.add_evidence(
                    path=self._relative_path(java_file),
                    line_start=line_num,
                    line_end=line_num + 20,
                    reason=f"Custom exception: {exc_name} extends {parent}",
                )
                self.output.add_fact(fact)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
