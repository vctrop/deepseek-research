---
target: SPEC-001 Professional Research Team Parity
plan_version: 1.0
created: 2026-05-21
status: ready_for_review
estimated_sessions: 8-10
skill_current: v1.0 (post-curto-prazo)
skill_target: v2.0.0
---

# IMPLEMENTATION PLAN — SPEC-001

## 0. Pre-flight

### 0.1 Current baseline

| Metric | Value |
|--------|-------|
| SKILL.md | 344 lines |
| Pipeline stages | Stage 1 → 1.5 → 2 → 2.5 → 3 → 4 → 4.5 → 5 → Close |
| References | 8 files (epistemology, iron-rule-c, anti-patterns, error-recovery, model-matrix, context-budget, configuration, subagent-prompts) |
| Templates | 7 files (rq-brief, local-corpus-triage, source-inventory, source-verification, synthesis, devils-advocate, report) |
| Scripts | helpers.py (276 lines), index_sources.py (388 lines) |
| Config | 8 variables in `.deepseek/deepseek-research.toml` |
| Gates | GATE-1 through GATE-7 in Close stage |

### 0.2 General implementation rules

1. **Every wave is self-contained.** A wave must leave the skill in a working state — no "broken intermediate" commits.
2. **Templates before pipeline.** When a feature adds new output, create the template first, then wire the pipeline to fill it. Reduces rework.
3. **Scripts before integration.** When a feature needs computation (`meta_analysis.py`), build and test the script standalone before wiring it into a Stage.
4. **Config is additive.** New config variables default to `false`/`none`/`"auto"` so existing installs are not broken.
5. **References before stages.** New epistemology/checklist content goes into `references/` and is referenced — never inlined into SKILL.md.
6. **Gates are feature-specific.** Each wave adds its own verification gate to Close. No wave is complete without its gate.
7. **SKILL.md budget:** target ≤ 500 lines after Phase 3. Current: 344. Headroom: ~150 lines for 13 features.

### 0.3 Dependency graph

```
F4 (PRISMA) ──┐
F5 (PRESS) ───┤
              ├──► F2 (Dual Screen) ──┐
F3 (RoB) ─────┤                       ├──► A1 (Meta) ──┬──► A3 (Sensitivity)
              └──► F1 (Protocol) ─────┘                ├──► A4 (Pub Bias)
                                                       ├──► A2 (GRADE) ──┐
A5 (Grey Lit) ────────────────────────────────────────┘                │
                                                                        └──► C1 (Living)

C2 (Outputs) ── independent
C3 (Stakeholder) ── independent
```

---

## Phase 1: v1.5 — Foundational Credibility

**Goal:** The skill can legitimately say "systematic review" without a
methodologist raising an eyebrow. PRISMA flow, dual screening, structured
risk of bias, protocol pre-registration, search strategy peer review.

**Gate:** All 5 Tier-1 features passing their individual gates. PRISMA compliance ≥ 80%.

### Wave 1.1 — Quick diagnostic wins (F4 + F5)

**Rationale:** PRISMA flow and PRESS review are template-only changes with no
pipeline restructuring. They establish the screening audit trail before we add
dual screening (which will use that trail).

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.1a | Add PRISMA flow section to `templates/source-inventory.md` | `templates/source-inventory.md` | Template renders without broken placeholders |
| 1.1b | Add PRISMA placeholders table to template | `templates/source-inventory.md` | All `{EXCLUDED_*}`, `{FULL_TEXT}`, `{INCLUDED}`, `{QUANT}`, `{QUAL}` placeholders documented |
| 1.1c | Update Stage 2 consolidation step in SKILL.md to populate PRISMA counts | `SKILL.md` §Stage 2 | Orchestrator instructions reference PRISMA section |
| 1.1d | Add PRESS checklist to `references/` | `references/press-checklist.md` (new) | File exists with 6 PRESS 2015 elements |
| 1.1e | Add Stage 2.2 (PRESS Review) to SKILL.md pipeline | `SKILL.md` §Stage 2 | New sub-stage between consolidation and checklist update |
| 1.1f | Add GATE-8: PRISMA compliance check to Close | `SKILL.md` §Close | Gate counts PRISMA items present ÷ total items expected |
| 1.1g | Update checklist in Stage 1 to include Stage 2.2 item | `SKILL.md` §Stage 1 | Checklist has 9 items (was 8) |

