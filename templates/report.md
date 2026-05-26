---
session: {date}-{slug}
stage: 5
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Research Report

**Session:** `{date}-{slug}`
**Stage:** 5 — Terminal Report

## Executive Summary

{4-6 paragraphs covering: research question, method, key findings, confidence, limitations.}

---

## Research Question

{RQ_TEXT}

## Key Findings

### K1: {finding_title}

{Qualified claim — Iron Rule C applies.}

**Sources:** S{n} (credibility: HIGH/MEDIUM/LOW, evidence: STRONG/MODERATE/WEAK),
S{m} (credibility: HIGH/MEDIUM/LOW, evidence: STRONG/MODERATE/WEAK)

**Confidence:** HIGH / MEDIUM / LOW / SPECULATIVE

### K2: {finding_title}
...

---

*If insufficient evidence (0 sources):*
> **Finding:** Insufficient evidence to answer this research question.
> **Sources:** 0 sources found across {available_axes} axes.
> **Negative search effort:** Queries X, Y, Z returned no contrary evidence either.

---

## Structured Data

### Numerical Constants

*If RQ is qualitative: "This research question is qualitative. No numerical constants were extracted."*

| Symbol | Value | Unit | Source | Evidence | Confidence |
|--------|-------|------|--------|----------|------------|
| {symbol} | {value} | {unit} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

### Algorithms / Patterns

| Name | Complexity / Structure | Domain Assumptions | Source | Evidence | Confidence |
|------|------------------------|--------------------|--------|----------|------------|
| {name} | {O(...) or pattern desc} | {assumptions} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

---

## Sources

| Source ID | Location | Type | Credibility | P/S/T | RoB | Used in |
|-----------|----------|------|-------------|-------|-----|---------|
| S{n} | {path/URL} | paper/code/doc | HIGH/MEDIUM/LOW | P/S/T | Low/Medium/High | K1, K2 |

---

## Open Questions

| Question | Severity | Next Step |
|----------|----------|-----------|
| {question} | BLOCKING / SIGNIFICANT / MINOR | {concrete action} |

---

## Methodological Note

This report was produced by an LLM-based rapid evidence assessment pipeline
(deepseek-research v3.0). The following limitations apply:

1. **Scope:** This is a rapid evidence assessment, not a systematic review.
   Source discovery is limited to the configured axes ({available_axes}) and
   may miss relevant literature.

2. **Single-reviewer bias:** All judgments (relevance, bias, evidence grading)
   are performed by LLM sub-agents without independent human review. There
   is no inter-rater reliability check.

3. **Coverage limitations:** Search is bounded by time ({date}), language
   (English-primary), and accessibility (paywalled sources excluded).

4. **Confidence labels:** HIGH / MEDIUM / LOW / SPECULATIVE are qualitative
   guidance based on source convergence and quality, not statistical measures.

5. **Mathematical claims:** Any mathematical claim (M-grade) is flagged and
   requires human verification. The LLM cannot verify mathematical proofs.

6. **Session-specific limitations:**
   {session_specific_limitations}

---

## IRON RULE C Compliance

All claims use qualified language. Bare claims (validated, proved, confirmed,
demonstrated, ensures, guarantees, always, never, optimal, definitive,
conclusive, certainly, undoubtedly, obviously, clearly) are forbidden
without source + method + conditions qualification.

Confidence language scale: HIGH / MEDIUM / LOW / SPECULATIVE.

<!-- STAGE_COMPLETE -->
