# Pipeline Detail Reference

Loaded by the orchestrator at each stage when the slim SKILL.md says
"See `references/pipeline-detail.md` §Stage N for detailed instructions."
Do NOT inline this content in SKILL.md.

This file contains the step-by-step instructions extracted from SKILL.md
to keep the main skill body under 400 lines.

---

## Stage Execution Order

Stages are executed in this sequence (pipeline-detail.md sections follow
this order; stage numbering reflects logical grouping, not execution order):

| Exec # | Stage ID | Description |
|--------|----------|-------------|
| 1 | Stage 1 | RQ Formulation |
| 2 | Stage 1.7 | Open-Source Applicability Decision |
| 3 | Stage 1.6 | Protocol Finalize |
| 4 | Stage 1.5 | Local Corpus Triage |
| 5 | Stage 2 | Source Discovery |
| 6 | Stage 2.1 | Reconciliation |
| 7 | Stage 2.2 | PRESS Review |
| 8 | Stage 2.5 | Persistence |
| 9 | Stage 3 | Source Verification |
| 10 | Stage 3.5 | Deep Source Reading |
| 11 | Stage 4 | Synthesis |
| 12 | Stage 4.5 | Devil's Advocate Checkpoint |
| 13 | Stage 4.6 | Stakeholder Review |
| 14 | Stage 5 | Terminal Report |
| 15 | Close | Verification (22 gates) |

**Rationale:** Stages 1.5-1.7 are "Stage 1 sub-stages" (planning), Stages 2.1-2.5 are
"Stage 2 sub-stages" (discovery), and Stage 3.5 is a Stage 3 sub-stage (deep reading).
The decimal numbering groups them logically even though execution order differs.

```
Stage 1   (RQ Formulation)
  ↓
Stage 1.7 (Open-Source Applicability Decision) — runs ALWAYS, before protocol
  ↓
Stage 1.6 (Protocol Finalize)
  ↓
Stage 1.5 (Local Corpus Triage) — conditional: bibliography axis + persist_sources
  ↓
Stage 2   (Source Discovery) — parallel sub-agents per axis
  ↓
Stage 2.1 (Reconciliation) — conditional: ≥2 axes returned sources
  ↓
Stage 2.2 (PRESS Review) — conditional: web axis active
  ↓
Stage 2.5 (Persistence) — conditional: persist_sources == true
  ↓
Stage 3   (Source Verification)
  ↓
Stage 3.5 (Deep Source Reading) — conditional: deep_reading != false
  ↓
Stage 4   (Synthesis)
  ↓
Stage 4.5 (Devil's Advocate Checkpoint)
  ↓
Stage 4.6 (Stakeholder Review) — conditional: stakeholder_review == true
  ↓
Stage 5   (Terminal Report)
  ↓
Close     (Verification — 22 gates)
```

**Checklist ID notes:**
- `id=14` is used for: Stage 1.7 (Open-Source Decision) and Close Verification. These run at opposite ends of the pipeline — Stage 1.7 sets it to `completed` early, Close reopens it as `in_progress` then `completed`. The dual-use is intentional to keep the checklist at 15 items.
- `id=15` is used for Stage 2.6 (Code Reference Extraction), an inline sub-step of Stage 2.

---

## Multi-RQ Batch Mode

When the user provides multiple research questions (e.g., "pesquise todas as áreas de ideias.md"),
the orchestrator can run them sequentially in batch mode:

1. **Extract RQ list:** Parse user input for multiple RQs, or read from a file.
2. **For each RQ in the list:**
   a. Run the full pipeline (Stages 1-5 + Close) independently.
   b. Each RQ produces its own session directory: `{output_dir}/{date}-{slug(rq)}/`.
   c. **After every 3 RQs (or when context indicator ≥ 60%):** Request `/compact` + "continue deep research batch". Never run >3 RQs without context reset. See anti-pattern #16.
   d. **After each RQ completes AND passes Close gates:** Verify output files exist via `list_dir`, THEN write batch manifest entry. Never write manifest optimistically before files are confirmed on disk.
3. **On crash mid-batch:** Read `_batch-manifest.json` to determine which RQs completed.
   Resume from the first incomplete RQ. The `.session-state.json` within each session dir
   provides finer-grained intra-RQ recovery.
4. **After all RQs complete:** write `_batch-summary.md` with:
   - Per-RQ verdict, sources used, review type, key findings summary
   - Cross-RQ insights (if RQs overlap in domain)
   - Batch statistics (total sources, total time, gate pass rate)

