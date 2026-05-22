---
target: SPEC-001 Professional Research Team Parity
plan_version: 2.0
created: 2026-05-21
updated: 2026-05-22
status: in_progress
estimated_sessions: 12-15
skill_current: v1.5 (post-Phase 1)
skill_target: v2.0.0
---

# IMPLEMENTATION PLAN — SPEC-001

## 0. Pre-flight

### 0.1 Current baseline

| Metric | Value |
|--------|-------|
| SKILL.md | 533 lines |
| Pipeline stages | Stage 1 → 1.6 → 1.5 → 2 → 2.1 → 2.2 → 2.5 → 3 → 4 → 4.5 → 4.6 → 5 → Close |
| References | 11 files |
| Templates | 11 files |
| Scripts | helpers.py (437 lines), index_sources.py, protocol_registry.py, meta_analysis.py (478 lines), living_review.py |
| Config | 17 variables in `.deepseek/deepseek-research.toml` |
| Gates | GATE-1 through GATE-17 in Close stage |

### 0.2 General implementation rules

1. **Every wave is self-contained.** A wave must leave the skill in a working state — no "broken intermediate" commits.
2. **Templates before pipeline.** When a feature adds new output, create the template first, then wire the pipeline to fill it.
3. **Scripts before integration.** When a feature needs computation, build and test the script standalone before wiring it into a Stage.
4. **Config is additive.** New config variables default to `false`/`none`/`"auto"` so existing installs are not broken.
5. **References before stages.** New epistemology/checklist content goes into `references/` and is referenced — never inlined into SKILL.md.
6. **Gates are feature-specific.** Each wave adds its own verification gate to Close.
7. **SKILL.md budget:** target ≤ 550 lines. Current: 533. Headroom: ~17 lines for 3 phases. Extraction to `references/pipeline-detail.md` in Phase 3 will reclaim ~150 lines.

### 0.3 Dependency graph (phases 1–3)

```
Phase 1 (Deep Source Reading)
  ├── references/deep-reading.md
  ├── templates/source-deep-read.md
  ├── helpers.py::_build_deep_read_prompt()
  ├── SKILL.md §Stage 3.5
  ├── SKILL.md §Stage 3 (modified)
  ├── SKILL.md §Stage 4 (modified)
  └── SKILL.md §GATE-18

Phase 2 (Epistemic Honesty)
  ├── references/epistemic-limitations.md
  ├── SKILL.md §Epistemic Limitations (intro)
  ├── references/grade-framework.md (modified)
  ├── SKILL.md §Stage 1.6 (modified pre-registration)
  ├── SKILL.md §Stage 4 (meta-analysis marked exploratory)
  └── SKILL.md §GATE-18 (human-in-the-loop)

Phase 3 (Skill Craftsmanship)
  ├── references/pipeline-detail.md (extracted)
  ├── references/placeholders.md (new)
  ├── SKILL.md (slimmed to ~380 lines)
  ├── SKILL.md §Quick Reference (conditional loading)
  ├── SKILL.md §Stage 4 (RLM for multi-source synthesis)
  └── SKILL.md §Close (ids 10/11 split)
```

---

## Phase 1: Deep Source Reading (v1.6)

**Goal:** A skill lê artigos, livros e relatórios em profundidade, não apenas
snippets. Todo claim no relatório final é respaldado por citação textual
(verbatim) extraída diretamente da fonte, permitindo verificação humana.

**Problem addressed:** Epistemic problem A — "O LLM não lê papers."
The pipeline currently judges relevance from abstracts and search snippets.
Deep reading processes full documents via RLM, extracting claims with exact
textual evidence and verifying internal consistency.

**Gate:** GATE-18 passes (every STRONG/MODERATE claim has textual evidence).
GATE-1 through GATE-17 continue to pass.

### Wave 1.1 — Epistemology + Template (deep reading foundation)

**Rationale:** Define what deep reading means before wiring it into the pipeline.
Template establishes the output contract that Stage 3.5 and Stage 4 will consume.

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.1a | Create `references/deep-reading.md` — epistemology of deep source reading | `references/deep-reading.md` (new) | Covers: RLM chunking strategy, textual evidence taxonomy (verbatim/paraphrase/inference), internal consistency checks, mathematical claim verification guidance |
| 1.1b | Create `templates/source-deep-read.md` — per-source deep read output | `templates/source-deep-read.md` (new) | Template has: metadata header, extracted claims with verbatim quotes, consistency notes, mathematical claims flag, evidence grade per claim |
| 1.1c | Add "textual evidence" section to `references/epistemology.md` | `references/epistemology.md` | New §Textual Evidence linking to deep-reading.md |
| 1.1d | Add `deep_reading` config variable (default: `true`) | `references/configuration.md` | Documented with other config vars |

