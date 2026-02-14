"""
XML Parser (generic, works with any XML format).

Supports:
- JIRA XML exports
- Custom XML task formats
- Generic structured XML
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def parse_xml(file_path: Path) -> list[dict[str, Any]]:
    """
    Parse XML file and extract task information.

    Handles multiple XML formats:
    - JIRA RSS format (<rss><channel><item>...)
    - Generic task format (<tasks><task>...)
    - Single task format (<task>...)

    Args:
        file_path: Path to XML file

    Returns:
        List of task dictionaries
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    tasks = []

    # Try JIRA RSS format
    if root.tag == "rss" or root.tag == "{http://www.w3.org/2005/Atom}feed":
        tasks = _parse_jira_rss(root)
    # Try generic tasks format
    elif root.tag == "tasks":
        tasks = _parse_tasks_xml(root)
    # Try single task format
    elif root.tag == "task":
        tasks = [_parse_task_element(root)]
    else:
        # Fallback: treat entire XML as single task
        tasks = [_parse_generic_xml(root)]

    return tasks


def _parse_jira_rss(root: ET.Element) -> list[dict[str, Any]]:
    """Parse JIRA RSS XML format with ALL fields."""
    tasks = []

    # Find all item elements
    items = root.findall(".//item")

    for item in items:
        # Basic fields
        task = {
            "task_id": _get_text(item, "key", "UNKNOWN"),
            "summary": _get_text(item, "summary", ""),
            "description": _get_text(item, "description", ""),
            "priority": _get_text(item, "priority", "Medium"),
            "type": _get_text(item, "type", "Task"),
            "status": _get_text(item, "status", ""),
            "labels": _get_list(item, "label"),
            "components": _get_list(item, "component"),
            "acceptance_criteria": [],
            "technical_notes": "",
        }

        # Additional JIRA fields
        assignee = _get_text(item, "assignee", "")
        reporter = _get_text(item, "reporter", "")
        created = _get_text(item, "created", "")
        updated = _get_text(item, "updated", "")
        fix_version = _get_text(item, "fixVersion", "")
        resolution = _get_text(item, "resolution", "")

        # Extract comments
        comments = []
        comments_elem = item.find("comments")
        if comments_elem is not None:
            for comment in comments_elem.findall("comment"):
                comment_text = comment.text if comment.text else ""
                comment_author = comment.get("author", "")
                comment_created = comment.get("created", "")
                if comment_text:
                    comments.append(
                        {"author": comment_author, "created": comment_created, "text": comment_text.strip()}
                    )

        # Build technical notes from metadata
        notes = []
        if assignee:
            notes.append(f"Assignee: {assignee}")
        if reporter:
            notes.append(f"Reporter: {reporter}")
        if created:
            notes.append(f"Created: {created}")
        if updated:
            notes.append(f"Updated: {updated}")
        if fix_version:
            notes.append(f"Fix Version: {fix_version}")
        if resolution:
            notes.append(f"Resolution: {resolution}")

        # Add comments to technical notes
        if comments:
            notes.append(f"\nComments ({len(comments)}):")
            for i, comment in enumerate(comments, 1):
                notes.append(f"\n[Comment {i}] {comment['author']} ({comment['created']}):")
                notes.append(comment["text"][:2000])  # Allow long technical comments

        task["technical_notes"] = "\n".join(notes)

        # Extract linked tasks (issuelinks, subtasks, description references)
        linked = _extract_linked_tasks(item, task["task_id"], task["description"])
        task["linked_tasks"] = linked
        task["jira_type"] = task["type"]

        tasks.append(task)

    return tasks


def _parse_tasks_xml(root: ET.Element) -> list[dict[str, Any]]:
    """Parse generic tasks XML format."""
    tasks = []

    for task_elem in root.findall("task"):
        task = _parse_task_element(task_elem)
        tasks.append(task)

    return tasks


def _parse_task_element(elem: ET.Element) -> dict[str, Any]:
    """Parse a single task element."""
    task = {
        "task_id": elem.get("id", _get_text(elem, "id", "UNKNOWN")),
        "summary": _get_text(elem, "summary", _get_text(elem, "title", "")),
        "description": _get_text(elem, "description", _get_text(elem, "details", "")),
        "priority": _get_text(elem, "priority", "Medium"),
        "type": _get_text(elem, "type", "Task"),
        "status": _get_text(elem, "status", ""),
        "labels": _get_list(elem, "label"),
        "components": _get_list(elem, "component"),
        "acceptance_criteria": _get_list(elem, "acceptance-criteria"),
        "technical_notes": _get_text(elem, "technical-notes", ""),
    }

    return task


def _parse_generic_xml(root: ET.Element) -> dict[str, Any]:
    """Parse generic XML as single task."""
    # Extract all text content
    all_text = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            all_text.append(elem.text.strip())

    description = "\n".join(all_text)

    return {
        "task_id": root.get("id", "UNKNOWN"),
        "summary": root.tag.replace("_", " ").title(),
        "description": description,
        "priority": "Medium",
        "type": "Task",
        "status": "",
        "labels": [],
        "components": [],
        "acceptance_criteria": [],
        "technical_notes": "",
    }


def _get_text(elem: ET.Element, tag: str, default: str = "") -> str:
    """Get text content of child element."""
    child = elem.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return default


def _get_list(elem: ET.Element, tag: str) -> list[str]:
    """Get list of text content from multiple child elements."""
    items = []
    for child in elem.findall(tag):
        if child.text:
            items.append(child.text.strip())
    return items


def _extract_linked_tasks(item: ET.Element, own_id: str, description: str) -> list[str]:
    """Extract linked ticket IDs from issuelinks, subtasks, and description references."""
    linked = set()

    # 1. Issuelinks (e.g., <issuelink><issuekey>PROJ-456</issuekey></issuelink>)
    for issuekey in item.findall(".//issuelinks//issuekey"):
        if issuekey.text:
            linked.add(issuekey.text.strip())

    # 2. Subtasks
    for subtask in item.findall(".//subtasks//key"):
        if subtask.text:
            linked.add(subtask.text.strip())

    # 3. Parent reference
    parent = item.find("parent")
    if parent is not None and parent.text:
        linked.add(parent.text.strip())

    # 4. Ticket references in description (e.g., PROJ-123, TEAM-456)
    if description:
        refs = re.findall(r"[A-Z][A-Z0-9]+-\d+", description)
        for ref in refs:
            if ref != own_id:
                linked.add(ref)

    return sorted(linked)
