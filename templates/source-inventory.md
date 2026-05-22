# Source Inventory

**Session:** `{date}-{slug}`
**Stage:** 2 — Source Discovery

## Discovery Summary

| Axis | Sources found | Agent | Status |
|------|---------------|-------|--------|
| bibliography | {N} | dsr-bib | completed/failed/skipped |
| web | {N} | dsr-web | completed/failed/skipped |
| codebase | {N} | dsr-code | completed |

**Total:** {TOTAL} sources before deduplication. {DEDUPED} after deduplication.

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
