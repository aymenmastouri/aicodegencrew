"""Multi-signal entry-point finder.

Matches issue text against:
  1. symbols.jsonl — exact class/method/interface name match
  2. components from architecture_facts — keyword match on name + package + stereotype
  3. interfaces from architecture_facts — URL/endpoint match if issue mentions paths
"""

import re
from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)

# URL-like pattern to extract path segments from issue text
_URL_PATH_RE = re.compile(r"(?:/api/[\w/\-]+|/[\w\-]+/[\w\-]+(?:/[\w\-]+)*)")

# Common noise words to exclude from keyword matching
_STOP_WORDS = frozenset({
    "the", "is", "in", "at", "to", "for", "of", "and", "or", "not",
    "a", "an", "this", "that", "with", "from", "on", "by", "as",
    "it", "be", "are", "was", "were", "been", "has", "have", "had",
    "should", "would", "could", "will", "can", "may", "must",
})


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from issue text."""
    words = re.findall(r"[A-Za-z][a-zA-Z0-9_]+", text)
    # Split camelCase
    split_words: list[str] = []
    for w in words:
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)", w)
        split_words.extend(parts)
        split_words.append(w)  # keep original too
    return [w.lower() for w in split_words if w.lower() not in _STOP_WORDS and len(w) > 2]


def _score_symbol_match(symbol: dict, keywords: set[str]) -> float:
    """Score a symbol record against keywords."""
    name = symbol.get("symbol", "").lower()
    # Split camelCase in symbol name
    name_parts = set(re.findall(r"[a-z]+", name.lower()))
    overlap = name_parts & keywords
    if not overlap:
        return 0.0
    # Bonus for exact name match
    base = len(overlap) / max(len(name_parts), 1)
    if name in keywords:
        base += 0.3
    return min(base, 1.0)


def _score_component_match(component: dict, keywords: set[str]) -> float:
    """Score a component against keywords."""
    name = component.get("name", "").lower()
    package = component.get("package", "").lower()
    stereotype = component.get("stereotype", "").lower()
    text = f"{name} {package} {stereotype}"
    text_words = set(re.findall(r"[a-z]+", text))
    overlap = text_words & keywords
    if not overlap:
        return 0.0
    return min(len(overlap) / max(len(keywords), 1) * 2, 1.0)


def find_entry_points(
    title: str,
    description: str,
    knowledge_context: dict[str, Any],
) -> list[dict]:
    """Find entry-point components using multi-signal matching.

    Args:
        title:             Issue title.
        description:       Issue description.
        knowledge_context: Output from KnowledgeLoader.load_available_context().

    Returns:
        Top-5 list of {"component": str, "file_path": str, "score": float, "signals": [str]}
    """
    text = f"{title} {description}"
    keywords = set(_extract_keywords(text))
    if not keywords:
        return []

    candidates: dict[str, dict] = {}  # keyed by component name or file_path

    # Signal 1: symbols.jsonl
    symbols = knowledge_context.get("discover", {}).get("symbols", [])
    for sym in symbols:
        score = _score_symbol_match(sym, keywords)
        if score > 0.15:
            key = sym.get("path", sym.get("symbol", ""))
            name = sym.get("symbol", "")
            existing = candidates.get(key, {"component": name, "file_path": key, "score": 0, "signals": []})
            existing["score"] = max(existing["score"], score)
            existing["signals"].append(f"symbol:{name}")
            candidates[key] = existing

    # Signal 2: components from architecture_facts
    facts = knowledge_context.get("extract", {}).get("architecture_facts", {})
    components = facts.get("components", [])
    if isinstance(components, list):
        for comp in components:
            score = _score_component_match(comp, keywords)
            if score > 0.15:
                name = comp.get("name", "")
                fp = comp.get("file_path", "")
                key = fp or name
                existing = candidates.get(key, {"component": name, "file_path": fp, "score": 0, "signals": []})
                existing["score"] = max(existing["score"], score)
                existing["signals"].append(f"component:{name}")
                candidates[key] = existing

    # Signal 3: interface/endpoint matching
    urls = _URL_PATH_RE.findall(text)
    if urls:
        interfaces = facts.get("interfaces", [])
        if isinstance(interfaces, list):
            for iface in interfaces:
                ipath = iface.get("path", "")
                for url in urls:
                    if url in ipath or ipath in url:
                        impl = iface.get("implemented_by", "")
                        key = impl or ipath
                        existing = candidates.get(
                            key, {"component": impl, "file_path": "", "score": 0, "signals": []}
                        )
                        existing["score"] = max(existing["score"], 0.8)
                        existing["signals"].append(f"endpoint:{ipath}")
                        candidates[key] = existing

    # Sort by score, return top-5
    ranked = sorted(candidates.values(), key=lambda c: c["score"], reverse=True)[:5]

    # Deduplicate signals
    for r in ranked:
        r["signals"] = list(dict.fromkeys(r["signals"]))[:5]
        r["score"] = round(r["score"], 3)

    logger.info("[EntryPointFinder] Found %d candidates from %d keywords", len(ranked), len(keywords))
    return ranked
