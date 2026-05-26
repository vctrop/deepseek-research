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

## Research Question

{RQ_TEXT}

## Sub-questions

1. {SQ1}
2. {SQ2}
3. {SQ3}

## Scope

**In scope:**
- {item}

**Out of scope:**
- {item}

## Inclusion / Exclusion Criteria

**Inclusion:**
- Relevance ≥ 3 on 5-point scale
- Source accessible (full-text or code)
- {additional criteria}

**Exclusion:**
- Paywall blocking full-text access
- Language inaccessible to reader
- {additional criteria}

## Discovery Axes

| Axis | Active | Notes |
|------|--------|-------|
| bibliography | {yes/no} | {bibliography_path} |
| codebase | {yes/no} | — |

## Deliverables

- [x] 01-rq-brief.md (this file)
- [ ] 02-source-inventory.md
- [ ] 03-source-verification.md
- [ ] deep-reads/*.md
- [ ] 04-synthesis.md
- [ ] 05-report.md
- [ ] MANIFEST.txt

## Protocol Freeze

**SHA256 of this file:** `{rq_sha256}`
**Registered in:** `protocol-freeze.json`
Any post-Stage-2 changes to RQ, scope, or criteria must be documented as
post-hoc refinements in the Methodological Note of the final report.

<!-- STAGE_COMPLETE -->