**Acceptance criteria:**
- `02-source-inventory.md` renders a PRISMA flow with all 8 line items populated (not "n = 0" for everything)
- PRESS checklist applied to ≥1 search query per active axis
- GATE-8 reports compliance percentage, warns if <80%

**Files touched:** `templates/source-inventory.md`, `SKILL.md`, `references/press-checklist.md` (new)

---

### Wave 1.2 — Risk of Bias matrix (F3)

**Rationale:** F3 replaces the ad-hoc COI Register with a domain-appropriate
structured assessment. This is a prerequisite for A1 (meta-analysis uses RoB
for study weighting) and A2 (GRADE uses RoB as a downgrade domain).

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.2a | Create `references/risk-of-bias.md` with 4 study-type tool definitions | `references/risk-of-bias.md` (new) | File defines domains for algorithm, empirical, simulation, survey studies |
| 1.2b | Update `templates/source-verification.md`: replace COI Register with Risk of Bias Assessment table | `templates/source-verification.md` | Template has RoB table with study-type-specific domain columns |
| 1.2c | Update `templates/synthesis.md`: replace source-tier-only columns with RoB column | `templates/synthesis.md` | Source Usage table gains `RoB` column |
| 1.2d | Update Stage 3 instructions in SKILL.md to reference RoB instead of COI | `SKILL.md` §Stage 3 | Step 6 references `references/risk-of-bias.md` |
| 1.2e | Update `references/epistemology.md`: add RoB-to-evidence-strength mapping | `references/epistemology.md` | New §Mapping Risk of Bias to Evidence Strength |
| 1.2f | Update Quick Reference table in SKILL.md | `SKILL.md` §Quick Reference | Risk of Bias entry added |
| 1.2g | Add GATE-9: RoB completeness check | `SKILL.md` §Close | Gate verifies every source has a completed RoB assessment |

**Acceptance criteria:**
- Every source in `03-source-verification.md` has domain ratings + overall RoB
- At least 2 different study types correctly classified across a test session
- COI Register is fully removed (grep confirms zero `COI Register` occurrences outside references)
- GATE-9 passes (100% source coverage)

**Files touched:** `references/risk-of-bias.md` (new), `templates/source-verification.md`, `templates/synthesis.md`, `templates/report.md`, `SKILL.md`, `references/epistemology.md`

---

### Wave 1.3 — Dual independent screening (F2)

**Rationale:** This is the highest-impact credibility change. Requires pipeline
restructuring: Stage 2 splits into dispatch + reconciliation + tiebreak.

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.3a | Add `dual_screening` and `agreement_threshold` to config reference | `references/configuration.md` | Both variables documented with defaults |
| 1.3b | Update `references/subagent-prompts.md`: add `dsr-bib-1`, `dsr-bib-2`, `dsr-bib-tiebreak` entries | `references/subagent-prompts.md` | 3 new prompt templates |
| 1.3c | Add `_build_tiebreak_prompt()` to `scripts/helpers.py` | `scripts/helpers.py` | New function in `build_subagent_prompt` dispatch table |
| 1.3d | Add Cohen's kappa to `scripts/helpers.py` | `scripts/helpers.py` | `compute_cohens_kappa(include_a, include_b, n_total)` — pure Python, no deps |
| 1.3e | Restructure Stage 2 in SKILL.md: dispatch → reconcile → tiebreak | `SKILL.md` §Stage 2 | Clear branching: if dual_screening=true, dispatch 2; else dispatch 1 (backward compat) |
| 1.3f | Add Stage 2.1 (Reconciliation) to SKILL.md | `SKILL.md` §Stage 2 | Computes agreement %, dispatches tiebreak for disagreements |
| 1.3g | Add "Screening Reliability" section to `templates/source-inventory.md` | `templates/source-inventory.md` | Reports κ, agreement %, disagreement count |
| 1.3h | Add GATE-10: Inter-rater reliability threshold check | `SKILL.md` §Close | If κ < agreement_threshold → WARNING (not FAIL — research can proceed with caution) |
| 1.3i | Update checklist in Stage 1 for new sub-stages (2.1) | `SKILL.md` §Stage 1 | Checklist covers dual-screen path |

