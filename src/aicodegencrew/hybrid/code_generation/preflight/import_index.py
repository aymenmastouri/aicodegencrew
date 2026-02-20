"""Preflight: Language-aware import index for the target repository.

Builds a complete symbol -> import_path map. Deterministic — no LLM calls.
Enforces strict language filtering (TypeScript files get only TS imports, etc.).

Duration: 3-10s (file I/O only)
"""

import json
import os
import re
from pathlib import Path

from ....shared.paths import DISCOVER_SYMBOLS
from ....shared.utils.logger import setup_logger
from ..schemas import ImportEntry

logger = setup_logger(__name__)

MAX_SCAN_SIZE = 500_000

# ── Java Regexes ──────────────────────────────────────────────────────────────
_JAVA_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
_JAVA_CLASS_RE = re.compile(
    r"(?:public\s+)?(?:abstract\s+)?(?:final\s+)?"
    r"(?:class|interface|enum|record)\s+(\w+)",
    re.MULTILINE,
)

# ── TypeScript/JS Regexes ─────────────────────────────────────────────────────
_TS_EXPORT_CLASS_RE = re.compile(
    r"export\s+(?:abstract\s+)?(?:class|interface|enum|type|function)\s+(\w+)",
    re.MULTILINE,
)
_TS_EXPORT_CONST_RE = re.compile(
    r"export\s+(?:const|let|var)\s+(\w+)",
    re.MULTILINE,
)
_TS_EXPORT_DEFAULT_RE = re.compile(
    r"export\s+default\s+(?:class|function|abstract\s+class)\s+(\w+)",
    re.MULTILINE,
)
_TS_RE_EXPORT_RE = re.compile(
    r"export\s*\{([^}]+)\}\s*(?:from\s*['\"]([^'\"]+)['\"])?",
    re.MULTILINE,
)

_JAVA_EXTS = {".java"}
_TS_EXTS = {".ts", ".tsx"}


class ImportIndex:
    """Language-safe symbol -> import path resolution index.

    Prevents cross-language resolution (e.g. Java symbols resolved for
    TypeScript files), which was a recurring source of invalid imports.
    """

    def __init__(self):
        self.by_symbol: dict[str, list[ImportEntry]] = {}
        self.by_file: dict[str, list[ImportEntry]] = {}

    def add(self, entry: ImportEntry) -> None:
        self.by_symbol.setdefault(entry.symbol, []).append(entry)
        self.by_file.setdefault(entry.file_path, []).append(entry)

    def resolve(self, symbol: str, from_file: str, language: str) -> str | None:
        """Return the exact import statement for a symbol relative to from_file.

        Strict language filtering: only returns imports matching the requested language.
        Returns None if the symbol is not found or has no match for the language.
        """
        entries = self.by_symbol.get(symbol)
        if not entries:
            return None

        normalized_lang = "typescript" if language in ("typescript", "html") else language
        filtered = [e for e in entries if e.language == normalized_lang]
        if not filtered:
            return None

        if normalized_lang == "java":
            return self._resolve_java(filtered, symbol)
        if normalized_lang == "typescript":
            return self._resolve_typescript(filtered, symbol, from_file)
        return None

    def resolve_all_for_file(self, file_path: str, language: str) -> dict[str, str]:
        """Return {symbol: import_statement} for all symbols reachable from file_path."""
        result: dict[str, str] = {}
        for symbol in self.by_symbol:
            stmt = self.resolve(symbol, file_path, language)
            if stmt:
                result[symbol] = stmt
        return result

    def get_exports(self, file_path: str) -> list[str]:
        entries = self.by_file.get(file_path, [])
        return [e.symbol for e in entries]

    @property
    def total_symbols(self) -> int:
        return sum(len(v) for v in self.by_symbol.values())

    # ── Java resolution ───────────────────────────────────────────────────

    @staticmethod
    def _resolve_java(entries: list[ImportEntry], symbol: str) -> str | None:
        for entry in entries:
            if entry.qualified_name:
                return f"import {entry.qualified_name};"
        return None

    # ── TypeScript resolution ─────────────────────────────────────────────

    @staticmethod
    def _resolve_typescript(entries: list[ImportEntry], symbol: str, from_file: str) -> str | None:
        if not entries:
            return None

        best = entries[0]
        if len(entries) > 1:
            from_parts = Path(from_file).parts
            best_score = -1
            for entry in entries:
                entry_parts = Path(entry.file_path).parts
                common = 0
                for a, b in zip(from_parts, entry_parts, strict=False):
                    if a == b:
                        common += 1
                    else:
                        break
                if common > best_score:
                    best_score = common
                    best = entry

        rel = _compute_ts_relative_import(from_file, best.file_path)
        return f"import {{ {symbol} }} from '{rel}';"

    def __repr__(self) -> str:
        return f"ImportIndex(symbols={len(self.by_symbol)}, files={len(self.by_file)})"


