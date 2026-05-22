# Pipeline Detail Reference

Loaded by the orchestrator at each stage when the slim SKILL.md says
"See `references/pipeline-detail.md` §Stage N for detailed instructions."
Do NOT inline this content in SKILL.md.

This file contains the step-by-step instructions extracted from SKILL.md
to keep the main skill body under 400 lines.

---

## Stage 1: RQ Formulation

> SKILL.md slim header has: Who, Output, Template, Config vars, References.
> This section has the numbered steps.

1. Load config: `read_file("{SKILL_DIR}/references/configuration.md")`. Note: `output_dir`, `bibliography_path`, `persist_sources`, `source_axes`, `deep_reading`, `agreement_threshold`, `living_review`.
2. Load epistemology: `read_file("{SKILL_DIR}/references/epistemology.md")` (focus on §Knowledge Type Taxonomy, §Operationalization, §Review Type Declaration).
3. Setup progress tracking:
   ```
   checklist_write(todos=[
     {"content": "Stage 1: RQ Formulation", "status": "in_progress"},
     {"content": "Stage 1.6: Protocol Finalize", "status": "pending"},
     {"content": "Stage 1.5: Local Corpus Triage", "status": "pending"},
     {"content": "Stage 2: Source Discovery", "status": "pending"},
     {"content": "Stage 2.1: Reconciliation", "status": "pending"},
     {"content": "Stage 2.2: PRESS Review", "status": "pending"},
     {"content": "Stage 2.5: Persistence", "status": "pending"},
     {"content": "Stage 3: Source Verification", "status": "pending"},
     {"content": "Stage 3.5: Deep Source Reading", "status": "pending"},
     {"content": "Stage 4: Synthesis", "status": "pending"},
     {"content": "Stage 4.5: Devil's Advocate", "status": "pending"},
     {"content": "Stage 4.6: Stakeholder Review", "status": "pending"},
     {"content": "Stage 5: Terminal Report + Close", "status": "pending"}
   ])
   ```
   Use `checklist_update(id, status)` for all subsequent updates — never `checklist_write` again.
4. Load template: `read_file("{SKILL_DIR}/templates/rq-brief.md")`.
5. Use `request_user_input` to clarify: central question, domains spanned, decisions depending on this research.
6. Generate slug from RQ: lowercase, hyphens, ≤ 50 chars. Example: "Estado da arte em co-kriging?" → `co-kriging-estado-da-arte`.
7. Check prior sessions: `grep_files` in `$SESSION_INDEX` for slug/topic. If found, ask user to extend or start fresh.
   - **Living review trigger:** If `living_review == true` and session exists, check update cadence via `living_review` module. If `needs_update == true`: enter "update mode." If `needs_update == false`: STOP.
8. **Classify knowledge type:** Per `references/epistemology.md` §Knowledge Type Taxonomy. Each sub-question gets a classification.
9. **Operationalize concepts:** Per `references/epistemology.md` §Operationalization. Every RQ construct needs observable criteria.
10. **Formulate analysis plan:** Fill the Analysis Plan section — synthesis method, effect size metric, inclusion/exclusion thresholds, saturation rule, sensitivity analyses. Narrative-only RQs mark quantitative entries as "N/A."
11. Apply FINER scoring (threshold: average ≥ 3.0, no criterion < 2).
12. **Declare review type:** Per `references/epistemology.md` §Review Type Declaration.
13. Detect available axes from `source_axes`: bibliography, codebase, web.
14. Fill template completely. Write `01-rq-brief.md`.
15. **Pre-register:** Compute SHA256 of `01-rq-brief.md` via `helpers.compute_sha256()`. Record in file and MANIFEST.txt.
16. `checklist_update(id=1, status="completed")`.

---

## Stage 1.6: Protocol Finalize

> SKILL.md slim header has: Who, Output, Condition, Config vars.