**Acceptance criteria:**
- With `dual_screening = true`: 2 bib sub-agents dispatched, reconciliation runs, κ reported
- With `dual_screening = false`: backward-compatible single-agent path (unchanged behavior)
- κ computation verified against known test case (2 raters, 100 items, 85 agree → κ ≈ 0.70)
- Tiebreak sub-agent resolves ≥1 disagreement in test session

**Files touched:** `SKILL.md`, `references/configuration.md`, `references/subagent-prompts.md`, `scripts/helpers.py`, `templates/source-inventory.md`

---

### Wave 1.4 — Protocol pre-registration (F1)

**Rationale:** Closes the credibility loop — protocol is publicly citable before
research begins. Depends on F2+F3+F4+F5 being complete so the protocol can
describe the full methodology.

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.4a | Add `protocol_registry`, `osf_token`, `osf_project_id` to config reference | `references/configuration.md` | Variables documented |
| 1.4b | Create `scripts/protocol_registry.py` — OSF API client (pure Python, stdlib `urllib`) | `scripts/protocol_registry.py` (new) | `register_protocol(osf_token, project_id, protocol_dict) → doi_url` |
| 1.4c | Create `templates/protocol-metadata.json` — Zenodo/OSF metadata template | `templates/protocol-metadata.json` (new) | Valid JSON with all required fields |
| 1.4d | Add Stage 1.6 (Protocol Finalize) to SKILL.md | `SKILL.md` §Stage 1 | New sub-stage after SHA256 computation |
| 1.4e | Add `register_protocol` to `scripts/helpers.py` as thin wrapper | `scripts/helpers.py` | Delegates to `protocol_registry.py` |
| 1.4f | Add `protocol_doi` field to session index entry format | `references/configuration.md` | Session index schema updated |
| 1.4g | Add GATE-11: Protocol DOI resolves | `SKILL.md` §Close | `fetch_url(protocol_doi)` returns 200; SKIP if registry=none |
| 1.4h | Update checklist for Stage 1.6 | `SKILL.md` §Stage 1 | Checklist covers protocol path |

**Acceptance criteria:**
- With `protocol_registry = "osf"` + valid token: DOI returned and recorded in MANIFEST.txt
- With `protocol_registry = "none"`: graceful skip, SHA256-only path (backward compatible)
- GATE-11 passes when DOI is present, SKIPs when registry is none

**Files touched:** `references/configuration.md`, `scripts/protocol_registry.py` (new), `scripts/helpers.py`, `templates/protocol-metadata.json` (new), `SKILL.md`

---

### Phase 1 Gate Summary

After Wave 1.4, Close verification runs 11 gates (GATE-1 through GATE-11).
Full PRISMA compliance (GATE-8 ≥ 80%) + RoB completeness (GATE-9 = 100%) +
κ threshold check (GATE-10) + protocol DOI (GATE-11).

**Phase 1 exit criteria:**
- [ ] All 11 gates pass on a test research question
- [ ] SKILL.md ≤ 420 lines (budget: 344 + ~76 for Phase 1 additions)
- [ ] `cargo test`-style equivalent: `python3 scripts/helpers.py --self-test` passes
- [ ] Backward compatibility: session with all new config vars set to `false`/`"none"` behaves identically to v1.0

---

## Phase 2: v1.7 — Professional Synthesis

**Goal:** The skill delivers quantitative synthesis with proper meta-analytic
methods, GRADE certainty ratings, sensitivity analysis, and publication bias
detection. Grey literature axis added.

**Prerequisites:** Phase 1 complete (F3 required for meta-analysis weighting
and GRADE downgrade; F2 required for trustworthy source pool).

### Wave 2.1 — Grey literature axis (A5)

**Rationale:** Lowest-dependency Tier-2 feature. Can be implemented in parallel
with meta_analysis.py development. Simple: new sub-agent + config flag.

**Duration:** 0.5 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 2.1a | Add `"grey"` to `source_axes` config options | `references/configuration.md` | Documented as optional axis |
| 2.1b | Add `dsr-grey` prompt template to `references/subagent-prompts.md` | `references/subagent-prompts.md` | Prompt includes arxiv, techrxiv, ProQuest, Google Scholar, DSpace |
| 2.1c | Add `_build_grey_prompt()` to `scripts/helpers.py` | `scripts/helpers.py` | New function in build_subagent_prompt dispatch |
| 2.1d | Update Stage 2 dispatch in SKILL.md: conditionally dispatch `dsr-grey` | `SKILL.md` §Stage 2 | Dispatched when `"grey"` in source_axes |
| 2.1e | Update PRISMA flow: grey literature line populated | `templates/source-inventory.md` | Flow shows grey lit count > 0 when axis active |

