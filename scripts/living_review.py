#!/usr/bin/env python3
"""living_review.py — Living systematic review support for deepseek-research.

Enables surveillance searches and update cycles for prior research sessions.
When a session has `living_review = true` in its config, this module:
1. Checks if the surveillance interval has elapsed since last search
2. Runs targeted web searches for new evidence since the last search date
3. Flags sessions needing updates

Usage:
    from living_review import check_update_needed, run_surveillance_search
    status = check_update_needed(session_dir, surveillance_interval_days=90)
    if status["needs_update"]:
        results = run_surveillance_search(session_dir, rq_text, main_topic)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _read_manifest(session_dir: str) -> dict:
    """Read MANIFEST.txt and extract structured data. Returns empty dict on failure."""
    manifest_path = Path(session_dir) / "MANIFEST.txt"
    if not manifest_path.exists():
        return {}

    data: dict = {"raw": manifest_path.read_text(encoding="utf-8")}

    # Extract structured fields from MANIFEST format
    text = data["raw"]
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## Gate Results"):
            break
        if line.startswith("- ") or line.startswith("* "):
            # Key-value pairs in list format
            content = line[2:]
            if ":" in content:
                key, _, value = content.partition(":")
                data[key.strip().lower().replace(" ", "_")] = value.strip()
        elif ":" in line and not line.startswith("#") and not line.startswith("|"):
            key, _, value = line.partition(":")
            data[key.strip().lower().replace(" ", "_")] = value.strip()

    return data


def check_update_needed(
    session_dir: str,
    surveillance_interval_days: int = 90,
) -> dict:
    """Check if a prior research session needs a living review update.

    Args:
        session_dir: Path to the session directory.
        surveillance_interval_days: Days between surveillance searches.

    Returns:
        dict with keys: needs_update, session_slug, last_search_date,
        days_elapsed, next_surveillance_date, reason.
    """
    slug = Path(session_dir).name
    manifest = _read_manifest(session_dir)

    last_search = manifest.get("last_search_date", "")
    if not last_search:
        # Try to extract from session directory name (date prefix)
        if len(slug) >= 10 and slug[4] == "-" and slug[7] == "-":
            last_search = slug[:10]  # YYYY-MM-DD

    if not last_search:
        return {
            "needs_update": True,
            "session_slug": slug,
            "last_search_date": "unknown",
            "days_elapsed": None,
            "next_surveillance_date": "unknown",
            "reason": "No last_search_date in MANIFEST — treat as needing update",
        }

    try:
        last_date = datetime.fromisoformat(last_search[:10]).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return {
            "needs_update": True,
            "session_slug": slug,
            "last_search_date": last_search,
            "days_elapsed": None,
            "next_surveillance_date": "unknown",
            "reason": f"Could not parse last_search_date: {last_search}",
        }

    now = datetime.now(timezone.utc)
    days_elapsed = (now - last_date).days
    next_surveillance = last_date + timedelta(days=surveillance_interval_days)

    if days_elapsed >= surveillance_interval_days:
        return {
            "needs_update": True,
            "session_slug": slug,
            "last_search_date": last_date.strftime("%Y-%m-%d"),
            "days_elapsed": days_elapsed,
            "next_surveillance_date": next_surveillance.strftime("%Y-%m-%d"),
            "reason": f"Surveillance interval exceeded ({days_elapsed}d ≥ {surveillance_interval_days}d)",
        }
    else:
        return {
            "needs_update": False,
            "session_slug": slug,
            "last_search_date": last_date.strftime("%Y-%m-%d"),
            "days_elapsed": days_elapsed,
            "next_surveillance_date": next_surveillance.strftime("%Y-%m-%d"),
            "reason": f"Within surveillance window ({days_elapsed}d < {surveillance_interval_days}d)",
        }


def build_surveillance_queries(
    rq_text: str,
    main_topic: str,
    last_search_date: str,
) -> list[str]:
    """Build date-filtered search queries for surveillance.

    Args:
        rq_text: Original research question.
        main_topic: Short topic name for focused queries.
        last_search_date: ISO date of last search (YYYY-MM-DD).

    Returns:
        List of query strings with date-range filters.
    """
    # Build date-filtered queries
    date_filter = f"after:{last_search_date}"
    return [
        f"{main_topic} {date_filter}",
        f'"{main_topic}" recent advances {date_filter}',
        f"{main_topic} new evidence {date_filter}",
        f'"{rq_text[:80]}" {date_filter}',
    ]


def record_surveillance(
    session_dir: str,
    queries_run: list[str],
    new_sources_found: int,
) -> None:
    """Record a surveillance search in MANIFEST.txt.

    Args:
        session_dir: Session directory path.
        queries_run: List of search queries executed.
        new_sources_found: Number of new sources discovered.
    """
    manifest_path = Path(session_dir) / "MANIFEST.txt"
    if not manifest_path.exists():
        return

    now = datetime.now(timezone.utc).isoformat()
    update_entry = f"""
## Living Review Update — {now[:19]}Z
- last_search_date: {now[:10]}
- queries_run: {len(queries_run)}
- new_sources_found: {new_sources_found}
- surveillance_status: {"new_evidence_found" if new_sources_found > 0 else "up_to_date"}
"""

    with open(manifest_path, "a", encoding="utf-8") as f:
        f.write(update_entry)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    """Run self-test. Returns 0 on success, 1 on failure."""
    import tempfile, os

    errors = 0
    tmpdir = tempfile.mkdtemp()

    try:
        # Create a test session with a MANIFEST
        session_dir = os.path.join(tmpdir, "2025-01-15-test-slug")
        os.makedirs(session_dir)

        manifest_content = """# MANIFEST — 2025-01-15-test-slug
- session_slug: 2025-01-15-test-slug
- last_search_date: 2025-01-15
- protocol_sha256: abc123
- sources_total: 12
## Gate Results
| GATE-1 | PASS | All expected files present |
"""
        with open(os.path.join(session_dir, "MANIFEST.txt"), "w") as f:
            f.write(manifest_content)

        # Test check_update_needed — should need update (Jan 2025 > 90 days ago)
        status = check_update_needed(session_dir, surveillance_interval_days=90)
        assert status["needs_update"], f"Expected needs_update=True, got {status}"
        assert status["last_search_date"] == "2025-01-15"
        print(f"  Update check: {status['reason']}")

        # Test with very long interval — should not need update
        status2 = check_update_needed(session_dir, surveillance_interval_days=9999)
        assert not status2["needs_update"], f"Expected needs_update=False, got {status2}"
        print(f"  No-update check: {status2['reason']}")

        # Test query builder
        queries = build_surveillance_queries(
            "How does X work?", "X mechanism", "2025-01-15"
        )
        assert len(queries) == 4, f"Expected 4 queries, got {len(queries)}"
        assert all("after:2025-01-15" in q for q in queries)
        print(f"  Query builder: {len(queries)} queries with date filter")

        # Test record_surveillance
        record_surveillance(session_dir, queries, 3)
        updated_manifest = _read_manifest(session_dir)
        assert "last_search_date" in updated_manifest
        print(f"  Record surveillance: OK")

    finally:
        import shutil
        shutil.rmtree(tmpdir)

    print(f"\nAll self-tests {'passed' if errors == 0 else 'FAILED'}.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    else:
        print("living_review.py — Use --self-test to validate, or import as module.")
        print("Functions: check_update_needed, build_surveillance_queries, record_surveillance")
