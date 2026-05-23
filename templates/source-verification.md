---
session: {date}-{slug}
stage: 3
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Source Verification

**Session:** `{date}-{slug}`
**Stage:** 3 — Source Verification

## Verification Summary

| Sources total | Accessible | Unverifiable | Excluded |
|---------------|------------|--------------|----------|
| {N} | {N} | {N} | {N} |

## Credibility Matrix

| Source ID | Tier | Rationale | P/S/T | Status |
|-----------|------|-----------|-------|--------|
| S1 | HIGH/MEDIUM/LOW | {why} | P/S/T | ACCESSIBLE / UNVERIFIABLE / EXCLUDED |
| S2 | ... | ... | ... | ... |

**Source credibility tiers:**
- **High:** Peer-reviewed paper, industry standard, multi-party validation
- **Medium:** Textbook, technical report, established codebase pattern
- **Low:** Blog post, single-source claim, preprint not yet peer-reviewed

**P/S/T:** Primary / Secondary / Tertiary. Primary sources have higher weight
for novel claims; secondary/tertiary for consensus.

## Risk of Bias Assessment

### RoB Summary Table

| Source ID | Type | Overall RoB | Key concern |
|-----------|------|------------|-------------|
| S{n} | paper/code | Low/Medium/High | {one-line summary} |

### Detailed RoB (per source with Medium or High)

#### S{n}: {title}

**Type:** paper / code

| Domain | Rating | Evidence |
|--------|--------|----------|
| {domain} | Low/Medium/High | {specific evidence from source} |
| **Overall RoB** | **{rating}** | **{rationale}** |

## Unverifiable Sources

| Source ID | Reason | Credibility |
|-----------|--------|-------------|
| S{n} | URL not accessible (404/403/timeout) | Reduced / Unchanged |

## Excluded Sources

| Source ID | Reason |
|-----------|--------|
| S{n} | Duplicate / irrelevant on inspection / credibility too low |
