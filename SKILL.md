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
     {"content": "Stage 1.5: Local Corpus Triage", "status": "pending"},
     {"content": "Stage 2: Source Discovery", "status": "pending"},
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

### Stage 1.5: Local Corpus Triage

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** `{output_dir}/{date}-{slug}/01a-local-corpus-triage.md`
**Template:** `{SKILL_DIR}/templates/local-corpus-triage.md`

**Condition:** Run ONLY if `"bibliography"` is in `source_axes` AND `persist_sources == true`. Otherwise skip — `checklist_update(id=2, status="completed")` and proceed to Stage 2.

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
6. Fill template. `checklist_update(id=2, status="completed")`.

---

### Stage 2: Source Discovery (parallel)

**Who:** 1 sub-agent per available axis (Flash — minimal thinking)
**Output:** `{output_dir}/{date}-{slug}/02-source-inventory.md`
**Template:** `{SKILL_DIR}/templates/source-inventory.md`

1. Load epistemology reference for negative search rules:
   `read_file("{SKILL_DIR}/references/epistemology.md", start_line=<Negative Search section>)`

2. Load sub-agent prompts: `read_file("{SKILL_DIR}/references/subagent-prompts.md")`.
3. Dispatch sub-agents in **one turn** — no inter-dependencies. Use the exact `agent_open` calls from the prompts file:
   - `dsr-bibliography` (if bibliography axis available)
   - `dsr-web` (if web axis available)
   - `dsr-code` (always)
   Interpolate `{RQ_TEXT}`, `{bibliography_path}`, `{main_topic}`, `{LOCAL_SOURCES_BLOCK}`, `{local_sources_json}` before dispatch.

4. RLM for large bibliography: if `bibliography_path` > 10KB, use `rlm_open`/`rlm_eval`/`rlm_close` instead of `read_file`. See `references/context-budget.md` §RLM Usage Thresholds.

5. Wait for all sub-agents: `agent_eval(agent_id="...", block=true)` for each.

6. **Validate outputs:** each sub-agent must return a Markdown table. If free-text, re-run with format instruction.

7. **Consolidate:** merge tables, assign sequential IDs (S1, S2, ...), remove exact duplicates. Write `02-source-inventory.md` using the template.

8. **Empty result:** if 0 sources across all axes → diagnostic in `02-source-inventory.md`, skip Stages 2.5 and 3. Stage 4 → "insufficient evidence".

9. `checklist_update(id=3, status="completed")`.

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
5. `checklist_update(id=4, status="completed")`.

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
   - COI flagging: author-is-creator, vendor self-report, same institution
7. If >20 sources: use RLM with `sub_query_batch(dependency_mode="independent")`.
8. Fill template. `checklist_update(id=5, status="completed")`.

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

11. Fill template. `checklist_update(id=6, status="completed")`.

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
6. `checklist_update(id=7, status="completed")`.

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
5. `checklist_update(id=8, status="completed")`.

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

Emit PASS/FAIL/WARNING/UNVERIFIABLE per gate. GATE-1/2/3/5 failures must be resolved.

`checklist_update(id=8, status="completed")`.

---

## Session directory structure

```
{output_dir}/{date}-{slug}/
├── MANIFEST.txt                     # SHA256 of 01-rq-brief.md + stage completion log
├── 01-rq-brief.md
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
