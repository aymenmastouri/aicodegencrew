"""Tests for the DocumentConverter (MD -> Confluence/AsciiDoc/HTML)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aicodegencrew.shared.utils.confluence_converter import (
    DocumentConverter,
    ARC42_CHAPTERS,
    _parse_markdown,
    _generate_arc42_toc,
    BlockType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MD = """\
# Architecture Overview

This is a **bold** and `inline code` paragraph.

## Components

| Name | Type | Technology |
|------|------|------------|
| UserService | Service | Spring Boot |
| AuthController | Controller | Spring MVC |

### Details

- Item one
- Item two
  - Nested item

1. First step
2. Second step

> This is a blockquote
> spanning two lines

```java
public class Foo {
    private int bar;
}
```

---

[Link text](https://example.com)

![Alt text](diagram.png)
"""


@pytest.fixture
def converter():
    return DocumentConverter()


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_parse_heading(self):
        blocks = _parse_markdown("# Title\n## Subtitle")
        headings = [b for b in blocks if b.type == BlockType.HEADING]
        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[0].lines == ["Title"]
        assert headings[1].level == 2

    def test_parse_code_block(self):
        md = "```java\nint x = 1;\n```"
        blocks = _parse_markdown(md)
        code = [b for b in blocks if b.type == BlockType.CODE_BLOCK]
        assert len(code) == 1
        assert code[0].language == "java"
        assert code[0].lines == ["int x = 1;"]

    def test_parse_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        blocks = _parse_markdown(md)
        tables = [b for b in blocks if b.type == BlockType.TABLE]
        assert len(tables) == 1
        assert tables[0].header_row == 0  # first data row is header
        assert len(tables[0].lines) == 2  # header + data (separator excluded)

    def test_parse_unordered_list(self):
        md = "- Apple\n- Banana"
        blocks = _parse_markdown(md)
        lists = [b for b in blocks if b.type == BlockType.UNORDERED_LIST]
        assert len(lists) == 1
        assert lists[0].lines == ["Apple", "Banana"]

    def test_parse_ordered_list(self):
        md = "1. First\n2. Second"
        blocks = _parse_markdown(md)
        lists = [b for b in blocks if b.type == BlockType.ORDERED_LIST]
        assert len(lists) == 1
        assert lists[0].lines == ["First", "Second"]

    def test_parse_blockquote(self):
        md = "> Quote line 1\n> Quote line 2"
        blocks = _parse_markdown(md)
        quotes = [b for b in blocks if b.type == BlockType.BLOCKQUOTE]
        assert len(quotes) == 1
        assert quotes[0].lines == ["Quote line 1", "Quote line 2"]

    def test_parse_hr(self):
        blocks = _parse_markdown("---")
        hrs = [b for b in blocks if b.type == BlockType.HORIZONTAL_RULE]
        assert len(hrs) == 1

    def test_empty_input(self):
        blocks = _parse_markdown("")
        # Empty string splits to [""] which is one empty line
        assert all(b.type == BlockType.EMPTY for b in blocks)


# ---------------------------------------------------------------------------
# Confluence tests
# ---------------------------------------------------------------------------

class TestConfluence:
    def test_heading(self, converter):
        result = converter.to_confluence("# Title")
        assert "h1. Title" in result

    def test_h2(self, converter):
        result = converter.to_confluence("## Subtitle")
        assert "h2. Subtitle" in result

    def test_bold(self, converter):
        result = converter.to_confluence("This is **bold** text")
        assert "*bold*" in result

    def test_inline_code(self, converter):
        result = converter.to_confluence("Use `myFunction()` here")
        assert "{{myFunction()}}" in result

    def test_code_block(self, converter):
        md = "```java\nint x = 1;\n```"
        result = converter.to_confluence(md)
        assert "{code:language=java}" in result
        assert "int x = 1;" in result
        assert "{code}" in result

    def test_code_block_no_lang(self, converter):
        md = "```\nplain code\n```"
        result = converter.to_confluence(md)
        assert "{code}" in result
        assert ":language=" not in result

    def test_table(self, converter):
        md = "| H1 | H2 |\n|---|---|\n| C1 | C2 |"
        result = converter.to_confluence(md)
        assert "||H1||H2||" in result
        assert "|C1|C2|" in result

    def test_link(self, converter):
        result = converter.to_confluence("[Click here](https://example.com)")
        assert "[Click here|https://example.com]" in result

    def test_image(self, converter):
        result = converter.to_confluence("![Alt](image.png)")
        assert "!image.png!" in result

    def test_unordered_list(self, converter):
        result = converter.to_confluence("- Item A\n- Item B")
        assert "* Item A" in result
        assert "* Item B" in result

    def test_ordered_list(self, converter):
        result = converter.to_confluence("1. Step 1\n2. Step 2")
        assert "# Step 1" in result
        assert "# Step 2" in result

    def test_blockquote(self, converter):
        result = converter.to_confluence("> Important note")
        assert "{quote}" in result
        assert "Important note" in result

    def test_horizontal_rule(self, converter):
        result = converter.to_confluence("---")
        assert "----" in result

    def test_full_document(self, converter):
        result = converter.to_confluence(SAMPLE_MD)
        assert "h1. Architecture Overview" in result
        assert "{code:language=java}" in result
        assert "||Name||Type||Technology||" in result
        assert "----" in result


# ---------------------------------------------------------------------------
# AsciiDoc tests
# ---------------------------------------------------------------------------

class TestAsciidoc:
    def test_heading(self, converter):
        result = converter.to_asciidoc("# Title")
        assert "= Title" in result

    def test_h2(self, converter):
        result = converter.to_asciidoc("## Subtitle")
        assert "== Subtitle" in result

    def test_bold(self, converter):
        result = converter.to_asciidoc("This is **bold** text")
        assert "*bold*" in result

    def test_code_block(self, converter):
        md = "```java\nint x = 1;\n```"
        result = converter.to_asciidoc(md)
        assert "[source,java]" in result
        assert "----" in result
        assert "int x = 1;" in result

    def test_link(self, converter):
        result = converter.to_asciidoc("[Click](https://example.com)")
        assert "link:https://example.com[Click]" in result

    def test_image(self, converter):
        result = converter.to_asciidoc("![Alt](diagram.png)")
        assert "image:diagram.png[Alt]" in result

    def test_table(self, converter):
        md = "| H1 | H2 |\n|---|---|\n| C1 | C2 |"
        result = converter.to_asciidoc(md)
        assert "|===" in result
        assert "| H1" in result
        assert "| C1" in result

    def test_unordered_list(self, converter):
        result = converter.to_asciidoc("- Item A\n- Item B")
        assert "* Item A" in result

    def test_ordered_list(self, converter):
        result = converter.to_asciidoc("1. Step 1\n2. Step 2")
        assert ". Step 1" in result

    def test_blockquote(self, converter):
        result = converter.to_asciidoc("> Quote text")
        assert "____" in result
        assert "Quote text" in result

    def test_horizontal_rule(self, converter):
        result = converter.to_asciidoc("---")
        assert "'''" in result

    def test_full_document(self, converter):
        result = converter.to_asciidoc(SAMPLE_MD)
        assert "= Architecture Overview" in result
        assert "[source,java]" in result
        assert "|===" in result


# ---------------------------------------------------------------------------
# HTML tests
# ---------------------------------------------------------------------------

class TestHTML:
    def test_basic_html(self, converter):
        result = converter.to_html("# Hello World")
        assert "<!DOCTYPE html>" in result
        assert "<h1>Hello World</h1>" in result

    def test_table_html(self, converter):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = converter.to_html(md)
        assert "<table>" in result
        assert "<th>" in result

    def test_code_block_html(self, converter):
        md = "```python\nprint('hi')\n```"
        result = converter.to_html(md)
        assert "<pre>" in result or "<code>" in result

    def test_custom_title(self, converter):
        result = converter.to_html("# Doc", title="My Title")
        assert "<title>My Title</title>" in result

    def test_full_document(self, converter):
        result = converter.to_html(SAMPLE_MD)
        assert "<!DOCTYPE html>" in result
        assert "Architecture Overview" in result
        assert "<table>" in result


# ---------------------------------------------------------------------------
# File conversion tests
# ---------------------------------------------------------------------------

class TestFileConversion:
    def test_convert_file(self, converter, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nHello **world**", encoding="utf-8")

        results = converter.convert_file(md_file)

        assert "confluence" in results
        assert "adoc" in results
        assert "html" in results
        assert results["confluence"].suffix == ".confluence"
        assert results["adoc"].suffix == ".adoc"
        assert results["html"].suffix == ".html"

        # Verify files exist and have content
        for path in results.values():
            assert path.exists()
            assert path.stat().st_size > 0

    def test_convert_file_single_format(self, converter, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Just Confluence", encoding="utf-8")

        results = converter.convert_file(md_file, formats=["confluence"])

        assert len(results) == 1
        assert "confluence" in results

    def test_convert_directory(self, converter, tmp_path):
        # Create arc42 structure
        arc42_dir = tmp_path / "arc42"
        arc42_dir.mkdir()
        (arc42_dir / "01-introduction.md").write_text("# Introduction", encoding="utf-8")
        (arc42_dir / "02-constraints.md").write_text("# Constraints", encoding="utf-8")

        c4_dir = tmp_path / "c4"
        c4_dir.mkdir()
        (c4_dir / "c4-context.md").write_text("# C4 Context", encoding="utf-8")

        total = converter.convert_directory(tmp_path, lang="en")

        # 3 md files x 3 formats = 9 + 3 ToC files = 12
        assert total == 12

        # Verify ToC files exist
        assert (arc42_dir / "00-arc42-toc.confluence").exists()
        assert (arc42_dir / "00-arc42-toc.adoc").exists()
        assert (arc42_dir / "00-arc42-toc.html").exists()

    def test_convert_directory_german(self, converter, tmp_path):
        arc42_dir = tmp_path / "arc42"
        arc42_dir.mkdir()
        (arc42_dir / "01-introduction.md").write_text("# Einfuhrung", encoding="utf-8")

        converter.convert_directory(tmp_path, lang="de")

        toc = (arc42_dir / "00-arc42-toc.confluence").read_text(encoding="utf-8")
        assert "Architekturdokumentation" in toc
        assert "Einführung und Ziele" in toc


# ---------------------------------------------------------------------------
# Arc42 template tests
# ---------------------------------------------------------------------------

class TestArc42Template:
    def test_chapters_have_12_entries(self):
        assert len(ARC42_CHAPTERS["en"]) == 12
        assert len(ARC42_CHAPTERS["de"]) == 12

    def test_chapter_numbers_01_to_12(self):
        expected = {f"{i:02d}" for i in range(1, 13)}
        assert set(ARC42_CHAPTERS["en"].keys()) == expected
        assert set(ARC42_CHAPTERS["de"].keys()) == expected

    def test_toc_confluence(self):
        toc = _generate_arc42_toc(ARC42_CHAPTERS["en"], "en", "confluence")
        assert "h1. arc42 Architecture Documentation" in toc
        assert "{info}" in toc
        assert "Introduction and Goals" in toc

    def test_toc_asciidoc(self):
        toc = _generate_arc42_toc(ARC42_CHAPTERS["en"], "en", "adoc")
        assert "= arc42 Architecture Documentation" in toc
        assert ":toc:" in toc
        assert "Introduction and Goals" in toc

    def test_toc_html(self):
        toc = _generate_arc42_toc(ARC42_CHAPTERS["en"], "en", "html")
        assert "<!DOCTYPE html>" in toc
        assert "Introduction and Goals" in toc
        assert "arc42.org" in toc

    def test_toc_unknown_format(self):
        toc = _generate_arc42_toc(ARC42_CHAPTERS["en"], "en", "xyz")
        assert toc == ""


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_markdown(self, converter):
        assert converter.to_confluence("") == ""
        assert converter.to_asciidoc("") == ""
        assert "<!DOCTYPE html>" in converter.to_html("")

    def test_only_whitespace(self, converter):
        result = converter.to_confluence("   \n   \n   ")
        assert isinstance(result, str)

    def test_nested_list(self, converter):
        md = "- Top\n  - Nested"
        result = converter.to_confluence(md)
        assert "* Top" in result
        assert "** Nested" in result

    def test_multiple_tables(self, converter):
        md = "| A |\n|---|\n| 1 |\n\n| B |\n|---|\n| 2 |"
        result = converter.to_confluence(md)
        assert result.count("||") >= 2  # at least 2 header rows
