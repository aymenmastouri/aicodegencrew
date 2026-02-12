"""
Multi-format document converter: Markdown → Confluence Wiki Markup / AsciiDoc / HTML.

Converts Phase 3 architecture docs (C4 + Arc42 Markdown) into additional formats
for Confluence integration, docToolchain compatibility, and standalone viewing.

No external upload — all conversion is local.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import mistune

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intermediate representation
# ---------------------------------------------------------------------------


class BlockType(Enum):
    HEADING = auto()
    PARAGRAPH = auto()
    TABLE = auto()
    CODE_BLOCK = auto()
    UNORDERED_LIST = auto()
    ORDERED_LIST = auto()
    BLOCKQUOTE = auto()
    HORIZONTAL_RULE = auto()
    EMPTY = auto()


@dataclass
class Block:
    type: BlockType
    lines: list[str] = field(default_factory=list)
    level: int = 0  # heading level (1-6) or list nesting depth
    language: str = ""  # code block language
    header_row: int = -1  # table: index of header row (-1 = none)


# ---------------------------------------------------------------------------
# Markdown Parser → Block list
# ---------------------------------------------------------------------------

_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)")
_RE_CODE_FENCE = re.compile(r"^```(\w*)")
_RE_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_RE_TABLE_SEP = re.compile(r"^\|[\s:]*-{2,}[\s:]*")
_RE_UNORDERED = re.compile(r"^(\s*)[*\-]\s+(.*)")
_RE_ORDERED = re.compile(r"^(\s*)\d+\.\s+(.*)")
_RE_BLOCKQUOTE = re.compile(r"^>\s?(.*)")
_RE_HR = re.compile(r"^-{3,}\s*$")


def _parse_markdown(text: str) -> list[Block]:
    """Parse Markdown text into a list of Block objects."""
    blocks: list[Block] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # --- Empty line ---
        if not line.strip():
            blocks.append(Block(BlockType.EMPTY))
            i += 1
            continue

        # --- Horizontal rule ---
        if _RE_HR.match(line):
            blocks.append(Block(BlockType.HORIZONTAL_RULE))
            i += 1
            continue

        # --- Heading ---
        m = _RE_HEADING.match(line)
        if m:
            blocks.append(Block(BlockType.HEADING, [m.group(2)], level=len(m.group(1))))
            i += 1
            continue

        # --- Code block ---
        m = _RE_CODE_FENCE.match(line)
        if m:
            lang = m.group(1) or ""
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append(Block(BlockType.CODE_BLOCK, code_lines, language=lang))
            continue

        # --- Table ---
        if _RE_TABLE_ROW.match(line):
            table_lines: list[str] = []
            header_idx = -1
            while i < len(lines) and (_RE_TABLE_ROW.match(lines[i]) or _RE_TABLE_SEP.match(lines[i])):
                if _RE_TABLE_SEP.match(lines[i]):
                    header_idx = len(table_lines) - 1  # previous row was header
                else:
                    table_lines.append(lines[i])
                i += 1
            blocks.append(Block(BlockType.TABLE, table_lines, header_row=header_idx))
            continue

        # --- Blockquote ---
        m = _RE_BLOCKQUOTE.match(line)
        if m:
            quote_lines: list[str] = []
            while i < len(lines):
                qm = _RE_BLOCKQUOTE.match(lines[i])
                if qm:
                    quote_lines.append(qm.group(1))
                    i += 1
                else:
                    break
            blocks.append(Block(BlockType.BLOCKQUOTE, quote_lines))
            continue

        # --- Unordered list ---
        m = _RE_UNORDERED.match(line)
        if m:
            list_items: list[str] = []
            levels: list[int] = []
            while i < len(lines):
                lm = _RE_UNORDERED.match(lines[i])
                if lm:
                    depth = len(lm.group(1)) // 2 + 1  # 0 spaces=1, 2 spaces=2, etc.
                    list_items.append(lm.group(2))
                    levels.append(depth)
                    i += 1
                else:
                    break
            blk = Block(BlockType.UNORDERED_LIST, list_items)
            blk._levels = levels  # type: ignore[attr-defined]
            blocks.append(blk)
            continue

        # --- Ordered list ---
        m = _RE_ORDERED.match(line)
        if m:
            list_items_o: list[str] = []
            levels_o: list[int] = []
            while i < len(lines):
                lm = _RE_ORDERED.match(lines[i])
                if lm:
                    depth = len(lm.group(1)) // 2 + 1
                    list_items_o.append(lm.group(2))
                    levels_o.append(depth)
                    i += 1
                else:
                    break
            blk = Block(BlockType.ORDERED_LIST, list_items_o)
            blk._levels = levels_o  # type: ignore[attr-defined]
            blocks.append(blk)
            continue

        # --- Paragraph (fallback) ---
        para_lines: list[str] = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not _RE_HEADING.match(lines[i])
            and not _RE_CODE_FENCE.match(lines[i])
            and not _RE_TABLE_ROW.match(lines[i])
            and not _RE_BLOCKQUOTE.match(lines[i])
            and not _RE_UNORDERED.match(lines[i])
            and not _RE_ORDERED.match(lines[i])
            and not _RE_HR.match(lines[i])
        ):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            blocks.append(Block(BlockType.PARAGRAPH, para_lines))

    return blocks


# ---------------------------------------------------------------------------
# Inline formatting converters
# ---------------------------------------------------------------------------


def _inline_confluence(text: str) -> str:
    """Convert inline Markdown formatting to Confluence Wiki Markup."""
    # Bold: **text** -> *text*  (do before single * handling)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Inline code: `code` -> {{code}}
    text = re.sub(r"`([^`]+)`", r"{{\1}}", text)
    # Images: ![alt](src) -> !src!
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"!\2!", text)
    # Links: [text](url) -> [text|url]
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[\1|\2]", text)
    return text


def _inline_asciidoc(text: str) -> str:
    """Convert inline Markdown formatting to AsciiDoc."""
    # Bold: **text** -> *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Inline code stays: `code` -> `code`
    # Images: ![alt](src) -> image:src[alt]
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"image:\2[\1]", text)
    # Links: [text](url) -> link:url[text]
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"link:\2[\1]", text)
    return text


def _parse_table_cells(row: str) -> list[str]:
    """Extract cell values from a Markdown table row."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _render_confluence(blocks: list[Block]) -> str:
    """Render blocks as Confluence Wiki Markup."""
    out: list[str] = []

    for blk in blocks:
        if blk.type == BlockType.EMPTY:
            out.append("")
            continue

        if blk.type == BlockType.HORIZONTAL_RULE:
            out.append("----")
            continue

        if blk.type == BlockType.HEADING:
            out.append(f"h{blk.level}. {_inline_confluence(blk.lines[0])}")
            out.append("")
            continue

        if blk.type == BlockType.PARAGRAPH:
            out.append(_inline_confluence(" ".join(blk.lines)))
            out.append("")
            continue

        if blk.type == BlockType.CODE_BLOCK:
            lang_attr = f":language={blk.language}" if blk.language else ""
            out.append(f"{{code{lang_attr}}}")
            out.extend(blk.lines)
            out.append("{code}")
            out.append("")
            continue

        if blk.type == BlockType.TABLE:
            for idx, row in enumerate(blk.lines):
                cells = _parse_table_cells(row)
                if idx == blk.header_row:
                    out.append("||" + "||".join(_inline_confluence(c) for c in cells) + "||")
                else:
                    out.append("|" + "|".join(_inline_confluence(c) for c in cells) + "|")
            out.append("")
            continue

        if blk.type == BlockType.BLOCKQUOTE:
            out.append("{quote}")
            for line in blk.lines:
                out.append(_inline_confluence(line))
            out.append("{quote}")
            out.append("")
            continue

        if blk.type == BlockType.UNORDERED_LIST:
            levels = getattr(blk, "_levels", [1] * len(blk.lines))
            for item, depth in zip(blk.lines, levels, strict=False):
                prefix = "*" * depth
                out.append(f"{prefix} {_inline_confluence(item)}")
            out.append("")
            continue

        if blk.type == BlockType.ORDERED_LIST:
            levels = getattr(blk, "_levels", [1] * len(blk.lines))
            for item, depth in zip(blk.lines, levels, strict=False):
                prefix = "#" * depth
                out.append(f"{prefix} {_inline_confluence(item)}")
            out.append("")
            continue

    return "\n".join(out)


