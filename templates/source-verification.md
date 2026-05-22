# Source Verification

**Session:** `{date}-{slug}`
**Stage:** 3 — Source Verification

## Verification Summary

| Sources total | Accessible | Unverifiable | Excluded |
|---------------|------------|--------------|----------|
| {N} | {N} | {N} | {N} |

## Credibility Matrix

| Source ID | Tier | Rationale | COI Flag | Status |
|-----------|------|-----------|----------|--------|
| S1 | HIGH/MEDIUM/LOW | {why} | {none/Minor/Moderate COI: reason} | ACCESSIBLE/UNVERIFIABLE/EXCLUDED |
| S2 | ... | ... | ... | ... |

**Credibility tiers:**
- **High:** Peer-reviewed paper, industry standard, experimentally validated, official docs of established project
- **Medium:** Textbook, technical report, established codebase pattern, internal project docs
- **Low:** Web article, blog post, single-source claim, AI-generated docs without cross-reference

## COI Register

| Source ID | COI Level | Concern | Mitigation |
|-----------|-----------|---------|------------|
| S{n} | Minor / Moderate | {description} | {how mitigated, or "not mitigated — flagged for synthesis"} |

**COI levels:**
- **Moderate:** Author is creator of evaluated framework, vendor self-report
- **Minor:** AI-generated documentation, internal project doc evaluating own architecture

## Unverifiable Sources

| Source ID | Reason | Was credibility reduced? |
|-----------|--------|--------------------------|
| S{n} | URL not accessible (404/403/timeout) / file not found / network error | Yes → Low / No (transient error) |

## Excluded Sources

| Source ID | Reason |
|-----------|--------|
| S{n} | Duplicate of S{m} / content irrelevant on inspection / credibility too low to use |
