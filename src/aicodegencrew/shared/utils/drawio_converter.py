"""
Draw.io File Converter

Converts LLM-generated Draw.io XML (plain text) to valid .drawio format
(deflate-compressed and base64-encoded).

Draw.io expects the mxGraphModel to be:
1. Deflate compressed
2. Base64 encoded
3. URL encoded (optional)

Usage:
    from aicodegencrew.shared.utils.drawio_converter import convert_drawio_file
    convert_drawio_file("path/to/file.drawio")

    # Or convert all files in a directory:
    convert_all_drawio_files("knowledge/architecture")
"""

import base64
import logging
import re
import urllib.parse
import zlib
from pathlib import Path

logger = logging.getLogger(__name__)


def compress_mxgraph(xml_content: str) -> str:
    """Compress mxGraphModel XML to Draw.io format.

    Args:
        xml_content: Plain XML string of mxGraphModel

    Returns:
        Base64-encoded deflate-compressed string
    """
    # Remove extra whitespace but keep structure
    xml_content = xml_content.strip()

    # URL encode first (Draw.io format)
    url_encoded = urllib.parse.quote(xml_content, safe="")

    # Deflate compress (raw deflate, not gzip)
    compressed = zlib.compress(url_encoded.encode("utf-8"), level=9)
    # Remove zlib header (first 2 bytes) and checksum (last 4 bytes) for raw deflate
    # Actually Draw.io uses deflateRaw which is different - let's use the proper method
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)  # -15 = raw deflate
    compressed = compressor.compress(url_encoded.encode("utf-8"))
    compressed += compressor.flush()

    # Base64 encode
    b64_encoded = base64.b64encode(compressed).decode("utf-8")

    return b64_encoded


def extract_mxgraphmodel(content: str) -> str | None:
    """Extract mxGraphModel XML from various formats.

    Handles:
    - CDATA wrapped content
    - Plain XML in diagram tag
    - Already compressed content (returns None)
    """
    # Check if already compressed (no XML tags visible)
    if "<mxGraphModel" not in content:
        return None  # Already compressed or invalid

    # Try to extract from CDATA
    cdata_match = re.search(r"<!\[CDATA\[(.*?)\]\]>", content, re.DOTALL)
    if cdata_match:
        return cdata_match.group(1).strip()

    # Try to extract mxGraphModel directly
    model_match = re.search(r"(<mxGraphModel.*?</mxGraphModel>)", content, re.DOTALL)
    if model_match:
        return model_match.group(1).strip()

    return None


def convert_drawio_file(file_path: Path) -> bool:
    """Convert a single Draw.io file to valid format.

    Args:
        file_path: Path to .drawio file

    Returns:
        True if converted, False if already valid or failed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False

    content = file_path.read_text(encoding="utf-8")

    # Extract mxGraphModel
    mxgraph_xml = extract_mxgraphmodel(content)

    if mxgraph_xml is None:
        logger.info(f"File already valid or no mxGraphModel found: {file_path}")
        return False

    # Compress the XML
    compressed = compress_mxgraph(mxgraph_xml)

    # Extract diagram id and name
    diagram_match = re.search(r'<diagram\s+id="([^"]*)"[^>]*name="([^"]*)"', content)
    diagram_id = diagram_match.group(1) if diagram_match else "diagram1"
    diagram_name = diagram_match.group(2) if diagram_match else "Page-1"

    # Extract mxfile attributes
    mxfile_match = re.search(r"<mxfile([^>]*)>", content)
    mxfile_attrs = mxfile_match.group(1) if mxfile_match else ' host="app.diagrams.net"'

    # Create valid Draw.io format
    valid_drawio = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile{mxfile_attrs}>
  <diagram id="{diagram_id}" name="{diagram_name}">{compressed}</diagram>
</mxfile>
'''

    # Write back
    file_path.write_text(valid_drawio, encoding="utf-8")
    logger.info(f"Converted: {file_path}")

    return True


def convert_all_drawio_files(directory: Path) -> int:
    """Convert all .drawio files in a directory (recursive).

    Args:
        directory: Root directory to search

    Returns:
        Number of files converted
    """
    directory = Path(directory)
    converted = 0

    for drawio_file in directory.rglob("*.drawio"):
        if convert_drawio_file(drawio_file):
            converted += 1

    logger.info(f"Converted {converted} Draw.io files in {directory}")
    return converted


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python drawio_converter.py <path>")
        print("  <path> can be a .drawio file or a directory")
        sys.exit(1)

    path = Path(sys.argv[1])

    logging.basicConfig(level=logging.INFO)

    if path.is_file():
        convert_drawio_file(path)
    elif path.is_dir():
        convert_all_drawio_files(path)
    else:
        print(f"Path not found: {path}")
        sys.exit(1)