**Acceptance criteria:**
- `deep-reading.md` defines chunking strategy for 4 document size tiers
- `source-deep-read.md` template renders without broken placeholders
- Epistemology reference cross-links to deep reading

### Wave 1.2 — Script + Sub-agent Prompt

**Rationale:** The deep reader is a sub-agent that processes one source at a time.
Build the prompt builder first, then integrate.

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.2a | Add `_build_deep_read_prompt()` to `helpers.py` | `scripts/helpers.py` | Function accepts source_id, source_path, rq_text, skill_dir; returns prompt string |
| 1.2b | Register `"dsr-deep-read"` in `build_subagent_prompt()` dispatch table | `scripts/helpers.py` | `build_subagent_prompt('dsr-deep-read', ...)` returns valid prompt |
| 1.2c | Add deep reader prompt specification to `references/subagent-prompts.md` | `references/subagent-prompts.md` | Documents the `code_execution` + `agent_open` invocation pattern |

**Acceptance criteria:**
- `build_subagent_prompt('dsr-deep-read', source_id='S1', source_path='...', rq_text='...', skill_dir='...')` returns non-empty prompt
- Prompt includes RLM chunking instructions, output format contract, and evidence taxonomy

### Wave 1.3 — Pipeline Integration (Stages 3, 3.5, 4)

**Rationale:** Wire deep reading into the pipeline. Stage 3 collects sources;
Stage 3.5 deep-reads each source in parallel; Stage 4 uses textual evidence
in synthesis.

**Duration:** 1 session

| Step | Action | File(s) | Verification |
|------|--------|---------|-------------|
| 1.3a | Add Stage 3.5 to SKILL.md checklist (new id=9, shift existing ids 9→10, 10→11, 11→12, 12→13) | `SKILL.md` §Stage 1 | Checklist has 13 items with correct ids |
| 1.3b | Add Stage 3.5 pipeline section to SKILL.md | `SKILL.md` §Stage 3.5 | Covers: condition (skip if 0 sources or deep_reading=false), dispatch (1 sub-agent per source in parallel), wait, consolidate |
| 1.3c | Add allowed tools for Stage 3.5 sub-agents | `SKILL.md` §Allowed tools | `rlm_open`, `rlm_eval`, `rlm_close`, `read_file`, `write_file`, `handle_read` |
| 1.3d | Modify Stage 3 to collect verbatim quotes from source text | `SKILL.md` §Stage 3 | Step added: "For each source, extract 1-2 key verbatim passages that will anchor deep reading" |
| 1.3e | Modify Stage 4 to require textual evidence for STRONG/MODERATE claims | `SKILL.md` §Stage 4 | Each K-finding must cite verbatim quote + line/section reference from source-deep-read output |
| 1.3f | Add GATE-18 to Close stage | `SKILL.md` §Close | Verifies ≥1 verbatim citation per STRONG/MODERATE claim; FAIL if missing |

**Acceptance criteria:**
- Pipeline runs Stage 3 → 3.5 → 4 without broken placeholders
- GATE-18 detects missing textual evidence
- Backward compatible: `deep_reading = false` skips Stage 3.5 entirely, Stages 3-4 behave as v1.5

### Phase 1 Gate Summary

After Wave 1.3, Close verification runs 18 gates (GATE-1 through GATE-18).
New: GATE-18 (textual evidence for STRONG/MODERATE claims).

**Phase 1 exit criteria:**
- [ ] All 18 gates pass on a test research question
- [ ] SKILL.md ≤ 580 lines (budget: 533 + ~47 for Phase 1 additions)
- [ ] At least 3 sources deep-read in a test session with verbatim quotes extracted
- [ ] Backward compatibility: session with `deep_reading = false` behaves identically to v1.5

---

## Phase 2: Epistemic Honesty & Human Verifiability (v1.7)

