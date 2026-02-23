"""Risk assessment aggregation.

Combines security details, error handling, and quality scores
for affected components to determine overall risk level.
"""

from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def assess_risk(
    affected_components: list[dict],
    knowledge_context: dict[str, Any],
) -> dict:
    """Assess risk for affected components.

    Checks:
      - security_details → auth/encryption/CORS sensitivity
      - error_handling → exception handling gaps
      - analyzed_architecture → quality scores + known issues

    Args:
        affected_components: Blast-radius affected list (with "component" key).
        knowledge_context:   Output from KnowledgeLoader.load_available_context().

    Returns:
        {"risk_level": "high", "security_sensitive": bool, "flags": [str]}
    """
    facts = knowledge_context.get("extract", {}).get("architecture_facts", {})
    analyzed = knowledge_context.get("analyze", {}).get("analyzed_architecture", {})
    affected_names = {c.get("component", "").lower() for c in affected_components if c.get("component")}

    flags: list[str] = []
    security_sensitive = False
    risk_score = 0  # 0-10 scale

    # ── Security dimension ──────────────────────────────────────────
    security = facts.get("security", [])
    if isinstance(security, list):
        for sec in security:
            sec_class = (sec.get("class_name", "") or sec.get("name", "")).lower()
            if sec_class in affected_names or any(n in sec_class for n in affected_names):
                security_sensitive = True
                sec_type = sec.get("security_type", sec.get("type", "security"))
                flags.append(f"security:{sec_type}")
                risk_score += 2

    # Also check if affected components touch authentication/authorization
    auth_keywords = {"auth", "login", "token", "session", "permission", "role", "security", "oauth", "jwt"}
    for name in affected_names:
        if any(kw in name for kw in auth_keywords):
            security_sensitive = True
            flags.append(f"auth_component:{name}")
            risk_score += 2

    # ── Error handling dimension ────────────────────────────────────
    error_handling = facts.get("error_handling", [])
    if isinstance(error_handling, list):
        handled_classes = set()
        for eh in error_handling:
            handled_classes.add((eh.get("exception_class", "") or eh.get("class_name", "")).lower())
        # Check if affected components have error handling
        missing_handling = affected_names - handled_classes
        if missing_handling and len(affected_names) > 0:
            gap_ratio = len(missing_handling) / len(affected_names)
            if gap_ratio > 0.5:
                flags.append("error_handling:gaps_detected")
                risk_score += 1

    # ── Architecture quality ────────────────────────────────────────
    quality = analyzed.get("quality", analyzed.get("quality_assessment", {}))
    if isinstance(quality, dict):
        overall_score = quality.get("overall_score", quality.get("score", 0))
        if isinstance(overall_score, (int, float)):
            if overall_score < 50:
                flags.append(f"quality:low_score({overall_score})")
                risk_score += 2
            elif overall_score < 70:
                flags.append(f"quality:medium_score({overall_score})")
                risk_score += 1

    # Known issues from analysis
    issues = analyzed.get("issues", [])
    if isinstance(issues, list):
        for issue in issues[:10]:
            issue_text = str(issue).lower()
            if any(name in issue_text for name in affected_names):
                flags.append("known_issue:affects_area")
                risk_score += 1
                break

    # ── Blast radius size factor ────────────────────────────────────
    comp_count = len(affected_components)
    if comp_count > 20:
        flags.append(f"blast_radius:large({comp_count})")
        risk_score += 2
    elif comp_count > 10:
        flags.append(f"blast_radius:medium({comp_count})")
        risk_score += 1

    # ── Determine risk level ────────────────────────────────────────
    if risk_score >= 7:
        risk_level = "critical"
    elif risk_score >= 5:
        risk_level = "high"
    elif risk_score >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    logger.info("[RiskAssessor] risk=%s, score=%d, security=%s", risk_level, risk_score, security_sensitive)
    return {
        "risk_level": risk_level,
        "security_sensitive": security_sensitive,
        "flags": flags[:15],
    }
