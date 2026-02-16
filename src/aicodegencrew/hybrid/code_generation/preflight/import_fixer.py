"""Preflight: Deterministic import fixer for generated code.

Zero LLM tokens — pure regex + ImportIndex lookups.

Operations:
1. Parse all import statements in generated code
2. Parse all symbol references in the body
3. Add missing imports (symbol referenced but not imported)
4. Fix incorrect import paths (import exists but path is wrong)
5. Remove duplicate imports
"""

import re

from ....shared.utils.logger import setup_logger
from ..schemas import GeneratedFile
from .import_index import ImportIndex

logger = setup_logger(__name__)

# ── Built-in types that never need imports ────────────────────────────────────
JAVA_BUILTINS = frozenset({
    "String", "Integer", "Long", "Double", "Float", "Boolean", "Byte", "Short",
    "Character", "Object", "Class", "Void", "Number", "Math",
    "Exception", "RuntimeException", "Error", "Throwable",
    "System", "Thread", "Runnable",
    "Override", "Deprecated", "SuppressWarnings", "FunctionalInterface",
    "int", "long", "double", "float", "boolean", "byte", "short", "char", "void",
    "var",
})

TS_BUILTINS = frozenset({
    "string", "number", "boolean", "any", "void", "never", "unknown", "object",
    "undefined", "null", "symbol", "bigint",
    "Promise", "Observable", "Subscription", "Subject", "BehaviorSubject",
    "Array", "Map", "Set", "Date", "RegExp", "Error", "JSON",
    "Record", "Partial", "Required", "Pick", "Omit", "Exclude", "Extract",
    "HTMLElement", "Event", "EventEmitter", "console", "window", "document",
    "TemplateRef", "ElementRef", "ViewChild", "ViewChildren",
    "true", "false", "this", "super", "new", "typeof", "instanceof",
    "T", "K", "V", "U", "R",
})

# ── Import parsing regexes ────────────────────────────────────────────────────
_JAVA_IMPORT_RE = re.compile(r"^(import\s+(static\s+)?([\w.]+)\s*;)\s*$", re.MULTILINE)
_TS_IMPORT_RE = re.compile(
    r"^(import\s+(?:type\s+)?\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"];?)\s*$",
    re.MULTILINE,
)
_TS_DEFAULT_IMPORT_RE = re.compile(
    r"^(import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"];?)\s*$",
    re.MULTILINE,
)

# ── Symbol reference regexes ──────────────────────────────────────────────────
_JAVA_SYMBOL_REF_RE = re.compile(
    r"(?:new\s+|extends\s+|implements\s+|@|:\s*|<|,\s*)"
    r"(\b[A-Z]\w+)\b"
)
_TS_SYMBOL_REF_RE = re.compile(
    r"(?::\s*|<|extends\s+|implements\s+|new\s+)"
    r"(\b[A-Z]\w+)\b"
)
_TS_DECORATOR_RE = re.compile(r"@(\w+)")