**Acceptance criteria:**
- With `source_axes = [..., "grey"]`: grey sub-agent dispatched, sources returned
- Grey sources appear in PRISMA flow as separate line item
- Without `"grey"` in axes: no behavioral change

**Files touched:** `references/configuration.md`, `references/subagent-prompts.md`, `scripts/helpers.py`, `SKILL.md`, `templates/source-inventory.md`

---

### Wave 2.2 — Meta-analysis engine (A1)

**Rationale:** The computational core of Phase 2. Must be built and validated
before GRADE (A2) and sensitivity (A3) can use it. This is the highest-effort
single feature in the plan.

**Duration:** 1.5 sessions

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 2.2a | Create `scripts/meta_analysis.py` — pure Python, stdlib only | `scripts/meta_analysis.py` (new) | Module with 0 external dependencies |
| 2.2b | Implement `random_effects_pool(effects, variances)` — DerSimonian-Laird | `scripts/meta_analysis.py` | Returns `{pooled, ci_lower, ci_upper, I2, tau2, Q, Q_pvalue}` |
| 2.2c | Implement `fixed_effects_pool(effects, variances)` | `scripts/meta_analysis.py` | Inverse-variance weighted; used as fallback when I² < 25% |
| 2.2d | Implement `forest_plot_text(effects, variances, labels)` — ASCII table | `scripts/meta_analysis.py` | Returns formatted string suitable for Markdown code block |
| 2.2e | Implement `cochran_q(effects, variances)` — heterogeneity test | `scripts/meta_analysis.py` | Returns Q statistic and p-value (chi² approximation) |
| 2.2f | Implement `i_squared(Q, df)` — heterogeneity index | `scripts/meta_analysis.py` | Returns I² as percentage, clamped to [0, 100] |
| 2.2g | Implement `tau2_dl(effects, variances, fixed_weights)` — DerSimonian-Laird τ² | `scripts/meta_analysis.py` | Returns τ² estimate |
| 2.2h | Validate against R `metafor` package on 3 test datasets | `scripts/meta_analysis.py` (embedded tests) | Pooled estimates within ±5% of R output; I² within ±3 percentage points |
| 2.2i | Add `meta_analysis` config variable | `references/configuration.md` | `meta_analysis = "auto"` (default: trigger when ≥3 sources report same effect) |
| 2.2j | Add "Quantitative Synthesis" sub-section to `templates/synthesis.md` | `templates/synthesis.md` | Conditional section: rendered only when meta-analysis triggers |
| 2.2k | Update Stage 4 in SKILL.md: dispatch meta-analysis via `code_execution` | `SKILL.md` §Stage 4 | New step between constants extraction and consensus assessment |
| 2.2l | Add "Quantitative Synthesis" section to `templates/report.md` | `templates/report.md` | Report template gains forest plot + heterogeneity section |
| 2.2m | Add GATE-12: Meta-analysis self-test | `SKILL.md` §Close | Runs `python3 scripts/meta_analysis.py --self-test`; FAIL if tests don't pass |

**Acceptance criteria:**
- `meta_analysis.py --self-test` passes all 3 validation datasets
- Forest plot renders correctly in Markdown (monospace alignment)
- Meta-analysis triggers on RQ with ≥3 quantitative sources reporting same effect
- Meta-analysis skips gracefully on qualitative RQs (no crash, no empty table)

**Key implementation notes:**
- **No numpy/scipy.** Use Welford's algorithm for variance accumulation. Chi² p-value via Wilson-Hilferty approximation (no `scipy.stats`). Matrix operations via list comprehensions.
- **DerSimonian-Laird:** Iterative method — converges in <10 iterations for typical datasets. Implement with explicit convergence check.
- **Test datasets:** Bundle 3 known datasets as JSON fixtures in `scripts/test-data/`:
  1. Normand 1999 (8 studies, psychotherapy) — classic meta-analysis textbook example
  2. Bangert-Drowns 2004 (15 studies, writing干预) — moderate heterogeneity (I² ≈ 60%)
  3. Synthetic (5 studies, homogeneous) — I² ≈ 0%

