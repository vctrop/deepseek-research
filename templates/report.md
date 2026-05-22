---
session: {date}-{slug}
stage: 5
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Terminal Report

**Session:** `{date}-{slug}`
**Stage:** 5 — Terminal Report

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| `{RQ_TEXT}` | Orchestrator | From `01-rq-brief.md` |
| All findings (K1, K2, ...) | Orchestrator | From `04-synthesis.md`, after Devil's Advocate revisions |
| `{available_axes}` | Orchestrator | From Stage 1 config |

## Research Question

{RQ_TEXT}

## Review Type

{review_type} — see `01-rq-brief.md` §Review Type for rationale and constraints on conclusions.

## Key Findings

### K1: {finding_title}
{Qualified claim. See `references/iron-rule-c.md` §Qualified Replacements.}
**Sources:** S{n} (source tier: HIGH/MEDIUM/LOW, evidence strength: STRONG/MODERATE/WEAK), S{m} (source tier: HIGH/MEDIUM/LOW, evidence strength: STRONG/MODERATE/WEAK)
**Confidence:** HIGH / MEDIUM / LOW / SPECULATIVE

### K2: {finding_title}
...

---

*If insufficient evidence (0 sources, negative report):*
> **Finding:** Insufficient evidence to answer this research question.
> **Sources:** 0 sources were found across {available_axes} axes.
> **Negative search effort:** Queries X, Y, Z returned no contrary evidence either.
> **See:** 02-source-inventory.md for diagnostic.

---

## Numerical Constants

*If RQ is qualitative:*
> This research question is qualitative. No numerical constants were extracted.

| Symbol | Value | Unit | Source | Evidence strength | Confidence |
|--------|-------|------|--------|-------------------|------------|
| {symbol} | {value} | {unit} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

## Algorithms / Patterns

| Name | Complexity / Structure | Domain Assumptions | Source | Evidence strength | Confidence |
|------|------------------------|--------------------|--------|-------------------|------------|
| {name} | {O(...) or pattern desc} | {assumptions} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

## Sources

| Source ID | Location | Type | Source Tier | P/S/T | Evidence Strength Used | COI | Used in |
|-----------|----------|------|-------------|-------|----------------------|-----|---------|
| S{n} | {path/URL} | {type} | HIGH/MEDIUM/LOW | P/S/T | STRONG/MODERATE/WEAK | {none/Minor/Moderate} | K1, K2 |

## Open Questions

| Question | Severity | Next Step |
|----------|----------|-----------|
| {question} | BLOCKING / SIGNIFICANT / MINOR | {concrete action} |

**Severity:** BLOCKING (cannot answer RQ without this), SIGNIFICANT (substantially weakens), MINOR (would improve but not essential).

## IRON RULE C Compliance

This report was written under IRON RULE C constraints. See `references/iron-rule-c.md`.
All claims use qualified language — verified by GATE-3 (two-pass grep for bare claims).

**Confidence language scale used:** HIGH / MEDIUM / LOW / SPECULATIVE (see `references/iron-rule-c.md` §Confidence Language Scale).