1. Build protocol dict from `01-rq-brief.md` content:
   - title = RQ
   - description = scope + operational definitions
   - category = "analysis" (engineering research)
   - questions = FINER criteria as Q&A, sub-questions as Q&A, review type declaration
   - analysis_plan = {from 01-rq-brief.md §Analysis Plan}
2. If `protocol_registry == "osf"`: use `protocol_registry.register_protocol()` with osf_token and osf_project_id.
3. If `protocol_registry == "local"`: write `protocol-registration.json` to session dir via `protocol_registry.register_local()`.
4. Record registration method and identifier in `MANIFEST.txt`.
5. `checklist_update(id=2, status="completed")`.

---

## Stage 1.5: Local Corpus Triage

> SKILL.md slim header has: Who, Output, Condition, Template, Config vars.

**Condition:** Run ONLY if `"bibliography"` is in `source_axes` AND `persist_sources == true`. Otherwise skip.

1. Load template: `read_file("{SKILL_DIR}/templates/local-corpus-triage.md")`.
2. Index local corpus: `code_execution` → `index_sources.main(bibliography_path, local_index_path)`.
3. Extract keywords from RQ. Use `code_execution` → Python string ops, never direct `exec_shell` grep (anti-pattern #11).
4. For each keyword, query the index. `code_execution` → `index_sources.query(local_index_path, keyword, max_results=20)`.
5. LLM relevance judgment for each candidate (relevance ≥ 3 → `local_sources`).
6. Fill template. `checklist_update(id=3, status="completed")`.

---

## Stage 2: Source Discovery

> SKILL.md slim header has: Who, Output, Template.

1. Load template: `read_file("{SKILL_DIR}/templates/source-inventory.md")`.
2. Extract keywords from `01-rq-brief.md`: use `code_execution` with Python, never shell interpolation.
3. Identify active axes from `source_axes`. For each active axis, dispatch sub-agents.
4. **Bibliography dispatch:** load sub-agent prompt spec from `references/subagent-prompts.md`. Use `helpers.build_subagent_prompt('dsr-bibliography', ...)`.
5. **Web dispatch:** load sub-agent prompt spec. Use `helpers.build_subagent_prompt('dsr-web', ...)`.
6. **Code dispatch:** load sub-agent prompt spec. Use `helpers.build_subagent_prompt('dsr-code', ...)`.
7. **Parallel dispatch:** all sub-agents in one turn.
8. Wait for all sub-agents: `agent_eval(agent_id="...", block=true)` for each.
9. Merge all `returned_sources` with dedup_by_url. `checklist_update(id=4, status="completed")`.

---

## Stage 2.1: Reconciliation

> SKILL.md slim header has: Who, Output, Condition.

**Condition:** Run ONLY if `source_axes` has ≥2 axes that returned sources.

1. Identify disagreements (one axis included a source another excluded). Extract source metadata.
2. For each disagreement, dispatch tiebreak sub-agent.
3. Load tiebreak spec from `references/subagent-prompts.md`. `helpers.build_subagent_prompt('dsr-tiebreak', ...)`.
4. Wait for tiebreak sub-agents.
5. Build reconciliation matrix: agreement %, counts. If κ < `agreement_threshold`: WARNING. `checklist_update(id=5, status="completed")`.

---

## Stage 2.2: PRESS Review

> SKILL.md slim header has: Who, Output, Template.

1. Load PRESS checklist: `read_file("{SKILL_DIR}/references/press-checklist.md")`.
2. For each web search query in `02-source-inventory.md`, evaluate: translation, operators, coverage, specificity, sensitivity. Rate ADEQUATE / INADEQUATE.
3. Re-run rule: if ≥2 elements INADEQUATE for any query, re-run search with corrected query.
4. Write PRESS Review section to `02-source-inventory.md` (append).
5. `checklist_update(id=6, status="completed")`.

---

## Stage 2.5: Persistence

> SKILL.md slim header has: Who, Output, Condition, Config vars.

**Condition:** Run ONLY if `persist_sources == true`.

1. Load index script: `code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import index_new, dedup_local; ...")`.
2. Index new sources: `index_new(bibliography_path, new_sources)`.
3. Process reused_local: update sessions_used for each.
4. Emit summary: "Corpus updated: {N} new, {M} reused."
5. `checklist_update(id=7, status="completed")`.

---

## Stage 3: Source Verification

> SKILL.md slim header has: Who, Output, Template.

1. Load template: `read_file("{SKILL_DIR}/templates/source-verification.md")`.
2. For each source from Stage 2 inventory: fetch header or first 2KB to verify accessibility.
3. Classify as ACCESSIBLE / INACCESSIBLE / PARTIAL (paywall, truncated).
4. Classify source type: primary / secondary / tertiary (per epistemology §Primary vs Secondary).
5. Load risk-of-bias: `read_file("{SKILL_DIR}/references/risk-of-bias.md")`.
6. For each ACCESSIBLE source, assess RoB across 5 domains. Assign overall rating.
7. Apply RoB → Evidence Strength modifier.
8. If >20 sources: use RLM with `sub_query_batch(dependency_mode="independent")`.
9. **Prepare for deep reading.** If `deep_reading != false`:
   a. Load deep reading reference: `read_file("{SKILL_DIR}/references/deep-reading.md")`.
   b. For each source, collect metadata: source_id, source_path_or_url, source_title. Estimate document tier.
   c. Record in `03-source-verification.md` under `## Deep Read Queue`.
   d. If `deep_reading == false` or source is UNVERIFIABLE: mark as "deep reading skipped."
10. Fill template. `checklist_update(id=8, status="completed")`.

---

## Stage 3.5: Deep Source Reading

> SKILL.md slim header has: Who, Output, Template, Condition, Config vars.

**Condition:** Skip if `deep_reading == false` OR 0 sources after Stage 2. For individual sources marked UNVERIFIABLE, skip deep reading for that source.

1. Load deep reading methodology: `read_file("{SKILL_DIR}/references/deep-reading.md")`.
2. Load sub-agent prompt spec: `read_file("{SKILL_DIR}/references/subagent-prompts.md")` §Stage 3.5.
3. Build the deep read queue from Stage 3 output (`03-source-verification.md` §Deep Read Queue).
4. Dispatch sub-agents in parallel — one per source. Use `helpers.build_subagent_prompt('dsr-deep-read', ...)`. If >10 sources, batch in groups of 10.
5. Wait for all sub-agents: `agent_eval(agent_id="...", block=true)` for each.
6. Validate outputs: each `{session_dir}/deep-reads/{source_id}.md` must exist with `## Extracted Claims` section.
7. Consolidate: count by status (COMPREHENSIVE/PARTIAL/MINIMAL/INACCESSIBLE/FAILED). Summarize claims by grade (V/P/I/M). Write `_consolidation.md`.
8. `checklist_update(id=9, status="completed")`.

---

## Stage 4: Synthesis

> SKILL.md slim header has: Who, Output, Template.

1. Load template: `read_file("{SKILL_DIR}/templates/synthesis.md")`.
2. Load IRON RULE C: `read_file("{SKILL_DIR}/references/iron-rule-c.md")`.
3. Load epistemology for evidence strength matrix and textual evidence: `read_file("{SKILL_DIR}/references/epistemology.md")` §Textual Evidence.
4. **Load deep read evidence.** If Stage 3.5 ran:
   a. Read consolidation: `read_file("{session_dir}/deep-reads/_consolidation.md")`.
   b. For each source with COMPREHENSIVE/PARTIAL status, load its deep read file.
   c. If Stage 3.5 was skipped: v1.5 behavior (evidence capped at MODERATE).
5. Deduplicate findings: group equivalent claims from multiple sources.
6. Evaluate each claim independently: evidence strength, source tier, textual evidence constraint (STRONG requires V-grade, MODERATE requires V or P).
7. Extract constants: numerical values with units, sources, evidence strength, confidence.
8. Quantitative synthesis (exploratory meta-analysis): trigger when RQ type is predictive/causal AND ≥3 sources. **Label:** "Exploratory quantitative synthesis — not a validated meta-analysis."
9. Apply GRADE framework: load `references/grade-framework.md` for overall certainty rating.
10. Build PRISMA flow diagram: count sources through each stage.
11. Consensus assessment: per epistemology §Consensus Assessment Rules.
12. Identify gaps: questions not answered by any source.
13. Content density: do not repeat >20% of content from prior stages.
14. **RLM multi-source synthesis (>10 sources).** When the session has >10 sources after Stage 3:
    a. Open an RLM session: `rlm_open(name="synth-{slug}", content="")`.
    b. Load all deep-read source files into the RLM as a corpus:
       ```python
       rlm_eval(name="synth-{slug}", code="""
       import json, glob
       source_files = [f for f in glob.glob("{session_dir}/deep-reads/*.md") if not f.endswith("_consolidation.md")]
       corpus = {}
       for f in source_files:
           with open(f) as fh:
               corpus[f] = fh.read()
       # Store corpus as RLM variable
       sources = corpus
       finalize({'n_sources': len(corpus), 'source_ids': list(corpus.keys())})
       """)
       ```
    c. Cross-reference claims across sources using `sub_query_batch`:
       ```python
       rlm_eval(name="synth-{slug}", code="""
       queries = [
           f"In source corpus, identify all claims about '{construct}' and classify agreement: CONSENSUS/MAJORITY/DIVERGENT/INSUFFICIENT. Extract verbatim quotes."
           for construct in constructs_from_rq
       ]
       results = sub_query_batch(queries=queries, dependency_mode="independent",
           safety_note="Each query examines the same corpus for a different construct. No dependencies.")
       finalize(results)
       """)
       ```
    d. Close the RLM session after synthesis: `rlm_close(name="synth-{slug}")`.
    e. Fallback: if RLM is unavailable or source count ≤10, process claims directly in the orchestrator context.
15. Fill template. `checklist_update(id=10, status="completed")`.

---

## Stage 4.5: Devil's Advocate Checkpoint

> SKILL.md slim header has: Who, Output, Template.

1. Load Devil's Advocate spec: `read_file("{SKILL_DIR}/references/subagent-prompts.md")` §Stage 4.5.
2. Build prompt: `helpers.build_subagent_prompt('dsr-da', ...)`.
3. Dispatch sub-agent: `agent_open(name="dsr-da", model="deepseek-v4-pro", ...)`.
4. Wait: `agent_eval(agent_id="...", block=true)`.
5. Read output: `read_file("{session_dir}/04a-devils-advocate.md")`.
6. Apply corrections to `04-synthesis.md`. Sub-agent NEVER modifies `04-synthesis.md` directly. `checklist_update(id=11, status="completed")`.

---

## Stage 4.6: Stakeholder Review

> SKILL.md slim header has: Who, Output, Template, Condition.

**Condition:** If `stakeholder_review == true`, run this stage using `request_user_input` to present findings and collect feedback.

1. Present summary of key findings to user via `request_user_input` with three options: ACCEPT, REVISE, or FLAG.
2. For each REVISE: ask what specific revision is needed.
3. Document feedback and actions taken in the template.
4. Apply feedback to `04-synthesis.md` before Stage 5.
5. `checklist_update(id=12, status="completed")`.

---

## Stage 5: Terminal Report

> SKILL.md slim header has: Who, Output, Template.

1. Load report template: `read_file("{SKILL_DIR}/templates/report.md")`.
2. Convert synthesis to final report format.
3. Append Epistemic Limitations: `read_file("{SKILL_DIR}/references/epistemic-limitations.md")` §Report Integration.
4. Append data supplement if numerical data was extracted. `read_file("{SKILL_DIR}/templates/data-supplement.json")`.
5. No knowledge entity creation. Report is the final artifact.
6. `checklist_update(id=13, status="completed")`.

---

## Close: Gate Details

> SKILL.md slim header references this section for executable gate commands.

Each gate is a structural integrity check. Gates verify form, not truth —
see `references/epistemic-limitations.md` §L2.
Emit PASS/FAIL/WARNING/UNVERIFIABLE per gate. GATE-1/2/3/5/8/16 failures must be resolved.

**GATE-1 — File integrity.** Verify expected files exist and are non-empty:
```
export PERSIST_SOURCES="{persist_sources}"
export PROTOCOL_REGISTRY="{protocol_registry}"
export STAKEHOLDER_REVIEW="{stakeholder_review}"
SESSION_DIR="{output_dir}/{date}-{slug}"
expected="01-rq-brief.md MANIFEST.txt"
[ "$PERSIST_SOURCES" = "true" ] && expected="$expected 01a-local-corpus-triage.md"
[ "$PROTOCOL_REGISTRY" != "none" ] && expected="$expected protocol-registration.json"
expected="$expected 02-source-inventory.md 03-source-verification.md 04-synthesis.md 04a-devils-advocate.md 05-report.md 05-plain-summary.md 05-decision-brief.md"
[ "$STAKEHOLDER_REVIEW" = "true" ] && expected="$expected 04b-stakeholder-review.md"
for stage in $expected; do
  f="$SESSION_DIR/$stage"
  [ -s "$f" ] && echo "OK $stage" || echo "FAIL: $stage missing or empty"
done
# 05-data-supplement.json is optional — WARNING if absent, never FAIL
[ -s "$SESSION_DIR/05-data-supplement.json" ] && echo "OK 05-data-supplement.json" || echo "WARNING: 05-data-supplement.json absent (optional)"
```

**GATE-2 — Session index.** `grep_files(pattern="{slug}", path="$SESSION_INDEX")`

**GATE-3 — IRON RULE C (two-pass).** See `references/iron-rule-c.md` §Detection.
- Pass 1: full bare claims regex across `{session_dir}/05-report.md` and `{session_dir}/04-synthesis.md`
- Pass 2: exclude matches with qualifying context. Report only unqualified matches.

**GATE-4 — Integration checks (optional).** Run `$INTEGRATION_CHECKS` if configured. Failure does NOT block.

**GATE-5 — Persistence manifest integrity.** If bibliography axis active:
```
grep_files(pattern="persistence_manifest", path="{session_dir}/")
```

**GATE-6 — Corpus index validity.** If `persist_sources == true` and index exists:
```
validate_data(path="{bibliography_path}/index/papers.json", format="json")
```
Repeat for `reports.json` and `books.json` if they exist. WARNING on parse failure.

**GATE-7 — Unindexed files check.** If `persist_sources == true` (informational, never FAIL).
```
exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py check-unindexed --base-dir {bibliography_path}")
```

**GATE-8 — PRISMA + PRESS compliance.**
```
grep_files(pattern="PRISMA 2020 Flow Diagram", path="{session_dir}/02-source-inventory.md")
```
Must return match. Count PRISMA line items present: each line not "n = 0" counts as 1. Total expected: 15 items. WARNING if < 80%; FAIL if < 50%.
```
grep_files(pattern="PRESS Review", path="{session_dir}/02-source-inventory.md")
```
Must return match. FAIL if absent.

**GATE-9 — Risk of Bias completeness.**
```
grep_files(pattern="Overall RoB", path="{session_dir}/03-source-verification.md")
```
Count matches. Expected count = number of sources in inventory. FAIL if mismatch.
```
grep_files(pattern="Study type", path="{session_dir}/03-source-verification.md")
```
Must return match. FAIL if absent.

**GATE-10 — Inter-rater reliability.** If `dual_screening == true`:
```
grep_files(pattern="Screening Reliability", path="{session_dir}/02-source-inventory.md")
grep_files(pattern="kappa", path="{session_dir}/02-source-inventory.md")
```
Both must return match. FAIL if absent.
If κ < `agreement_threshold` → WARNING (not FAIL — research may proceed with caution).
If `dual_screening == false`: SKIP.

**GATE-11 — Protocol registration.** If `protocol_registry != "none"`:
```
grep_files(pattern="registration", path="{session_dir}/MANIFEST.txt")
```
Must return match. FAIL if absent.
If `protocol_registry == "osf"`: `fetch_url({doi_url})` → must return 200. WARNING if fails (OSF may be down).
If `protocol_registry == "local"`: verify `protocol-registration.json` exists and is valid JSON (`validate_data`). FAIL if absent.

**GATE-12 — Meta-analysis self-test.** If `meta_analysis != "never"`:
```
exec_shell(command: "python3 {SKILL_DIR}/scripts/meta_analysis.py --self-test")
```
Must return exit code 0. FAIL if non-zero.
If `meta_analysis == "never"`: SKIP.

**GATE-13 — GRADE completeness.** Verify every key finding has a GRADE rating:
```
grep_files(pattern="GRADE Certainty", path="{session_dir}/04-synthesis.md")
```
Count matches. Expected count = number of K-findings. WARNING if mismatch; FAIL if 0.
Qualitative RQ: SKIP.

**GATE-14 — Sensitivity flagging.** If meta-analysis ran:
```
grep_files(pattern="Leave-one-out", path="{session_dir}/04-synthesis.md")
```
Must return match if ≥5 studies. WARNING if absent.
```
grep_files(pattern="Fail-safe", path="{session_dir}/04-synthesis.md")
```
Must return match. WARNING if absent.

**GATE-15 — Output format completeness.** Verify all output files:
```
[ -s "{session_dir}/05-report.md" ] || echo "FAIL: 05-report.md missing"
[ -s "{session_dir}/05-plain-summary.md" ] || echo "FAIL: 05-plain-summary.md missing"
[ -s "{session_dir}/05-decision-brief.md" ] || echo "FAIL: 05-decision-brief.md missing"
```
`validate_data(path="{session_dir}/05-data-supplement.json", format="json")` — WARNING if absent or invalid (optional).

**GATE-16 — Stakeholder review.** If `stakeholder_review == true`:
```
[ -s "{session_dir}/04b-stakeholder-review.md" ] || echo "FAIL: 04b-stakeholder-review.md missing"
```
If `stakeholder_review == false`: SKIP.

**GATE-17 — Living review cadence.** If `living_review == true`:
```
grep_files(pattern="last_search_date", path="{session_dir}/MANIFEST.txt")
```
Must return match. FAIL if absent.
WARNING if `surveillance_interval_days` exceeded and no update triggered.
If `living_review == false`: SKIP.

**GATE-18 — Textual evidence + human verifiability.** If `deep_reading != false` and sources were deep-read:
```
grep_files(pattern="Verbatim evidence", path="{session_dir}/04-synthesis.md")
```
Count STRONG claims: `grep_files(pattern="Evidence strength: STRONG", path="{session_dir}/04-synthesis.md")` → count. FAIL if mismatch.
**Human-verifiability sub-check (STRONG claims):** For each STRONG claim, verify the verbatim quote is traceable:
```
grep_files(pattern="{quote excerpt}", path="{session_dir}/deep-reads/")
```
If the exact quote is not found in any `{source_id}.md` under `## Extracted Claims`, FAIL.
Verify every MODERATE claim has either `**Verbatim evidence:**` or `**Paraphrase evidence:**` field.
If any deep-read source has M-grade claims, verify flagged with `⚠ MATHEMATICAL` in the synthesis.
If `deep_reading == false` or 0 sources: SKIP.

**GATE-19 — Session MANIFEST integrity.**
```
grep_files(pattern="SHA256", path="{session_dir}/MANIFEST.txt")
grep_files(pattern="stage_completion", path="{session_dir}/MANIFEST.txt")
```
Both must return match. FAIL if absent.

`checklist_update(id=13, status="completed")`.
