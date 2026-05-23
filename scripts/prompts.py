#!/usr/bin/env python3
"""prompts.py — Sub-agent prompt builders for deepseek-research.

Extracted from helpers.py (Onda 4 audit, 2026-05-23).
Each function builds a prompt string for a specific sub-agent type.
All functions are called via `build_subagent_prompt()` in helpers.py —
do not call them directly from pipeline stages.

Functions:
  _build_per_topic_queries  — shared helper for per-topic negative queries
  _build_bibliography_prompt — dsr-bibliography
  _build_web_prompt          — dsr-web
  _build_code_prompt         — dsr-code
  _build_opensource_prompt   — dsr-opensource
  _build_deep_read_t5_prompt — dsr-deep-read-t5
  _build_adversarial_prompt  — dsr-adversarial
  _build_da_prompt           — dsr-da (Devil's Advocate)
  _build_tiebreak_prompt     — dsr-tiebreak
  _build_grey_prompt         — dsr-grey
  _build_deep_read_prompt    — dsr-deep-read
"""

from __future__ import annotations

import json


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

## MANDATORY: Write complete results to file
Before responding, you MUST write your COMPLETE markdown source table and
persistence_manifest JSON block to `/tmp/dsr-bibliography-results.md` using the
write_file tool. This file will be read by the orchestrator after you finish.
Your inline response can be a summary — the file must contain the full results."""
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
| Source ID | File:Line | Type (impl/doc/test/config) | Relevance (1-5) | Why relevant |

## MANDATORY: Write complete results to file
Before responding, you MUST write your COMPLETE source table to `/tmp/dsr-code-results.md`
using the write_file tool. This file will be read by the orchestrator after you finish.
Your inline response can be a summary — the file must contain the full results."""


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

## Negative Search Results table

| Topic | Query | Results found | Summary |
|-------|-------|--------------|---------|
{neg_results_rows}

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
    session_dir: str,
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

Write to `{session_dir}/deep-reads/{source_id}.md` using the template at {skill_dir}/templates/source-deep-read.md.

Use T5, codebase_grep, and include the commit hash in the metadata header."""


def _build_adversarial_prompt(
    rq_text: str,
    included_sources_json: str,
    main_topic: str,
    topics: str = "",
) -> str:
    """Build adversarial search prompt to find contrary evidence.

    This sub-agent is dispatched AFTER source inventory closes and BEFORE
    verification. Its job is to find evidence the main search may have missed
    due to confirmation bias — the structural equivalent of red-teaming.
    """
    import json as _json

    sources = _json.loads(included_sources_json)
    source_titles = [
        s.get("title", s.get("source_id", "?")) for s in sources[:10]
    ]

    titles_block = "\n".join(f"  - {t}" for t in source_titles)

    if topics:
        per_topic_neg = _build_per_topic_queries(topics, '"evidence against {topic}"')
        per_topic_neg += "\n" + _build_per_topic_queries(topics, '"{topic} replication failure"')
        per_topic_neg += "\n" + _build_per_topic_queries(topics, '"{topic} contradictory"')
        per_topic_neg += "\n" + _build_per_topic_queries(topics, '"{topic} critique"')
        adversary_queries_block = f"""## Adversarial Search Queries (per-topic)

Execute ALL of these searches for EACH topic:
{per_topic_neg}"""
    else:
        adversary_queries_block = f"""## Adversarial Search Queries

