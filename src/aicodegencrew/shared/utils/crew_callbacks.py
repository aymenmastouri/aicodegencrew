"""Callback utilities for CrewAI monitoring and error handling."""

import logging
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def step_callback(step_output) -> None:
    """
    Callback for each agent step - shows detailed activity.
    
    Args:
        step_output: CrewAI step output object with agent activities
    """
    try:
        # Agent Info - handle both string and Agent object
        agent_attr = getattr(step_output, 'agent', None)
        if agent_attr is None:
            agent_name = "Agent"
        elif hasattr(agent_attr, 'role'):
            agent_name = agent_attr.role
        elif hasattr(agent_attr, 'name'):
            agent_name = agent_attr.name
        else:
            agent_name = str(agent_attr) if agent_attr else "Agent"
        
        # Thought/Reasoning of the agent
        thought = getattr(step_output, 'thought', None)
        if thought:
            print(f"\n{'='*60}")
            print(f"AGENT THINKING: {agent_name}")
            print(f"{'='*60}")
            print(f"{thought[:500]}..." if len(str(thought)) > 500 else thought)
        
        # Tool-Aufrufe
        tool = getattr(step_output, 'tool', None)
        tool_input = getattr(step_output, 'tool_input', None)
        if tool:
            print(f"\nTOOL CALL: {tool}")
            if tool_input:
                input_str = str(tool_input)
                print(f"   Input: {input_str[:200]}..." if len(input_str) > 200 else f"   Input: {input_str}")
        
        # Tool Output/Result
        result = getattr(step_output, 'result', None) or getattr(step_output, 'observation', None)
        if result:
            result_str = str(result)
            print(f"   Result: {result_str[:300]}..." if len(result_str) > 300 else f"   Result: {result_str}")
        
        # Log auch in File
        logger.debug(f"Step - Agent: {agent_name}, Tool: {tool}, Input: {tool_input}")
        
    except Exception as e:
        logger.warning(f"Step callback error: {e}")
        # Fallback: zeige raw output
        print(f"\nSTEP: {step_output}")


def task_callback(task_output) -> None:
    """
    Callback wenn ein Task abgeschlossen ist.
    
    Args:
        task_output: CrewAI task output mit Ergebnis
    """
    try:
        print(f"\n{'#'*60}")
        print(f"TASK COMPLETED")
        print(f"{'#'*60}")
        
        # Task description
        description = getattr(task_output, 'description', None)
        if description:
            print(f"Task: {description[:100]}...")
        
        # Output/Result
        raw = getattr(task_output, 'raw', None)
        if raw:
            output_str = str(raw)
            print(f"Output: {output_str[:500]}..." if len(output_str) > 500 else f"Output: {output_str}")
        
        # Summary
        summary = getattr(task_output, 'summary', None)
        if summary:
            # Encode to ASCII to avoid Unicode errors on Windows console
            safe_summary = summary.encode('ascii', 'replace').decode('ascii')
            print(f"Summary: {safe_summary}")
            
        print(f"{'#'*60}\n")
        
        logger.info(f"Task completed - Description: {description[:50] if description else 'N/A'}...")
        
    except Exception as e:
        logger.warning(f"Task callback error: {e}")
        # Encode to ASCII to avoid Unicode errors
        safe_output = str(task_output).encode('ascii', 'replace').decode('ascii')
        print(f"\nTASK DONE: {safe_output}")


class CrewMonitorCallback:
    """Monitor crew execution with callbacks."""
    
    def __init__(self, log_dir: str = "./logs"):
        """Initialize callback handler.
        
        Args:
            log_dir: Directory for execution logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = None
        self.task_timings = {}
        
    def on_crew_start(self, inputs: Dict[str, Any]) -> None:
        """Called when crew execution starts."""
        self.start_time = datetime.now()
        logger.info(f"Crew started at {self.start_time.isoformat()}")
        logger.info(f"Inputs: {inputs}")
        
    def on_task_start(self, task_name: str) -> None:
        """Called when a task starts."""
        self.task_timings[task_name] = {
            "start": datetime.now(),
            "end": None,
            "duration": None
        }
        logger.info(f"Task started: {task_name}")
        
    def on_task_end(self, task_name: str, output: Any) -> None:
        """Called when a task completes."""
        end_time = datetime.now()
        if task_name in self.task_timings:
            self.task_timings[task_name]["end"] = end_time
            duration = end_time - self.task_timings[task_name]["start"]
            self.task_timings[task_name]["duration"] = duration.total_seconds()
            logger.info(f"[OK] Task completed: {task_name} (Duration: {duration.total_seconds():.2f}s)")
        
    def on_crew_end(self, result: Any) -> None:
        """Called when crew execution completes."""
        end_time = datetime.now()
        if self.start_time:
            total_duration = (end_time - self.start_time).total_seconds()
            logger.info(f"Crew completed! Total duration: {total_duration:.2f}s")
            
        # Log task summary
        logger.info("Task Execution Summary:")
        for task_name, timing in self.task_timings.items():
            duration = timing.get("duration", "N/A")
            logger.info(f"  - {task_name}: {duration}s")
            
    def on_agent_error(self, agent_name: str, error: Exception) -> None:
        """Called when an agent encounters an error."""
        logger.error(f"[ERROR] Agent error in {agent_name}: {str(error)}", exc_info=True)
        
    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Called when a tool encounters an error."""
        logger.error(f"Tool error in {tool_name}: {str(error)}", exc_info=True)


class CrewRetryHandler:
    """Handle retries for crew operations."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if operation should be retried.
        
        Args:
            attempt: Current attempt number (0-indexed)
            error: Exception that occurred
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False
            
        # Retry on specific error types
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            IOError,
        )
        
        return isinstance(error, retryable_errors)
        
    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay for retry.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        return min(60, self.backoff_factor ** attempt)
