#!/usr/bin/env python3
"""helpers.py — Reusable Python functions for deepseek-research pipeline.

Called via `code_execution` from SKILL.md stages. Each function is a standalone
unit that accepts all parameters explicitly — no global state, no config file reads.
The orchestrator interpolates variables before calling.

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
    result = result.replace("{date}", now.strftime("%Y-%m-%d"))

    if session_slug:
        result = result.replace("{slug}", session_slug)
        # Also support the compound form used in session headers
        result = result.replace("{date}-{slug}", session_slug)

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
            existing = {}

    # Merge new fields
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    for key, value in kwargs.items():
        if key == "config_snapshot" and isinstance(value, str):
            try:
                existing[key] = json.loads(value)
            except json.JSONDecodeError:
                existing[key] = value
        elif key in ("pending_actions",) and isinstance(value, str):
            try:
                existing[key] = json.loads(value)
            except json.JSONDecodeError:
                existing[key] = [value]
        elif key == "sub_agent_map" and isinstance(value, str):
            try:
                existing[key] = json.loads(value)
            except json.JSONDecodeError:
                existing[key] = value
        else:
            existing[key] = value

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return str(state_path)


def read_session_state(session_dir: str) -> dict:
    """Read .session-state.json for crash recovery.

    Returns empty dict if no state file exists (fresh session).
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

    Returns:
        (stage_name, checklist_item_id) or ("1", 1) for fresh session.
        Example: ("3.5", 10) means resume at Stage 3.5, checklist item 10.
    """
    state = read_session_state(session_dir)
    if not state:
        return ("1", 1)
    current = state.get("current_stage", "1")
    item = state.get("current_checklist_item", 1)
    return (str(current), int(item))


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
      - dsr-deep-read-t5: kwargs = {source_id, repo_url, rq_text, skill_dir, oss_clone_dir}
      - dsr-da: kwargs = {session_dir, skill_dir}
      - dsr-grey: kwargs = {rq_text, main_topic, topics (optional)}
      - dsr-tiebreak: kwargs = {rq_text, bibliography_path, disagreement_list}
      - dsr-deep-read: kwargs = {source_id, source_path_or_url, source_title, rq_text, skill_dir}
    """
    prompts = {
        "dsr-bibliography": _build_bibliography_prompt,
        "dsr-web": _build_web_prompt,
        "dsr-code": _build_code_prompt,
        "dsr-opensource": _build_opensource_prompt,
        "dsr-deep-read-t5": _build_deep_read_t5_prompt,
        "dsr-da": _build_da_prompt,
        "dsr-grey": _build_grey_prompt,
        "dsr-tiebreak": _build_tiebreak_prompt,
        "dsr-deep-read": _build_deep_read_prompt,
    }
    builder = prompts.get(template_name)
    if builder is None:
        raise ValueError(f"Unknown template: {template_name}. Valid: {list(prompts.keys())}")
    return builder(**kwargs)


def _build_per_topic_queries(topics_str: str, query_template: str) -> str:
    """Generate per-topic queries from a comma-separated topics string.

    Args:
        topics_str: Comma-separated short topic names, e.g. "TBT,CBH,FEP"
        query_template: Template with {topic} placeholder, e.g. '"limitations of {topic}"'

    Returns:
        Newline-separated bullet list of queries, one per topic.
        If topics_str is empty, returns empty string.
    """
    if not topics_str or not topics_str.strip():
        return ""
    topics = [t.strip() for t in topics_str.split(",") if t.strip()]
    if not topics:
        return ""
    return "\n".join(f'- {query_template.format(topic=t)}' for t in topics)