class ImportFixer:
    """Deterministic import fixer — zero LLM tokens."""

    def __init__(self):
        self.total_fixes = 0
        self.total_added = 0
        self.total_corrected = 0
        self.total_deduped = 0

    def run(
        self,
        generated_files: list[GeneratedFile],
        import_index: ImportIndex,
    ) -> list[GeneratedFile]:
        logger.info("[Preflight] Fixing imports in %d files", len(generated_files))

        for gf in generated_files:
            if gf.error or gf.action == "delete" or not gf.content:
                continue

            original = gf.content
            gf.content = self._fix_file(gf, import_index)

            if gf.content != original:
                self.total_fixes += 1

        logger.info(
            "[Preflight] Import fixes: %d files modified, %d imports added, "
            "%d paths corrected, %d duplicates removed",
            self.total_fixes, self.total_added, self.total_corrected, self.total_deduped,
        )
        return generated_files

    def _fix_file(self, gf: GeneratedFile, import_index: ImportIndex) -> str:
        language = gf.language
        if language == "java":
            return self._fix_java(gf, import_index)
        elif language in ("typescript",):
            return self._fix_typescript(gf, import_index)
        return gf.content

    def _fix_java(self, gf: GeneratedFile, import_index: ImportIndex) -> str:
        content = gf.content
        lines = content.split("\n")

        existing_imports: dict[str, str] = {}
        import_lines: set[int] = set()

        for i, line in enumerate(lines):
            m = _JAVA_IMPORT_RE.match(line)
            if m:
                full_stmt = m.group(1)
                qualified = m.group(3)
                symbol = qualified.split(".")[-1]
                import_lines.add(i)
                if symbol not in existing_imports:
                    existing_imports[symbol] = full_stmt
                else:
                    self.total_deduped += 1

        body_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("public ") or line.strip().startswith("class ") or line.strip().startswith("@"):
                if i > 0:
                    body_start = i
                    break

        body_text = "\n".join(lines[body_start:])
        referenced = set()
        for m in _JAVA_SYMBOL_REF_RE.finditer(body_text):
            symbol = m.group(1)
            if symbol not in JAVA_BUILTINS:
                referenced.add(symbol)

        missing: list[str] = []
        for symbol in referenced:
            if symbol not in existing_imports:
                resolved = import_index.resolve(symbol, gf.file_path, "java")
                if resolved:
                    missing.append(resolved)
                    self.total_added += 1

        if not missing:
            return self._rebuild_java(lines, import_lines, existing_imports, [])
        return self._rebuild_java(lines, import_lines, existing_imports, missing)

    @staticmethod
    def _rebuild_java(
        lines: list[str],
        import_lines: set[int],
        existing_imports: dict[str, str],
        new_imports: list[str],
    ) -> str:
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("package "):
                insert_at = i + 1
                break

        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1

        result_lines = [line for i, line in enumerate(lines) if i not in import_lines]

        removed_before = sum(1 for i in import_lines if i < insert_at)
        insert_at -= removed_before

        all_imports = sorted(set(existing_imports.values()) | set(new_imports))

        import_block = "\n".join(all_imports)
        if import_block:
            result_lines.insert(insert_at, "")
            result_lines.insert(insert_at + 1, import_block)
            result_lines.insert(insert_at + 2, "")

        return "\n".join(result_lines)

    def _fix_typescript(self, gf: GeneratedFile, import_index: ImportIndex) -> str:
        content = gf.content
        lines = content.split("\n")

        existing_imports: dict[str, str] = {}
        existing_paths: dict[str, str] = {}
        import_lines: set[int] = set()

        for i, line in enumerate(lines):
            m = _TS_IMPORT_RE.match(line)
            if m:
                import_lines.add(i)
                symbols_str = m.group(2)
                path = m.group(3)
                for sym_part in symbols_str.split(","):
                    sym = sym_part.strip()
                    if " as " in sym:
                        sym = sym.split(" as ")[0].strip()
                    if sym:
                        existing_imports[sym] = line.strip()
                        existing_paths[sym] = path
                continue

            m = _TS_DEFAULT_IMPORT_RE.match(line)
            if m:
                import_lines.add(i)
                symbol = m.group(2)
                path = m.group(3)
                existing_imports[symbol] = line.strip()
                existing_paths[symbol] = path

        first_non_import = 0
        for i, line in enumerate(lines):
            if i not in import_lines and line.strip() and not line.strip().startswith("//"):
                first_non_import = i
                break

        body_text = "\n".join(lines[first_non_import:])
        referenced: set[str] = set()

        for m in _TS_SYMBOL_REF_RE.finditer(body_text):
            symbol = m.group(1)
            if symbol not in TS_BUILTINS:
                referenced.add(symbol)

        for m in _TS_DECORATOR_RE.finditer(body_text):
            symbol = m.group(1)
            if symbol not in TS_BUILTINS:
                referenced.add(symbol)

        corrected_in_file = 0
        for symbol, current_path in list(existing_paths.items()):
            if current_path.startswith("@") or current_path.startswith("rxjs"):
                continue
            if not current_path.startswith("."):
                continue

            resolved = import_index.resolve(symbol, gf.file_path, "typescript")
            if resolved and resolved != existing_imports.get(symbol):
                existing_imports[symbol] = resolved
                corrected_in_file += 1
                self.total_corrected += 1

        new_imports: list[str] = []
        for symbol in referenced:
            if symbol not in existing_imports:
                resolved = import_index.resolve(symbol, gf.file_path, "typescript")
                if resolved:
                    new_imports.append(resolved)
                    self.total_added += 1

        if not new_imports and corrected_in_file == 0:
            return content

        return self._rebuild_typescript(lines, import_lines, existing_imports, new_imports)

    @staticmethod
    def _rebuild_typescript(
        lines: list[str],
        import_lines: set[int],
        existing_imports: dict[str, str],
        new_imports: list[str],
    ) -> str:
        result_lines = [line for i, line in enumerate(lines) if i not in import_lines]

        all_stmts = sorted(set(existing_imports.values()) | set(new_imports))

        insert_at = 0
        for i, line in enumerate(result_lines):
            if line.strip() and not line.strip().startswith("//") and not line.strip().startswith("/*"):
                insert_at = i
                break

        import_block = "\n".join(all_stmts)
        if import_block:
            result_lines.insert(insert_at, import_block)
            result_lines.insert(insert_at + 1, "")

        return "\n".join(result_lines)
