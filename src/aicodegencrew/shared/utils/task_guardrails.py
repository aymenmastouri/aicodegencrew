"""Task-level guardrails for CrewAI output validation."""
import json
import logging

logger = logging.getLogger(__name__)


def validate_json_output(task_output) -> tuple[bool, str]:
    """Guardrail: reject output that is not valid JSON."""
    raw = task_output.raw if hasattr(task_output, "raw") else str(task_output)
    text = raw.strip()
    # Strip markdown fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        json.loads(text)
        return (True, text)
    except json.JSONDecodeError as e:
        logger.info("[Guardrail] JSON validation failed: %s", e)
        return (False, f"Output is not valid JSON: {e}. Please output ONLY a valid JSON object.")


def validate_plan_json(task_output) -> tuple[bool, str]:
    """Guardrail: reject plan output missing required keys.

    Accepts two formats:
    1. Full wrapper: {"task_id": ..., "understanding": ..., "development_plan": ...}
    2. Bare plan: {"affected_components": ..., "implementation_steps": ...}
       (Stage 4 _plan_from_dict wraps this automatically after the guardrail)
    """
    raw = task_output.raw if hasattr(task_output, "raw") else str(task_output)
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return (False, f"Output is not valid JSON: {e}. Please output ONLY a valid JSON object.")
    # Accept full wrapper format
    if "development_plan" in data:
        return (True, text)
    # Accept bare plan (has plan-level keys like affected_components or implementation_steps)
    plan_keys = {"affected_components", "implementation_steps", "test_strategy", "estimated_complexity"}
    if plan_keys & set(data.keys()):
        return (True, text)
    return (False, "JSON must contain 'development_plan' key or plan-level keys (affected_components, implementation_steps). Please output a valid plan JSON.")