**Files touched:** `scripts/meta_analysis.py` (new, ~250 lines), `scripts/test-data/` (new, 3 JSON files), `templates/synthesis.md`, `templates/report.md`, `SKILL.md`, `references/configuration.md`

---

### Wave 2.3 — GRADE certainty framework (A2)

**Rationale:** Uses A1 output (heterogeneity) and F3 output (RoB) as inputs.
Without A1+F3, GRADE has nothing to grade.

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 2.3a | Create `references/grade-framework.md` — adapted GRADE for engineering | `references/grade-framework.md` (new) | 5 domains with upgrade/downgrade criteria; adapted evidence hierarchy |
| 2.3b | Add GRADE rating to `templates/synthesis.md` per-finding section | `templates/synthesis.md` | Each K-finding gains `GRADE Certainty: ⊕⊕⊕⊝ MODERATE` line |
| 2.3c | Add GRADE justification to finding template | `templates/synthesis.md` | `Downgraded for:` or `Upgraded for:` line per finding |
| 2.3d | Update Stage 4 in SKILL.md: GRADE rating step after consensus assessment | `SKILL.md` §Stage 4 | Orchestrator applies GRADE domains using RoB (Stage 3) + I² (Stage 4 meta-analysis) |
| 2.3e | Add GRADE certainty to `templates/report.md` findings | `templates/report.md` | Report findings show GRADE rating |
| 2.3f | Add GATE-13: GRADE completeness | `SKILL.md` §Close | Every K-finding has a GRADE rating; SKIP if qualitative RQ |

**Acceptance criteria:**
- ≥80% of findings in a test session have internally consistent GRADE ratings (downgrades match RoB and I² evidence)
- GRADE ratings use correct symbols (⊕⊕⊕⊕, ⊕⊕⊕⊝, ⊕⊕⊝⊝, ⊕⊝⊝⊝)
- Qualitative RQs skip GRADE cleanly (no "⊕⊕⊕⊕ N/A" noise)

**Files touched:** `references/grade-framework.md` (new), `templates/synthesis.md`, `templates/report.md`, `SKILL.md`

---

### Wave 2.4 — Sensitivity + Publication Bias (A3 + A4)

**Rationale:** Both piggyback on meta-analysis output. Can be implemented
together since they share the same trigger condition (≥5 sources + quantitative synthesis).

**Duration:** 0.5 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 2.4a | Add `sensitivity_leave_one_out()` to `scripts/meta_analysis.py` | `scripts/meta_analysis.py` | Returns list of `{excluded, pooled, ci_lower, ci_upper, I2}` |
| 2.4b | Add `fail_safe_n(effects, variances, alpha=0.05)` to `scripts/meta_analysis.py` | `scripts/meta_analysis.py` | Rosenthal's method; returns N |
| 2.4c | Add `source_diversity_check(source_list)` to `scripts/helpers.py` | `scripts/helpers.py` | Returns % from same author group, institution |
| 2.4d | Add "Sensitivity Analysis" and "Publication Bias" sub-sections to `templates/synthesis.md` | `templates/synthesis.md` | Conditional: rendered when ≥5 sources |
| 2.4e | Update Stage 4 in SKILL.md: run sensitivity + pub bias after meta-analysis | `SKILL.md` §Stage 4 | New steps with `code_execution` calls |
| 2.4f | Add GATE-14: Sensitivity flagging | `SKILL.md` §Close | If any leave-one-out changes conclusion direction → WARNING in gate output |

**Acceptance criteria:**
- Leave-one-out runs without error on ≥5 studies
- Fail-safe N computed and reported
- If ≥50% of sources share same author group → publication bias flag in report

**Files touched:** `scripts/meta_analysis.py`, `scripts/helpers.py`, `templates/synthesis.md`, `SKILL.md`

---

### Phase 2 Gate Summary

After Wave 2.4, Close verification runs 14 gates. Gate failures on
GATE-12 (meta-analysis self-test) and GATE-13 (GRADE completeness) are
blocking.