**Batch manifest format:**
```json
{
  "batch_started": "2026-05-23T00:00:00Z",
  "total_rqs": 3,
  "completed_rqs": 1,
  "rqs": [
    {"slug": "teorias-computacionais-cerebro", "status": "completed", "sources": 23},
    {"slug": "simulacao-uav", "status": "pending"},
    {"slug": "metodologia-nux", "status": "pending"}
  ]
}
```

---

## Context Budget Monitoring

**CRITICAL:** The orchestrator accumulates references, templates, and stage outputs.
To prevent TUI freeze from context overflow:

- **After each stage**, estimate tokens consumed (files read × ~1.3 chars/token for code, ~1.0 for prose).
- **Warning threshold:** ≥ 120K tokens → emit: "⚠ Context pressure: {N}K tokens estimated. Consider `/compact` after this stage."
- **Halt threshold:** ≥ 180K tokens → **PAUSE the pipeline.** Emit: "⛔ Context critical: {N}K tokens. Write session state and request `/compact` + 'continue deep research {slug}'."
- **Stage 3.5 and Stage 4** are the highest-risk stages for context overflow. Monitor especially after deep reading.
- **After `/compact`:** Read MANIFEST.txt and `.session-state.json`. Skip completed stages. Resume from current stage.

---

## Crash Recovery

If the orchestrator process dies mid-pipeline, the session can be resumed by
reading `.session-state.json` in the session directory:

1. Read state: `code_execution` → `helpers.read_session_state("{session_dir}")`
2. Get resume point: `helpers.get_resume_stage("{session_dir}")` returns (stage, checklist_item)
3. Skip completed stages. Resume from the returned stage.
4. On successful resume: delete `.session-state.json` at Close.

**State is written automatically** at the end of every stage (see steps below).
No manual intervention needed for normal execution.

---

## Stage 1: RQ Formulation

> SKILL.md slim header has: Who, Output, Template, Config vars, References.
> This section has the numbered steps.

> **Idempotency rule (all stages):** Before executing any stage, check if its primary
> output file already exists and is non-empty. If yes: `checklist_update(id=N, status="completed")`
> and skip to the next stage. This makes resume safe and prevents overwriting completed work.
> To force re-execution: delete the output file before starting the stage.

1. Load config:
   a. Check for `.deepseek/deepseek-research.toml` in project root: `read_file(".deepseek/deepseek-research.toml")`.
   b. If absent: auto-bootstrap via `exec_shell(command: "python3 {SKILL_DIR}/scripts/bootstrap_config.py")`. This detects available axes and writes a config file.
   c. If present: parse with `read_file` and extract variables. Load reference: `read_file("{SKILL_DIR}/references/configuration.md")` for variable descriptions.
   d. Note active variables: `output_dir`, `bibliography_path`, `persist_sources`, `source_axes`, `deep_reading`, `agreement_threshold`, `living_review`.
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
     {"content": "Stage 5: Terminal Report", "status": "pending"},
     {"content": "Stage 1.7: Open-Source Decision + Close", "status": "pending"},
     {"content": "Stage 2.6: Code Reference Extraction", "status": "pending"}
   ])
   ```
   Use `checklist_update(id, status)` for all subsequent updates — never `checklist_write` again.
4. Load template: `read_file("{SKILL_DIR}/templates/rq-brief.md")`.
4a. **Auto-resolve placeholders:** Use `code_execution` to call `helpers.resolve_placeholders(template_text, skill_dir="{SKILL_DIR}", session_slug="{date}-{slug}")`. This replaces `{iso8601_utc}`, `{date}`, `{skill_git_hash}`, `{slug}` automatically. Placeholders requiring stage output (`{RQ_TEXT}`, `{rq_sha256}`) are filled later.
5. Use `request_user_input` to clarify: central question, domains spanned, decisions depending on this research.
6. Generate slug from RQ: lowercase, hyphens, ≤ 50 chars. Example: "Estado da arte em co-kriging?" → `co-kriging-estado-da-arte`.
7. Check prior sessions: `grep_files` in `$SESSION_INDEX` for slug/topic. If found, ask user to extend or start fresh.
   - **Living review trigger:** If `living_review == true` and prior session found for this slug, check update cadence via `code_execution`:
     ```python
     import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
     from living_review import check_update_needed, build_surveillance_queries
     status = check_update_needed(session_dir, surveillance_interval_days={surveillance_interval_days})
     ```
     - If `status["needs_update"] == True`: enter "update mode" — re-run Stage 2 with date-filtered queries from `build_surveillance_queries()`. Append findings to existing report with "Update N" header. Do NOT re-screen previously screened sources.
     - If `status["needs_update"] == False`: inform user session is up to date. STOP.
8. **Classify knowledge type:** Per `references/epistemology.md` §Knowledge Type Taxonomy. Each sub-question gets a classification.
9. **Operationalize concepts:** Per `references/epistemology.md` §Operationalization. Every RQ construct needs observable criteria.
10. **Formulate analysis plan:** Fill the Analysis Plan section — synthesis method, effect size metric, inclusion/exclusion thresholds, saturation rule, sensitivity analyses. Narrative-only RQs mark quantitative entries as "N/A."
11. Apply FINER scoring (threshold: average ≥ 3.0, no criterion < 2).
12. **Declare review type:** Per `references/epistemology.md` §Review Type Declaration.
13. Detect available axes from `source_axes`: bibliography, codebase, web.
14. Fill template completely. Write `01-rq-brief.md`.
15. **Pre-register:** Compute SHA256 of `01-rq-brief.md` via `helpers.compute_sha256()`. Record in file and MANIFEST.txt.
16. `checklist_update(id=1, status="completed")`.
17. **Write session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="1.6", current_checklist_item="2", last_completed_stage="1")`.