Execute ALL of these contrary-evidence searches:
- "evidence against {main_topic}"
- "{main_topic} replication failure"
- "{main_topic} contradictory evidence"
- "{main_topic} critique\""""

    return f"""## ADVERSARIAL SEARCH — Red-Team the Source Inventory

Your mission: find evidence that contradicts, challenges, or complicates the
current understanding of this research question. You are searching for what
the main discovery sub-agents may have MISSED due to confirmation bias.

Research question: {rq_text}

## Sources already found (do NOT re-discover these)

These {len(sources)} sources are already in the inventory:
{titles_block}

Your job is to find sources that:
1. Contradict the findings these sources would be expected to support
2. Present alternative explanations or competing theories
3. Show replication failures for key methods/claims in this domain
4. Critique the methodology used by the primary sources
5. Contain null results or negative findings in this area

## {adversary_queries_block.split(chr(10))[0]}

{chr(10).join(adversary_queries_block.split(chr(10))[1:])}

Also run these cross-cutting contrary searches:
- "meta-analysis {main_topic} null result"
- "systematic review {main_topic} inconclusive"
- "debate {main_topic}"
- "{main_topic} methodological limitations"

## Output REQUIRED format

### Adversarial Source Table
| Source ID | Title/URL | Type (paper/blog/preprint/thesis) | Finding contradicts | Strength (1-5) | Why relevant |

**Strength scale:**
- 5: Directly refutes a key claim from the included sources
- 4: Presents strong contradictory evidence or alternative explanation
- 3: Documents methodological problems or replication failures
- 2: Tangential critique or minor disagreement
- 1: Mentioned but weak/imprecise contradictory evidence

### Search Audit
| Query | Results returned | Results used |

### Adversarial Assessment
Summarize the strongest contrary evidence found. If no contrary evidence
was found for a particular topic, state "No contrary evidence found for {main_topic}."

## MANDATORY: Write complete results to file
Before responding, you MUST write your COMPLETE adversarial source table,
search audit, and adversarial assessment to `/tmp/dsr-adversarial-results.md`
using the write_file tool. This file will be read by the orchestrator after
you finish. Your inline response can be a summary — the file must contain
the full results."""


def _build_da_prompt(session_dir: str, skill_dir: str) -> str:
    return f"""Read {session_dir}/04-synthesis.md.
Also read {skill_dir}/references/iron-rule-c.md for the full bare claims list.
Review against the Devil's Advocate checklist below.
Write findings to {session_dir}/04a-devils-advocate.md using the template at {skill_dir}/templates/devils-advocate.md.

## Checklist

0. **Validate Contradiction Stress Test (mandatory — do this FIRST):**
   The synthesis you read contains a "Contradiction Stress Test" section appended by
   Phase A of this stage. For EACH claim in that table:
   - Verify the "Contrary Evidence" column is accurate against the cited source.
     If the source is from Stage 2.6 (ADV-S*), cross-check against
     {session_dir}/01c-adversarial-results.md.
   - Flag any claim where contrary evidence was MISSED (present in adversarial results
     but absent from the Stress Test table).
   - Validate the "Impact on Certainty" column: does the downgrade follow GRADE rules?
     (e.g., MODERATE → LOW requires substantial contrary evidence, not minor disagreement).
   - If >50% of claims are ⚠ UNCONTESTED, verify the disclaimer note exists and is accurate.
     Check whether the uncontested rate signals genuine consensus or publication bias.

1. **Strongest contrary evidence:** For each key finding K1-KN, identify the strongest
   contrary evidence from any source BEYOND what the Contradiction Stress Test already
   identified. If none found beyond the Stress Test, state "No additional contrary evidence
   beyond the Contradiction Stress Test."

2. **IRON RULE C compliance:** Scan every claim in 04-synthesis.md. Flag any claim that:
   - Uses "proves", "demonstrates", "establishes", "confirms" without qualification
   - Asserts a finding without citing the specific source + section
   - Generalizes beyond the source set (e.g., "X is the best approach" vs "among the 12 sources reviewed, X had the highest benchmark scores")
   Replace with qualified forms from the IRON RULE C reference.

3. **Epistemic scope compliance:** Verify that:
   - The report declares itself as "rapid evidence assessment"
   - No claim implies systematic review certainty
   - The Epistemic Limitations section is present and honest
   - The GRADE ratings do not exceed what the evidence base supports

4. **Selection bias check:**
   - Are the included sources diverse? (authors, institutions, years, methods)
   - Is there evidence of cherry-picking positive results?
   - Are negative/null results from the source set reported?

5. **Gap analysis challenge:**
   - What key evidence is MISSING that would change the conclusions?
   - Are there known counter-examples to the findings?
   - What would a skeptic ask that this report doesn't answer?

6. **Methodological audit:**
   - Were any sources excluded for questionable reasons?
   - Does the risk-of-bias assessment align with the evidence strength claims?
   - Are mathematical claims properly flagged?

## Verdict

After completing the checklist, issue one of:
- **MINOR:** <3 findings, all cosmetic or easily corrected
- **MODERATE:** 3-7 findings, at least 1 affecting an evidence claim
- **MAJOR:** >7 findings, or any finding that invalidates a key conclusion

## Output format

Use the Devil's Advocate template strictly. Every checklist item must have a response.
If an item produces no findings, write "No issues found." — never omit."""