def _render_asciidoc(blocks: list[Block]) -> str:
    """Render blocks as AsciiDoc."""
    out: list[str] = []

    for blk in blocks:
        if blk.type == BlockType.EMPTY:
            out.append("")
            continue

        if blk.type == BlockType.HORIZONTAL_RULE:
            out.append("'''")
            out.append("")
            continue

        if blk.type == BlockType.HEADING:
            prefix = "=" * blk.level
            out.append(f"{prefix} {_inline_asciidoc(blk.lines[0])}")
            out.append("")
            continue

        if blk.type == BlockType.PARAGRAPH:
            out.append(_inline_asciidoc(" ".join(blk.lines)))
            out.append("")
            continue

        if blk.type == BlockType.CODE_BLOCK:
            if blk.language:
                out.append(f"[source,{blk.language}]")
            out.append("----")
            out.extend(blk.lines)
            out.append("----")
            out.append("")
            continue

        if blk.type == BlockType.TABLE:
            # AsciiDoc table format
            # Determine column count from first row
            first_cells = _parse_table_cells(blk.lines[0]) if blk.lines else []
            col_count = len(first_cells)
            out.append(f'[cols="{",".join(["1"] * col_count)}", options="header"]')
            out.append("|===")
            for idx, row in enumerate(blk.lines):
                cells = _parse_table_cells(row)
                if idx == blk.header_row:
                    # Header row
                    for cell in cells:
                        out.append(f"| {_inline_asciidoc(cell)}")
                    out.append("")
                else:
                    for cell in cells:
                        out.append(f"| {_inline_asciidoc(cell)}")
                    out.append("")
            out.append("|===")
            out.append("")
            continue

        if blk.type == BlockType.BLOCKQUOTE:
            out.append("[quote]")
            out.append("____")
            for line in blk.lines:
                out.append(_inline_asciidoc(line))
            out.append("____")
            out.append("")
            continue

        if blk.type == BlockType.UNORDERED_LIST:
            levels = getattr(blk, "_levels", [1] * len(blk.lines))
            for item, depth in zip(blk.lines, levels, strict=False):
                prefix = "*" * depth
                out.append(f"{prefix} {_inline_asciidoc(item)}")
            out.append("")
            continue

        if blk.type == BlockType.ORDERED_LIST:
            levels = getattr(blk, "_levels", [1] * len(blk.lines))
            for item, depth in zip(blk.lines, levels, strict=False):
                prefix = "." * depth
                out.append(f"{prefix} {_inline_asciidoc(item)}")
            out.append("")
            continue

    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML renderer (via mistune)
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 900px; margin: 2em auto; padding: 0 1em; color: #333; line-height: 1.6; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }}
  pre {{ background: #f5f5f5; padding: 1em; border-radius: 5px; overflow-x: auto; }}
  pre code {{ background: none; padding: 0; }}
  blockquote {{ border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; }}
  h1, h2, h3 {{ color: #2c3e50; }}
  hr {{ border: none; border-top: 2px solid #eee; margin: 2em 0; }}
  a {{ color: #3498db; }}
</style>
</head>
<body>
{content}
</body>
</html>"""


def _render_html(markdown_text: str, title: str = "Architecture Document") -> str:
    """Render Markdown as standalone HTML using mistune."""
    md = mistune.create_markdown(plugins=["table", "strikethrough"])
    html_body = md(markdown_text)
    return _HTML_TEMPLATE.format(title=title, content=html_body)


# ---------------------------------------------------------------------------
# Arc42 Template — Official chapter structure (EN + DE)
# ---------------------------------------------------------------------------

ARC42_CHAPTERS = {
    "en": {
        "01": "Introduction and Goals",
        "02": "Architecture Constraints",
        "03": "System Scope and Context",
        "04": "Solution Strategy",
        "05": "Building Block View",
        "06": "Runtime View",
        "07": "Deployment View",
        "08": "Crosscutting Concepts",
        "09": "Architecture Decisions",
        "10": "Quality Requirements",
        "11": "Risks and Technical Debt",
        "12": "Glossary",
    },
    "de": {
        "01": "Einführung und Ziele",
        "02": "Randbedingungen",
        "03": "Kontextabgrenzung",
        "04": "Lösungsstrategie",
        "05": "Bausteinsicht",
        "06": "Laufzeitsicht",
        "07": "Verteilungssicht",
        "08": "Querschnittliche Konzepte",
        "09": "Architekturentscheidungen",
        "10": "Qualitätsanforderungen",
        "11": "Risiken und technische Schulden",
        "12": "Glossar",
    },
}


def _get_chapter_number(filename: str) -> str | None:
    """Extract 2-digit chapter number from filename like '01-introduction.md'."""
    m = re.match(r"^(\d{2})-", filename)
    return m.group(1) if m else None


def _generate_arc42_toc(chapters: dict[str, str], lang: str, fmt: str) -> str:
    """Generate a Table of Contents page for arc42 in the given format."""
    title_map = {"en": "arc42 Architecture Documentation", "de": "arc42 Architekturdokumentation"}
    title = title_map.get(lang, title_map["en"])

    if fmt == "confluence":
        lines = [f"h1. {title}", ""]
        for num, name in sorted(chapters.items()):
            lines.append(f"# [{num}. {name}]")
        lines.append("")
        lines.append("{info}")
        lines.append("Based on arc42 template (https://arc42.org)")
        lines.append("{info}")
        return "\n".join(lines)

    elif fmt == "adoc":
        lines = [f"= {title}", ":toc:", ":toclevels: 2", ""]
        for num, name in sorted(chapters.items()):
            lines.append(f". {num}. {name}")
        lines.append("")
        lines.append("[NOTE]")
        lines.append("====")
        lines.append("Based on arc42 template (https://arc42.org)")
        lines.append("====")
        return "\n".join(lines)

    elif fmt == "html":
        items = "\n".join(
            f'  <li><a href="{num}-*.html">{num}. {name}</a></li>' for num, name in sorted(chapters.items())
        )
        body = f"<h1>{title}</h1>\n<ol>\n{items}\n</ol>\n"
        body += '<p><em>Based on <a href="https://arc42.org">arc42</a> template</em></p>'
        return _HTML_TEMPLATE.format(title=title, content=body)

    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class DocumentConverter:
    """Convert Markdown to Confluence Wiki Markup, AsciiDoc, and HTML.

    Usage:
        converter = DocumentConverter()
        converter.convert_directory(Path("architecture-docs"), ["confluence", "adoc", "html"])
    """

    FORMAT_EXTENSIONS = {
        "confluence": ".confluence",
        "adoc": ".adoc",
        "html": ".html",
    }

    def to_confluence(self, markdown: str) -> str:
        """Convert Markdown to Confluence Wiki Markup."""
        blocks = _parse_markdown(markdown)
        return _render_confluence(blocks)

    def to_asciidoc(self, markdown: str) -> str:
        """Convert Markdown to AsciiDoc."""
        blocks = _parse_markdown(markdown)
        return _render_asciidoc(blocks)

    def to_html(self, markdown: str, title: str = "Architecture Document") -> str:
        """Convert Markdown to standalone HTML."""
        return _render_html(markdown, title)

    def convert_file(self, md_path: Path, formats: list[str] | None = None) -> dict[str, Path]:
        """Convert a single .md file to the requested formats.

        Returns dict of {format_name: output_path}.
        """
        if formats is None:
            formats = list(self.FORMAT_EXTENSIONS.keys())

        content = md_path.read_text(encoding="utf-8")
        results: dict[str, Path] = {}

        for fmt in formats:
            ext = self.FORMAT_EXTENSIONS.get(fmt)
            if not ext:
                logger.warning(f"Unknown format: {fmt}")
                continue

            out_path = md_path.with_suffix(ext)

            if fmt == "confluence":
                converted = self.to_confluence(content)
            elif fmt == "adoc":
                converted = self.to_asciidoc(content)
            elif fmt == "html":
                title = md_path.stem.replace("-", " ").replace("_", " ").title()
                converted = self.to_html(content, title=title)
            else:
                continue

            out_path.write_text(converted, encoding="utf-8")
            results[fmt] = out_path

        return results

    def convert_directory(
        self,
        dir_path: Path,
        formats: list[str] | None = None,
        lang: str = "en",
    ) -> int:
        """Convert all .md files in a directory tree.

        Generates arc42 Table of Contents page for the arc42/ subdirectory.
        Args:
            lang: Language for arc42 chapter titles ("en" or "de").

        Returns total number of output files generated.
        """
        if formats is None:
            formats = list(self.FORMAT_EXTENSIONS.keys())

        total = 0
        md_files = sorted(dir_path.rglob("*.md"))

        for md_file in md_files:
            try:
                results = self.convert_file(md_file, formats)
                total += len(results)
            except Exception as e:
                logger.warning(f"Failed to convert {md_file.name}: {e}")

        # Generate arc42 Table of Contents
        arc42_dir = dir_path / "arc42"
        if arc42_dir.exists():
            chapters = ARC42_CHAPTERS.get(lang, ARC42_CHAPTERS["en"])
            for fmt in formats:
                ext = self.FORMAT_EXTENSIONS.get(fmt, "")
                toc_content = _generate_arc42_toc(chapters, lang, fmt)
                if toc_content:
                    toc_path = arc42_dir / f"00-arc42-toc{ext}"
                    toc_path.write_text(toc_content, encoding="utf-8")
                    total += 1

        return total