> **Global rule:** After every stage's final `checklist_update`, write session state with
> `current_stage` pointing to the next stage and `last_completed_stage` to the current one.
> This enables crash recovery at any pipeline point.

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
6. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="1.7", last_completed_stage="1.6", current_checklist_item=2)`.

---

## Stage 1.7: Open-Source Applicability Decision

> **Who:** Orchestrator (Pro — think carefully about RQ classification)
> **Output:** `01b-opensource-decision.md`
> **Template:** `{SKILL_DIR}/templates/opensource-decision.md`
> **Condition:** Run ALWAYS. Determines whether `opensource` axis should be active.

1. Load template: `read_file("{SKILL_DIR}/templates/opensource-decision.md")`.
2. Load epistemology for knowledge type classification: `read_file("{SKILL_DIR}/references/epistemology.md")` §Knowledge Type Taxonomy.
3. Score the RQ against the 6 criteria in the template:
   - C1: RQ is Procedural or Causal → 3 pts
   - C2: RQ involves benchmarks, performance, latency → 2 pts
   - C3: RQ mentions specific tools, libraries, frameworks → 2 pts
   - C4: RQ is Predictive without established datasets → 1 pt
   - C5: Answer depends on real implementation evidence → 3 pts
   - C6: Known OSS repositories implement the domain → 2 pts
   - **Penalty:** If C6 scores 0, subtract 2 from total.
4. **If score ≥ 6 (RECOMMEND) AND `"opensource"` NOT in `source_axes`:**
   - In YOLO mode: auto-add `"opensource"` to `source_axes`. Record: "Auto-enabled — score {score} ≥ 6."
   - In interactive mode: use `request_user_input` to ask user. Record response.
5. **If score ≥ 6 AND `"opensource"` already in `source_axes`:** No action needed.
6. **If score < 6 (NOT RECOMMENDED):** Record decision. Skip opensource discovery.
7. Fill template. `checklist_update(id=14, status="completed")`.
8. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="1.5", last_completed_stage="1.7", current_checklist_item=3)`.

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
7. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="2", last_completed_stage="1.5", current_checklist_item=4)`.

---

## Stage 2: Source Discovery

> SKILL.md slim header has: Who, Output, Template.

1. Load template: `read_file("{SKILL_DIR}/templates/source-inventory.md")`.
2. Extract keywords from `01-rq-brief.md`: use `code_execution` with Python, never shell interpolation.
2a. **Extract short topic names for negative queries:** Use `code_execution` to extract 3-6 short topic names (1-5 words each, lowercase, e.g. "thousand brain theory", "free energy principle") from the RQ. Pass as `topics="topic1,topic2,..."` to `build_subagent_prompt` for web, opensource, and grey axes. This enables per-topic negative queries instead of one giant blob.
3. Identify active axes from `source_axes`. For each active axis, dispatch sub-agents.
4. **Bibliography dispatch:** load sub-agent prompt spec from `references/subagent-prompts.md`. Use `helpers.build_subagent_prompt('dsr-bibliography', ...)`.
5. **Web dispatch:** load sub-agent prompt spec. Use `helpers.build_subagent_prompt('dsr-web', ...)`.
6. **Code dispatch:** load sub-agent prompt spec. Use `helpers.build_subagent_prompt('dsr-code', ...)`.
7. **Opensource dispatch (conditional):** If `"opensource"` in `source_axes`, load sub-agent prompt spec. Use `helpers.build_subagent_prompt('dsr-opensource', rq_text='{RQ_TEXT}', main_topic='{main_topic}')`.
8. **Grey literature dispatch (conditional):** If `"grey"` in `source_axes`, load sub-agent prompt spec from `references/subagent-prompts.md` §Stage 2: dsr-grey. Use `helpers.build_subagent_prompt('dsr-grey', rq_text='{RQ_TEXT}', main_topic='{main_topic}', topics='{topics}')`. Grey literature targets: arxiv, techrxiv, ProQuest, Google Scholar, institutional repositories. Stricter relevance threshold: ≥4 to include.
9. **Parallel dispatch:** all sub-agents in one turn.
10. Wait for all sub-agents: `agent_eval(agent_id="...", block=true, timeout_ms=180000)` for each.
   **CRITICAL:** Always use `timeout_ms=180000` (3 min). If a sub-agent times out:
   - Read its output file if available (`/tmp/dsr-web-results.md`, `/tmp/dsr-opensource-results.md`, `/tmp/dsr-grey-results.md`).
   - Re-dispatch ONCE with reduced scope (fewer queries). If still times out, mark axis DEGRADED.
   - Continue with successful axes. Never block indefinitely.
10a. **Read sub-agent output files:** After each sub-agent completes, read the full results:
    - Web axis: `read_file("/tmp/dsr-web-results.md")`
    - Code axis: `read_file("/tmp/dsr-code-results.md")`
- Opensource axis: `read_file("/tmp/dsr-opensource-results.md")`
     - Grey axis: `read_file("/tmp/dsr-grey-results.md")`
     - Bibliography axis: the persistence_manifest JSON block in the sub-agent response
    - These files contain the COMPLETE source tables (sub-agent inline responses may be truncated).
11. **Code Reference Extraction (conditional):** If `"bibliography"` in `source_axes` OR `"web"` in `source_axes`:
   a. Scan sub-agent outputs for repository URL patterns (github.com, gitlab.com, crates.io, pypi.org, npmjs.com, or "available at"/"code:"/"repository:" mentions).
   b. For each URL found: verify accessibility via `fetch_url`, classify relevance (1-5), record source of origin.
   c. Append code references to the source list before deduplication.
   d. `checklist_update(id=15, status="completed")`.
12. Merge all `returned_sources` + code references with dedup_by_url. `checklist_update(id=4, status="completed")`.
13. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="2.1", last_completed_stage="2", current_checklist_item=5)`.

