"""
DrawioDiagramTool - Tool for creating Draw.io diagrams programmatically.

Agents can use this tool to create C4 diagrams without worrying about XML encoding.
"""

import base64
import urllib.parse
import zlib
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class DrawioDiagramInput(BaseModel):
    """Input schema for DrawioDiagramTool."""

    file_path: str = Field(description="The path to save the .drawio file (relative to knowledge/document/)")
    diagram_name: str = Field(description="Name of the diagram (shown in tab)")
    nodes: list[dict[str, Any]] = Field(
        description="List of nodes. Each node: {id: str, label: str, x: int, y: int, width: int, height: int, style: str}"
    )
    edges: list[dict[str, Any]] = Field(
        description="List of edges. Each edge: {source: str, target: str, label: str (optional)}"
    )


class DrawioDiagramTool(BaseTool):
    """
    Tool for creating Draw.io diagrams programmatically.

    Example usage:
        nodes = [
            {"id": "frontend", "label": "Frontend\\n(Angular)", "x": 100, "y": 100, "width": 180, "height": 80, "style": "rounded=1;fillColor=#E3F2FD"},
            {"id": "backend", "label": "Backend\\n(Spring Boot)", "x": 350, "y": 100, "width": 200, "height": 80, "style": "rounded=1;fillColor=#FFF3E0"}
        ]
        edges = [
            {"source": "frontend", "target": "backend", "label": "REST API"}
        ]

        create_drawio_diagram(file_path="c4/diagram.drawio", diagram_name="Container", nodes=nodes, edges=edges)
    """

    name: str = "create_drawio_diagram"
    description: str = (
        "Create a Draw.io diagram file. "
        "Provide nodes (boxes/shapes) and edges (connections). "
        "The tool handles XML generation and compression automatically."
    )
    args_schema: type[BaseModel] = DrawioDiagramInput

    def _run(self, file_path: str, diagram_name: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
        """Create a Draw.io diagram."""
        try:
            # Build mxGraphModel XML
            xml_parts = [
                '<mxGraphModel dx="1240" dy="720" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100">',
                "  <root>",
                '    <mxCell id="0"/>',
                '    <mxCell id="1" parent="0"/>',
            ]

            # Add nodes
            for node in nodes:
                node_id = node.get("id", "node_" + str(hash(node.get("label", "unnamed"))))
                label = node.get("label", "").replace("\n", "&#xa;")  # Convert newlines for XML
                x = node.get("x", 100)
                y = node.get("y", 100)
                width = node.get("width", 120)
                height = node.get("height", 60)
                style = node.get("style", "rounded=1;whiteSpace=wrap;html=1")

                xml_parts.append(f'    <mxCell id="{node_id}" value="{label}" style="{style}" vertex="1" parent="1">')
                xml_parts.append(f'      <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry"/>')
                xml_parts.append("    </mxCell>")

            # Add edges
            edge_id_counter = 0
            for edge in edges:
                edge_id = f"edge_{edge_id_counter}"
                edge_id_counter += 1
                source = edge.get("source", "")
                target = edge.get("target", "")
                label = edge.get("label", "").replace("\n", "&#xa;")

                xml_parts.append(
                    f'    <mxCell id="{edge_id}" value="{label}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1" edge="1" parent="1" source="{source}" target="{target}">'
                )
                xml_parts.append('      <mxGeometry relative="1" as="geometry"/>')
                xml_parts.append("    </mxCell>")

            xml_parts.append("  </root>")
            xml_parts.append("</mxGraphModel>")

            mxgraph_xml = "\n".join(xml_parts)

            # Compress and encode
            compressed = self._compress_mxgraph(mxgraph_xml)

            # Create Draw.io file format
            drawio_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="{self._get_timestamp()}" agent="AI Agent" version="20.0.5" type="device">
  <diagram id="diagram1" name="{diagram_name}">{compressed}</diagram>
</mxfile>
'''

            # Write to file
            base_dir = Path("knowledge/document")
            # Strip base_dir prefix if agent already included it (prevents double-nesting)
            clean_path = file_path.replace("knowledge/document/", "").replace("knowledge\\document\\", "")
            # Also strip legacy path if agent uses old convention
            clean_path = clean_path.replace("knowledge/architecture/", "").replace("knowledge\\architecture\\", "")
            full_path = base_dir / clean_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(drawio_content, encoding="utf-8")

            return f"Successfully created Draw.io diagram: {full_path} ({len(nodes)} nodes, {len(edges)} edges)"

        except Exception as e:
            return f"Error creating Draw.io diagram: {e}"

    def _compress_mxgraph(self, xml_content: str) -> str:
        """Compress mxGraphModel XML to Draw.io format."""
        # URL encode
        url_encoded = urllib.parse.quote(xml_content, safe="")

        # Deflate compress (raw deflate)
        compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed = compressor.compress(url_encoded.encode("utf-8"))
        compressed += compressor.flush()

        # Base64 encode
        b64_encoded = base64.b64encode(compressed).decode("utf-8")

        return b64_encoded

    def _get_timestamp(self) -> str:
        """Get current timestamp in Draw.io format."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
