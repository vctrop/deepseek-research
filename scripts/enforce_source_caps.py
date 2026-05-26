#!/usr/bin/env python3
"""Enforce max_sources_per_axis cap on 02-source-inventory.md.

Reads the source inventory, counts sources per axis (bibliography / codebase),
and truncates to the top-N by relevance if any axis exceeds the cap.

Usage:
    from enforce_source_caps import enforce_caps
    result = enforce_caps("path/to/02-source-inventory.md", max_per_axis=20)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _parse_inventory_sections(content: str) -> dict[str, list[dict]]:
    """Parse 02-source-inventory.md and return sources grouped by axis section.

    Returns dict with keys like 'bibliography', 'codebase', 'references', 'other'.
    Each value is a list of dicts with keys: id, title, relevance, raw_line.
    """
    sections: dict[str, list[dict]] = {}
    current_section: str | None = None

    # Patterns for section headers — match any header line that classifies sources
    # Examples: "### Section A: Bibliography Sources (Web-Discovered)"
    #           "### Section B: Codebase Sources"
    #           "## Bibliography Sources"
    section_pattern = re.compile(
        r'^#{2,3}\s+(?:Section\s+\w+:\s+)?(.+?)\s+Sources?\b', re.IGNORECASE
    )

    # Source row pattern: | S01 | Title ... | ... | N |
    source_row_pattern = re.compile(
        r'^\|\s*(S\d+|C\d+|B\d+|R\d+)\s*\|'
    )

    for line in content.split('\n'):
        # Detect section
        m = section_pattern.match(line)
        if m:
            section_name = m.group(1).strip().lower()
            # Normalize section names
            if 'bibliography' in section_name or 'bib' in section_name:
                current_section = 'bibliography'
            elif 'codebase' in section_name or 'code' in section_name:
                current_section = 'codebase'
            elif 'reference' in section_name or 'prior' in section_name or 'project' in section_name:
                current_section = 'references'
            elif 'oss' in section_name:
                current_section = 'codebase'
            else:
                current_section = 'other'
            if current_section not in sections:
                sections[current_section] = []

        # Detect source row
        m_src = source_row_pattern.match(line)
        if m_src and current_section:
            source_id = m_src.group(1)
            # Extract relevance (last numeric column before the final "| Why" column)
            # Format: | ID | Title | Location | Type | DOI | Relevance | Why |
            cols = [c.strip() for c in line.split('|')[1:-1]]
            relevance = 0
            if len(cols) >= 6:
                # Try the 6th column (0-indexed: 5)
                try:
                    relevance = int(cols[5])
                except (ValueError, IndexError):
                    pass
            if relevance == 0 and len(cols) >= 5:
                # Old format: 5 columns, relevance is 4th (index 4)
                try:
                    relevance = int(cols[4])
                except (ValueError, IndexError):
                    relevance = 0

            sections[current_section].append({
                'id': source_id,
                'relevance': relevance,
            })

    return sections


def enforce_caps(inventory_path: str, max_per_axis: int = 20) -> dict:
    """Enforce max_sources_per_axis on a source inventory file.

    Args:
        inventory_path: Path to 02-source-inventory.md (or draft).
        max_per_axis: Maximum sources per axis. 0 = disabled (no cap).

    Returns:
        Dict with per-axis before/after counts and removed source IDs.
    """
    path = Path(inventory_path)
    if not path.exists():
        return {"error": f"File not found: {inventory_path}"}

    content = path.read_text(encoding='utf-8')
    sections = _parse_inventory_sections(content)

    result = {}

    for axis, sources in sections.items():
        count = len(sources)
        if max_per_axis <= 0 or count <= max_per_axis:
            result[axis] = {
                "before": count,
                "after": count,
                "removed": [],
            }
            continue

        # Sort by relevance descending, then by source_id for determinism
        sources_sorted = sorted(sources, key=lambda s: (-s['relevance'], s['id']))
        kept = sources_sorted[:max_per_axis]
        removed = sources_sorted[max_per_axis:]

        result[axis] = {
            "before": count,
            "after": len(kept),
            "removed": [s['id'] for s in removed],
            "kept": [s['id'] for s in kept],
        }

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python enforce_source_caps.py <inventory_path> [max_per_axis]",
              file=sys.stderr)
        sys.exit(1)

    inventory_path = sys.argv[1]
    max_per_axis = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    result = enforce_caps(inventory_path, max_per_axis)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