---

## Stage 2.1: Reconciliation

> SKILL.md slim header has: Who, Output, Condition.

**Condition:** Run ONLY if `source_axes` has ≥2 axes that returned sources.

1. Identify disagreements (one axis included a source another excluded). Extract source metadata.
2. For each disagreement, dispatch tiebreak sub-agent.
3. Load tiebreak spec from `references/subagent-prompts.md`. `helpers.build_subagent_prompt('dsr-tiebreak', ...)`.
4. Wait for tiebreak sub-agents: `agent_eval(agent_id="...", block=true, timeout_ms=120000)` for each.
   On timeout: mark disagreement as UNRESOLVED, default to INCLUDE (inclusive screening).
5. Build reconciliation matrix: agreement %, counts. If κ < `agreement_threshold`: WARNING. `checklist_update(id=5, status="completed")`.
6. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="2.2", last_completed_stage="2.1", current_checklist_item=6)`.

---

## Stage 2.2: PRESS Review

> SKILL.md slim header has: Who, Output, Template.

1. Load PRESS checklist: `read_file("{SKILL_DIR}/references/press-checklist.md")`.
2. For each web search query in `02-source-inventory.md`, evaluate: translation, operators, coverage, specificity, sensitivity. Rate ADEQUATE / INADEQUATE.
3. Re-run rule: if ≥2 elements INADEQUATE for any query, re-run search with corrected query.
4. Write PRESS Review section to `02-source-inventory.md` (append).
5. `checklist_update(id=6, status="completed")`.
6. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="2.5", last_completed_stage="2.2", current_checklist_item=7)`.

