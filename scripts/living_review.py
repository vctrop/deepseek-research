#!/usr/bin/env python3
"""living_review.py — Living systematic review infrastructure.

Called via `code_execution` from Stage 1. Manages session state for update
cycles: load prior session, check if update is needed, merge new findings.

Usage:
    from living_review import load_session, needs_update, merge_update
    state = load_session(output_dir, slug)
    if needs_update(state, interval_days=90):
        merge_update(state, new_sources, new_findings)
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def load_session(output_dir: str, slug: str) -> dict | None:
    """Load a prior research session by slug.

    Returns dict with session metadata and artifact paths, or None if not found.
    Scans {output_dir}/ for directories matching *-{slug}.
    """
    base = Path(output_dir)
    if not base.exists():
        return None

    for session_dir in sorted(base.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue
        if session_dir.name.endswith(f"-{slug}"):
            return _load_session_from_dir(session_dir)
    return None


def needs_update(session: dict, interval_days: int = 90) -> bool:
    """Check if a session is due for surveillance update.

    Returns True if the last search date + interval_days < today.
    """
    last_search = session.get("last_search_date")
    if not last_search:
        return True

    try:
        last = datetime.fromisoformat(last_search).date()
    except (ValueError, TypeError):
        return True

    today = date.today()
    return (today - last).days >= interval_days


def merge_update(
    session_dir: str,
    update_number: int,
    new_sources: list[dict],
    new_findings: list[dict],
) -> dict:
    """Record an update to a living review.

    Args:
        session_dir: Path to the session directory.
        update_number: 1-based update count.
        new_sources: List of new source dicts found in this update.
        new_findings: List of new or revised findings.

    Returns:
        dict with update metadata.
    """
    update_record = {
        "update_number": update_number,
        "date": date.today().isoformat(),
        "new_sources_count": len(new_sources),
        "new_findings_count": len(new_findings),
    }

    # Append to MANIFEST.txt
    manifest_path = Path(session_dir) / "MANIFEST.txt"
    if manifest_path.exists():
        content = manifest_path.read_text(encoding="utf-8")
        content += (
            f"\n## Update {update_number}\n"
            f"date: {update_record['date']}\n"
            f"new_sources: {update_record['new_sources_count']}\n"
            f"new_findings: {update_record['new_findings_count']}\n"
        )
        manifest_path.write_text(content, encoding="utf-8")

    # Write update-specific manifest
    update_manifest_path = Path(session_dir) / f"update-{update_number}.json"
    update_manifest_path.write_text(
        json.dumps(update_record, indent=2) + "\n", encoding="utf-8"
    )

    return update_record


def get_latest_update(session_dir: str) -> int:
    """Return the latest update number for a session (0 if none)."""
    base = Path(session_dir)
    if not base.exists():
        return 0

    manifest = base / "MANIFEST.txt"
    if not manifest.exists():
        return 0

    content = manifest.read_text(encoding="utf-8")
    # Count "## Update N" headers
    import re

    updates = re.findall(r"## Update (\d+)", content)
    return max(int(u) for u in updates) if updates else 0


def _load_session_from_dir(session_dir: Path) -> dict | None:
    """Load session metadata from a session directory."""
    manifest = session_dir / "MANIFEST.txt"
    rq_brief = session_dir / "01-rq-brief.md"
    report = session_dir / "05-report.md"

    if not manifest.exists():
        return None

    # Parse MANIFEST.txt for key metadata
    content = manifest.read_text(encoding="utf-8")

    session = {
        "session_dir": str(session_dir),
        "slug": session_dir.name.split("-", 1)[1]
        if "-" in session_dir.name
        else session_dir.name,
        "date": session_dir.name.split("-", 1)[0]
        if "-" in session_dir.name
        else "",
        "has_rq_brief": rq_brief.exists(),
        "has_report": report.exists(),
    }

    # Extract last search date from manifest
    import re

    match = re.search(r"last_search_date:\s*(\S+)", content)
    if match:
        session["last_search_date"] = match.group(1)

    # Extract protocol DOI
    match = re.search(r"protocol_doi:\s*(\S+)", content)
    if match:
        session["protocol_doi"] = match.group(1)

    # Extract sources count
    match = re.search(r"sources_used:\s*(\d+)", content)
    if match:
        session["sources_used"] = int(match.group(1))

    # Extract RQ SHA
    match = re.search(r"rq_sha256:\s*([a-f0-9]+)", content)
    if match:
        session["rq_sha256"] = match.group(1)

    return session
