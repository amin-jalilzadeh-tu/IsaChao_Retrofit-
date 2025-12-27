"""
Semantic chunking strategies for markdown documentation.

Uses header-based splitting to preserve document structure,
which provides better context than arbitrary token-based splits.
"""
import re
from pathlib import Path
from typing import List, Dict, Any


def chunk_markdown_by_headers(
    content: str,
    source_file: str
) -> List[Dict[str, Any]]:
    """Chunk markdown content by headers (H1, H2, H3).

    Preserves document structure by splitting on headers and
    tracking the header hierarchy in metadata.

    Args:
        content: Markdown content
        source_file: Name of source file (for metadata)

    Returns:
        List of chunks with text and metadata
    """
    chunks = []

    # Track current header hierarchy
    current_h1 = ""
    current_h2 = ""
    current_h3 = ""

    # Split by any header
    lines = content.split("\n")
    current_chunk_lines = []

    for line in lines:
        # Check for headers
        h1_match = re.match(r"^# (.+)$", line)
        h2_match = re.match(r"^## (.+)$", line)
        h3_match = re.match(r"^### (.+)$", line)

        if h1_match or h2_match or h3_match:
            # Save current chunk if it has content
            if current_chunk_lines:
                chunk_text = "\n".join(current_chunk_lines).strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "source": source_file,
                            "h1": current_h1,
                            "h2": current_h2,
                            "h3": current_h3,
                        }
                    })
                current_chunk_lines = []

            # Update header hierarchy
            if h1_match:
                current_h1 = h1_match.group(1)
                current_h2 = ""
                current_h3 = ""
            elif h2_match:
                current_h2 = h2_match.group(1)
                current_h3 = ""
            elif h3_match:
                current_h3 = h3_match.group(1)

        # Add line to current chunk
        current_chunk_lines.append(line)

    # Don't forget the last chunk
    if current_chunk_lines:
        chunk_text = "\n".join(current_chunk_lines).strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": source_file,
                    "h1": current_h1,
                    "h2": current_h2,
                    "h3": current_h3,
                }
            })

    return chunks


def chunk_markdown_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read and chunk a markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        List of chunks with text and metadata
    """
    content = file_path.read_text(encoding="utf-8")
    return chunk_markdown_by_headers(content, file_path.name)


def chunk_all_markdown_files(docs_dir: Path) -> List[Dict[str, Any]]:
    """Chunk all markdown files in a directory.

    Args:
        docs_dir: Directory containing markdown files

    Returns:
        List of all chunks from all files
    """
    all_chunks = []

    for md_file in docs_dir.glob("*.md"):
        file_chunks = chunk_markdown_file(md_file)
        all_chunks.extend(file_chunks)
        print(f"  Chunked {md_file.name}: {len(file_chunks)} chunks")

    return all_chunks


def csv_row_to_text(row: Dict[str, Any], time_horizon: int) -> str:
    """Convert a CSV row to natural language description.

    Args:
        row: Row from simulation CSV as dictionary
        time_horizon: Climate scenario year (2020, 2050, 2100)

    Returns:
        Natural language description of the building scenario
    """
    # Handle different column naming conventions
    sim_id = row.get("Simulation ID", row.get("simulation_id", "unknown"))
    windows_u = row.get("windows_U_Factor", row.get("Windows U-Factor", 0))
    ground_r = row.get("groundfloor_thermal_resistance",
                       row.get("Ground Floor Thermal Resistance", 0))
    walls_r = row.get("ext_walls_thermal_resistance",
                      row.get("External Walls Thermal Resistance", 0))
    roof_r = row.get("roof_thermal_resistance",
                     row.get("Roof Thermal Resistance", 0))

    return f"""Building retrofit scenario {sim_id}:
Climate scenario: {time_horizon}
Design variables:
- Windows U-Factor: {windows_u} W/m²K
- Ground floor thermal resistance: {ground_r} m²K/W
- External walls thermal resistance: {walls_r} m²K/W
- Roof thermal resistance: {roof_r} m²K/W"""