**Goal:** A skill declara explicitamente suas limitações epistêmicas. Meta-análise
quantitativa é marcada como exploratória. GRADE-for-engineering é declarado como
adaptação experimental. Pre-registration inclui plano de análise. Claims STRONG
exigem verificabilidade humana.

**Problems addressed:** B (gates sintáticos, não semânticos), C (pre-registration
incompleto), D (meta-análise frágil), G (GRADE não validado para engenharia).

### Wave 2.1 — Epistemic Limitations Document

| Step | Action | File(s) |
|------|--------|---------|
| 2.1a | Create `references/epistemic-limitations.md` | New file |
| 2.1b | Add "Epistemic Limitations" section to SKILL.md intro (5-8 lines) | `SKILL.md` |
| 2.1c | Modify `references/grade-framework.md` — add "Adaptation Notice" header | `references/grade-framework.md` |
| 2.1d | Modify Stage 4 meta-analysis section — mark as "exploratory/illustrative" | `SKILL.md` §Stage 4 |

### Wave 2.2 — Enhanced Pre-registration + Human-in-the-Loop

| Step | Action | File(s) |
|------|--------|---------|
| 2.2a | Modify Stage 1 (RQ Formulation) — add analysis plan to RQ brief | `SKILL.md` §Stage 1 |
| 2.2b | Modify `templates/rq-brief.md` — add Analysis Plan section | `templates/rq-brief.md` |
| 2.2c | Modify Stage 1.6 (Protocol Finalize) — include analysis plan in protocol_dict | `SKILL.md` §Stage 1.6 |
| 2.2d | Add GATE-18 sub-check: human-verifiability for STRONG claims (verbatim quote + source location) | `SKILL.md` §Close |

### Phase 2 exit criteria:
- [ ] `references/epistemic-limitations.md` covers all 5 gaps identified in critical review
- [ ] RQ brief template includes Analysis Plan section
- [ ] Meta-analysis output labeled "Exploratory quantitative synthesis — not a validated meta-analysis"
- [ ] GRADE framework header declares adaptation status
- [ ] All gates continue to pass

---

## Phase 3: Skill Craftsmanship & Resource Optimization (v1.8)

**Goal:** SKILL.md slimmed to ~380 lines. Pipeline details extracted to
references. Placeholder resolution table created. RLM used for multi-source
synthesis. Quick Reference shows conditional loading.

**Problems addressed:** Skill-writing issues A-F, Resource management issues A-E.

### Wave 3.1 — Pipeline Detail Extraction

| Step | Action | File(s) |
|------|--------|---------|
| 3.1a | Create `references/pipeline-detail.md` — extract step-by-step instructions | New file |
| 3.1b | Slim SKILL.md stages to: Who, Output, Condition, Template ref, Key decisions, Reference to pipeline-detail.md | `SKILL.md` |
| 3.1c | Create `references/placeholders.md` — master resolution table (32 placeholders) | New file |
| 3.1d | Update Quick Reference with conditional loading indicators | `SKILL.md` §Quick Reference |

### Wave 3.2 — Resource Optimization

| Step | Action | File(s) |
|------|--------|---------|
| 3.2a | Add RLM-based multi-source synthesis to Stage 4 (>10 sources path) | `SKILL.md` §Stage 4 |
| 3.2b | Split checklist ids 10/11 (Devil's Advocate / Stakeholder Review) | `SKILL.md` §Stage 1 |
| 3.2c | Update `references/context-budget.md` — add orchestrator context ceiling | `references/context-budget.md` |
| 3.2d | Fix stage numbering: 1.6→1.4 (Protocol), 1.5→1.5 (Corpus Triage) — or document rationale | `SKILL.md` |

### Phase 3 exit criteria:
- [ ] SKILL.md ≤ 400 lines
- [ ] `references/placeholders.md` covers all 32+ placeholders with source stage
- [ ] Stage 4 RLM path functional for 10+ source sessions
- [ ] Quick Reference shows which references load conditionally
- [ ] All 18 gates continue to pass

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-05-21 | 1.0 | Initial plan — 3 phases (Foundational Credibility, Professional Synthesis, Dissemination) |
| 2026-05-22 | 2.0 | Replanned based on critical review. Phase 1 pivoted to Deep Source Reading. Original Phase 1 features (F1-F5) already shipped. New 3-phase structure: Deep Reading → Epistemic Honesty → Craftsmanship. |