def _build_bibliography_prompt(
    rq_text: str,
    bibliography_path: str,
    main_topic: str,
    topics: str = "",
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

    if topics:
        per_topic = _build_per_topic_queries(topics, '"limitations of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"criticism of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"failure cases of {topic}"')
        negative_queries_block = f"""## Mandatory: Negative search (per-topic)
For each topic below, you MUST run ALL of these queries:
{per_topic}"""
    else:
        negative_queries_block = f"""## Mandatory: Negative search
For the main topic of this RQ, you MUST run at least these queries:
- "limitations of {main_topic}"
- "criticism of {main_topic}"
- "failure cases of {main_topic}\""""

    prompt = f"""Search project bibliography at {bibliography_path} for sources relevant to RQ: {rq_text}

{local_sources_block}

{negative_queries_block}
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


def _build_web_prompt(rq_text: str, main_topic: str, topics: str = "") -> str:
    if topics:
        per_topic = _build_per_topic_queries(topics, '"limitations of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"criticism of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"alternatives to {topic}"')
        negative_section = f"""## Mandatory: Negative search (per-topic)
You MUST run these queries IN ADDITION to the primary topic queries:
{per_topic}"""
    else:
        negative_section = f"""## Mandatory: Negative search
You MUST run these queries IN ADDITION to the primary topic queries:
- "limitations of {main_topic}"
- "criticism of {main_topic}"
- "alternatives to {main_topic}\""""

    return f"""Web search for RQ: {rq_text}

{negative_section}
Report all queries and their results in a 'negative_search' section.

## Output REQUIRED format
### Source Table
| Source ID | URL | Type (academic/industry/blog) | Relevance (1-5) | Why relevant |

### Search Audit
| Query | Results returned | Results used |

### Negative Search
| Query | Results found | Key findings |

## MANDATORY: Write complete results to file
Before responding, you MUST write your COMPLETE source table, search audit, and
negative search results to `/tmp/dsr-web-results.md` using the write_file tool.
This file will be read by the orchestrator after you finish. Your inline response
can be a summary — the file must contain the full results."""


def _build_code_prompt(rq_text: str) -> str:
    return f"""Search project codebase for implementations, patterns, docs relevant to: {rq_text}

## Output REQUIRED format
| Source ID | File:Line | Type (impl/doc/test/config) | Relevance (1-5) | Why relevant |"""


def _build_opensource_prompt(rq_text: str, main_topic: str = "", topics: str = "") -> str:
    topic = main_topic or rq_text
    if topics:
        per_topic_neg = _build_per_topic_queries(topics, '"{topic} abandoned"')
        per_topic_neg += "\n" + _build_per_topic_queries(topics, '"{topic} unmaintained"')
        per_topic_neg += "\n" + _build_per_topic_queries(topics, '"{topic} deprecated"')
        negative_section = f"""## Negative Search (MANDATORY — per-topic)

Execute ALL of these contrary-evidence searches:
{per_topic_neg}"""
        neg_results_rows = "\n".join(
            f'| {t} | "abandoned {t}" | (N) | (summary or "No abandoned projects found") |\n'
            f'| {t} | "unmaintained {t}" | (N) | (summary or "No unmaintained projects found") |'
            for t in [x.strip() for x in topics.split(",") if x.strip()]
        )
    else:
        negative_section = f"""## Negative Search (MANDATORY)

Execute ALL of these contrary-evidence searches:
- "{topic} abandoned"
- "{topic} unmaintained"
- "{topic} deprecated\""""
        neg_results_rows = f'| {topic} | "abandoned {topic}" | (N) | (summary or "No abandoned projects found") |\n| {topic} | "unmaintained {topic}" | (N) | (summary or "No unmaintained projects found") |'

    return f"""Search open-source repositories for implementations, benchmarks,
libraries, and tools relevant to: {rq_text}

Main topic for search queries: {topic}

## Search Strategy

Search across these targets in order:
1. GitHub code search: site:github.com
2. GitLab explore: site:gitlab.com
3. Package registries: crates.io, PyPI, npm
4. Papers with Code: site:paperswithcode.com
5. Fallback (if < 5 results from above): SourceForge (site:sourceforge.net), Codeberg (site:codeberg.org)

## Mandatory Queries

Execute ALL of these searches:
- "{topic} implementation github"
- "{topic} benchmark"
- "{topic} open source"
- "{topic} library" (append programming language if mentioned in RQ)

{negative_section}

Report what you found — "No results" is valid.

## Output REQUIRED format

| Source ID | Repository URL | Type (impl/benchmark/lib/tool) | Relevance (1-5) | Why relevant | Stars | Last commit |
|-----------|---------------|-------------------------------|-----------------|--------------|-------|-------------|

**Relevance scale:**
- 5 — Directly implements the algorithm/method described in RQ
- 4 — Related implementation or benchmark suite for the domain
- 3 — Library in same domain, potentially useful
- 2 — Tangentially related tool or utility
- 1 — Mentioned but not directly applicable

**Stars and Last commit:** Extract from GitHub/GitLab metadata when available. Write "N/A" for package registries.

## Negative Search Results

| Topic | Query | Results found | Key findings |
|-------|-------|--------------|--------------|
{neg_results_rows}

## Saturation

Report whether saturation was reached:
- **Criterion met:** (yes — last N sources added no new repositories / no — below saturation_window)
- **Sources capped:** (yes — reached max_sources_per_axis / no)

## MANDATORY: Write complete results to file
Before responding, you MUST write your COMPLETE source table, negative search results,
and saturation declaration to `/tmp/dsr-opensource-results.md` using the write_file tool.
This file will be read by the orchestrator after you finish. Your inline response
can be a summary — the file must contain the full results."""


def _build_deep_read_t5_prompt(
    source_id: str,
    repo_url: str,
    rq_text: str,
    skill_dir: str,
    oss_clone_dir: str = "oss",
) -> str:
    return f"""Deep-read the open-source repository at {repo_url} for claims relevant to: {rq_text}

Source ID: {source_id}

## Procedure

1. **Clone the repository:**
   - Run: `git clone --depth 1 --single-branch {repo_url} {oss_clone_dir}/{source_id}/`
   - If the directory already exists, run: `cd {oss_clone_dir}/{source_id} && git pull`

2. **Record commit hash:**
   - Run: `cd {oss_clone_dir}/{source_id} && git rev-parse HEAD`
   - Record the hash as `**Commit analyzed:** <hash>` in your output.

3. **Structure survey:**
   - Read README.md, package manifest (Cargo.toml/pyproject.toml/package.json), and top-level directory listing.

4. **Targeted grep:**
   - Extract keywords from the RQ: {rq_text}
   - Use grep_files to search for these patterns across {oss_clone_dir}/{source_id}/
   - Focus on function names, algorithm names, class names, constant values, benchmark results.

5. **Key file reading:**
   - read_file the files containing grep matches (limit to files directly relevant to RQ).
   - Focus on: core algorithm implementations, benchmark harnesses, test files, configuration constants, docstrings with design decisions.

6. **Claim extraction:**
   - Extract claims with **E-grade (Empirical — implementation)**.
   - Each claim must include: verbatim code excerpt, file:line reference, what the code actually does.
   - E-grade STRONG requires: (a) repository RoB Low, AND (b) cross-source corroboration (V-grade from a paper or second independent E-grade repository). Without corroboration, cap at MODERATE.

7. **Consistency check:**
   - Does the implementation match the documented algorithm?
   - Are there discrepancies between docstring claims and actual code?
   - Check for internal contradictions.

## Output

Write to `{{session_dir}}/deep-reads/{source_id}.md` using the template at {skill_dir}/templates/source-deep-read.md.

Use T5, codebase_grep, and include the commit hash in the metadata header."""


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


def _build_grey_prompt(rq_text: str, main_topic: str, topics: str = "") -> str:
    if topics:
        per_topic = _build_per_topic_queries(topics, '"limitations of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"alternatives to {topic}"')
        negative_section = f"""## Mandatory: Negative search (per-topic)
You MUST run these queries IN ADDITION to the primary topic queries:
{per_topic}"""
    else:
        negative_section = f"""## Mandatory: Negative search
You MUST run these queries IN ADDITION to the primary topic queries:
- "limitations of {main_topic}"
- "alternatives to {main_topic}\""""

    return f"""Search grey literature for RQ: {rq_text}

Grey literature = theses, preprints, conference proceedings, technical reports,
and institutional repository content NOT indexed in mainstream academic databases.

## Sources to search
- arxiv.org (preprints — physics, math, CS, engineering)
- techrxiv.org (engineering preprints)
- Google Scholar (conference papers, theses)
- ProQuest Dissertations & Theses (if accessible)
- Institutional repositories (MIT DSpace, Stanford Digital Repository, etc.)

{negative_section}
Report all queries and their results in a 'negative_search' section.

## Output REQUIRED format
### Source Table
| Source ID | URL | Type (thesis/preprint/conference/tech-report) | Relevance (1-5) | Why relevant |

### Search Audit
| Query | Source | Results returned | Results used |

### Negative Search
| Query | Results found | Key findings |

Rules:
- Grey literature has higher false-positive rate. Apply stricter relevance threshold (≥4 to include).
- Prefer sources with DOI or persistent identifier over ephemeral URLs.
- Flag retraction/withdrawal notices if found."""


def _build_deep_read_prompt(
    source_id: str,
    source_path_or_url: str,
    source_title: str,
    rq_text: str,
    skill_dir: str,
) -> str:
    """Build a deep reading sub-agent prompt for a single source.

    The sub-agent processes the full document via RLM chunking (for T3/T4)
    or direct reading (for T1/T2), extracts claims with verbatim quotes,
    checks internal consistency, and writes a structured output file.

    Args:
        source_id: Source identifier from Stage 2 inventory (e.g., "S3", "W7").
        source_path_or_url: File path (bibliography) or URL (web source).
        source_title: Human-readable title of the source.
        rq_text: Full research question text for relevance filtering.
        skill_dir: Path to the skill directory (for template and reference paths).
    """
    return f"""Deep-read source {source_id} for relevance to RQ: {rq_text}

Source title: {source_title}
Source location: {source_path_or_url}

## Instructions

1. Read the methodology reference:
   `read_file("{skill_dir}/references/deep-reading.md")`
   Pay special attention to: Document Size Tiers, Textual Evidence Taxonomy,
   Internal Consistency Checks, and RLM Chunking Contract.

2. Determine the document tier:
   - Fetch or read the first 2KB of the document.
   - Estimate total size from headers or file metadata.
   - Classify as T1 (<5KB), T2 (5-50KB), T3 (50-200KB), or T4 (>200KB).

3. Process according to tier:
   - **T1/T2:** Read the full document directly with `read_file`.
   - **T3:** `rlm_open` → `rlm_configure(output_feedback="metadata")` → chunk
     with 8K chars + 1K overlap → `sub_query_batch(dependency_mode="independent")`
     for claim extraction → `rlm_close`.
   - **T4:** Selective reading: chunk ToC/intro/conclusion first to identify
     relevant sections, then deep-read only those sections.

4. Extract claims:
   For each claim relevant to the RQ, extract:
   - Verbatim quote (exact text from source)
   - Evidence grade: V (Verbatim), P (Paraphrase with context),
     I (Inference from data/figures), or M (Mathematical — theorem/proof/equation)
   - Section reference (§X.Y or chapter name)
   - Page/line reference if available

5. Check internal consistency:
   - Claim-claim: any two claims contradict each other?
   - Claim-data: reported numbers match tables/figures?
   - Claim-method: conclusion follows from method?
   - Abstract-body: abstract accurately represents body?

6. Flag mathematical claims:
   Any M-grade claim MUST be flagged with:
   "⚠ MATHEMATICAL — requires human verification. The LLM cannot verify mathematical proofs."

7. Write output:
   Use the template at `{skill_dir}/templates/source-deep-read.md`.
   Fill every section. Write to `{{session_dir}}/deep-reads/{source_id}.md`.

## Output contract

- File path: `{{session_dir}}/deep-reads/{source_id}.md`
- Format: Strictly follow the template structure
- Every claim in the Extracted Claims table MUST include a verbatim quote
- Internal consistency section: report 0 issues if none found (don't omit)
- Mathematical claims: flag if present; state "None" if absent
- Overall assessment: COMPREHENSIVE / PARTIAL / MINIMAL with one-sentence rationale

## Failure handling

- If document is inaccessible (HTTP error, file not found, paywall):
  Write INACCESSIBLE status with reason. Do NOT fabricate claims.
- If RLM fails: Write FAILED status with error message.
- If T4 with >50% sections skipped: Write PARTIAL with coverage percentage.
"""
