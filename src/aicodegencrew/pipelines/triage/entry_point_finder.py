"""Multi-signal entry-point finder.

Matches issue text against:
  1. symbols.jsonl — exact class/method/interface name match
  2. components from architecture_facts — keyword match on name + package + stereotype
  3. interfaces from architecture_facts — URL/endpoint match if issue mentions paths

Filtering is DATA-DRIVEN — no hardcoded language-specific lists.
"""

import re
from collections import Counter
from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)

# URL-like pattern to extract path segments from issue text
_URL_PATH_RE = re.compile(r"(?:/api/[\w/\-]+|/[\w\-]+/[\w\-]+(?:/[\w\-]+)*)")

# Common noise words to exclude from keyword matching (language-agnostic)
_STOP_WORDS = frozenset({
    "the", "is", "in", "at", "to", "for", "of", "and", "or", "not",
    "a", "an", "this", "that", "with", "from", "on", "by", "as",
    "it", "be", "are", "was", "were", "been", "has", "have", "had",
    "should", "would", "could", "will", "can", "may", "must",
    "but", "if", "than", "then", "also", "into", "only", "more",
    "about", "when", "which", "their", "there", "these", "those",
    "what", "how", "who", "where", "why", "does", "did", "done",
    "its", "our", "your", "his", "her", "all", "any", "each",
    "see", "via", "per", "using", "used", "still", "currently",
    "being", "nach", "und", "der", "die", "das", "ein", "eine",
    "auf", "fuer", "mit", "von", "noch", "bei", "vor", "bis",
})

# Minimum symbol name length to be considered as entry point.
# Names <= 3 chars (get, set, id, add, run, map, key, ...) are too generic
# in ANY language.
_MIN_SYMBOL_LENGTH = 4


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from issue text."""
    words = re.findall(r"[A-Za-z][a-zA-Z0-9_]+", text)
    # Split camelCase
    split_words: list[str] = []
    for w in words:
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)", w)
        split_words.extend(parts)
        split_words.append(w)  # keep original too
    return [w.lower() for w in split_words
            if w.lower() not in _STOP_WORDS and len(w) >= _MIN_SYMBOL_LENGTH]


def _build_symbol_frequency(symbols: list[dict]) -> Counter:
    """Count how often each symbol name appears across all files.

    High-frequency names (appearing in many files) are generic
    regardless of the programming language.
    """
    freq: Counter = Counter()
    for sym in symbols:
        name = sym.get("symbol", "").lower()
        if name:
            freq[name] += 1
    return freq


def _is_generic_symbol(name: str, frequency: Counter, total_symbols: int) -> bool:
    """Determine if a symbol is too generic to be a useful entry point.

    Uses data-driven heuristics:
    - Name too short (<=3 chars)
    - Name appears in >2% of all symbols (very common in the codebase)
    """
    if len(name) <= 3:
        return True
    if total_symbols > 0 and frequency.get(name, 0) > max(total_symbols * 0.02, 5):
        return True
    return False


def _score_symbol_match(
    symbol: dict, keywords: set[str],
    frequency: Counter, total_symbols: int,
) -> float:
    """Score a symbol record against keywords."""
    name = symbol.get("symbol", "").lower()
    if _is_generic_symbol(name, frequency, total_symbols):
        return 0.0
    # Split camelCase in symbol name
    name_parts = {p for p in re.findall(r"[a-z]+", name) if len(p) >= _MIN_SYMBOL_LENGTH}
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
    text_words = {w for w in re.findall(r"[a-z]+", text) if len(w) >= _MIN_SYMBOL_LENGTH}
    overlap = text_words & keywords
    if not overlap:
        return 0.0
    return min(len(overlap) / max(len(keywords), 1) * 2, 1.0)


def _should_skip_keyword_matching(classification_type: str) -> bool:
    """Determine whether keyword-based entry point matching should be skipped.

    Keyword matching works well for **bugs** — the issue text mentions specific
    class/method names that map directly to code entry points.

    For **refactors, features, and investigations**, keyword matching produces
    garbage: domain words like "action" (from "action bar") match unrelated
    endpoints (/action/{type}), generic words like "name" and "user" match
    random DTOs.  The LLM agent can determine affected components from the
    task description far more reliably than keyword matching.
    """
    return classification_type != "bug"


def find_entry_points(
    title: str,
    description: str,
    knowledge_context: dict[str, Any],
    classification_type: str = "bug",
) -> list[dict]:
    """Find entry-point components using multi-signal matching.

    Args:
        title:               Issue title.
        description:         Issue description.
        knowledge_context:   Output from KnowledgeLoader.load_available_context().
        classification_type: Issue classification ("bug", "feature", "refactor",
                             "investigation").  Higher thresholds are used for
                             non-bug types to reduce false positives from
                             coincidental keyword matches.

    Returns:
        Top-5 list of {"component": str, "file_path": str, "score": float, "signals": [str]}
    """
    text = f"{title} {description}"
    keywords = set(_extract_keywords(text))
    if not keywords:
        return []

    # For non-bug tasks, keyword matching is unreliable — return empty and
    # let the LLM agent determine affected components from the task context.
    if _should_skip_keyword_matching(classification_type):
        logger.info(
            "[EntryPointFinder] Skipping keyword matching for type=%s "
            "(unreliable for non-bug tasks — LLM will determine affected components)",
            classification_type,
        )
        return []

    candidates: dict[str, dict] = {}  # keyed by component name or file_path

    # Signal 1: symbols.jsonl
    symbols = knowledge_context.get("discover", {}).get("symbols", [])
    sym_freq = _build_symbol_frequency(symbols)
    total_symbols = len(symbols)

    for sym in symbols:
        score = _score_symbol_match(sym, keywords, sym_freq, total_symbols)
        if score > 0.15:
            key = sym.get("path", sym.get("symbol", ""))
            name = sym.get("symbol", "")
            if not key:
                continue
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
                if not key:
                    continue
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
                        if not key:
                            continue
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

    logger.info(
        "[EntryPointFinder] Found %d candidates from %d keywords (type=%s)",
        len(ranked), len(keywords), classification_type,
    )
    return ranked
