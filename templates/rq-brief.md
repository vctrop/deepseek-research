---
session: {date}-{slug}
stage: 1
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Research Question Brief

**Session:** `{date}-{slug}`
**Stage:** 1 — RQ Formulation

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date (ISO 8601) |
| `{slug}` | Orchestrator | Generated from RQ: lowercase, hyphens, ≤50 chars |
| `{RQ_TEXT}` | Orchestrator | `request_user_input` — full research question |
| `{SQ1}`, `{SQ2}`, ... | Orchestrator | Derived from RQ decomposition |
| `{FINER scores}` | Orchestrator | FINER assessment (Feasible, Interesting, Novel, Ethical, Relevant) |
| `{bibliography_path}` | Config | `.deepseek/deepseek-research.toml` or default `"bibliography/"` |
| `{source_axes}` | Config | `.deepseek/deepseek-research.toml` or default `["bibliography","codebase","web"]` |

## Research Question

{RQ_TEXT}

## Knowledge Type

Classify each sub-question. See `references/epistemology.md` §Knowledge Type Taxonomy.

| Sub-question | Type | Rationale |
|---|---|---|
| {SQ1} | Declarative / Procedural / Causal / Predictive | {why this classification} |
| {SQ2} | ... | ... |

## Sub-questions

1. {SQ1}
2. {SQ2}
3. ...

## Operational Definitions

Every construct in the RQ must have observable criteria. See `references/epistemology.md` §Operationalization.

| Construct | Observable criterion | Measurement method |
|-----------|---------------------|-------------------|
| {construct from RQ} | {what counts as satisfying this construct} | {how to measure it} |
| {construct} | ... | ... |

**Limitations:** {constructs that could NOT be operationalized, and why}

## Scope

**In scope:**
- {item}

**Out of scope (explicitly excluded):**
- {item}

## FINER Assessment

| Criterion | Score (1-5) | Rationale |
|-----------|-------------|-----------|
| Feasible | {score} | {rationale} |
| Interesting | {score} | {rationale} |
| Novel | {score} | {rationale} |
| Ethical | {score} | {rationale} |
| Relevant | {score} | {rationale} |
| **Average** | **{avg}** | |

**Threshold:** Average ≥ 3.0, no criterion < 2. {PASS/FAIL}

## Review Type

See `references/epistemology.md` §Review Type Declaration.

- [ ] **Systematic review** — PRISMA-based, exhaustive within defined databases, reproducible
- [ ] **Rapid evidence assessment** — Structured search, limited databases, faster turnaround
- [ ] **Scoping review** — Mapping breadth of evidence, not depth
- [ ] **Narrative review** — Expert-led, selective, interpretive

**Selected:** {review_type}
**Rationale:** {why this type fits the RQ and time budget}

## Available Discovery Axes

| Axis | Available | Path / Notes |
|------|-----------|--------------|
| bibliography | {yes/no} | {bibliography_path} |
| codebase | yes | — |
| web | {yes/no} | {offline note if unavailable} |

## Decisions Depending on This Research

- {decision_1}
- {decision_2}

## Deliverables

- [x] 01-rq-brief.md (this file)
- [ ] 01a-local-corpus-triage.md
- [ ] 02-source-inventory.md
- [ ] 03-source-verification.md
- [ ] 04-synthesis.md
- [ ] 04a-devils-advocate.md
- [ ] 05-report.md
- [ ] MANIFEST.txt

## Pre-registration

**SHA256 of this file at Stage 1 completion:** `{rq_sha256}`
Any post-Stage-2 changes to RQ, scope, or criteria must be documented as post-hoc refinements.
