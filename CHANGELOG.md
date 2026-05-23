# Changelog

## v1.7.0 (2026-05-23) — SPEC-001 Complete

### Tier 3: Living & Dissemination
- **C1: Living Systematic Review** — `scripts/living_review.py` with `check_update_needed()` and `build_surveillance_queries()`. Trigger: "update research {slug}".
- **C2: Multiple Output Formats** — Stage 5 produces report, plain-summary, decision-brief, data-supplement.
- **C3: Stakeholder Review** — Stage 4.6 with `request_user_input`.

### Tier 2: Professional Synthesis
- **A1: Meta-Analysis** — `scripts/meta_analysis.py` (478L) with DerSimonian-Laird, forest plot, fail-safe N, leave-one-out.
- **A2: GRADE Certainty** — `scripts/grade.py` (313L) with `rate_certainty()` and 5 self-tests.
- **A3: Sensitivity Analysis** — Stage 4 step 8a: leave-one-out + fail-safe N. GATE-14.
- **A4: Publication Bias** — Stage 3 step 9a: source diversity, result distribution, funnel plot. GATE-23.
- **A5: Grey Literature** — `dsr-grey` sub-agent active. arxiv, techrxiv, ProQuest, Google Scholar.

### Audit (Ondas 1-4)
- **Checklist alignment:** `checklist_write` reordered to match `checklist_update` IDs (13/15 were mismatched).
- **Gate count:** Unified to 22→23 across all references.
- **Stage count:** Corrected to 14.
- **`{{session_dir}}` bug:** Fixed double-brace in deep read prompts.
- **Prompt extraction:** 461 lines → `scripts/prompts.py`. `helpers.py`: 852→367 lines (-57%).
- **`{date}-{slug}` bug:** Fixed compound placeholder resolution order.
- **Tiebreak f-string bug:** `{n}`→`{{n}}` in `_build_tiebreak_prompt`.
- **Grey prompt:** Added `write_file` output contract.
- **AGENTS.md:** Created development guide.
- **README.md:** Full rewrite with architecture, config, pipeline stages.
- **Smoke test:** Updated to 23 gates, grade.py + living_review.py imports.

---

## v1.5.0 (2026-05-22) — Tier 1: Foundational Credibility

- **F1: Protocol Pre-registration** — `protocol_registry.py` with OSF/local support. GATE-11.
- **F2: Dual Independent Screening** — Bibliography dual-screening with tiebreak resolution. GATE-10.
- **F3: Structured Risk of Bias** — ROBIS-adapted matrix across 5 domains. GATE-9.
- **F4: PRISMA Flow Diagram** — Screening audit trail in source inventory.
- **F5: PRESS Search Review** — Search strategy validation. GATE-8.

### Deep Reading & Synthesis
- Deep source reading via RLM chunking (T1-T4 tiers)
- Evidence taxonomy: V/P/I/M/E grades
- Internal consistency checks
- Devil's Advocate adversarial checkpoint
- 19→22 verification gates

---

## v1.0.0 (2026-05-21) — Initial Release

- Core pipeline: RQ formulation → discovery → verification → synthesis → report
- 3 discovery axes: bibliography, codebase, web
- RLM-based deep reading for T3/T4 documents
- IRON RULE C enforcement
- Session state crash recovery
- Epistemic limitations disclosure
- 7 verification gates