class ImportIndexBuilder:
    """Build a language-safe ImportIndex from the target repository."""

    def __init__(self, repo_path: str, facts_path: str = "knowledge/extract/architecture_facts.json"):
        self.repo_path = Path(repo_path)
        self.facts_path = Path(facts_path)

    def run(self) -> ImportIndex:
        index = ImportIndex()

        symbols_loaded = self._load_from_symbols_jsonl(index)
        scanned = self._scan_repo_files(index)

        logger.info(
            "[Preflight] ImportIndex built: %d entries (%d from symbols.jsonl, %d from repo scan)",
            index.total_symbols,
            symbols_loaded,
            scanned,
        )
        return index

    def _load_from_symbols_jsonl(self, index: ImportIndex) -> int:
        symbols_path = Path(DISCOVER_SYMBOLS)
        if not symbols_path.exists():
            return 0

        count = 0
        try:
            with open(symbols_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    symbol = rec.get("symbol", "")
                    kind = rec.get("kind", "")
                    file_path = rec.get("path", "")

                    if not symbol or kind not in ("class", "interface", "enum", "function", "type", "const"):
                        continue

                    ext = Path(file_path).suffix.lower()
                    if ext in _JAVA_EXTS:
                        lang = "java"
                        qname = rec.get("qualified_name", "")
                        if not qname:
                            pkg = rec.get("package", "")
                            qname = f"{pkg}.{symbol}" if pkg else symbol
                    elif ext in _TS_EXTS:
                        lang = "typescript"
                        qname = symbol
                    else:
                        continue

                    abs_path = file_path
                    if not Path(file_path).is_absolute():
                        abs_path = str(self.repo_path / file_path)

                    # Skip stale entries — file may have been deleted/moved since
                    # the last indexing run (INDEX_MODE=off keeps old symbols.jsonl)
                    if not Path(abs_path).exists():
                        continue

                    index.add(
                        ImportEntry(
                            symbol=symbol,
                            qualified_name=qname,
                            import_path=file_path,
                            file_path=abs_path,
                            kind=kind,
                            language=lang,
                        )
                    )
                    count += 1
        except Exception as e:
            logger.warning("[Preflight] Error reading symbols.jsonl: %s", e)

        return count

    def _scan_repo_files(self, index: ImportIndex) -> int:
        count = 0
        known_files = set(index.by_file.keys())

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [
                d
                for d in dirs
                if d not in ("node_modules", ".git", "build", "dist", "target", "__pycache__", ".gradle")
            ]
            for fname in files:
                ext = Path(fname).suffix.lower()
                if ext not in _JAVA_EXTS and ext not in _TS_EXTS:
                    continue

                full_path = os.path.join(root, fname)
                norm_path = full_path.replace("\\", "/")
                if any(
                    norm_path.endswith(k.replace("\\", "/")) or k.replace("\\", "/").endswith(norm_path)
                    for k in known_files
                ):
                    continue

                try:
                    size = os.path.getsize(full_path)
                    if size > MAX_SCAN_SIZE:
                        continue
                    content = Path(full_path).read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                if ext in _JAVA_EXTS:
                    count += self._index_java_file(index, full_path, content)
                elif ext in _TS_EXTS:
                    count += self._index_ts_file(index, full_path, content)

        return count

    def _index_java_file(self, index: ImportIndex, file_path: str, content: str) -> int:
        count = 0
        pkg_match = _JAVA_PACKAGE_RE.search(content)
        package = pkg_match.group(1) if pkg_match else ""

        for match in _JAVA_CLASS_RE.finditer(content):
            symbol = match.group(1)
            qualified = f"{package}.{symbol}" if package else symbol
            index.add(
                ImportEntry(
                    symbol=symbol,
                    qualified_name=qualified,
                    import_path=file_path,
                    file_path=file_path,
                    kind="class",
                    language="java",
                )
            )
            count += 1
        return count

    def _index_ts_file(self, index: ImportIndex, file_path: str, content: str) -> int:
        count = 0
        seen: set[str] = set()

        for match in _TS_EXPORT_CLASS_RE.finditer(content):
            symbol = match.group(1)
            if symbol not in seen:
                seen.add(symbol)
                index.add(
                    ImportEntry(
                        symbol=symbol,
                        qualified_name=symbol,
                        import_path=file_path,
                        file_path=file_path,
                        kind="class",
                        language="typescript",
                    )
                )
                count += 1

        for match in _TS_EXPORT_CONST_RE.finditer(content):
            symbol = match.group(1)
            if symbol not in seen:
                seen.add(symbol)
                index.add(
                    ImportEntry(
                        symbol=symbol,
                        qualified_name=symbol,
                        import_path=file_path,
                        file_path=file_path,
                        kind="const",
                        language="typescript",
                    )
                )
                count += 1

        for match in _TS_EXPORT_DEFAULT_RE.finditer(content):
            symbol = match.group(1)
            if symbol not in seen:
                seen.add(symbol)
                index.add(
                    ImportEntry(
                        symbol=symbol,
                        qualified_name=symbol,
                        import_path=file_path,
                        file_path=file_path,
                        kind="class",
                        language="typescript",
                    )
                )
                count += 1

        for match in _TS_RE_EXPORT_RE.finditer(content):
            symbols_str = match.group(1)
            for sym_part in symbols_str.split(","):
                sym_part = sym_part.strip()
                if " as " in sym_part:
                    sym_part = sym_part.split(" as ")[1].strip()
                if sym_part and sym_part not in seen:
                    seen.add(sym_part)
                    index.add(
                        ImportEntry(
                            symbol=sym_part,
                            qualified_name=sym_part,
                            import_path=file_path,
                            file_path=file_path,
                            kind="class",
                            language="typescript",
                        )
                    )
                    count += 1

        return count


def _compute_ts_relative_import(from_file: str, to_file: str) -> str:
    from_dir = Path(from_file).parent
    to_path = Path(to_file)

    try:
        rel = os.path.relpath(to_path, from_dir).replace("\\", "/")
    except ValueError:
        rel = to_file.replace("\\", "/")

    for ext in (".ts", ".tsx", ".js", ".jsx"):
        if rel.endswith(ext):
            rel = rel[: -len(ext)]
            break

    if rel.endswith("/index"):
        rel = rel[: -len("/index")]

    if not rel.startswith("."):
        rel = "./" + rel

    return rel