**Phase 2 exit criteria:**
- [ ] All 14 gates pass on a test RQ with ≥5 quantitative sources
- [ ] `meta_analysis.py --self-test` passes (pooled estimates within ±5% of R)
- [ ] SKILL.md ≤ 480 lines
- [ ] Qualitative RQ path unaffected (meta-analysis + GRADE cleanly skip)
- [ ] Backward compatibility: `meta_analysis = "never"` produces identical output to v1.0

---

## Phase 3: v2.0 — Living & Dissemination

**Goal:** Research is updatable, multi-audience, and stakeholder-validated.

**Prerequisites:** Phase 2 complete (living review needs meta-analysis for
re-synthesis; stakeholder review needs credible findings to present).

### Wave 3.1 — Multiple output formats (C2)

**Rationale:** Pure template work. Independent of everything else.

**Duration:** 0.5 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 3.1a | Create `templates/plain-summary.md` — ≤500 word template | `templates/plain-summary.md` (new) | Template with plain-language constraints |
| 3.1b | Create `templates/decision-brief.md` — 1-pager template | `templates/decision-brief.md` (new) | Actionable recommendations format |
| 3.1c | Create `templates/data-supplement.json` — machine-readable schema | `templates/data-supplement.json` (new) | JSON schema for extracted constants, findings, sources |
| 3.1d | Add Stage 5 steps in SKILL.md: generate additional formats | `SKILL.md` §Stage 5 | Orchestrator fills plain-summary and decision-brief templates |
| 3.1e | Add GATE-15: Output format completeness | `SKILL.md` §Close | Verify all 4 output files exist and are non-empty |

**Acceptance criteria:**
- Plain summary ≤ 500 words and 0 jargon terms from a configurable blocklist
- Decision brief contains ≤5 actionable bullets
- Data supplement is valid JSON with all findings machine-readable

**Files touched:** `templates/plain-summary.md` (new), `templates/decision-brief.md` (new), `templates/data-supplement.json` (new), `SKILL.md`

---

### Wave 3.2 — Stakeholder review panel (C3)

**Rationale:** Simple pipeline insertion. Independent of other Tier 3 features.

**Duration:** 0.5 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 3.2a | Add `stakeholder_review` config variable | `references/configuration.md` | Default: `false` |
| 3.2b | Create `templates/stakeholder-review.md` | `templates/stakeholder-review.md` (new) | Template for feedback capture |
| 3.2c | Add Stage 4.6 (Stakeholder Review) to SKILL.md | `SKILL.md` §Stage 4.5 | New stage between Devil's Advocate and Stage 5 |
| 3.2d | Implement `request_user_input` call for stakeholder feedback | `SKILL.md` §Stage 4.6 | Presents K1-K3, asks for concerns |
| 3.2e | Document feedback application step | `SKILL.md` §Stage 4.6 | Orchestrator addresses feedback before Stage 5 |
| 3.2f | Add GATE-16: Stakeholder review documentation | `SKILL.md` §Close | If enabled, `04b-stakeholder-review.md` exists and is non-empty |

**Acceptance criteria:**
- With `stakeholder_review = true`: user prompted after Devil's Advocate, feedback documented
- With `stakeholder_review = false`: stage skipped, no behavioral change
- Feedback that changes findings triggers a note in the report

**Files touched:** `references/configuration.md`, `templates/stakeholder-review.md` (new), `SKILL.md`

---

### Wave 3.3 — Living systematic review (C1)

**Rationale:** Most complex Tier-3 feature. Requires MANIFEST versioning,
surveillance search logic, and update-append semantics. Depends on A1+A2
(re-synthesis on update) and F1 (protocol DOI for version linking).

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 3.3a | Add `living_review`, `surveillance_interval_days`, `surveillance_queries` to config | `references/configuration.md` | Variables documented |
| 3.3b | Update `MANIFEST.txt` format: add `search_date`, `search_queries`, `update_history` | `SKILL.md` §Session directory | Structured metadata for resumption |
| 3.3c | Create `scripts/living_review.py` — session loader + update logic | `scripts/living_review.py` (new) | `load_prior_session(slug) → session_state`, `needs_update(session_state, interval_days) → bool` |
| 3.3d | Add update trigger detection to Stage 1 | `SKILL.md` §Stage 1 | If session exists + `living_review = true` + interval exceeded → "update mode" |
| 3.3e | Add update-mode pipeline: re-run Stage 2 with date-filtered queries, skip Stage 1 (RQ unchanged) | `SKILL.md` §Stage 1 | Branching logic for update vs. fresh |
| 3.3f | Add re-synthesis logic: only re-run meta-analysis if new studies found | `SKILL.md` §Stage 4 | Conditional re-synthesis step |
| 3.3g | Add append-to-report logic in Stage 5 | `SKILL.md` §Stage 5 | "Update N" header appended to existing `05-report.md` |
| 3.3h | Add GATE-17: Living review freshness | `SKILL.md` §Close | If `living_review = true` + interval exceeded → WARNING |

