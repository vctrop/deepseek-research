#!/usr/bin/env python3
"""index_sources.py -- Searchable JSON index manager for bibliography persistence.

Manages a bibliography/ directory tree with typed subdirectories (papers, reports, books)
and per-type JSON index files. Provides init, scan, add, query, and session tracking.

CLI subcommands: init, scan-unindexed, add, query, update-sessions.

Pure Python 3.12 stdlib -- no external packages.
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

INDEX_FILES: dict[str, str] = {
    "papers": "papers.json",
    "reports": "reports.json",
    "books": "books.json",
}

SOURCE_DIRS: tuple[str, ...] = ("papers", "reports", "books")

SOURCE_EXTENSIONS: set[str] = {".pdf", ".txt", ".md", ".epub", ".djvu", ".ps", ".bib"}

TYPE_TO_DIR: dict[str, str] = {
    "paper": "papers",
    "report": "reports",
    "book": "books",
}

TYPE_TO_INDEX: dict[str, str] = {
    "paper": "papers.json",
    "report": "reports.json",
    "book": "books.json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _index_dir(base_dir: Path) -> Path:
    """Return the index/ subdirectory within base_dir."""
    return base_dir / "index"


def _load_index(base_dir: Path, index_filename: str) -> list[dict]:
    path = _index_dir(base_dir) / index_filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index(base_dir: Path, index_filename: str, entries: list[dict]) -> None:
    path = _index_dir(base_dir) / index_filename
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _all_indexed_paths(base_dir: Path) -> set[str]:
    """Return the set of all 'path' values across every index file."""
    paths: set[str] = set()
    for idx_file in INDEX_FILES.values():
        for entry in _load_index(base_dir, idx_file):
            p = entry.get("path")
            if p:
                paths.add(p)
    return paths


def _all_indexed_ids(base_dir: Path) -> set[str]:
    """Return the set of all 'id' values across every index file."""
    ids: set[str] = set()
    for idx_file in INDEX_FILES.values():
        for entry in _load_index(base_dir, idx_file):
            eid = entry.get("id")
            if eid:
                ids.add(eid)
    return ids


def _tokenize(text: str) -> list[str]:
    """Split text on non-alphanumeric chars and lowercase.
    Unicode-aware: uses \w (word characters) with re.UNICODE flag.
    """
    return [t.lower() for t in re.findall(r"\w+", text, re.UNICODE) if t]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def init_sources(base_dir: Path) -> None:
    """Bootstrap bibliography/ directory structure with empty JSON arrays.

    Idempotent: creates missing dirs and index files but never overwrites
    existing index files.
    """
    # Create typed subdirectories directly under base_dir
    for d in SOURCE_DIRS:
        (base_dir / d).mkdir(parents=True, exist_ok=True)
    idx_dir = _index_dir(base_dir)
    idx_dir.mkdir(parents=True, exist_ok=True)
    # Create index files only if they don't already exist
    for fname in INDEX_FILES.values():
        idx_path = idx_dir / fname
        if not idx_path.exists():
            idx_path.write_text("[]", encoding="utf-8")


def scan_unindexed(base_dir: Path) -> list[str]:
    """Find files in typed subdirs not present in any index.

    Returns a list of relative paths (e.g. 'papers/author-slug.pdf') for
    unindexed files. Ignores dotfiles, directories, and files with extensions
    not in SOURCE_EXTENSIONS.
    """
    indexed_paths = _all_indexed_paths(base_dir)
    unindexed: list[str] = []

    for subdir in SOURCE_DIRS:
        d = base_dir / subdir
        if not d.is_dir():
            continue
        for item in sorted(d.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                continue
            if item.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            rel = f"{subdir}/{item.name}"
            if rel not in indexed_paths:
                unindexed.append(rel)

    return unindexed


def add_source(
    base_dir: Path,
    file_path: Path,
    entry: dict,
    source_type: str,
) -> dict:
    """Move/rename a file to the correct typed subdir and append an index entry.

    Args:
        base_dir: Path to the bibliography/ directory.
        file_path: Current location of the source file.
        entry: Index entry dict (must include 'id' and other schema fields).
        source_type: One of 'paper', 'report', 'book'.

    Returns:
        The completed entry dict (with path, indexed_at, indexed_by filled in).

    Raises:
        ValueError: If source_type is invalid or id already exists.
    """
    if source_type not in TYPE_TO_DIR:
        raise ValueError(
            f"Invalid source_type '{source_type}'. Must be one of: {list(TYPE_TO_DIR.keys())}"
        )

    entry_id = entry["id"]

    # Check for duplicate ID across ALL index files
    if entry_id in _all_indexed_ids(base_dir):
        raise ValueError(f"Duplicate ID '{entry_id}' already exists in the index.")

    target_dir_name = TYPE_TO_DIR[source_type]
    idx_filename = TYPE_TO_INDEX[source_type]

    # Determine destination filename: {id}{original_extension}
    ext = file_path.suffix.lower()
    dest = base_dir / target_dir_name / f"{entry_id}{ext}"

    # Move (rename) the file
    shutil.move(str(file_path), str(dest))

    # Build the final entry
    entry["path"] = f"{target_dir_name}/{entry_id}{ext}"
    entry["indexed_at"] = str(date.today())
    entry["indexed_by"] = "deepseek-research-auto"

    # Append to the correct index
    entries = _load_index(base_dir, idx_filename)
    entries.append(entry)
    _save_index(base_dir, idx_filename, entries)

    return entry


def query_sources(
    base_dir: Path,
    keywords: list[str],
    top_n: int = 10,
) -> list[dict]:
    """Score index entries by weighted token overlap and return top N.

    Scoring weights:
        - keywords field: 3x per matching token
        - title field: 2x per matching token
        - summary field: 1x per matching token

    Tokens are produced by splitting on non-alphanumeric chars, lowercased.
    Entries with zero score are excluded.
    """
    query_tokens = set(_tokenize(" ".join(keywords)))
    if not query_tokens:
        return []

    scored: list[tuple[float, dict]] = []

    for idx_file in INDEX_FILES.values():
        for entry in _load_index(base_dir, idx_file):
            score = 0.0

            # Keywords (3x)
            kw_tokens = set()
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

    # Sort descending by score, then by id for determinism
    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [entry for _, entry in scored[:top_n]]


def update_sessions(base_dir: Path, entry_id: str, session_slug: str) -> None:
    """Append a session slug to sessions_used for a given entry.

    Raises:
        KeyError: If the entry_id is not found in any index file.
    """
    for idx_file in INDEX_FILES.values():
        entries = _load_index(base_dir, idx_file)
        for entry in entries:
            if entry.get("id") == entry_id:
                sessions = entry.setdefault("sessions_used", [])
                if session_slug not in sessions:
                    sessions.append(session_slug)
                _save_index(base_dir, idx_file, entries)
                return

    raise KeyError(f"Entry ID '{entry_id}' not found in any index file.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_from_stdin(base_dir: Path) -> int:
    """Read a JSON entry from stdin and add it as a source.

    Expected JSON shape:
    {
      "source_type": "paper",
      "file_path": "/abs/path/to/downloaded/file.pdf",
      "entry": {
        "id": "author-year-slug",
        "title": "...",
        "authors": ["..."],
        "year": 2024,
        "doi": "...",
        "keywords": ["..."],
        "summary": "...",
        "quality_level": "II",
        "source_type": "journal"
      }
    }
    """
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON on stdin: {e}", file=sys.stderr)
        return 1

    source_type = payload.get("source_type")
    file_path_str = payload.get("file_path")
    entry = payload.get("entry")

    if not all([source_type, file_path_str, entry]):
        print("Missing required fields: source_type, file_path, entry", file=sys.stderr)
        return 1

    file_path = Path(file_path_str)
    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        return 1

    try:
        result = add_source(base_dir, file_path, entry, source_type)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError) as e:
        print(f"Error adding source: {e}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="index_sources",
        description="Manage the bibliography source index.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Bootstrap bibliography/ directory structure.")
    p_init.add_argument("--base-dir", required=True, type=Path, help="Path to bibliography/ directory.")

    # scan-unindexed
    p_scan = sub.add_parser("scan-unindexed", help="Find unindexed files in bibliography/.")
    p_scan.add_argument("--base-dir", required=True, type=Path, help="Path to bibliography/ directory.")

    # add (reads JSON from stdin)
    p_add = sub.add_parser("add", help="Add a source entry from stdin JSON.")
    p_add.add_argument("--base-dir", required=True, type=Path, help="Path to bibliography/ directory.")

    # query
    p_query = sub.add_parser("query", help="Keyword pre-filter search of the index.")
    p_query.add_argument("--base-dir", required=True, type=Path, help="Path to bibliography/ directory.")
    p_query.add_argument("--keywords", required=True, type=str, help="Comma-separated keywords.")
    p_query.add_argument("--top", type=int, default=10, help="Number of results to return (default: 10).")

    # update-sessions
    p_update = sub.add_parser("update-sessions", help="Append a session slug to an entry.")
    p_update.add_argument("--base-dir", required=True, type=Path, help="Path to bibliography/ directory.")
    p_update.add_argument("--id", required=True, type=str, help="Entry ID.")
    p_update.add_argument("--session", required=True, type=str, help="Session slug to append.")

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

    elif args.command == "add":
        return _add_from_stdin(args.base_dir)

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