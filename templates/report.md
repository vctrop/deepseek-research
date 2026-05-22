# Terminal Report

**Session:** `{date}-{slug}`
**Stage:** 5 — Terminal Report

## Research Question

{RQ_TEXT}

## Key Findings

### K1: {finding_title}
{Qualified claim. No bare "validated"/"confirmed"/"proved".}
**Sources:** S{n} (HIGH), S{m} (MEDIUM)
**Confidence:** HIGH / MEDIUM / LOW

### K2: {finding_title}
...

---

*If insufficient evidence (0 sources, negative report):*
> **Finding:** Insufficient evidence to answer this research question.
> **Sources:** 0 sources were found across {available_axes} axes.
> **See:** 02-source-inventory.md for diagnostic.

---

## Numerical Constants

*If RQ is qualitative:*
> This research question is qualitative. No numerical constants were extracted.

| Symbol | Value | Unit | Source | Confidence |
|--------|-------|------|--------|------------|
| {symbol} | {value} | {unit} | S{n} (HIGH) | HIGH/MEDIUM/LOW |

## Algorithms / Patterns

| Name | Complexity / Structure | Domain Assumptions | Source | Confidence |
|------|------------------------|--------------------|--------|------------|
| {name} | {O(...) or pattern desc} | {assumptions} | S{n} | HIGH/MEDIUM/LOW |

## Sources

| Source ID | Location | Type | Credibility | COI | Used in |
|-----------|----------|------|-------------|-----|---------|
| S{n} | {path/URL} | {type} | HIGH/MEDIUM/LOW | {none/Minor/Moderate} | K1, K2 |

## Open Questions

| Question | Severity | Next Step |
|----------|----------|-----------|
| {question} | BLOCKING / SIGNIFICANT / MINOR | {concrete action} |

**Severity:** BLOCKING (cannot answer RQ without this), SIGNIFICANT (substantially weakens), MINOR (would improve but not essential).

## IRON RULE C Compliance

This report was written under IRON RULE C constraints (§IRON RULE C in SKILL.md). All claims use qualified language — verified by GATE-3 (two-pass grep for bare claims).
