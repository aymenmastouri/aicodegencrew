"""Triage API routes — issue classification, blast radius, dual-audience reports."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import settings

router = APIRouter(prefix="/api/triage", tags=["triage"])

_triage_dir = settings.knowledge_dir / "triage"


# ── Request schemas ─────────────────────────────────────────────────────────


class TriageFullRequest(BaseModel):
    """Full triage request (deterministic + LLM)."""

    issue_id: str = Field(..., description="Unique issue identifier")
    title: str = Field(default="", description="Issue title")
    description: str = Field(default="", description="Issue description")
    task_file: str | None = Field(default=None, description="Path to task file")
    supplementary_files: dict[str, list[str]] = Field(default_factory=dict)


class TriageQuickRequest(BaseModel):
    """Quick triage request (deterministic only)."""

    title: str = Field(..., description="Issue title")
    description: str = Field(default="", description="Issue description")


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("")
def run_full_triage(body: TriageFullRequest):
    """Run full triage: deterministic analysis + LLM synthesis."""
    try:
        from aicodegencrew.crews.triage import TriageCrew
        from aicodegencrew.crews.triage.schemas import TriageRequest

        crew = TriageCrew(knowledge_dir=str(settings.knowledge_dir))
        request = TriageRequest(
            issue_id=body.issue_id,
            title=body.title,
            description=body.description,
            task_file=body.task_file,
            supplementary_files=body.supplementary_files,
        )
        return crew.run(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
def run_quick_triage(body: TriageQuickRequest):
    """Run quick triage: deterministic only (<2s, no LLM)."""
    try:
        from aicodegencrew.crews.triage import TriageCrew

        crew = TriageCrew(knowledge_dir=str(settings.knowledge_dir))
        return crew.triage_quick(title=body.title, description=body.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
def list_triage_results():
    """List all past triage results."""
    if not _triage_dir.exists():
        return {"results": []}

    results = []
    for f in sorted(_triage_dir.glob("*_triage.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            findings = data.get("findings", {})
            results.append({
                "issue_id": data.get("issue_id", f.stem.replace("_triage", "")),
                "classification": data.get("classification", {}),
                "risk_level": findings.get("risk_assessment", {}).get("risk_level", "unknown"),
                "entry_points_count": len(findings.get("entry_points", [])),
                "blast_radius_count": findings.get("blast_radius", {}).get("component_count", 0),
                "file": f.name,
            })
        except Exception:
            continue

    return {"results": results}


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@router.get("/results/{issue_id}")
def get_triage_result(issue_id: str):
    """Get a specific triage result by issue ID."""
    if not _SAFE_ID_RE.match(issue_id):
        raise HTTPException(status_code=400, detail="Invalid issue_id")
    triage_file = _triage_dir / f"{issue_id}_triage.json"
    if not triage_file.exists():
        raise HTTPException(status_code=404, detail=f"No triage result for {issue_id}")

    data = json.loads(triage_file.read_text(encoding="utf-8"))
    result: dict = {"triage": data}

    # Attach markdown reports if available
    customer_md = _triage_dir / f"{issue_id}_customer.md"
    if customer_md.exists():
        result["customer_md"] = customer_md.read_text(encoding="utf-8")

    developer_md = _triage_dir / f"{issue_id}_developer.md"
    if developer_md.exists():
        result["developer_md"] = developer_md.read_text(encoding="utf-8")

    findings_file = _triage_dir / f"{issue_id}_findings.json"
    if findings_file.exists():
        result["findings"] = json.loads(findings_file.read_text(encoding="utf-8"))

    return result
