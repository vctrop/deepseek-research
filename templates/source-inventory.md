---
session: {date}-{slug}
stage: 2
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Source Inventory

**Session:** `{date}-{slug}`
**Stage:** 2 — Source Discovery

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| `{N}` (per axis) | Sub-agent output | dsr-bibliography / dsr-web / dsr-code |
| `{TOTAL}` | Orchestrator | Sum of all axes |
| `{DEDUPED}` | Orchestrator | After exact duplicate removal |
| `{negative_search}` | Sub-agents | Mandatory negative queries per `references/epistemology.md` |
| `{BIB_COUNT}`, `{WEB_COUNT}`, `{CODE_COUNT}` | Orchestrator | Counts from each axis sub-agent output |
| `{TOTAL}`, `{DEDUPED}` | Orchestrator | Computed in consolidation |
| `{EXCLUDED_IRRELEVANT}`, `{FULL_TEXT}`, `{INCLUDED}` | Orchestrator | PRISMA flow counts — computed during eligibility assessment |
| `{QUANT}`, `{QUAL}` | Orchestrator | Quantitative vs. qualitative synthesis split |
| `{N_REASON_1}`, `{N_REASON_2}`, `{N_REASON_3}` | Orchestrator | Exclusion reasons from full-text review |
| `{PRESS_REVIEW_CONTENT}` | Orchestrator | Generated at Stage 2.2 per `references/press-checklist.md` |

## Discovery Summary

| Axis | Sources found | Agent | Status |
|------|---------------|-------|--------|
| bibliography | {N} | dsr-bib | completed/failed/skipped |
| web | {N} | dsr-web | completed/failed/skipped |
| codebase | {N} | dsr-code | completed |

**Total:** {TOTAL} sources before deduplication. {DEDUPED} after deduplication.

## Search Audit

| Axis | Query | Engine | Date | Results returned | Results used |
|------|-------|--------|------|-----------------|--------------|
| web | "{primary_query}" | {search_engine} | {date} | {N} | {N} |
| web | "{negative_query_1}" | {search_engine} | {date} | {N} | {N} |
| web | "{negative_query_2}" | {search_engine} | {date} | {N} | {N} |
| bibliography | "{keywords}" | index_sources.py | {date} | {N} | {N} |
| codebase | "{grep_pattern}" | grep_files | {date} | {N} | {N} |

## Negative Search Results

See `references/epistemology.md` §Active Search for Contrary Evidence.

| Topic | Query | Results found | Key findings |
|-------|-------|--------------|--------------|
| {topic} | "{query}" | {N} | {summary of contrary evidence, or "No contrary evidence found"} |

## Saturation

See `references/epistemology.md` §Saturation Criterion.

- **Criterion met:** {description or "N/A — sources below saturation_window"}
- **Sources capped:** {yes — reached max_sources_per_axis / no — saturation reached naturally}

## Consolidated Sources

| Source ID | Location | Type | Relevance | Why relevant |
|-----------|----------|------|-----------|--------------|
| S1 | {path or URL} | {paper/book/impl/doc/web} | 1-5 | {one sentence} |
| S2 | ... | ... | ... | ... |

**Relevance scale:**
- 5 — Directly answers sub-question
- 4 — Strongly related, likely contains key data
- 3 — Possibly useful, requires verification
- 2 — Tangential, may provide context
- 1 — Low relevance, included for completeness

## Source Details

### S{n}: {title / file:line / URL}

- **Type:** {bibliography source type / codebase artifact type}
- **Relevance:** {score}/5
- **Why:** {rationale from sub-agent}
- **Needs verification:** {yes/no — particular concerns}

---

*If 0 sources found across all axes:*

## Screening Reliability

*Only when `dual_screening == true`. See `references/subagent-prompts.md` §Stage 2.1.*

- **Cohen's κ:** {kappa_value} — {interpretation} agreement
- **Agreement:** {agreement_pct}%
- **Agree-include:** {n_agree_include} | **Agree-exclude:** {n_agree_exclude} | **Disagreements:** {n_disagree}
- **Total sources screened:** {n_total}
- **Tiebreak decisions:** {n_tiebreak} (if applicable)
- **Warning:** {threshold_warning or "None — κ ≥ agreement_threshold"}

---

## PRISMA 2020 Flow Diagram

Records identified from:
  Bibliography .................... n = {BIB_COUNT}
  Web search ...................... n = {WEB_COUNT}
  Codebase ........................ n = {CODE_COUNT}
  Citation chasing (snowball) ..... n = 0 (not implemented)
  Grey literature ................. n = 0 (not implemented)
                                    ---------
Total records ..................... n = {TOTAL}

Records after deduplication ....... n = {DEDUPED}
  Excluded (duplicate) ............ n = {TOTAL - DEDUPED}

Records screened (title/abstract) . n = {DEDUPED}
  Excluded (irrelevant) ........... n = {EXCLUDED_IRRELEVANT}

Full-text assessed for eligibility  n = {FULL_TEXT}
  Excluded with reasons ........... n = {FULL_TEXT - INCLUDED}
    Reason 1: insufficient detail   n = {N_REASON_1}
    Reason 2: wrong population      n = {N_REASON_2}
    Reason 3: retracted             n = {N_REASON_3}

Studies included in synthesis ..... n = {INCLUDED}
  Quantitative synthesis ........... n = {QUANT}
  Qualitative synthesis ............ n = {QUAL}

## PRESS Review

See `references/press-checklist.md`.

{PRESS_REVIEW_CONTENT: for each query, 6-element checklist table with ADEQUATE/INADEQUATE/N/A ratings}

---

## Diagnosis: No Sources Found

**Bibliography axis:** {path exists? format recognized? search terms too narrow?}
**Web axis:** {search terms too broad/narrow? paywalled content?}
**Codebase axis:** {RQ not related to codebase? search patterns too specific?}

**Recommendation:** {widen scope, refine RQ, or accept negative result}
