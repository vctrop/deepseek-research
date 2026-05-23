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

## Discovery Summary

| Axis | Sources found | Agent | Status |
|------|---------------|-------|--------|
| bibliography | {N} | dsr-bib | completed/failed/skipped |
| codebase | {N} | dsr-code | completed/failed/skipped |

**Total:** {TOTAL} sources before deduplication. {DEDUPED} after deduplication.

## PRISMA-style Flow

Identified: {TOTAL} → After dedup: {DEDUPED} → Selected for verification: {VERIFY_COUNT}

## Negative Search Results

| Topic | Query | Results found | Key findings |
|-------|-------|--------------|--------------|
| {topic} | "{query}" | {N} | {summary or "No contrary evidence found"} |

## Consolidated Sources

| Source ID | Location | Type | Relevance | Why relevant |
|-----------|----------|------|-----------|--------------|
| S1 | {path or URL} | paper/code/doc | 1-5 | {one sentence} |
| S2 | ... | ... | ... | ... |

**Relevance scale:**
- 5 — Directly answers sub-question
- 4 — Strongly related, likely contains key data
- 3 — Possibly useful, requires verification
- 2 — Tangential, may provide context
- 1 — Low relevance, included for completeness

## Source Details

### S{n}: {title / file:line / URL}

- **Type:** {paper / code / documentation}
- **Relevance:** {score}/5
- **Why:** {rationale}
- **Needs verification:** {yes/no}

---

## Diagnosis: No Sources Found (if applicable)

**Bibliography axis:** {diagnostic}
**Codebase axis:** {diagnostic}

**Recommendation:** {widen scope, refine RQ, or accept negative result}
