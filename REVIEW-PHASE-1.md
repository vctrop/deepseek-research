---
review_target: Phase 1 — Foundational Credibility (v1.5)
review_date: 2026-05-22
reviewer: deepseek-tui (DeepSeek V4 Pro)
review_type: post-implementation audit
commits_reviewed: 625732d (feat), df66a7b (fix)
status: APPROVED with minor observations
---

# Phase 1 Review Report

## 1. Summary

Phase 1 delivers all 5 Tier-1 features (F1–F5) with 11 verification gates.
Three bugs found during review were corrected in commit `df66a7b`. The skill
is functional, self-consistent, and backward-compatible when `protocol_registry`
is set to `"none"`. With default config (`protocol_registry = "local"`),
behavior is additive — one extra file is produced but no existing output changes.

## 2. Correctness

### 2.1 Checklist consistency: ✅ PASS

All 11 checklist items (ids 1–11) have exactly one `checklist_update` call
at the end of their respective stage, with two exceptions that are correct:
- id=3 (Stage 1.5): two calls — one in the skip-condition path, one at stage end
- id=11 (Stage 5 + Close): two calls — Stage 5 end + Close verification end

The `checklist_write` call in Stage 1 lists exactly 11 items matching ids 1–11.
No orphan ids. No duplicate ids in the active path.

### 2.2 Cross-references: ✅ PASS

All 10 `references/*.md` files referenced in Quick Reference exist on disk.
All 3 `scripts/*.py` files referenced exist on disk. All 7 `templates/*.md`
files are loadable.

### 2.3 Feature completeness: ✅ PASS

| Feature | Stage | Gate | Script/Reference | Status |
|---------|-------|------|-----------------|--------|
| F1: Protocol pre-registration | Stage 1.6 | GATE-11 | `protocol_registry.py` | ✅ |
| F2: Dual independent screening | Stage 2 + 2.1 | GATE-10 | `helpers.py::compute_cohens_kappa` | ✅ |
| F3: Risk of Bias matrix | Stage 3 | GATE-9 | `risk-of-bias.md` | ✅ |
| F4: PRISMA flow diagram | Stage 2 + template | GATE-8 | `source-inventory.md` | ✅ |
| F5: PRESS search review | Stage 2.2 | GATE-8 | `press-checklist.md` | ✅ |

### 2.4 Gate coverage: ✅ PASS

11 gates (GATE-1 through GATE-11). All blocking gates documented with
pass/fail/warning/skip semantics. Gate numbering is contiguous and
monotonically increasing.

## 3. Bugs Found & Fixed

| # | Severity | Bug | Fix |
|---|----------|-----|-----|
| B1 | LOW | Stage 2 step numbering: two "4." steps (dispatch + RLM) | Renumbered 4→5, 5→6, 6→7, 7→8 |
| B2 | LOW | Intro line: "7 verification gates" (stale from v1.0) | Updated to "11 verification gates" |
| B3 | MEDIUM | GATE-1 didn't check MANIFEST.txt or protocol-registration.json | Added to file integrity list; fixed `.md` suffix assumption |

## 4. Observations (non-blocking)

### O1 — Stage 1.6 has no graceful fallback for missing `protocol_registry.py`

**Severity:** Low
**Location:** `SKILL.md` line ≈117-125
**Issue:** The `code_execution` call imports `protocol_registry` unconditionally.
If the script file is missing (partial clone, corrupted install), Stage 1.6
crashes with an ImportError. The error-recovery table doesn't cover this case.
**Recommendation:** Add to `references/error-recovery.md`: "If `protocol_registry.py`
not found → log warning, skip Stage 1.6, continue with local SHA256-only."

### O2 — `protocol_registry = "local"` is default but changes output from v1.0

**Severity:** Low
**Issue:** v1.0 didn't produce `protocol-registration.json`. With default config,
Phase 1 always writes this file. This is additive (no existing files change) but
may surprise users expecting identical output.
**Recommendation:** Document in CHANGELOG that `protocol_registry` defaults to
`"local"` and produces a new output file. Users wanting exact v1.0 behavior
should set `protocol_registry = "none"`.

