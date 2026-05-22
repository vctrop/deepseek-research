---
name: deepseek-research
description: Multi-source research pipeline with adversarial review. RQ formulation → discovery → verification → synthesis → Devil's Advocate → report. Triggered by "deep research X", "/deep-research Z", "investigate deeply Y", "foundational research W".
---

# deepseek-research

Deep multi-source research pipeline: 5 stages + adversarial checkpoint + 7 verification gates.
Corpus vivo: web-discovered sources are persisted and reused cross-session.
Generic — no project-specific infrastructure dependencies.

## Allowed tools

**Orchestrator (all inline stages):**
`request_user_input`, `agent_open`, `agent_eval`, `handle_read`, `rlm_open`, `rlm_eval`, `rlm_configure`, `rlm_close`, `grep_files`, `read_file`, `write_file`, `exec_shell`, `web_search`, `fetch_url`, `checklist_write`, `checklist_update`, `validate_data`, `code_execution`

**Stage 2 sub-agents (discovery):**
`web_search`, `fetch_url`, `grep_files`, `read_file`, `file_search`, `rlm_open`, `rlm_eval`, `rlm_close`, `write_file`

**Stage 4.5 sub-agent (Devil's Advocate):**
`read_file`, `write_file`

---

## Assumptions

- Orchestrator is **DeepSeek V4 Pro**. Sub-agents use **Flash** for discovery, **Pro** for Devil's Advocate.
- `request_user_input` only works in the orchestrator (parent) context — never from sub-agents.
- Internet access expected for web axis. Offline degrades gracefully (see `references/error-recovery.md`).
- **Variable interpolation:** Placeholders in braces (`{output_dir}`, `{date}-{slug}`, `{RQ}`, `{bibliography_path}`, `{session_dir}`, `{SKILL_DIR}`, `{session_index}`) must be interpolated by the orchestrator from config or Stage 1 output.
- `{SKILL_DIR}` resolves to `~/.deepseek/skills/deepseek-research/`.

---

## Quick Reference

| Resource | Path | When to load |
|----------|------|--------------|
| Configuration | `references/configuration.md` | Stage 1 |
| Epistemology (evidence matrix, knowledge types, saturation, negative search) | `references/epistemology.md` | Stages 1, 3, 4 |
| IRON RULE C (qualified language) | `references/iron-rule-c.md` | Stages 4, 5, Close |
| Anti-patterns | `references/anti-patterns.md` | Pipeline start |
| Error recovery | `references/error-recovery.md` | On error |
| Model matrix + thinking budget | `references/model-matrix.md` | Pipeline start |
| Context budget + RLM thresholds | `references/context-budget.md` | Continuous |
| Sub-agent prompts (Stage 2, Stage 4.5) | `references/subagent-prompts.md` | Stages 2, 4.5 |
| Python helpers (SHA256, index ops, prompt builder) | `scripts/helpers.py` | Stages 1, 1.5, 2, 2.5, 5 |
| PRESS search strategy peer review | `references/press-checklist.md` | Stage 2.2 |
| Risk of Bias assessment | `references/risk-of-bias.md` | Stage 3 |
| Protocol registry (OSF/local) | `scripts/protocol_registry.py` | Stage 1.6 |

**Templates** live in `{SKILL_DIR}/templates/`. Load with `read_file` at the start of each stage. Never inline template content in SKILL.md.

---

## Pipeline

### Stage 1: Research Question Formulation

**Who:** Orchestrator (Pro — think carefully about RQ structure, FINER, and knowledge type classification)
**Output:** `{output_dir}/{date}-{slug}/01-rq-brief.md`
**Template:** `{SKILL_DIR}/templates/rq-brief.md`

1. Load config: `read_file("{SKILL_DIR}/references/configuration.md")` → parse `.deepseek/deepseek-research.toml` or use defaults.
2. Load epistemology: `read_file("{SKILL_DIR}/references/epistemology.md")` (focus on §Knowledge Type Taxonomy and §Review Type Declaration).
3. Create checkpoint checklist:
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
     {"content": "Stage 4: Synthesis", "status": "pending"},
     {"content": "Stage 4.5: Devil's Advocate", "status": "pending"},
     {"content": "Stage 5: Terminal Report + Close", "status": "pending"}
   ])
   ```
   Use `checklist_update(id, status)` for all subsequent updates — never `checklist_write` again.
4. Load template: `read_file("{SKILL_DIR}/templates/rq-brief.md")`.
5. Use `request_user_input` to clarify: central question, domains spanned, decisions depending on this research.
6. Generate slug from RQ: lowercase, hyphens, ≤ 50 chars. Example: "Estado da arte em co-kriging?" → `co-kriging-estado-da-arte`.
7. Check prior sessions: `grep_files` in `$SESSION_INDEX` for slug/topic. If found, ask user to extend or start fresh.
8. **Classify knowledge type:** Per `references/epistemology.md` §Knowledge Type Taxonomy. Each sub-question gets a classification. This determines what counts as valid evidence.
9. **Operationalize concepts:** Per `references/epistemology.md` §Operationalization. Every RQ construct needs observable criteria. Flag unoperationalizable constructs as limitations.
10. Apply FINER scoring (threshold: average ≥ 3.0, no criterion < 2).
11. **Declare review type:** Per `references/epistemology.md` §Review Type Declaration.
12. Detect available axes from `source_axes`:
    - `bibliography`: verify `bibliography_path` exists
    - `codebase`: always available
    - `web`: try `web_search("test")` — if fails, mark "web unavailable", continue offline
13. Fill template completely. Write `01-rq-brief.md`.
14. **Pre-register:** Compute SHA256 via `helpers.py`:
    ```
    code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_sha256; print(compute_sha256('{session_dir}/01-rq-brief.md'))")
    ```
    Record digest in the file and in `MANIFEST.txt`.
15. `checklist_update(id=1, status="completed")`.

---

### Stage 1.6: Protocol Finalize

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** Protocol registration record in `{output_dir}/{date}-{slug}/protocol-registration.json`

**Condition:** If `protocol_registry == "none"`: skip — proceed to Stage 1.5.

1. Build protocol dict from `01-rq-brief.md` content:
   - title = RQ text (first 200 chars)
   - description = scope + operational definitions
   - category = "analysis" (engineering research)
   - questions = FINER criteria as Q&A, sub-questions as Q&A, review type declaration
2. If `protocol_registry == "osf"`:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from protocol_registry import register_protocol; import json; result = register_protocol('{osf_token}', '{osf_project_id}', {protocol_dict}); print(json.dumps(result))")
   ```
   Record DOI URL in `MANIFEST.txt`.
