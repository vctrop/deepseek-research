#!/usr/bin/env python3
"""helpers.py — Reusable Python functions for deepseek-research pipeline.

Called via `code_execution` from SKILL.md stages. Each function is a standalone
unit that accepts all parameters explicitly — no global state, no config file reads.
The orchestrator interpolates variables before calling.

Usage (in SKILL.md):
    code_execution(code="""
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
from helpers import compute_sha256
print(compute_sha256('{session_dir}/01-rq-brief.md'))
    """)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def compute_sha256(filepath: str) -> str:
    """Compute SHA256 hex digest of a file. Returns empty string on error."""
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, FileNotFoundError):
        return ""


def query_index(
    skill_dir: str,
    bibliography_path: str,
    keywords: str,  # comma-separated
    top_n: int = 20,
) -> list[dict]:
    """Run index_sources.py query and return parsed results.

    Uses subprocess with list arguments — no shell interpolation.
    Returns empty list on error.
    """
    try:
        result = subprocess.run(
            [
                "python3",
                f"{skill_dir}/scripts/index_sources.py",
                "query",
                "--base-dir", bibliography_path,
                "--keywords", keywords,
                "--top", str(top_n),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []


def add_source_to_index(
    skill_dir: str,
    bibliography_path: str,
    source_type: str,  # "paper" | "report" | "book"
    file_path: str,
    entry: dict,
) -> dict | None:
    """Add a source to the bibliography index via index_sources.py.

    Returns the completed entry dict on success, None on failure.
    Uses subprocess with stdin pipe — no shell interpolation.
    """
    add_payload = {
        "source_type": source_type,
        "file_path": file_path,
        "entry": entry,
    }
    try:
        result = subprocess.run(
            [
                "python3",
                f"{skill_dir}/scripts/index_sources.py",
                "add",
                "--base-dir", bibliography_path,
            ],
            input=json.dumps(add_payload),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def update_session_index(
    session_index_path: str,
    entry: dict,
) -> bool:
    """Append a session entry to the session index JSON array.

    Creates the file with an empty array if it doesn't exist.
    Returns True on success, False on failure.
    """
    try:
        path = Path(session_index_path)
        if path.exists():
            sessions = json.loads(path.read_text(encoding="utf-8"))
        else:
            sessions = []
        sessions.append(entry)
        path.write_text(json.dumps(sessions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except (json.JSONDecodeError, OSError):
        return False


def compute_cohens_kappa(
    rater1_included: list[str],
    rater2_included: list[str],
    all_source_ids: list[str],
) -> dict:
    """Compute Cohen's kappa for inter-rater reliability between two screeners.

    Args:
        rater1_included: List of source_ids that rater 1 marked as "include".
        rater2_included: List of source_ids that rater 2 marked as "include".
        all_source_ids: List of all source_ids screened by both raters.

    Returns:
        dict with keys: kappa, agreement_pct, n_agree_include, n_agree_exclude,
        n_disagree, n_total, interpretation.

    Uses scipy.stats.cohen_kappa if available; falls back to manual computation.

    Interpretation:
        κ < 0.00: Poor agreement
        0.00 ≤ κ ≤ 0.20: Slight
        0.21 ≤ κ ≤ 0.40: Fair
        0.41 ≤ κ ≤ 0.60: Moderate
        0.61 ≤ κ ≤ 0.80: Substantial
        0.81 ≤ κ ≤ 1.00: Almost perfect
    """
    set1 = set(rater1_included)
    set2 = set(rater2_included)
    all_ids = set(all_source_ids)

    n_total = len(all_ids)
    if n_total == 0:
        return {
            "kappa": 1.0, "agreement_pct": 100.0,
            "n_agree_include": 0, "n_agree_exclude": 0,
            "n_disagree": 0, "n_total": 0,
            "interpretation": "No sources to rate"
        }

    n_agree_include = len(set1 & set2)
    n_agree_exclude = len(all_ids - set1 - set2)
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


def build_subagent_prompt(
    template_name: str,  # "dsr-bibliography" | "dsr-web" | "dsr-code" | "dsr-da"
    **kwargs: str,
) -> str:
    """Build a sub-agent prompt string from a template with safe interpolation.

    Uses kwargs for all variable substitutions — no manual escaping needed.
    The returned string is safe to pass directly to agent_open(prompt=...).

    Supported templates:
      - dsr-bibliography: kwargs = {rq_text, bibliography_path, main_topic,
           local_sources_block (optional), local_sources_json (optional)}
      - dsr-web: kwargs = {rq_text, main_topic}
      - dsr-code: kwargs = {rq_text}
      - dsr-da: kwargs = {session_dir, skill_dir}
    """
    prompts = {
        "dsr-bibliography": _build_bibliography_prompt,
        "dsr-web": _build_web_prompt,
        "dsr-code": _build_code_prompt,
        "dsr-da": _build_da_prompt,
        "dsr-tiebreak": _build_tiebreak_prompt,
    }
    builder = prompts.get(template_name)
    if builder is None:
        raise ValueError(f"Unknown template: {template_name}. Valid: {list(prompts.keys())}")
    return builder(**kwargs)


def _build_bibliography_prompt(
    rq_text: str,
    bibliography_path: str,
    main_topic: str,
    local_sources_block: str = "",
    local_sources_json: str = "",
) -> str:
    persistence_manifest_example = {
        "persistence_manifest": {
            "new_sources": [
                {
                    "save_as": "papers/author-year-slug.pdf",
                    "source_id": "author-year-slug",
                    "type": "paper",
                    "title": "Full title",
                    "authors": ["Author, A."],
                    "year": 2024,
                    "doi": "10.xxxx/xxxxx",
                    "keywords": ["kw1", "kw2"],
                    "summary": "2-3 sentence summary of key contributions.",
                    "quality_level": "II",
                    "source_type": "journal",
                }
            ],
            "reused_local": [{"source_id": "existing-id"}],
            "negative_search": {
                "queries_attempted": ["limitations of X", "X fails when"],
                "results_found": 2,
                "results_summary": "Instability with >5 fidelity levels (Le Gratiet 2014)",
            },
        }
    }
    manifest_json = json.dumps(persistence_manifest_example, indent=2)

    prompt = f"""Search project bibliography at {bibliography_path} for sources relevant to RQ: {rq_text}

