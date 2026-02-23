"""Rule-based issue classification.

Reuses TASK_TYPE_RULES pattern from stage1_input_parser.py, enhanced with
log-context scanning for stack traces and exceptions.
"""

import re

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)

# Classification rules — extend without touching classify_issue() logic.
_CLASSIFICATION_RULES: dict[str, dict] = {
    "bug": {
        "keywords": [
            "bug", "error", "crash", "exception", "fail", "broken",
            "regression", "defect", "nullpointer", "stacktrace",
            "traceback", "500", "404", "timeout", "deadlock",
        ],
        "log_patterns": [
            r"(?i)(exception|error|fatal|caused by|traceback|stack\s*trace)",
            r"(?i)(nullpointer|classnotfound|outofmemory|segfault)",
        ],
    },
    "feature": {
        "keywords": [
            "feature", "implement", "add", "new", "create", "introduce",
            "enable", "support", "extend",
        ],
    },
    "refactor": {
        "keywords": [
            "refactor", "cleanup", "clean up", "technical debt", "restructure",
            "modernize", "deprecat", "migrate",
        ],
    },
    "investigation": {
        "keywords": [
            "investigate", "research", "spike", "analyse", "analyze",
            "evaluate", "assess", "explore", "poc", "proof of concept",
        ],
    },
}

# Stack trace / exception patterns in log context
_STACK_TRACE_RE = re.compile(
    r"(?i)(exception|error|fatal|caused by|traceback|at\s+[\w.]+\([\w.]+:\d+\))",
)


def classify_issue(
    title: str,
    description: str,
    log_context: str | None = None,
) -> dict:
    """Classify an issue as bug | feature | refactor | investigation.

    Returns:
        {"type": "bug", "confidence": 0.85, "signals": ["keyword:error", "log:exception"]}
    """
    text = f"{title} {description}".lower()
    signals: list[str] = []
    scores: dict[str, float] = {k: 0.0 for k in _CLASSIFICATION_RULES}

    # Keyword scoring
    for issue_type, rules in _CLASSIFICATION_RULES.items():
        for kw in rules.get("keywords", []):
            if kw in text:
                scores[issue_type] += 1.0
                signals.append(f"keyword:{kw}")

    # Log context scanning — strong bug signal
    if log_context:
        log_lower = log_context.lower()
        for issue_type, rules in _CLASSIFICATION_RULES.items():
            for pattern in rules.get("log_patterns", []):
                if re.search(pattern, log_lower):
                    scores[issue_type] += 2.0
                    signals.append(f"log:{pattern[:30]}")

        # Stack traces are a strong bug indicator
        if _STACK_TRACE_RE.search(log_context):
            scores["bug"] += 3.0
            signals.append("log:stack_trace_detected")

    # Pick highest scoring type
    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_type]

    # Default to "feature" if no signals
    if best_score == 0:
        best_type = "feature"
        confidence = 0.3
    else:
        total = sum(scores.values())
        confidence = round(best_score / total, 2) if total > 0 else 0.3

    # Clamp confidence
    confidence = min(confidence, 0.99)

    logger.info("[Classifier] %s (confidence=%.2f, signals=%d)", best_type, confidence, len(signals))
    return {
        "type": best_type,
        "confidence": confidence,
        "signals": signals[:15],  # cap signal list
    }
