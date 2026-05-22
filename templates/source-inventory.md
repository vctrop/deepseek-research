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

## Diagnosis: No Sources Found

**Bibliography axis:** {path exists? format recognized? search terms too narrow?}
**Web axis:** {search terms too broad/narrow? paywalled content?}
**Codebase axis:** {RQ not related to codebase? search patterns too specific?}

**Recommendation:** {widen scope, refine RQ, or accept negative result}
