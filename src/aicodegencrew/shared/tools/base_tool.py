"""Base tool class with common functionality and error handling."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolMetrics(BaseModel):
    """Metrics for tool execution."""

    tool_name: str
    execution_time: float
    success: bool
    error_message: str | None = None
    retry_count: int = 0


class EnhancedBaseTool(BaseTool, ABC):
    """Enhanced base tool with retry logic and monitoring."""

    # Tool configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0

    def _execute_with_retry(self, func, *args, **kwargs) -> dict[str, Any]:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Log metrics
                self._log_metrics(
                    ToolMetrics(tool_name=self.name, execution_time=execution_time, success=True, retry_count=attempt)
                )

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Tool {self.name} attempt {attempt + 1}/{self.max_retries} failed: {e!s}")

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    # Log failure metrics
                    self._log_metrics(
                        ToolMetrics(
                            tool_name=self.name,
                            execution_time=0,
                            success=False,
                            error_message=str(e),
                            retry_count=attempt + 1,
                        )
                    )

        # All retries exhausted
        error_msg = f"Tool {self.name} failed after {self.max_retries} attempts: {last_error!s}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_error

    def _log_metrics(self, metrics: ToolMetrics):
        """Log tool execution metrics.

        Args:
            metrics: Tool metrics to log
        """
        if metrics.success:
            logger.info(
                f"[OK] {metrics.tool_name} completed in {metrics.execution_time:.2f}s "
                f"(attempts: {metrics.retry_count + 1})"
            )
        else:
            logger.error(
                f"[FAIL] {metrics.tool_name} failed after {metrics.retry_count} attempts: {metrics.error_message}"
            )

    def _validate_input(self, **kwargs) -> dict[str, Any]:
        """Validate tool input against schema.

        Args:
            **kwargs: Input parameters

        Returns:
            Validated input dictionary

        Raises:
            ValueError: If validation fails
        """
        try:
            validated = self.args_schema(**kwargs)
            return validated.dict()
        except Exception as e:
            logger.error(f"Input validation failed for {self.name}: {e!s}")
            raise ValueError(f"Invalid input: {e!s}") from e

    def _format_success_response(self, data: Any, **metadata) -> dict[str, Any]:
        """Format successful tool response.

        Args:
            data: Response data
            **metadata: Additional metadata

        Returns:
            Formatted response dictionary
        """
        return {"success": True, "data": data, "metadata": {"tool_name": self.name, **metadata}}

    def _format_error_response(self, error: Exception, **metadata) -> dict[str, Any]:
        """Format error tool response.

        Args:
            error: Exception that occurred
            **metadata: Additional metadata

        Returns:
            Formatted error response dictionary
        """
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "metadata": {"tool_name": self.name, **metadata},
        }

    @abstractmethod
    def _execute(self, **kwargs) -> dict[str, Any]:
        """Execute the tool's main logic.

        This method should be implemented by subclasses.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        pass

    def _run(self, **kwargs) -> dict[str, Any]:
        """Main execution method with error handling.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        try:
            # Validate input
            validated_input = self._validate_input(**kwargs)

            # Execute with retry logic
            result = self._execute_with_retry(self._execute, **validated_input)

            return result

        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e!s}", exc_info=True)
            return self._format_error_response(e)


class ToolConfig(BaseModel):
    """Configuration for tool initialization."""

    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")
    timeout: float = Field(default=30.0, description="Execution timeout in seconds")
    verbose: bool = Field(default=True, description="Enable verbose logging")


def create_tool_with_config(tool_class: type[EnhancedBaseTool], config: ToolConfig) -> EnhancedBaseTool:
    """Factory function to create tool with configuration.

    Args:
        tool_class: Tool class to instantiate
        config: Tool configuration

    Returns:
        Configured tool instance
    """
    tool = tool_class()
    tool.max_retries = config.max_retries
    tool.retry_delay = config.retry_delay
    tool.timeout = config.timeout
    return tool
