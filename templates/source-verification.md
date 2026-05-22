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

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| `{N}` | Orchestrator | From `02-source-inventory.md` |

## Verification Summary

| Sources total | Accessible | Unverifiable | Excluded |
|---------------|------------|--------------|----------|
| {N} | {N} | {N} | {N} |

## Credibility Matrix (source-level)

| Source ID | Tier | Rationale | Primary/Secondary/Tertiary | Status |
|-----------|------|-----------|---------------------------|--------|
| S1 | HIGH/MEDIUM/LOW | {why} | {P/S/T} | ACCESSIBLE/UNVERIFIABLE/EXCLUDED |
| S2 | ... | ... | ... | ... |

**Source credibility tiers:**
- **High:** Peer-reviewed paper in established venue, industry standard with multi-party validation, experimentally validated by independent teams
- **Medium:** Textbook, technical report from recognized institution, established codebase pattern, internal project docs with revision history
- **Low:** Web article, blog post, single-source claim, AI-generated docs without cross-reference, preprint not yet peer-reviewed

**Primary/Secondary/Tertiary:** See `references/epistemology.md` §Primary vs. Secondary vs. Tertiary.
Primary sources receive higher weight for novel claims; secondary for consensus claims.

## Risk of Bias Assessment

See `references/risk-of-bias.md` for domain definitions and rating criteria.

### RoB Summary Table (all sources)

| Source ID | Study type | Overall RoB | Key concern | Methodological quality | Reporting quality |
|-----------|-----------|------------|-------------|----------------------|-------------------|
| S{n} | simulation/empirical/algorithm/review/documentation | Low / Some concerns / High / Critical | {one-line summary} | Adequate / Concerning / Poor | Adequate / Incomplete / Poor |

### Detailed RoB (per source with Some concerns or higher)

#### S{n}: {title} — Study type: {type}

| Domain | Rating | Evidence |
|--------|--------|----------|
| D1: {domain_name} | Low / Some concerns / High / Critical | {specific evidence from source} |
| D2: {domain_name} | ... | ... |
| **Overall RoB** | **{rating}** | **{rationale}** |

## Unverifiable Sources

| Source ID | Reason | Was credibility reduced? |
|-----------|--------|--------------------------|
| S{n} | URL not accessible (404/403/timeout) / file not found / network error | Yes → Low / No (transient error) |

## Excluded Sources

| Source ID | Reason |
|-----------|--------|
| S{n} | Duplicate of S{m} / content irrelevant on inspection / credibility too low to use |