---

## Stage 2.5: Persistence

> SKILL.md slim header has: Who, Output, Condition, Config vars.

**Condition:** Run ONLY if `persist_sources == true`.

1. Load index script: `code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import index_new, dedup_local; ...")`.
2. Index new sources: `index_new(bibliography_path, new_sources)`.
3. Process reused_local: update sessions_used for each.
4. Emit summary: "Corpus updated: {N} new, {M} reused."
5. `checklist_update(id=7, status="completed")`.
6. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="3", last_completed_stage="2.5", current_checklist_item=8)`.

---

## Stage 3: Source Verification

> SKILL.md slim header has: Who, Output, Template.

1. Load template: `read_file("{SKILL_DIR}/templates/source-verification.md")`.
1a. **Auto-resolve placeholders:** Use `code_execution` to call `helpers.resolve_placeholders(template_text, skill_dir="{SKILL_DIR}", session_slug="{date}-{slug}")`.
2. For each source from Stage 2 inventory: fetch header or first 2KB to verify accessibility.
2a. **Cross-check title against fetched content.** For each source, extract the `<title>` or first heading from the fetched content. Compare against the Stage 2 title using fuzzy matching (`difflib.SequenceMatcher` or equivalent). If similarity < 0.5: flag the source as "⚠ TITLE MISMATCH — possible hallucinated source." Re-dispatch discovery sub-agent for a replacement source. If similarity ≥ 0.5 but < 0.8: flag as "⚠ TITLE DRIFT — verify manually."
3. Classify as ACCESSIBLE / INACCESSIBLE / PARTIAL (paywall, truncated).
4. Classify source type: primary / secondary / tertiary (per epistemology §Primary vs Secondary).
5. Load risk-of-bias: `read_file("{SKILL_DIR}/references/risk-of-bias.md")`.
6. For each ACCESSIBLE source, assess RoB across 5 domains. Assign overall rating.
7. Apply RoB → Evidence Strength modifier.
8. If >20 sources: use RLM with `sub_query_batch(dependency_mode="independent")`.
9. **Prepare for deep reading.** If `deep_reading != false`:
   a. Load deep reading reference: `read_file("{SKILL_DIR}/references/deep-reading.md")`.
   b. For each source, collect metadata: source_id, source_path_or_url, source_title. Estimate document tier.
      - **T5 (Source code):** Assign to opensource repositories and code_ref sources. Deep reading will clone to `./oss/` and grep for RQ patterns.
   c. Record in `03-source-verification.md` under `## Deep Read Queue`.
   d. If `deep_reading == false` or source is UNVERIFIABLE: mark as "deep reading skipped."
9a. **Publication bias assessment (conditional):** If ≥5 sources from web or bibliography axes:
     a. **Source diversity check:** Count unique author groups/institutions. Compute `same_group_pct = (sources from dominant group / total) * 100`. Flag if ≥50%.
     b. **Result distribution:** Count positive vs. negative/null results. Flag if negative/null < 20% of total.
     c. **Funnel plot text description:** If ≥5 sources report same effect with variance, describe symmetry (e.g., "symmetric around pooled estimate" or "asymmetric — fewer small/negative studies").
     d. Record findings under `## Publication Bias Assessment` in `03-source-verification.md`.
