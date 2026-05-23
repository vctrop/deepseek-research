#!/usr/bin/env python3
"""stage_output.py — Stage output validation for idempotent pipeline execution.

Provides stage_output_exists(), stage_output_valid(), and stage_is_complete()
so the orchestrator can skip completed stages safely and detect corrupt outputs.

Called via code_execution from SKILL.md pre-flight checks at each stage.
"""

from __future__ import annotations

import json
from pathlib import Path

# Minimum expected content markers per stage output file.
# Each entry: filename -> list of substrings that must appear in a valid output.
# An empty list means "any non-empty content is valid" (for JSON files).
STAGE_MARKERS: dict[str, list[str]] = {
    "01-rq-brief.md":              ["## Research Question", "## Sub-Questions"],
    "01b-opensource-decision.md":  ["## Open-Source Applicability"],
    "02-source-inventory.md":      ["## Source Table", "PRISMA"],
    "03-source-verification.md":   ["Risk of Bias", "## Verification"],
    "04-synthesis.md":             ["## Summary", "## Evidence"],
    "04a-devils-advocate.md":      ["## Devil's Advocate"],
    "05-report.md":                ["## Abstract", "## Findings"],
    "05-plain-summary.md":         ["## Plain Language Summary"],
    "05-decision-brief.md":        ["## Decision Brief"],
}


def stage_output_exists(session_dir: str, filename: str) -> bool:
    """Check if a stage output file exists and is non-empty.

    Args:
        session_dir: Session output directory (e.g., "research-reports/2026-05-22-slug/").
        filename: Output filename (e.g., "01-rq-brief.md").

    Returns:
        True if the file exists and has > 0 bytes.
    """
    path = Path(session_dir) / filename
    return path.is_file() and path.stat().st_size > 0


def stage_output_valid(session_dir: str, filename: str) -> bool:
    """Check if a stage output file exists, is non-empty, and is structurally valid.

    Validation rules:
      - Markdown files with known markers: must contain all expected headings.
      - JSON files: must be valid JSON.
      - Files without known markers: non-empty is sufficient.
      - Unknown files: non-empty is sufficient.

    Args:
        session_dir: Session output directory.
        filename: Output filename.

    Returns:
        True if the file passes structural validation.
    """
    path = Path(session_dir) / filename
    if not stage_output_exists(session_dir, filename):
        return False

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    # JSON files: validate parseability
    if filename.endswith(".json"):
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False

    # Markdown files with known markers
    if filename in STAGE_MARKERS:
        markers = STAGE_MARKERS[filename]
        if markers:
            return all(marker in content for marker in markers)

    # Unknown files: already verified non-empty by stage_output_exists
    return True


def stage_is_complete(session_dir: str, filename: str) -> bool:
    """Both exists and structurally valid → stage is complete. Safe to skip.

    Args:
        session_dir: Session output directory.
        filename: Output filename.

    Returns:
        True if the stage output is present and valid.
    """
    return stage_output_exists(session_dir, filename) and stage_output_valid(session_dir, filename)


# Self-test
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        # Test 1: missing file
        assert not stage_output_exists(tmp, "01-rq-brief.md")
        assert not stage_is_complete(tmp, "01-rq-brief.md")

        # Test 2: empty file → NOT considered "exists" (0 bytes = no output)
        path = Path(tmp) / "01-rq-brief.md"
        path.write_text("")
        assert not stage_output_exists(tmp, "01-rq-brief.md")
        assert not stage_is_complete(tmp, "01-rq-brief.md")

        # Test 3: valid file with all markers
        path.write_text("## Research Question\n...\n## Sub-Questions\n...")
        assert stage_is_complete(tmp, "01-rq-brief.md")

        # Test 4: file missing one marker → invalid
        path.write_text("## Research Question\n...\n## Methods\n...")
        assert not stage_output_valid(tmp, "01-rq-brief.md")

        # Test 5: JSON validation — valid
        json_path = Path(tmp) / "05-data-supplement.json"
        json_path.write_text('{"key": "value"}')
        assert stage_is_complete(tmp, "05-data-supplement.json")

        # Test 6: JSON validation — invalid
        json_path.write_text("not json at all")
        assert not stage_output_valid(tmp, "05-data-supplement.json")

        # Test 7: unknown extension — non-empty is sufficient
        unknown = Path(tmp) / "some-file.txt"
        unknown.write_text("hello world")
        assert stage_is_complete(tmp, "some-file.txt")

        # Test 8: unicode content
        unicode_path = Path(tmp) / "05-report.md"
        unicode_path.write_text("## Abstract\nRésumé\n## Findings\nConclusão")
        assert stage_is_complete(tmp, "05-report.md")

    print("All self-tests PASSED")