def _build_tiebreak_prompt(
    rq_text: str,
    bibliography_path: str,
    disagreement_list: str,
) -> str:
    return f"""Resolve screening disagreements for RQ: {rq_text}

Bibliography path: {bibliography_path}

## Disagreements to resolve

{disagreement_list}

For each source where the two screeners disagreed:

1. Read the source from the bibliography path
2. Apply the inclusion/exclusion criteria from the RQ
3. Determine: INCLUDE or EXCLUDE with a one-sentence rationale
4. Record your determination

## Output format

| Source ID | Screener 1 | Screener 2 | Tiebreak | Rationale |
|-----------|------------|------------|----------|-----------|
| S{{n}} | INCLUDE | EXCLUDE | INCLUDE/EXCLUDE | {{rationale}} |

Be decisive — do not return UNRESOLVED unless the source is genuinely ambiguous."""


def _build_grey_prompt(rq_text: str, main_topic: str, topics: str = "") -> str:
    if topics:
        per_topic = _build_per_topic_queries(topics, '"limitations of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"criticism of {topic}"')
        negative_section = f"""## Mandatory: Negative search (per-topic)
{per_topic}"""
    else:
        negative_section = f"""## Mandatory: Negative search
- "limitations of {main_topic}"
- "criticism of {main_topic}\""""

    return f"""Search grey literature for: {rq_text}

Search these sources specifically:
- arxiv.org (preprints)
- techrxiv.org (engineering preprints)
- ProQuest Dissertations (theses)
- Google Scholar (conference papers)
- institutional repositories (MIT DSpace, etc.)

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
- Flag retraction/withdrawal notices if found.

## MANDATORY: Write complete results to file
Before responding, you MUST write your COMPLETE source table, search audit, and
negative search results to `/tmp/dsr-grey-results.md` using the write_file tool.
This file will be read by the orchestrator after you finish. Your inline response
can be a summary — the file must contain the full results."""


def _build_deep_read_prompt(
    source_id: str,
    source_path_or_url: str,
    source_title: str,
    rq_text: str,
    skill_dir: str,
    session_dir: str,
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
   Fill every section. Write to `{session_dir}/deep-reads/{source_id}.md`.

## Output contract

- File path: `{session_dir}/deep-reads/{source_id}.md`
- Format: Strictly follow the template structure
- Every claim in the Extracted Claims table MUST include a verbatim quote
- Internal consistency section: report 0 issues if none found (don't omit)
- Mathematical claims: flag if present; state "None" if absent
- Overall assessment: COMPREHENSIVE / PARTIAL / MINIMAL with one-sentence rationale

## Failure handling

- If document is inaccessible (HTTP error, file not found, paywall):
  Write INACCESSIBLE status with reason. Do NOT fabricate claims.
- If RLM fails: Write FAILED status with error message.
- If T4 with >50% sections skipped: Write PARTIAL with coverage percentage."""