10. Fill template. `checklist_update(id=8, status="completed")`.
11. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="3.5", last_completed_stage="3", current_checklist_item=9)`.

---

## Stage 3.5: Deep Source Reading

> SKILL.md slim header has: Who, Output, Template, Condition, Config vars.

**Condition:** Skip if `deep_reading == false` OR 0 sources after Stage 2. For individual sources marked UNVERIFIABLE, skip deep reading for that source.

1. Load deep reading methodology: `read_file("{SKILL_DIR}/references/deep-reading.md")`.
2. Load sub-agent prompt spec: `read_file("{SKILL_DIR}/references/subagent-prompts.md")` §Stage 3.5.

### Priority Queue (guarantees most important sources are deep-read first)

3. Build the deep read queue from Stage 3 output (`03-source-verification.md` §Deep Read Queue).
3a. **Sort by priority.** Assign each source a priority class and sort ascending:
    - **P1 (answers SQ directly):** Source directly answers a specific sub-question (e.g., S6 directly challenges CBH evidence → SQ2). Re-rank to the top.
    - **P2 (cross-theory comparison):** Source compares multiple theories (e.g., S4 compares FEP+PP).
    - **P3 (primary empirical):** High-tier primary source with peer-reviewed empirical data (e.g., S8 in Nature Neuroscience).
    - **P4 (review/secondary):** Review papers, book chapters, secondary synthesis.
    - **P5 (code reference):** T5 source code repositories (OSS repos).
    Sources at the same priority tie-break by relevance score (5 > 4 > 3).
3b. **Record priority in queue.** Add a `Priority` column to the Deep Read Queue table in `03-source-verification.md`.

### Parallel dispatch with batch cap

4. **Calculate batch size.** MAX_CONCURRENT = 5 (hard cap to avoid dispatcher overload). If total sources > MAX_CONCURRENT, split into batches of MAX_CONCURRENT.
5. **Batch loop:** For each batch:
    a. **T5 sources in batch:** If batch contains T5 (source code) sources:
       - Pre-flight check: verify repo accessible (`fetch_url` for repo URL).
       - If already cloned (`oss/{org}_{repo}/` exists with .git): `git pull`, record new HEAD.
       - If not cloned: note in sub-agent prompt that git clone is needed.
       - Dispatch: `agent_open(name="dr-t5-{source_id}", model="deepseek-v4-pro", allowed_tools=[...], prompt=build_subagent_prompt('dsr-deep-read-t5', ...))`.
    b. **Non-T5 sources in batch:** Dispatch: `agent_open(name="dr-{source_id}", model="deepseek-v4-pro", allowed_tools=[...], prompt=build_subagent_prompt('dsr-deep-read', ...))`.
    c. **Wait for batch:** `agent_eval(agent_id="...", block=true, timeout_ms=300000)` for each sub-agent in this batch.
       **CRITICAL:** Deep reading can take 2-5 min per source. Use `timeout_ms=300000` (5 min).
       On timeout: mark source as FAILED in consolidation. Re-dispatch ONCE with reduced scope.
       If still times out: record "deep-read failed — timeout" in `_consolidation.md` and continue.
    d. **Batch checkpoint:** Write `_consolidation.md` partial update after each batch completes. This ensures progress is preserved even if later batches fail.
       ```python
       code_execution → helpers.write_session_state("{session_dir}", deep_read_batch_progress="batch {N}/{total}", pending_sources=[...])
       ```
6. After all batches complete: final consolidation.
7. Validate outputs: each `{session_dir}/deep-reads/{source_id}.md` must exist with `## Extracted Claims` section. Missing outputs → re-dispatch individually or mark as FAILED.
8. Consolidate: count by status (COMPREHENSIVE/PARTIAL/MINIMAL/INACCESSIBLE/FAILED). Summarize claims by grade (V/P/I/M/E). Write final `_consolidation.md`.
9. `checklist_update(id=9, status="completed")`.
10. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="4", last_completed_stage="3.5", current_checklist_item=10)`.

---

## Stage 4: Synthesis

> SKILL.md slim header has: Who, Output, Template.

1. Load template: `read_file("{SKILL_DIR}/templates/synthesis.md")`.
1a. **Auto-resolve placeholders:** Use `code_execution` to call `helpers.resolve_placeholders(template_text, skill_dir="{SKILL_DIR}", session_slug="{date}-{slug}")`.
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
8a. **Sensitivity analysis (conditional):** If meta-analysis ran AND ≥3 sources:
     a. **Leave-one-out:** Recompute pooled estimate excluding each study in turn. Use `code_execution`:
        ```python
        import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
        from meta_analysis import sensitivity_leave_one_out
        loo = sensitivity_leave_one_out(effects, variances)
        # Report: which study has largest influence? Does exclusion change conclusion?
        ```
     b. **Fail-safe N:** Compute Rosenthal's fail-safe N. Use `code_execution`:
        ```python
        from meta_analysis import fail_safe_n
        fsn = fail_safe_n(effects, variances)
        # Report: how many null studies needed to nullify the finding?
        ```
     c. **Report threshold:** Flag when any exclusion changes the pooled estimate by >50% OR changes significance (CI crosses zero) OR fail-safe N < 5.
9. Apply GRADE framework: load `references/grade-framework.md` for overall certainty rating. For each K-finding, compute certainty via `code_execution`:
    ```python
    import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
    from grade import rate_certainty
    result = rate_certainty(
        finding_id="K{n}",
        study_designs=[...],  # per contributing source
        rob_scores=[...],     # from Stage 3 RoB assessment
        i2=meta_i2,           # from meta-analysis (0 if qualitative)
        indirectness="direct",
    )
    print(json.dumps(result))
    ```
    Record `final_symbol`, `final_certainty`, and `rationale` in the synthesis for each K-finding.
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
16. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="4.5", last_completed_stage="4", current_checklist_item=11)`.

