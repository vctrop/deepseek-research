#!/usr/bin/env python3
"""index_sources.py — Flat JSON index manager for deepseek-research corpus persistence.

Manages bibliography/ as a flat directory with a single bibliography/index/sources.json
index.  Provides init, scan-unindexed, query, add_source (programmatic), and
update-sessions.

Pure Python 3.12 stdlib — no external packages.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDEX_FILENAME: str = "sources.json"

SOURCE_EXTENSIONS: set[str] = {".pdf", ".txt", ".md", ".epub", ".djvu", ".ps"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bibliography_root(base_dir: Path) -> Path:
    """Return base_dir as-is — bibliography_path already points to the bibliography/ directory."""
    return base_dir


def _index_dir(base_dir: Path) -> Path:
    return _bibliography_root(base_dir) / "index"


def _index_path(base_dir: Path) -> Path:
    return _index_dir(base_dir) / INDEX_FILENAME


def _load_index(base_dir: Path) -> list[dict]:
    path = _index_path(base_dir)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index(base_dir: Path, entries: list[dict]) -> None:
    path = _index_path(base_dir)
    path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _indexed_paths(base_dir: Path) -> set[str]:
    return {e.get("path", "") for e in _load_index(base_dir) if e.get("path")}


def _indexed_ids(base_dir: Path) -> set[str]:
    return {e.get("id", "") for e in _load_index(base_dir) if e.get("id")}


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", text) if t]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def init_sources(base_dir: Path) -> None:
    """Bootstrap bibliography/index/ directory with an empty sources.json.

    Idempotent: creates missing dirs and index file, never overwrites existing index.
    """
    biblio = _bibliography_root(base_dir)
    biblio.mkdir(parents=True, exist_ok=True)
    idx_dir = _index_dir(base_dir)
    idx_dir.mkdir(parents=True, exist_ok=True)
    idx_path = _index_path(base_dir)
    if not idx_path.exists():
        idx_path.write_text("[]", encoding="utf-8")


def scan_unindexed(base_dir: Path) -> list[str]:
    """Find files in bibliography/ not present in the index.

    Scans bibliography/ root only (flat directory). Ignores dotfiles, the index/
    subdirectory, and files with extensions not in SOURCE_EXTENSIONS.

    Returns a list of relative paths (relative to bibliography/).
    """
    biblio = _bibliography_root(base_dir)
    indexed = _indexed_paths(base_dir)
    unindexed: list[str] = []

    if not biblio.is_dir():
        return unindexed

    for item in sorted(biblio.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            continue  # skip index/ and any other subdirs
        if item.suffix not in SOURCE_EXTENSIONS:
            continue
        if item.name not in indexed:
            unindexed.append(item.name)

    return unindexed


def query_sources(
    base_dir: Path,
    keywords: list[str],
    top_n: int = 10,
) -> list[dict]:
    """Score index entries by weighted token overlap and return top N.

    Scoring weights:
        - keywords field: 3x per matching token
        - title field:      2x per matching token
        - summary field:    1x per matching token

    Tokens are produced by splitting on non-alphanumeric chars, lowercased.
    Entries with zero score are excluded.
    """
    query_tokens = set(_tokenize(" ".join(keywords)))
    if not query_tokens:
        return []

    scored: list[tuple[float, dict]] = []

    for entry in _load_index(base_dir):
        score = 0.0

        # Keywords (3x)
        kw_tokens: set[str] = set()
        for kw in entry.get("keywords", []):
            kw_tokens.update(_tokenize(kw))
        score += 3 * len(query_tokens & kw_tokens)

        # Title (2x)
        title_tokens = set(_tokenize(entry.get("title", "")))
        score += 2 * len(query_tokens & title_tokens)

        # Summary (1x)
        summary_tokens = set(_tokenize(entry.get("summary", "")))
        score += 1 * len(query_tokens & summary_tokens)

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [entry for _, entry in scored[:top_n]]


def add_source(
    base_dir: Path,
    file_path: Path,
    entry: dict,
) -> dict:
    """Copy a file into bibliography/ and append an index entry.

    Args:
        base_dir: Path to the research-reports/ directory (or skill dir).
        file_path: Current location of the source file (will be copied, not moved).
        entry: Index entry dict (must include 'id').

    Returns:
        The completed entry dict (with path, indexed_at, indexed_by filled in).

    Raises:
        ValueError: If entry['id'] is missing or already exists in the index.
    """
    if "id" not in entry:
        raise ValueError("Entry must include an 'id' field.")

    entry_id = entry["id"]

    if entry_id in _indexed_ids(base_dir):
        raise ValueError(f"Duplicate ID '{entry_id}' already exists in the index.")

    biblio = _bibliography_root(base_dir)
    biblio.mkdir(parents=True, exist_ok=True)

    ext = file_path.suffix
    dest = biblio / f"{entry_id}{ext}"

    # Copy (not move) — original may still be in session dir
    shutil.copy2(str(file_path), str(dest))

    entry["path"] = f"{entry_id}{ext}"
    entry["indexed_at"] = str(date.today())
    entry["indexed_by"] = "auto"

    entries = _load_index(base_dir)
    entries.append(entry)
    _save_index(base_dir, entries)

    return entry


def update_sessions(base_dir: Path, entry_id: str, session_slug: str) -> None:
    """Append a session slug to sessions_used for a given entry.

    Raises:
        KeyError: If the entry_id is not found in the index.
    """
    entries = _load_index(base_dir)
    for entry in entries:
        if entry.get("id") == entry_id:
            sessions = entry.setdefault("sessions_used", [])
            if session_slug not in sessions:
                sessions.append(session_slug)
            _save_index(base_dir, entries)
            return

    raise KeyError(f"Entry ID '{entry_id}' not found in the index.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="index_sources",
        description="Manage the deepseek-research bibliography index.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Bootstrap bibliography/index/ directory.")
    p_init.add_argument(
        "--base-dir", required=True, type=Path,
        help="Path to research-reports/ or skill directory.",
    )

    p_scan = sub.add_parser("scan-unindexed", help="Find unindexed files in bibliography/.")
    p_scan.add_argument(
        "--base-dir", required=True, type=Path,
        help="Path to research-reports/ or skill directory.",
    )

    p_query = sub.add_parser("query", help="Keyword search of the index.")
    p_query.add_argument(
        "--base-dir", required=True, type=Path,
        help="Path to research-reports/ or skill directory.",
    )
    p_query.add_argument(
        "--keywords", required=True, type=str,
        help="Comma-separated keywords.",
    )
    p_query.add_argument(
        "--top", type=int, default=10,
        help="Number of results (default: 10).",
    )

    p_update = sub.add_parser("update-sessions", help="Append a session slug to an entry.")
    p_update.add_argument(
        "--base-dir", required=True, type=Path,
        help="Path to research-reports/ or skill directory.",
    )
    p_update.add_argument("--id", required=True, type=str, help="Entry ID.")
    p_update.add_argument("--session", required=True, type=str, help="Session slug.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        init_sources(args.base_dir)
        return 0

    elif args.command == "scan-unindexed":
        result = scan_unindexed(args.base_dir)
        print(json.dumps(result, indent=2))
        return 0

    elif args.command == "query":
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        result = query_sources(args.base_dir, kws, top_n=args.top)
        print(json.dumps(result, indent=2))
        return 0

    elif args.command == "update-sessions":
        try:
            update_sessions(args.base_dir, getattr(args, "id"), args.session)
        except KeyError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
