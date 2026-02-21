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
    """Guardrail: reject plan output missing required keys."""
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
    required = {"task_id", "understanding", "development_plan"}
    missing = required - set(data.keys())
    if missing:
        return (False, f"Missing required keys: {missing}. Include all of: {required}")
    return (True, text)