---

## Stage 4.5: Devil's Advocate Checkpoint

> SKILL.md slim header has: Who, Output, Template.

1. Load Devil's Advocate spec: `read_file("{SKILL_DIR}/references/subagent-prompts.md")` §Stage 4.5.
2. Build prompt: `helpers.build_subagent_prompt('dsr-da', ...)`.
3. Dispatch sub-agent: `agent_open(name="dsr-da", model="deepseek-v4-pro", ...)`.
4. Wait: `agent_eval(agent_id="...", block=true, timeout_ms=180000)`.
   **CRITICAL:** Devil's Advocate review can take 1-3 min. Use `timeout_ms=180000` (3 min).
   On timeout: orchestrator applies Devil's Advocate checklist inline against `04-synthesis.md`.
5. Read output: `read_file("{session_dir}/04a-devils-advocate.md")`.
6. Apply corrections to `04-synthesis.md`. Sub-agent NEVER modifies `04-synthesis.md` directly. `checklist_update(id=11, status="completed")`.
7. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="4.6", last_completed_stage="4.5", current_checklist_item=12)`.

---

## Stage 4.6: Stakeholder Review

> SKILL.md slim header has: Who, Output, Template, Condition.

**Condition:** If `stakeholder_review == true`, run this stage using `request_user_input` to present findings and collect feedback.

1. Present summary of key findings to user via `request_user_input` with three options: ACCEPT, REVISE, or FLAG.
2. For each REVISE: ask what specific revision is needed.
3. Document feedback and actions taken in the template.
4. Apply feedback to `04-synthesis.md` before Stage 5.
5. `checklist_update(id=12, status="completed")`.
6. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="5", last_completed_stage="4.6", current_checklist_item=13)`.

---

## Stage 5: Terminal Report

> SKILL.md slim header has: Who, Output, Template.

1. Load report template: `read_file("{SKILL_DIR}/templates/report.md")`.
1a. **Auto-resolve placeholders:** Use `code_execution` to call `helpers.resolve_placeholders(template_text, skill_dir="{SKILL_DIR}", session_slug="{date}-{slug}")`.
2. Convert synthesis to final report format.
3. Append Epistemic Limitations: `read_file("{SKILL_DIR}/references/epistemic-limitations.md")` §Report Integration.
4. Append data supplement if numerical data was extracted. `read_file("{SKILL_DIR}/templates/data-supplement.json")`.
5. No knowledge entity creation. Report is the final artifact.
6. `checklist_update(id=13, status="completed")`.
7. **Session state:** `code_execution` → `helpers.write_session_state("{session_dir}", current_stage="close", last_completed_stage="5", current_checklist_item=14)`.

---

## Close: Verification

> SKILL.md slim header references this section for executable gate commands.

### Auto-Run Procedure

The orchestrator MUST execute all 22 gates systematically — never skip this stage.
Gates verify structural completeness, not truth (see `references/epistemic-limitations.md` §L2).

1. `checklist_update(id=14, status="in_progress")`.
2. For each gate GATE-1 through GATE-22:
   a. Execute the gate command(s) described below.
   b. Record result: PASS / FAIL / WARNING / UNVERIFIABLE / SKIP.
   c. If FAIL on a blocking gate (GATE-1, GATE-2, GATE-3, GATE-5, GATE-8, GATE-16, GATE-20, GATE-21, GATE-22):
      - Document the failure reason.
      - Attempt resolution (e.g., missing file → write it; bare claim → qualify it).
      - Re-run the gate after resolution.
   d. Append result to MANIFEST.txt under `## Gate Results`.
3. After all gates: write final MANIFEST.txt with SHA256 of each output file.
4. Cleanup temporary artifacts (see Cleanup section below).
5. Delete `.session-state.json` (crash recovery no longer needed).
6. `checklist_update(id=14, status="completed")`.

### Gate Results Format (in MANIFEST.txt)

```
## Gate Results
| Gate | Result | Notes |
|------|--------|-------|
| GATE-1 | PASS | All expected output files present |
| GATE-2 | PASS | Session recorded in index |
| GATE-3 | PASS | 0 bare claims (2 false positives cleared) |
| ... | ... | ... |
```

### Gate Details