**Acceptance criteria:**
- Triggering `"update research {slug}"` loads prior session and re-runs searches with date filter
- New studies found → meta-analysis updated, report appended
- No new studies → report marked "No new evidence as of {date}"
- Update history recorded in MANIFEST.txt

**Files touched:** `references/configuration.md`, `scripts/living_review.py` (new), `scripts/helpers.py`, `SKILL.md`

---

### Phase 3 Gate Summary

Final tally: 17 gates. Phase 3 adds GATE-15 (output formats), GATE-16
(stakeholder review), GATE-17 (living review freshness).

**Phase 3 exit criteria:**
- [ ] All 17 gates pass on a test session
- [ ] SKILL.md ≤ 500 lines
- [ ] Update cycle: fresh → update → re-update sequence works without state corruption
- [ ] All 4 output formats generated and valid
- [ ] Backward compatibility: all new features disabled by default

---

## 4. Effort Summary

| Phase | Waves | Sessions | New files | Lines (est.) |
|-------|-------|----------|-----------|-------------|
| Phase 1 (v1.5) | 4 | 4 | 4 | ~600 |
| Phase 2 (v1.7) | 4 | 3.5 | 5 | ~700 |
| Phase 3 (v2.0) | 3 | 2 | 8 | ~400 |
| **Total** | **11** | **9.5** | **17** | **~1700** |

---

## 5. Risk Register

| Risk | Phase | Likelihood | Impact | Mitigation |
|------|-------|-----------|--------|------------|
| `meta_analysis.py` numerical instability without scipy | 2.2 | Medium | High | Validate against R; use Welford's algorithm; embed test datasets |
| Dual screening with same model = pseudo-replication | 1.3 | High | Medium | Use Flash for rater-1, Pro for rater-2; measure κ empirically |
| OSF API rate-limiting or auth changes | 1.4 | Low | Medium | Graceful fallback to local SHA256; configurable timeout |
| SKILL.md exceeds 500-line budget | All | Medium | Low | Aggressively reference instead of inline; extract Stage instructions to references/ if needed |
| GRADE adaptation rejected by domain experts | 2.3 | Medium | Medium | Document as "GRADE-adapted"; flag as experimental in config |
| Living review state corruption on partial update | 3.3 | Medium | High | Atomic writes; MANIFEST.txt as single source of truth; rollback on failure |
| Grey literature sub-agent returns noise | 2.1 | High | Low | Stricter inclusion criteria; `relevance ≥ 4` threshold for grey sources |

---

## 6. Verification Strategy

### Per-wave verification

Every wave ends with:
1. **Unit:** Script self-tests pass (`--self-test` flag where applicable)
2. **Integration:** Feature works end-to-end on a canned test RQ
3. **Regression:** Backward-compatible path produces identical output

### Cross-phase verification

- **Meta-research spike:** After Phase 1, run 3 identical RQs through the skill and compare outputs — do dual screening and RoB produce consistent results?
- **Calibration study:** After Phase 2, compare skill's GRADE ratings against 2 human researchers on 10 test findings
- **Living review drill:** After Phase 3, simulate a 90-day update cycle with synthetic new evidence

### Final acceptance

- [ ] 17/17 gates pass on `"deep research calibration test"`
- [ ] `python3 scripts/helpers.py --self-test && python3 scripts/meta_analysis.py --self-test && python3 scripts/index_sources.py --self-test` all pass
- [ ] SKILL.md ≤ 500 lines
- [ ] README.md in skill root updated with v2.0 feature summary
- [ ] CHANGELOG.md updated with breaking changes (config variable additions are additive — no breaks expected)
