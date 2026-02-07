"""Callback utilities for CrewAI monitoring."""

import logging

logger = logging.getLogger(__name__)


def step_callback(step_output) -> None:
    """
    Callback for each agent step - logs activity to file + console.

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

        # Thought/Reasoning — verbose, file only
        thought = getattr(step_output, 'thought', None)
        if thought:
            thought_str = str(thought)
            logger.debug(
                f"[THINK] {agent_name}: "
                f"{thought_str[:500]}{'...' if len(thought_str) > 500 else ''}"
            )

        # Tool calls — important, file + console
        tool = getattr(step_output, 'tool', None)
        tool_input = getattr(step_output, 'tool_input', None)
        if tool:
            input_str = str(tool_input) if tool_input else ""
            logger.info(
                f"[TOOL] {tool}: "
                f"{input_str[:200]}{'...' if len(input_str) > 200 else ''}"
            )

        # Tool result — verbose, file only
        result = getattr(step_output, 'result', None) or getattr(step_output, 'observation', None)
        if result:
            result_str = str(result)
            logger.debug(
                f"[TOOL_RESULT] {result_str[:300]}{'...' if len(result_str) > 300 else ''}"
            )

    except Exception as e:
        logger.warning(f"Step callback error: {e}")


def task_callback(task_output) -> None:
    """
    Callback when a task is completed.

    Args:
        task_output: CrewAI task output with result
    """
    try:
        description = getattr(task_output, 'description', None)
        desc_short = description[:80] if description else "N/A"
        logger.info(f"[TASK] Completed: {desc_short}")

        raw = getattr(task_output, 'raw', None)
        if raw:
            output_str = str(raw)
            logger.debug(
                f"[TASK_OUTPUT] {output_str[:500]}{'...' if len(output_str) > 500 else ''}"
            )

    except Exception as e:
        logger.warning(f"Task callback error: {e}")