### O3 — Tiebreak sub-agent tools not listed in Allowed Tools section

**Severity:** Low
**Location:** `SKILL.md` line 17-21
**Issue:** The "Stage 2 sub-agents (discovery)" tool list should explicitly
include the tiebreak sub-agent's toolset (`grep_files`, `read_file`,
`file_search`, `write_file`), or a separate "Stage 2.1 sub-agent (tiebreak)"
entry should be added.
**Current state:** Tiebreak tools ARE defined in `references/subagent-prompts.md`
but the SKILL.md overview doesn't mention them.

### O4 — Quick Reference table says "When to load" column

**Severity:** Cosmetic
**Issue:** The "When to load" column is redundant with the pipeline itself.
Removing it saves 2-3 lines per row (≈20 lines total).

### O5 — Pipeline ordering: Stage 1.6 runs before Stage 1.5

**Severity:** Design observation (not a bug)
**Issue:** Protocol is finalized before local corpus is triaged. The protocol
includes inclusion/exclusion criteria defined in the RQ, but doesn't reflect
corpus-specific adjustments discovered during triage.
**Rationale:** The SPEC explicitly says the protocol is based on `01-rq-brief.md`,
which captures the research PLAN. Corpus triage is execution, not planning.
Inclusion criteria don't change based on what's available — they're defined
by the RQ. **No change needed.**

## 5. Budget Analysis

| Metric | Target | Actual | Δ |
|--------|--------|--------|---|
| SKILL.md lines | ≤420 | 456 | +36 (8.6%) |
| Within ceiling (500)? | ≤500 | ✅ 456 | — |

### Line distribution

| Section | Lines | % | Notes |
|---------|-------|---|-------|
| Allowed tools | 12 | 3% | |
| Assumptions | 9 | 2% | |
| Quick Reference | 20 | 4% | See O4 — trimmable |
| Pipeline | 358 | 78% | Dominant; expected for operational content |
| Session directory | 28 | 6% | |
| Integration | 13 | 3% | |

### Cut opportunities

| Opportunity | Lines saved | Risk |
|------------|-------------|------|
| Remove "When to load" column from Quick Reference | ~12 | None — pipeline already defines when each ref loads |
| Extract Stage 1.6 detailed instructions to `references/protocol-finalize.md` | ~15 | Slight — adds one more reference to load |
| Extract Stage 2.1 detailed instructions to `references/reconciliation.md` | ~18 | Slight — same tradeoff |
| **Total potential** | **~45** | Would bring SKILL.md to ~411 lines |

## 6. Backward Compatibility

### Default config path: additive change

With default `.deepseek/deepseek-research.toml` (or absent config):
- `dual_screening = false` → single-agent bibliography screening (unchanged)
- `protocol_registry = "local"` → writes `protocol-registration.json` (new file)
- All existing outputs are identical to v1.0
- One extra file appears in session directory

### Exact v1.0 compatibility

Set in `.deepseek/deepseek-research.toml`:
```toml
protocol_registry = "none"
dual_screening = false
```
This produces byte-identical output to v1.0 (no new files, no changed behavior).

## 7. Verdict

**APPROVED** — Phase 1 is functionally complete and correct. All 5 features
are implemented with verification gates. Three bugs found and fixed.
Five non-blocking observations documented for future refinement.

**Recommendation:** Proceed to Phase 2 (v1.7 — Professional Synthesis) after:
1. Addressing O1 (error recovery for missing protocol_registry.py) — 5 min
2. Optionally addressing O3 (tiebreak tools in Allowed Tools) — 2 min
3. Optionally applying budget cuts (O4 + extractions) — 15 min

The skill is stable at 456 lines and well within the 500-line ceiling.
Budget cuts can be deferred to the next refactoring pass without risk.