{local_sources_block}

## Mandatory: Negative search
For the main topic of this RQ, you MUST run at least these queries:
- "limitations of {main_topic}"
- "criticism of {main_topic}"
- "failure cases of {main_topic}"
Report findings in the persistence_manifest under 'negative_search'.

## Output contract
1. Markdown table: | Source ID | Title/Path | Type | Relevance (1-5) | Why relevant |
2. persistence_manifest JSON block — LAST element of response, in dedicated ```json fence.

## persistence_manifest format
```json
{manifest_json}
```

Rules:
- new_sources: every source obtained online. save_as = {{type}}s/{{first-author}}-{{year}}-{{short-title-kebab}}.{{ext}}
- reused_local: every source read from local corpus. Only source_id.
- negative_search: REQUIRED — report all negative queries and their findings.
- If empty: emit [] (never omit the block).
- The block MUST be the last element of the response."""
    return prompt


def _build_web_prompt(rq_text: str, main_topic: str) -> str:
    return f"""Web search for RQ: {rq_text}

## Mandatory: Negative search
You MUST run these queries IN ADDITION to the primary topic queries:
- "limitations of {main_topic}"
- "criticism of {main_topic}"
- "alternatives to {main_topic}"
Report all queries and their results in a 'negative_search' section.

## Output REQUIRED format
### Source Table
| Source ID | URL | Type (academic/industry/blog) | Relevance (1-5) | Why relevant |

### Search Audit
| Query | Results returned | Results used |

### Negative Search
| Query | Results found | Key findings |"""


def _build_code_prompt(rq_text: str) -> str:
    return f"""Search project codebase for implementations, patterns, docs relevant to: {rq_text}

## Output REQUIRED format
| Source ID | File:Line | Type (impl/doc/test/config) | Relevance (1-5) | Why relevant |"""


def _build_da_prompt(session_dir: str, skill_dir: str) -> str:
    return f"""Read {session_dir}/04-synthesis.md.
Also read {skill_dir}/references/iron-rule-c.md for the full bare claims list.
Review against the Devil's Advocate checklist below.
Write findings to {session_dir}/04a-devils-advocate.md using the template at {skill_dir}/templates/devils-advocate.md.

## Checklist

### Cherry-picking
- Contradictory sources excluded or downweighted?
- If DIVERGENT consensus, minority view given fair space?
- Negative evidence found but not reported?
- Negative search results from Stage 2 acknowledged?

### Overconfidence
- Bare claims (validated, proved, confirmed, demonstrated, ensures, guarantees, always, never, optimal, definitive, conclusive, certainly, undoubtedly, obviously, clearly) without qualifiers?
- Evidence strength propagated into claim language?
- Source credibility tier conflated with evidence strength?
- Would hostile reviewer find confidence disproportionate to evidence?

### Gap honesty
- Gaps with severity + concrete next steps?
- Absence of evidence distinguished from evidence of absence?
- 'Open questions' genuinely open, or rhetorical?

### Bias
- Synthesis favors project-internal sources over external?
- Reference frameworks evaluated by same standard as project?
- Confirmation bias toward pre-existing architectural decisions?
- All agreeing sources share same author group/institution/funding?

## Verdict
PASS / MINOR (cosmetic fixes) / REVISE (substantive — list required revisions with line references).
Write verdict as a single line: **Verdict: {{PASS/MINOR/REVISE}}**"""


def _build_tiebreak_prompt(
    rq_text: str,
    bibliography_path: str,
    disagreement_list: str,  # JSON array of {source_id, rater1_decision, rater2_decision, title}
) -> str:
    return f"""You are a tiebreak reviewer resolving disagreements between two independent screeners.

Research Question: {rq_text}
Bibliography path: {bibliography_path}

The following sources received conflicting include/exclude decisions from the two screeners.
For each source, read the title and available metadata, then make a final decision: INCLUDE or EXCLUDE.

Disagreements:
{disagreement_list}

## Output REQUIRED format
| Source ID | Decision | Rationale (one sentence) |
|-----------|----------|--------------------------|

Rules:
- Default to INCLUDE if uncertain (inclusive screening reduces false negatives).
- If rationale from one screener is clearly stronger, adopt that decision.
- Do NOT introduce new sources — only resolve the listed disagreements."""
