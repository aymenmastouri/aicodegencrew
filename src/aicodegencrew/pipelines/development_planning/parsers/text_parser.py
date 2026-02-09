"""
Text Parser for plain text and log files.
"""

import re
from pathlib import Path
from typing import Dict, Any, List


def parse_text(file_path: Path) -> Dict[str, Any]:
    """
    Parse text or log file.

    Args:
        file_path: Path to text file

    Returns:
        Dictionary with content, log entries, errors
    """
    content = file_path.read_text(encoding='utf-8')

    result = {
        'content': content,
        'log_entries': [],
        'errors': [],
        'lines': content.splitlines(),
    }

    # Try to parse as log file
    if file_path.suffix in ['.log', '.txt']:
        result['log_entries'] = _parse_log_entries(content)
        result['errors'] = _extract_errors(content)

    return result


def _parse_log_entries(content: str) -> List[Dict[str, Any]]:
    """Parse log entries from text."""
    entries = []

    # Common log patterns
    patterns = [
        # [LEVEL] message
        r'\[(\w+)\]\s*(.+)',
        # YYYY-MM-DD HH:MM:SS LEVEL message
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)',
        # Level: message
        r'(\w+):\s*(.+)',
    ]

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    entries.append({
                        'level': groups[0],
                        'message': groups[1],
                    })
                elif len(groups) == 3:
                    entries.append({
                        'timestamp': groups[0],
                        'level': groups[1],
                        'message': groups[2],
                    })
                break

    return entries


def _extract_errors(content: str) -> List[Dict[str, Any]]:
    """Extract error information from text."""
    errors = []

    # Error patterns
    error_keywords = ['error', 'exception', 'failed', 'failure']

    lines = content.splitlines()
    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Check if line contains error keywords
        if any(keyword in line_lower for keyword in error_keywords):
            # Extract context (3 lines before and after)
            start = max(0, i - 3)
            end = min(len(lines), i + 4)
            context = '\n'.join(lines[start:end])

            errors.append({
                'message': line.strip(),
                'line_number': i + 1,
                'context': context,
            })

    return errors