Each gate is a structural integrity check. Gates verify form, not truth —
see `references/epistemic-limitations.md` §L2.
Emit PASS/FAIL/WARNING/UNVERIFIABLE per gate. GATE-1/2/3/5/8/16 failures must be resolved.

**GATE-1 — File integrity.** Verify expected files exist and are non-empty:
```
export PERSIST_SOURCES="{persist_sources}"
export PROTOCOL_REGISTRY="{protocol_registry}"
export STAKEHOLDER_REVIEW="{stakeholder_review}"
SESSION_DIR="{output_dir}/{date}-{slug}"
expected="01-rq-brief.md 01b-opensource-decision.md MANIFEST.txt"
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
Must return match. Count PRISMA line items present: each line not "n = 0" counts as 1. Total expected: 20 items (bibliography, web, codebase, opensource, code_refs, grey, and their associated counts). WARNING if < 80%; FAIL if < 50%.
```
grep_files(pattern="PRESS Review", path="{session_dir}/02-source-inventory.md")
```
Must return match. FAIL if absent.

**GATE-9 — Risk of Bias completeness.**
```
grep_files(pattern="Overall RoB", path="{session_dir}/03-source-verification.md")
```
Count matches. Expected count = number of sources in inventory (including opensource repositories and code_refs). FAIL if mismatch.
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

**GATE-14 — Sensitivity flagging.** If meta-analysis ran (Step 8a executed):
```
grep_files(pattern="Leave-one-out", path="{session_dir}/04-synthesis.md")
```
Must return match if ≥3 studies with variance data. FAIL if absent for ≥5 studies; WARNING if absent for 3-4.
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

**GATE-20 — Placeholder resolution.** Verify no unresolved placeholders remain in output files:
```
grep_files(pattern="SKILL_DIR_HASH|\\\\{SKILL_DIR\\\\}|\\\\{output_dir\\\\}|\\\\{date\\\\}|T00:00:00Z|\\\\(Placeholder\\\\)", path="{session_dir}/", include=["*.md", "*.json"])
```
Must return 0 matches. FAIL if any unresolved placeholders found.
Re-check after resolution: re-run the grep. Only PASS when all placeholders are resolved.

**GATE-21 — Minimum file count for completed status.**
A session claiming "completed" or "complete" must have at minimum these 7 core files present and non-empty:
- `01-rq-brief.md`
- `02-source-inventory.md` (or documented reason for absence)
- `04-synthesis.md`
- `04a-devils-advocate.md`
- `05-report.md`
- `05-plain-summary.md`
- `05-decision-brief.md`
```
for f in 01-rq-brief.md 02-source-inventory.md 04-synthesis.md 04a-devils-advocate.md 05-report.md 05-plain-summary.md 05-decision-brief.md; do
  [ -s "{session_dir}/$f" ] || echo "FAIL: $f missing or empty"
done
```
FAIL if any core file is missing. If FAIL: change MANIFEST status from "complete"/"completed" to "INCOMPLETE — {N} core files missing."
Sessions with < 5 files: mark as "DEGRADED — pipeline truncated."

**GATE-22 — Deep reading enforcement.** If `deep_reading != false`:
```
[ -f "{session_dir}/deep-reads/_consolidation.md" ] || echo "FAIL: deep-reads/_consolidation.md missing"
[ -s "{session_dir}/deep-reads/_consolidation.md" ] || echo "FAIL: deep-reads/_consolidation.md empty"
```
Must find at least one `{session_dir}/deep-reads/S*.md` file:
```
ls "{session_dir}/deep-reads/"S*.md 2>/dev/null | head -1 || echo "FAIL: no source deep-read files found"
```
FAIL if deep reading was configured but no output exists. WARNING if `_consolidation.md` exists but all sources marked FAILED/INACCESSIBLE.
If `deep_reading == false`: SKIP.
If no sources survived to Stage 3.5 (0 sources): SKIP with note "no sources to deep-read."

**GATE-23 — Publication bias flagged.** If sources ≥ 5:
```
grep_files(pattern="Publication Bias Assessment", path="{session_dir}/03-source-verification.md")
```
Must return match. FAIL if absent and sources ≥ 5 (publication bias assessment is mandatory for adequate source sets).
If sources < 5: SKIP.

---

**Cleanup note:** Temporary repository clones in `{oss_clone_dir}` are removed during Close (see Close: Verification §Auto-Run Procedure step 4). They persist only if `persist_sources == true`.