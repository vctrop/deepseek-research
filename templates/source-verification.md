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

| Sources total | Accessible | Unverifiable | Hallucinated | Excluded |
|---------------|------------|--------------|-------------|----------|
| {N} | {N} | {N} | {N} | {N} |

**Note:** "Accessible" means the source URL was verified via `fetch_url` and the
title matched the sub-agent's report. No sources are marked accessible by inference.

## Title Mismatch Detection (GATE-0)

*If no mismatches:*
> ✅ GATE-0 PASS — all source URLs were verified; titles match sub-agent reports.

*If mismatches found:*

| Source ID | Reported URL | Actual content | Resolution |
|-----------|-------------|----------------|------------|
| S{n} | {url reported by sub-agent} | {actual title/content at that URL} | **HALLUCINATED** — {corrective action, e.g., "correct URL is X", "source removed"} |

**⚠ Warning:** This is a known LLM failure mode. The sub-agent generated a
plausible-looking URL that does not correspond to the claimed source. All
arxiv-sourced IDs must be verified against actual content.

## Credibility Matrix

| Source ID | Tier | Rationale | P/S/T | Status |
|-----------|------|-----------|-------|--------|
| S1 | HIGH/MEDIUM/LOW | {why} | P/S/T | ACCESSIBLE |
| S2 | ... | ... | ... | UNVERIFIABLE |
| S{n} | ... | ... | ... | HALLUCINATED |

**Status values:**
- **ACCESSIBLE:** URL fetched successfully; title matches sub-agent report.
- **UNVERIFIABLE:** URL not accessible (404/403/timeout/bot-protection) or
  rate-limited — content could not be confirmed.
- **HALLUCINATED:** URL fetches successfully but content does not match the
  title/source claimed by the sub-agent. Source is removed from active set.
- **EXCLUDED:** Accessible but excluded for other reasons (duplicate, out of scope).

**⚠ There is no "ACCESSIBLE (inferred)" status.** Every source is verified or
marked UNVERIFIABLE.

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
| S{n} | URL not accessible (404/403/timeout/bot-protection) | Reduced / Unchanged |

## Excluded Sources

| Source ID | Reason |
|-----------|--------|
| S{n} | Duplicate / irrelevant on inspection / credibility too low |
