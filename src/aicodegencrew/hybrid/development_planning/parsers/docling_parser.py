"""Docling document parser — PDF/DOCX/PPTX to Markdown via REST API.

Converts documents using the Docling REST API when DOCLING_URL is set.
Returns the same dict format as other parsers: {title, sections, tables}.

Env vars:
    DOCLING_URL: Docling REST API base URL (empty = disabled)
"""

import logging
import os
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


def parse_with_docling(file_path: str | Path) -> dict[str, Any]:
    """Convert a document to structured Markdown via Docling REST API.

    Args:
        file_path: Path to PDF, DOCX, or PPTX file.

    Returns:
        Dict with keys: title, sections (list of {title, content}), tables (list of str).

    Raises:
        ValueError: If DOCLING_URL is not set or the API call fails.
    """
    docling_url = os.getenv("DOCLING_URL", "").strip()
    if not docling_url:
        raise ValueError("DOCLING_URL environment variable is not set")

    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    url = f"{docling_url.rstrip('/')}/convert"

    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                files={"file": (file_path.name, f)},
                timeout=120,
            )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"Docling API call failed: {exc}") from exc

    # Parse Docling response into standard format
    markdown = data.get("markdown", data.get("content", ""))
    title = data.get("title", file_path.stem)

    sections = []
    tables = []
    current_section = {"title": "Introduction", "content": []}

    for line in markdown.split("\n"):
        if line.startswith("## "):
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"title": line[3:].strip(), "content": []}
        elif line.startswith("| "):
            tables.append(line)
        elif line.strip():
            current_section["content"].append(line)

    if current_section["content"]:
        sections.append(current_section)

    return {
        "title": title,
        "sections": sections,
        "tables": tables,
    }
