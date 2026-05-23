#!/usr/bin/env python3
"""helpers.py — Reusable Python functions for deepseek-research pipeline.

Called via `code_execution` from SKILL.md stages. Each function is a standalone
unit that accepts all parameters explicitly — no global state, no config file reads.
The orchestrator interpolates variables before calling.

Functions:
    resolve_placeholders     — auto-fill computable template placeholders
    compute_sha256           — SHA256 hex digest of a file
    write_session_state      — write/update .session-state.json for crash recovery
    read_session_state       — read .session-state.json
    get_resume_stage         — determine stage to resume from
    query_index              — search local bibliography index
    add_source_to_index      — add entry to bibliography index
    update_session_index     — append to session index JSON
    compute_cohens_kappa     — inter-rater reliability (Cohen's κ)
    sort_deep_read_queue     — sort sources by deep read priority
    build_subagent_prompt    — dispatch one of 10 prompt builders

Usage (in SKILL.md):
    code_execution(code='''
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
from helpers import compute_sha256
print(compute_sha256('{session_dir}/01-rq-brief.md'))
    ''')
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from prompts import (
    _build_adversarial_prompt,
    _build_bibliography_prompt,
    _build_code_prompt,
    _build_da_prompt,
    _build_deep_read_prompt,
    _build_deep_read_t5_prompt,
    _build_grey_prompt,
    _build_opensource_prompt,
    _build_tiebreak_prompt,
    _build_web_prompt,
)


def resolve_placeholders(template_text: str, skill_dir: str = "", session_slug: str = "") -> str:
    """Auto-resolve computable placeholders in a template string.

    Resolves: {iso8601_utc}, {date}, {skill_git_hash}, {slug}
    Does NOT resolve: {RQ_TEXT}, {rq_sha256}, {session_dir} (require stage output).

    Args:
        template_text: Template content with placeholders in braces.
        skill_dir: Path to skill directory for git hash detection.
        session_slug: Session slug (e.g., "2026-05-22-teorias-computacionais-cerebro").

    Returns:
        Template text with computable placeholders replaced.
    """
    from datetime import datetime, timezone

    result = template_text
    now = datetime.now(timezone.utc)
    result = result.replace("{iso8601_utc}", now.isoformat())

    if session_slug:
        # Compound form MUST be replaced before individual {date} and {slug},
        # otherwise they are consumed and {date}-{slug} is never matched.
        result = result.replace("{date}-{slug}", session_slug)
        result = result.replace("{slug}", session_slug)

    result = result.replace("{date}", now.strftime("%Y-%m-%d"))

    # Git hash from skill directory (fallback to "unknown")
    git_hash = "unknown"
    if skill_dir:
        try:
            import subprocess
            r = subprocess.run(
                ["git", "-C", skill_dir, "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                git_hash = r.stdout.strip()
        except Exception:
            pass
    result = result.replace("{skill_git_hash}", git_hash)

    return result


def compute_sha256(filepath: str) -> str:
    """Compute SHA256 hex digest of a file. Returns empty string on error."""
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, FileNotFoundError):
        return ""


def write_session_state(session_dir: str, **kwargs: str) -> str:
    """Write or update .session-state.json for crash recovery.

    Records current stage, config snapshot, pending actions, and sub-agent map.
    Called after every checklist_update in the orchestrator.

    Args:
        session_dir: Session output directory (e.g., "research-reports/2026-05-22-slug/").
        **kwargs: Fields to update: current_stage, current_checklist_item,
                  last_completed_stage, pending_actions, sub_agent_map,
                  config_snapshot (as JSON string).

    Returns:
        Path to the written state file.
    """
    from datetime import datetime, timezone

    state_path = Path(session_dir) / ".session-state.json"

    # Load existing state if present
    existing = {}
    if state_path.exists():
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Merge updates
    existing.update(kwargs)
    existing.setdefault("session_started", existing.get("session_started",
                         datetime.now(timezone.utc).isoformat()))
    existing["last_updated"] = datetime.now(timezone.utc).isoformat()

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(state_path)


def read_session_state(session_dir: str) -> dict:
    """Read .session-state.json for crash recovery.

    Args:
        session_dir: Session output directory.

    Returns:
        State dict, or empty dict if file not found or corrupt.
    """
    state_path = Path(session_dir) / ".session-state.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_resume_stage(session_dir: str) -> tuple[str, int]:
    """Determine which stage and checklist item to resume from.

    Returns (stage_name, checklist_item_id). If no state file, returns ("1", 1).
    """
    state = read_session_state(session_dir)
    stage = state.get("current_stage", "1")
    item = state.get("current_checklist_item", 1)
    return (stage, item)


def query_index(
    skill_dir: str,
    bibliography_path: str,
    keyword: str,
    max_results: int = 20,
) -> list[dict]:
    """Query the local bibliography index for a keyword.

    Returns list of matching source entries.
    """
    index_path = Path(bibliography_path) / "index.json"
    if not index_path.exists():
        return []
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    results = []
    keyword_lower = keyword.lower()
    for entry in index:
        title = (entry.get("title") or "").lower()
        keywords = [k.lower() for k in entry.get("keywords", [])]
        summary = (entry.get("summary") or "").lower()
        if keyword_lower in title or keyword_lower in " ".join(keywords) or keyword_lower in summary:
            results.append(entry)
            if len(results) >= max_results:
                break
    return results


def add_source_to_index(
    skill_dir: str,
    bibliography_path: str,
    entry: dict,
) -> str:
    """Add a new source to the local bibliography index.

    Returns status message.
    """
    index_path = Path(bibliography_path) / "index.json"
    existing = []
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Dedup by source_id
    entry_id = entry.get("source_id", "")
    for e in existing:
        if e.get("source_id") == entry_id:
            return f"Duplicate: {entry_id} already in index"

    existing.append(entry)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"Added: {entry_id}"


def update_session_index(
    session_index_path: str,
    entry: dict,
) -> str:
    """Append a session entry to the session index JSON array.

    Returns status message.
    """
    idx_path = Path(session_index_path)
    existing = []
    if idx_path.exists():
        try:
            existing = json.loads(idx_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    existing.append(entry)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"Session recorded: {entry.get('slug', 'unknown')}"


def compute_cohens_kappa(
    rater1_included: list[str],
    rater2_included: list[str],
    all_ids: list[str],
) -> dict:
    """Compute Cohen's kappa for dual-screening inter-rater reliability.

    Args:
        rater1_included: Source IDs that screener 1 marked as INCLUDE.
        rater2_included: Source IDs that screener 2 marked as INCLUDE.
        all_ids: Complete list of all source IDs screened (union).

    Returns:
        dict with keys: kappa, agreement_pct, n_agree_include, n_agree_exclude,
        n_disagree, n_total, interpretation.
    """
    set1 = set(rater1_included)
    set2 = set(rater2_included)
    n_total = len(all_ids)

    if n_total == 0:
        return {
            "kappa": 1.0, "agreement_pct": 100.0,
            "n_agree_include": 0, "n_agree_exclude": 0,
            "n_disagree": 0, "n_total": 0,
            "interpretation": "No sources to rate"
        }

    n_agree_include = len(set1 & set2)
    n_agree_exclude = len(set(all_ids) - set1 - set2)
    n_disagree = n_total - n_agree_include - n_agree_exclude
    agreement_pct = (n_agree_include + n_agree_exclude) / n_total * 100

    # Build contingency table
    a = n_agree_include                          # both include
    b = len(set1 - set2)                          # rater1 include, rater2 exclude
    c = len(set2 - set1)                          # rater1 exclude, rater2 include
    d = n_agree_exclude                           # both exclude

    # Expected agreement by chance
    n = a + b + c + d
    if n == 0:
        return {
            "kappa": 1.0, "agreement_pct": 100.0,
            "n_agree_include": a, "n_agree_exclude": d,
            "n_disagree": 0, "n_total": n_total,
            "interpretation": "No sources to rate"
        }

    p_o = (a + d) / n                            # observed agreement
    p_yes = ((a + b) / n) * ((a + c) / n)        # chance agreement on "include"
    p_no = ((c + d) / n) * ((b + d) / n)         # chance agreement on "exclude"
    p_e = p_yes + p_no                            # expected agreement by chance

    if p_e == 1.0:
        kappa = 1.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    # Clamp to [-1, 1]
    kappa = max(-1.0, min(1.0, kappa))

    # Interpretation
    if kappa < 0.0:
        interp = "Poor"
    elif kappa <= 0.20:
        interp = "Slight"
    elif kappa <= 0.40:
        interp = "Fair"
    elif kappa <= 0.60:
        interp = "Moderate"
    elif kappa <= 0.80:
        interp = "Substantial"
    else:
        interp = "Almost perfect"

    return {
        "kappa": round(kappa, 4),
        "agreement_pct": round(agreement_pct, 1),
        "n_agree_include": a,
        "n_agree_exclude": d,
        "n_disagree": n_disagree,
        "n_total": n_total,
        "interpretation": interp,
    }


def sort_deep_read_queue(sources_json: str) -> str:
    """Sort deep read queue by priority. Returns JSON string with sorted sources.

    Priority tiers:
      1 = answers_SQ_directly    — directly answers a sub-question
      2 = cross_theory_comparison — compares multiple theories/methods
      3 = primary_empirical       — primary empirical evidence
      4 = review_secondary        — review or secondary source
      5 = code_reference          — open-source implementation

    Within each tier: higher relevance score first.
    Sources without a priority field default to tier 3.

    Args:
        sources_json: JSON array of source objects, each with at minimum:
            {source_id, priority (optional), relevance (optional)}

    Returns:
        JSON string with sources sorted by (priority ASC, relevance DESC).
    """
    import json

    sources = json.loads(sources_json)
    if not isinstance(sources, list):
        raise ValueError("sources_json must be a JSON array")

    priority_order = {
        "answers_SQ_directly": 1,
        "cross_theory_comparison": 2,
        "primary_empirical": 3,
        "review_secondary": 4,
        "code_reference": 5,
    }

    def sort_key(s):
        p = priority_order.get(s.get("priority", ""), 3)
        r = -int(s.get("relevance", 3))  # negative for descending
        return (p, r)

    sources.sort(key=sort_key)
    return json.dumps(sources, indent=2, ensure_ascii=False)


def build_subagent_prompt(
    template_name: str,  # "dsr-bibliography" | "dsr-web" | "dsr-code" | "dsr-da"
    **kwargs: str,
) -> str:
    """Build a sub-agent prompt string from a template with safe interpolation.

    Uses kwargs for all variable substitutions — no manual escaping needed.
    The returned string is safe to pass directly to agent_open(prompt=...).

    Supported templates:
      - dsr-bibliography: kwargs = {rq_text, bibliography_path, main_topic, topics (optional),
           local_sources_block (optional), local_sources_json (optional)}
        topics: comma-separated short topic names for per-topic negative queries.
          Example: "thousand brain theory,critical brain hypothesis,free energy principle"
          When omitted, negative queries fall back to main_topic (backward compatible).
      - dsr-web: kwargs = {rq_text, main_topic, topics (optional)}
          topics: same as above. Generates per-topic queries like
          "limitations of thousand brain theory" instead of one giant blob.
      - dsr-code: kwargs = {rq_text}
      - dsr-opensource: kwargs = {rq_text, main_topic (optional), topics (optional)}
      - dsr-deep-read-t5: kwargs = {source_id, repo_url, rq_text, skill_dir, session_dir, oss_clone_dir (optional)}
      - dsr-da: kwargs = {session_dir, skill_dir}
      - dsr-adversarial: kwargs = {rq_text, included_sources_json, main_topic, topics (optional)}
      - dsr-grey: kwargs = {rq_text, main_topic, topics (optional)}
      - dsr-tiebreak: kwargs = {rq_text, bibliography_path, disagreement_list}
      - dsr-deep-read: kwargs = {source_id, source_path_or_url, source_title, rq_text, skill_dir, session_dir}
    """
    prompts = {
        "dsr-bibliography": _build_bibliography_prompt,
        "dsr-web": _build_web_prompt,
        "dsr-code": _build_code_prompt,
        "dsr-opensource": _build_opensource_prompt,
        "dsr-deep-read-t5": _build_deep_read_t5_prompt,
        "dsr-da": _build_da_prompt,
        "dsr-adversarial": _build_adversarial_prompt,
        "dsr-grey": _build_grey_prompt,
        "dsr-tiebreak": _build_tiebreak_prompt,
        "dsr-deep-read": _build_deep_read_prompt,
    }
    builder = prompts.get(template_name)
    if builder is None:
        raise ValueError(f"Unknown template: {template_name}. Valid: {list(prompts.keys())}")
    return builder(**kwargs)