3. If `protocol_registry == "local"` or OSF fails:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from protocol_registry import register_local; import json; result = register_local({protocol_dict}, '{session_dir}/protocol-registration.json'); print(json.dumps(result))")
   ```
4. Record registration method and identifier in `MANIFEST.txt`.
5. `checklist_update(id=2, status="completed")`.

---

### Stage 1.5: Local Corpus Triage

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** `{output_dir}/{date}-{slug}/01a-local-corpus-triage.md`
**Template:** `{SKILL_DIR}/templates/local-corpus-triage.md`

**Condition:** Run ONLY if `"bibliography"` is in `source_axes` AND `persist_sources == true`. Otherwise skip — `checklist_update(id=3, status="completed")` and proceed to Stage 2.

1. Load template: `read_file("{SKILL_DIR}/templates/local-corpus-triage.md")`.
2. Initialize index if needed (idempotent):
   ```
   exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py init --base-dir {bibliography_path}")
   ```
3. Scan for unindexed files. If found, emit warning with count.
4. Extract keywords from RQ + sub-questions. Query via `helpers.py` (no shell interpolation):
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import query_index; import json; print(json.dumps(query_index('{SKILL_DIR}', '{bibliography_path}', '{comma_separated_keywords}', 20)))")
   ```
   **Never interpolate keywords directly into `exec_shell` — shell injection risk (anti-pattern #11).**
5. LLM relevance judgment for each candidate (relevance ≥ 3 → `local_sources`).
6. Fill template. `checklist_update(id=3, status="completed")`.

---

### Stage 2: Source Discovery (parallel)

**Who:** 1-2 sub-agents per available axis (Flash — minimal thinking)
**Output:** `{output_dir}/{date}-{slug}/02-source-inventory.md`
**Template:** `{SKILL_DIR}/templates/source-inventory.md`

1. Load epistemology: `read_file("{SKILL_DIR}/references/epistemology.md", start_line=<Negative Search section>)`.
2. Load sub-agent prompts: `read_file("{SKILL_DIR}/references/subagent-prompts.md")`.
3. **Check `dual_screening` config.** If `true` AND bibliography axis active:
   - Dispatch **two** bibliography sub-agents (`dsr-bib-1`, `dsr-bib-2`) with identical prompts but note in prompt: "You are Rater {1/2}. Screen independently."
   - Otherwise: dispatch single `dsr-bibliography` (backward compatible).
4. Dispatch remaining sub-agents in **one turn**:
   - `dsr-web` (if web axis available)
   - `dsr-code` (always)
   Interpolate `{RQ_TEXT}`, `{bibliography_path}`, `{main_topic}`, `{LOCAL_SOURCES_BLOCK}`, `{local_sources_json}` before dispatch.

4. RLM for large bibliography: if `bibliography_path` > 10KB, use `rlm_open`/`rlm_eval`/`rlm_close` instead of `read_file`. See `references/context-budget.md` §RLM Usage Thresholds.

5. Wait for all sub-agents: `agent_eval(agent_id="...", block=true)` for each.

6. **Validate outputs:** each sub-agent must return a Markdown table. If free-text, re-run with format instruction.

7. **Consolidate + PRISMA:** merge tables, assign sequential IDs (S1, S2, ...), remove exact duplicates. Populate the PRISMA flow diagram in the template:
   - `{BIB_COUNT}`, `{WEB_COUNT}`, `{CODE_COUNT}` from axis sub-agent output counts
   - `{TOTAL}` = sum; `{DEDUPED}` = after duplicate removal
   - `{EXCLUDED_IRRELEVANT}` = sources with relevance < 2 (title/abstract irrelevant)
   - `{FULL_TEXT}` = sources assessed in detail; `{INCLUDED}` = sources passing Stage 3 verification
   - `{QUANT}` / `{QUAL}` = estimated from RQ knowledge type
   - `{N_REASON_1..3}` = counted from excluded sources with reasons
   - Write `02-source-inventory.md` using the template.

8. **Empty result:** if 0 sources across all axes → diagnostic in `02-source-inventory.md`, skip Stages 2.2, 2.5 and 3. Stage 4 → "insufficient evidence".

9. `checklist_update(id=4, status="completed")`.

---

### Stage 2.1: Reconciliation (dual screening only)

**Condition:** Run ONLY if `dual_screening == true`. Otherwise skip — proceed to Stage 2.2.

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** Screening Reliability section in `{output_dir}/{date}-{slug}/02-source-inventory.md`

1. Compare `dsr-bib-1` and `dsr-bib-2` outputs:
   a. Extract included source IDs from each.
   b. Sources both include → auto-include.
   c. Sources both exclude → auto-exclude.
   d. Disagreements → build disagreement list.
2. Compute inter-rater reliability via `code_execution`:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_cohens_kappa; import json; print(json.dumps(compute_cohens_kappa({rater1_ids}, {rater2_ids}, {all_ids})))")
   ```
3. If disagreements exist AND `agreement_threshold` is set:
   a. Dispatch tiebreak sub-agent: `dsr-tiebreak` (see `references/subagent-prompts.md` §Stage 2.1).
   b. Adopt tiebreak decisions.
   c. Recompute κ after tiebreak.
4. Write Screening Reliability section to `02-source-inventory.md`:
   - κ value with interpretation (Poor/Slight/Fair/Moderate/Substantial/Almost perfect)
   - Agreement %, counts (agree-include, agree-exclude, disagree)
   - If κ < `agreement_threshold`: WARNING — "Inter-rater reliability below threshold ({threshold}). Review screening criteria."
5. `checklist_update(id=5, status="completed")`.

---

### Stage 2.2: PRESS Review

**Who:** Orchestrator (Pro — moderate thinking)
**Output:** PRESS Review section in `{output_dir}/{date}-{slug}/02-source-inventory.md`
**Reference:** `{SKILL_DIR}/references/press-checklist.md`

1. Load PRESS checklist: `read_file("{SKILL_DIR}/references/press-checklist.md")`.
2. For each unique search query in the Search Audit table of `02-source-inventory.md`:
   a. Apply the 6-element checklist (Translation of RQ, Boolean operators, Subject headings, Text word searching, Spelling & syntax, Limits & filters).
   b. Rate each element: ADEQUATE / INADEQUATE / NOT APPLICABLE.
   c. Document issues and proposed corrections for any INADEQUATE element.
3. **Re-run rule:** If ≥2 elements are INADEQUATE for any query, re-run that search with the corrected query before proceeding to Stage 2.5. If 1 element, note and proceed.
4. Write PRESS Review section to `02-source-inventory.md` (append).
5. `checklist_update(id=6, status="completed")`.

---

### Stage 2.5: Persistence

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** None (writes to `{bibliography_path}/index/` and `{bibliography_path}/{papers,reports,books}/`)

**Condition:** Run ONLY if `persist_sources == true` AND `dsr-bibliography` was dispatched. Otherwise skip.

1. Extract `persistence_manifest` from `dsr-bibliography` output.
2. Process `new_sources` — for each, verify file exists, then add via `helpers.py`:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import add_source_to_index; import json; print(json.dumps(add_source_to_index('{SKILL_DIR}', '{bibliography_path}', 'paper', '/abs/path/to/file.pdf', {entry_dict})))")
   ```
   **Never pipe JSON through shell — use `code_execution` with `helpers.py`.**
3. Process `reused_local` — update sessions_used for each.
4. Emit summary: "Corpus updated: {N} new, {M} reused."
5. `checklist_update(id=7, status="completed")`.

---

### Stage 3: Source Verification

**Who:** Orchestrator (Pro — moderate thinking) + optional RLM for batch verification
**Output:** `{output_dir}/{date}-{slug}/03-source-verification.md`
**Template:** `{SKILL_DIR}/templates/source-verification.md`

Skip if Stage 2 found 0 sources.

1. Load template: `read_file("{SKILL_DIR}/templates/source-verification.md")`.
2. Load epistemology for P/S/T classification: `read_file("{SKILL_DIR}/references/epistemology.md", start_line=<Primary vs Secondary section>)`.
3. Verify web sources: `fetch_url(url)` — if fails → "UNVERIFIABLE".
4. Verify bibliography: `read_file(path, max_lines=5)` — if fails → "UNVERIFIABLE".
5. Verify codebase: `read_file(path, start_line=N, max_lines=5)` + `grep_files` for presence.
6. **Classify each source:**
   - Source tier: HIGH / MEDIUM / LOW (venue + validation criteria)
   - Primary / Secondary / Tertiary per epistemology reference
7. **Risk of Bias assessment.** Load `read_file("{SKILL_DIR}/references/risk-of-bias.md")`. For each source:
   a. Classify study type (simulation/empirical/algorithm/review/documentation).
   b. Apply domain-specific RoB checklist.
   c. Rate each domain: Low / Some concerns / High / Critical.
   d. Record overall RoB, methodological quality, and reporting quality.
   e. The RoB rating modifies evidence strength per `references/risk-of-bias.md` §RoB → Evidence Strength Mapping.
8. If >20 sources: use RLM with `sub_query_batch(dependency_mode="independent")`.
9. Fill template. `checklist_update(id=8, status="completed")`.

---

### Stage 4: Synthesis

**Who:** Orchestrator (Pro — think carefully about evidence strength, consensus, and gaps)
**Output:** `{output_dir}/{date}-{slug}/04-synthesis.md`
**Template:** `{SKILL_DIR}/templates/synthesis.md`

1. Load template: `read_file("{SKILL_DIR}/templates/synthesis.md")`.
2. Load IRON RULE C: `read_file("{SKILL_DIR}/references/iron-rule-c.md")`.
3. Load epistemology for evidence strength matrix and consensus rules.

4. **Deduplicate findings:**
   - Same numerical value (±1%) → same finding, keep highest-evidence-strength source
   - Same semantic claim → same finding, cite both as converging
   - Contradictory claims → do NOT deduplicate; document as divergence
   - Same source, different sections → complementary

5. **Cross-reference:** web finding consistent with codebase → document link with file:line.

6. **Evaluate each claim independently** from its source:
   - Evidence strength: STRONG / MODERATE / WEAK (per 2×2 matrix in epistemology reference)
   - Source tier: HIGH / MEDIUM / LOW (separate dimension)
   - These are ORTHOGONAL — do not conflate (anti-pattern #12)

7. **Extract constants:** numerical values with units, sources, evidence strength, confidence.

8. **Assess consensus:** per `references/epistemology.md` §Consensus Assessment Rules. Use CONSENSUS / MAJORITY / DIVERGENT / INSUFFICIENT labels.

9. **Flag gaps:** BLOCKING / SIGNIFICANT / MINOR with concrete next steps.

10. **Content density:** do not repeat >20% of content from prior stages. Use forward references: "see S5 in 03-source-verification.md §Credibility".

11. Fill template. `checklist_update(id=9, status="completed")`.

---

### Stage 4.5: Devil's Advocate Checkpoint

**Who:** Sub-agent (Pro — think adversarially: find every weakness in the synthesis)
**Output:** `{output_dir}/{date}-{slug}/04a-devils-advocate.md`
**Template:** `{SKILL_DIR}/templates/devils-advocate.md`

1. Load template: `read_file("{SKILL_DIR}/templates/devils-advocate.md")`.
2. Load IRON RULE C for bare claim checklist: `read_file("{SKILL_DIR}/references/iron-rule-c.md")`.

3. Dispatch sub-agent using the exact `agent_open` call from `references/subagent-prompts.md` §Stage 4.5. Interpolate `{session_dir}` and `{SKILL_DIR}` before dispatch.

4. Wait for `<deepseek:subagent.done>`.
5. Orchestrator reads `04a-devils-advocate.md`:
   - PASS → proceed
   - MINOR → orchestrator applies cosmetic fixes to `04-synthesis.md`
   - REVISE → orchestrator applies listed revisions to `04-synthesis.md`
   - Sub-agent NEVER modifies `04-synthesis.md` directly.
6. `checklist_update(id=10, status="completed")`.

---

### Stage 5: Terminal Report

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** `{output_dir}/{date}-{slug}/05-report.md`
**Template:** `{SKILL_DIR}/templates/report.md`

1. Load template: `read_file("{SKILL_DIR}/templates/report.md")`.
2. Fill from synthesis (after Devil's Advocate revisions). Every claim must use qualified language per `references/iron-rule-c.md`.
3. **Update session index** via `helpers.py`:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import update_session_index; print(update_session_index('{session_index_path}', {{'slug': '{slug}', 'date': '{date}', 'rq': '{rq_summary}', 'verdict': '{verdict_summary}', 'sources_used': {sources_count}, 'review_type': '{review_type}', 'rq_sha256': '{rq_sha256}'}}))")
   ```
4. No knowledge entity creation. Report is the final artifact.
5. `checklist_update(id=11, status="completed")`.

---

### Close: Verification

**Who:** Orchestrator (Pro — minimal thinking)

**GATE-1 — File integrity.** Verify expected files exist and are non-empty:
```
SESSION_DIR="{output_dir}/{date}-{slug}"
expected="01-rq-brief"
[ "$PERSIST_SOURCES" = "true" ] && expected="$expected 01a-local-corpus-triage"
expected="$expected 02-source-inventory 03-source-verification 04-synthesis 04a-devils-advocate 05-report"
for stage in $expected; do
  f="$SESSION_DIR/$stage.md"
  [ -s "$f" ] && echo "OK $stage" || echo "FAIL: $stage missing or empty"
done
```

**GATE-2 — Session index.** `grep_files(pattern="{slug}", path="$SESSION_INDEX")`

**GATE-3 — IRON RULE C (two-pass).** See `references/iron-rule-c.md` §Detection.
- Pass 1: full bare claims regex across `{session_dir}/05-report.md` and `{session_dir}/04-synthesis.md`
- Pass 2: exclude matches with qualifying context. Report only unqualified matches.

**GATE-4 — Integration checks (optional).** Run `$INTEGRATION_CHECKS` if configured. Failure does NOT block.

**GATE-5 — Persistence manifest integrity.** If bibliography axis active: `grep_files(pattern="persistence_manifest", path="{session_dir}/")`

**GATE-6 — Corpus index validity.** If `persist_sources == true` and index exists: `validate_data` on each index file.

**GATE-7 — Unindexed files check.** If `persist_sources == true` (informational, never FAIL).

Emit PASS/FAIL/WARNING/UNVERIFIABLE per gate. GATE-1/2/3/5/8 failures must be resolved.

**GATE-8 — PRISMA + PRESS compliance.** Verify PRISMA flow and PRESS review are present:
- `grep_files(pattern="PRISMA 2020 Flow Diagram", path="{session_dir}/02-source-inventory.md")` → must return match
- Count PRISMA line items present: each line that is not "n = 0 (not implemented)" counts as 1. Total expected: 15 items. Compliance = present/15 as percentage.
- WARNING if < 80%; FAIL if < 50%.
- `grep_files(pattern="PRESS Review", path="{session_dir}/02-source-inventory.md")` → must return match. FAIL if absent.

**GATE-9 — Risk of Bias completeness.** Verify every source has a RoB assessment:
- `grep_files(pattern="Overall RoB", path="{session_dir}/03-source-verification.md")` → count matches.
- Expected count = number of sources in the credibility matrix. FAIL if mismatch.
- `grep_files(pattern="Study type", path="{session_dir}/03-source-verification.md")` → must return match. FAIL if absent.

**GATE-10 — Inter-rater reliability.** If `dual_screening == true`:
- `grep_files(pattern="Screening Reliability", path="{session_dir}/02-source-inventory.md")` → must return match. FAIL if absent.
- `grep_files(pattern="kappa", path="{session_dir}/02-source-inventory.md")` → must return match. FAIL if absent.
- If κ < `agreement_threshold` → WARNING (not FAIL — research may proceed with caution).
- If `dual_screening == false`: SKIP.

**GATE-11 — Protocol registration.** If `protocol_registry != "none"`:
- `grep_files(pattern="registration", path="{session_dir}/MANIFEST.txt")` → must return match. FAIL if absent.
- If `protocol_registry == "osf"`: `fetch_url({doi_url})` → must return 200. WARNING if fails (OSF may be down).
- If `protocol_registry == "local"`: verify `protocol-registration.json` exists and is valid JSON (`validate_data`). FAIL if absent.

`checklist_update(id=11, status="completed")`.

---

## Session directory structure

```
{output_dir}/{date}-{slug}/
├── MANIFEST.txt                     # SHA256 + protocol DOI + stage completion log
├── 01-rq-brief.md
├── protocol-registration.json       # only if protocol_registry != "none"
├── 01a-local-corpus-triage.md       # only if bibliography axis active
├── 02-source-inventory.md
├── 03-source-verification.md        # omitted if 0 sources
├── 04-synthesis.md
├── 04a-devils-advocate.md
└── 05-report.md
```

**Bibliography corpus (persisted cross-session):**
```
{bibliography_path}/
├── papers/
├── reports/
├── books/
└── index/
    ├── papers.json
    ├── reports.json
    └── books.json
```

---

## Integration with host project

The skill reads `.deepseek/deepseek-research.toml` in Stage 1. If absent, defaults are used.
See `references/configuration.md` for full variable table and examples.

For projects without bibliography:
```toml
# .deepseek/deepseek-research.toml
source_axes = ["codebase", "web"]
output_dir = "research-reports/"
session_index = "deep-search-sessions.json"
persist_sources = false
integration_checks = ["npm test", "npm run lint"]
```
