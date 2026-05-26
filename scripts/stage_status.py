#!/usr/bin/env python3
"""stage_status.py — Resume-from-interruption stage detection.

Scans a session directory for stage output files and checks for the
<!-- STAGE_COMPLETE --> marker in the last 50 bytes. Reports the next
stage to execute, or "all stages complete".

Usage (via code_execution no SKILL.md):
    code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from stage_status import check
print(check("{session_dir}"))
    ''')
"""

from __future__ import annotations

import json
from pathlib import Path


# Stage output files in pipeline order
STAGE_FILES = [
    ("01-rq-brief.md", "Stage 1"),
    ("02-source-inventory.md", "Stage 2"),
    ("03-source-verification.md", "Stage 3"),
    ("04-synthesis.md", "Stage 4 / Synthesis"),
    ("05-report.md", "Stage 5 / Report"),
]

MARKER = "<!-- STAGE_COMPLETE -->"
SATURATION_CHECK = "_saturation_check.md"
SATURATION_STOP_MARKER = "STOP — proceed to Stage 5"


def _check_stage4_via_saturation(session: Path) -> str | None:
    """Check if Stage 4 is complete via _saturation_check.md.

    Returns:
        "complete" if saturation file exists and says STOP.
        "in_progress" if saturation file exists and says CONTINUE.
        None if no saturation file exists (fall back to 04-synthesis.md marker).
    """
    sat_path = session / "deep-reads" / SATURATION_CHECK
    if not sat_path.exists():
        return None
    try:
        text = sat_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if SATURATION_STOP_MARKER in text:
        return "complete"
    if "CONTINUE" in text:
        return "in_progress"
    return None


def check(session_dir: str) -> str:
    """Check which stages are complete in a session directory.

    Args:
        session_dir: Path to the session directory.

    Returns:
        JSON string with {"complete": [...], "incomplete": [...],
        "next_stage": str, "all_complete": bool}
    """
    session = Path(session_dir)
    complete: list[str] = []
    incomplete: list[str] = []
    missing: list[str] = []

    for filename, stage_name in STAGE_FILES:
        # Stage 4: prefer _saturation_check.md over 04-synthesis.md marker
        if filename == "04-synthesis.md":
            sat_status = _check_stage4_via_saturation(session)
            if sat_status == "complete":
                complete.append(stage_name)
                continue
            elif sat_status == "in_progress":
                incomplete.append(stage_name)
                continue
            # Fall through to normal marker check

        fpath = session / filename
        if not fpath.exists():
            missing.append(stage_name)
            continue
        try:
            # Check last 100 bytes for the marker
            with open(fpath, "rb") as f:
                f.seek(max(0, fpath.stat().st_size - 100))
                tail = f.read(100).decode("utf-8", errors="replace")
                if MARKER in tail:
                    complete.append(stage_name)
                else:
                    incomplete.append(stage_name)
        except OSError:
            incomplete.append(stage_name)

    # Determine next stage
    if missing:
        next_stage = missing[0]
        all_complete = False
    elif incomplete:
        next_stage = incomplete[0]
        all_complete = False
    else:
        next_stage = "Close / Verification"
        all_complete = True

    result = {
        "session_dir": str(session),
        "complete": complete,
        "incomplete": incomplete,
        "missing": missing,
        "next_stage": next_stage,
        "all_complete": all_complete,
    }

    # Add guidance for manual resumption
    if incomplete:
        result["warning"] = (
            f"Stage file(s) exist without STAGE_COMPLETE marker: "
            f"{', '.join(incomplete)}. These may be truncated — "
            f"recommend re-running from {incomplete[0] if incomplete else next_stage}."
        )

    # Add saturation check info if applicable
    sat_path = session / "deep-reads" / SATURATION_CHECK
    if sat_path.exists():
        try:
            sat_text = sat_path.read_text(encoding="utf-8")
            if "STOP" in sat_text:
                result["saturation_note"] = (
                    "Stage 4 saturation checkpoint found with STOP marker. "
                    "Stage 4 is considered complete even if 04-synthesis.md "
                    "does not have a STAGE_COMPLETE marker."
                )
        except OSError:
            pass

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        print(check(sys.argv[1]))
    else:
        print("Usage: python stage_status.py <session_dir>")
