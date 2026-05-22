# deepseek-research

**Name:** deepseek-research
**Description:** Deep multi-source research pipeline for any workspace. 5-stage pipeline: RQ formulation → local corpus triage → parallel source discovery → persistence → source verification → synthesis → Devil's Advocate checkpoint → terminal report. Corpus vivo: fontes web descobertas são persistidas e reutilizadas cross-session. Generic — no project-specific infrastructure dependencies. Optimized for DeepSeek TUI (Flash sub-agents, RLM for large corpora, prefix cache discipline, two-pass IRON RULE C).
**Triggers:** "deep research X", "/deep-research Z", "investigate deeply Y", "comprehensive research on W", "foundational research V"

## Allowed tools

**Orchestrator (all inline stages):**
`request_user_input`, `agent_open`, `agent_eval`, `handle_read`, `rlm_open`, `rlm_eval`, `rlm_configure`, `rlm_close`, `grep_files`, `read_file`, `write_file`, `exec_shell`, `web_search`, `fetch_url`, `checklist_write`, `checklist_update`, `validate_data`, `code_execution`

**Stage 2 sub-agents (discovery):**
`web_search`, `fetch_url`, `grep_files`, `read_file`, `file_search`, `rlm_open`, `rlm_eval`, `rlm_close`, `write_file`

**Stage 4.5 sub-agent (Devil's Advocate):**
`read_file`, `write_file`

---

## Assumptions

- Orchestrator is **DeepSeek V4 Pro**. Sub-agents use **Flash** for discovery (mechanical, parallelizable, 12× cheaper).
- Skill is always loaded at orchestrator level (not as sub-agent). `request_user_input` only works in parent context.
- Skill expects internet access for web axis. Offline environments degrade gracefully (§Error Recovery).
- **Variable interpolation:** Placeholders in braces (`{output_dir}`, `{date}-{slug}`, `{RQ}`, `{bibliography_path}`, `{session_dir}`, `{SKILL_DIR}`, `{session_index}`) must be interpolated by the orchestrator from config or Stage 1 output before use in prompts or commands.
- **`{SKILL_DIR}`** resolves to `~/.deepseek/skills/deepseek-research/` — the directory containing this SKILL.md.

---

## Configuration

The host project defines 6 variables in `.deepseek/deepseek-research.toml`:

| Variable | Default | Description |
|---|---|---|
| `source_axes` | `["bibliography", "codebase", "web"]` | Discovery axes |
| `bibliography_path` | `"bibliography/"` | Path to bibliography index |
| `output_dir` | `"research-reports/"` | Session output directory |
| `session_index` | `"deep-search-sessions.json"` | JSON array of session history |
| `persist_sources` | `true` | When `true`, web-discovered sources are persisted to the local corpus. When `false`, current behavior (no persistence). |
| `integration_checks` | `[]` | Shell commands for final verification |

If the file is absent, defaults are used. User can override per-session in the prompt.

**Session index format:** JSON array:
```json
[{"slug": "...", "date": "2026-05-21", "rq": "...", "verdict": "K1: ...", "sources_used": 5}]
```

---

## Context budget

| Trigger | Threshold | Action |
|---|---|---|
| Warning | ~60% TUI context indicator | "Context pressure. Consider `/compact` after this stage." |
| Halt | ~80% TUI context indicator | Pause. Save state. Resume with `/compact` + "continue deep research {slug}" |

**Prefix cache discipline:**
- Reference by path + §, never re-read between stages
- Append, never reorder messages
- Stable sections (FINER table, credibility tiers) are reused via prefix cache
- Never `fork_context: true`

---

## Pipeline

### Stage 1: Research Question Formulation

**Who:** Orchestrator (Pro, `reasoning_effort="high"`)
**Output:** `{output_dir}/{date}-{slug}/01-rq-brief.md`

1. Create checkpoint checklist with 8 items:
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
2. Use `request_user_input` to clarify: central question, domains spanned, decisions depending on this research.
3. Generate slug from RQ: lowercase, hyphens, ≤ 50 chars. Example: "Estado da arte em co-kriging?" → `co-kriging-estado-da-arte`.
4. Check prior sessions: `grep_files` in `$SESSION_INDEX` for slug/topic. If found, ask user to extend or start fresh.
5. Apply FINER scoring:

| Criterion | Question | Score (1-5) |
|-----------|----------|-------------|
| Feasible | Answerable with available sources? | |
| Interesting | Addresses genuine uncertainty? | |
| Novel | Goes beyond existing project knowledge? | |
| Ethical | No concerns? (computational research = 5) | |
| Relevant | Directly informs a decision or artifact? | |

Threshold: average ≥ 3.0, no criterion < 2. If below, report and request RQ refinement.

6. Detect available axes from `source_axes`:
   - `bibliography`: verify `bibliography_path` exists
   - `codebase`: always available
   - `web`: try `web_search("test")` — if fails, mark "web unavailable", continue offline
7. Write `01-rq-brief.md`: RQ, sub-questions, scope (in/out), FINER scores, available axes.
8. Update checklist: Stage 1 → done.

---

### Stage 1.5: Local Corpus Triage

**Who:** Orchestrator (inline, Pro)
**Thinking:** `low`
**Output:** `{output_dir}/{date}-{slug}/01a-local-corpus-triage.md`

**Condition:** Run ONLY if `"bibliography"` is in `source_axes` AND `$PERSIST_SOURCES == true`. Otherwise skip — update checklist and proceed to Stage 2.

If condition is false: update checklist Stage 1.5 → done, proceed to Stage 2.

1. Initialize the index if needed:
   ```
   exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py init --base-dir {bibliography_path}")
   ```
   (Idempotent — only creates dirs and empty index files if they don't exist)

2. Check for unindexed files:
   ```
   exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py scan-unindexed --base-dir {bibliography_path}")
   ```
   If the output contains file paths (non-empty JSON array), emit: `"Note: {N} unindexed files in bibliography/. They will not appear in query results. Run index_sources.py add for each new file."`

3. Extract keywords from the RQ: use FINER terms + sub-question keywords, comma-separated, lowercase.

4. Query the index:
   ```
   exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py query --base-dir {bibliography_path} --keywords '{comma_separated_keywords}' --top 20")
   ```
   Output: JSON array of candidates with `id`, `path`, `title`, `authors`, `year`, `keywords`, `summary`, `quality_level`.

5. For each candidate, LLM relevance judgment (orchestrator, inline):
   - Prompt: "Given RQ '{RQ_TEXT}' and candidate '{title}' by {authors} ({year}) with summary '{summary}', rate relevance 1-5 and explain why."
   - Classify as `local_sources` (relevance ≥ 3) or `skip` (< 3).

6. Write `01a-local-corpus-triage.md`:
   - Table: `# | ID | Title | Authors | Year | Relevance | Access`
   - List `local_sources` as JSON array (for consumption by Stage 2)
   - List `skip` with rationale
   - If 0 matches: document and proceed normally (Stage 2 will do full discovery)

**Density:** Keep this file short (typically < 40 lines).

7. Update checklist: Stage 1.5 → done.

---

### Stage 2: Source Discovery (parallel)

**Who:** 1 sub-agent per available axis (Flash, `reasoning_effort="low"`)
**Output:** `{output_dir}/{date}-{slug}/02-source-inventory.md`

1. Dispatch sub-agents in one turn — no inter-dependencies:

```
// Bibliography axis (if available)
agent_open(name="dsr-bibliography", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","file_search","web_search","fetch_url","rlm_open","rlm_eval","rlm_close","write_file"],
  prompt="Search project bibliography at {bibliography_path} for sources relevant to RQ: {RQ_TEXT}

  {LOCAL_SOURCES_BLOCK}

  ## Output contract
  1. Markdown table with columns | Source ID | Title/Path | Type (paper/book/report) | Relevance (1-5) | Why relevant |
  2. persistence_manifest JSON block — last element of response, in dedicated ```json fence.

  ## persistence_manifest format
  ```json
  {
    \"persistence_manifest\": {
      \"new_sources\": [
        {
          \"save_as\": \"papers/author-year-slug.pdf\",
          \"source_id\": \"author-year-slug\",
          \"type\": \"paper\",
          \"title\": \"Full title\",
          \"authors\": [\"Author, A.\"],
          \"year\": 2024,
          \"doi\": \"10.xxxx/xxxxx\",
          \"keywords\": [\"kw1\", \"kw2\"],
          \"summary\": \"2-3 sentence summary of key contributions.\",
          \"quality_level\": \"II\",
          \"source_type\": \"journal\"
        }
      ],
      \"reused_local\": [{\"source_id\": \"existing-id\"}]
    }
  }
  ```

  Rules:
  - new_sources: every source obtained online (web_search + fetch_url). save_as = {type}s/{first-author}-{year}-{short-title-kebab}.{ext}. type ∈ {paper, report, book}.
  - reused_local: every source read from local corpus. Only source_id.
  - If empty: emit [] (never omit the block).
  - The block MUST be the last element of the response.")

  If LOCAL_SOURCES_BLOCK is empty (Stage 1.5 skipped or found nothing), omit that section.
  LOCAL_SOURCES_BLOCK format if non-empty:
  ```
  ## Local Corpus (pre-indexed sources — do NOT fetch online)

  The following sources are already on disk. Read each from {bibliography_path}/{path},
  re-annotate for the current RQ, and mark as Access: ✓ Local corpus.

  {local_sources_json}

  Focus online search effort on topics, authors, and time periods NOT covered by these sources.
  ```

// Web axis (if available)
agent_open(name="dsr-web", model="deepseek-v4-flash",
  allowed_tools=["web_search","fetch_url","write_file"],
  prompt="Web search for: {RQ_TEXT}

  Output REQUIRED format — Markdown table:
  | Source ID | URL | Type (academic/industry/blog) | Relevance (1-5) | Why relevant |
  |-----------|-----|------------------------------|-----------------|--------------|
  | W1        | ... | ...                          | ...             | ...          |")

// Codebase axis (always)
agent_open(name="dsr-code", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","file_search","write_file"],
  prompt="Search project codebase for implementations, patterns, docs relevant to: {RQ_TEXT}

  Output REQUIRED format — Markdown table:
  | Source ID | File:Line | Type (impl/doc/test/config) | Relevance (1-5) | Why relevant |
  |-----------|-----------|-----------------------------|-----------------|--------------|
  | C1        | ...       | ...                         | ...             | ...          |")
```

2. If `bibliography_path` > 10KB: use RLM instead of `read_file`.
   - `rlm_open(name="dsr-bib-rlm", file_path=bibliography_path)`
   - `rlm_configure(name="dsr-bib-rlm", output_feedback="metadata")`
   - Process via `rlm_eval` + `search` helper
   - `rlm_close(name="dsr-bib-rlm")` after use

3. Wait for all sub-agents to complete. Use `agent_eval` with `block=true` for each:
   ```
   agent_eval(agent_id="dsr-bibliography", block=true)  // if bibliography axis dispatched
   agent_eval(agent_id="dsr-web", block=true)            // if web axis dispatched
   agent_eval(agent_id="dsr-code", block=true)           // always dispatched
   ```
   Sub-agents emit `<deepseek:subagent.done>` with `status: completed/failed`. Check the summary line before each sentinel.

4. **Validate outputs:** each sub-agent must return a Markdown table. If free-text, re-run with format instruction.

5. **Consolidate (orchestrator):** merge tables, assign sequential IDs (S1, S2, ...), remove exact duplicates (same URL or same path). Write `02-source-inventory.md`.

6. **Empty result:** if 0 sources across all axes → write diagnostic in `02-source-inventory.md`, skip Stages 2.5 and 3. Stage 4 reports "insufficient evidence" directly, Stage 5 issues negative report.

7. **Truncation:** use `handle_read` with `transcript_handle` if `agent_eval` output is truncated.

8. Update checklist: Stage 2 → done.

---

### Stage 2.5: Persistence

**Who:** Orchestrator (inline, Pro)
**Thinking:** `low`
**Output:** None (writes to `{bibliography_path}/index/` and `{bibliography_path}/{papers,reports,books}/`)

**Condition:** Run ONLY if `$PERSIST_SOURCES == true` AND the `dsr-bibliography` sub-agent was dispatched (bibliography axis was active). Otherwise skip.

1. Extract `persistence_manifest` from `dsr-bibliography` output:
   - Locate ```json block containing `"persistence_manifest"`.
   - Parse with `validate_data(content=..., format="json")`.

2. Process `new_sources` — for each entry:
   a. Verify the source file was downloaded by the sub-agent (using `read_file` on the expected path).
   b. If the file exists at the sub-agent's temp location: call `add_source` via stdin JSON:
      ```
      exec_shell(command: "echo '{add_json_escaped}' | python3 {SKILL_DIR}/scripts/index_sources.py add --base-dir {bibliography_path}")
      ```
      Where `add_json` has shape:
      ```json
      {
        "source_type": "{paper|report|book}",
        "file_path": "/absolute/path/to/downloaded/file.{ext}",
        "entry": {
          "id": "{source_id}",
          "title": "{title}",
          "authors": ["{author1}", "..."],
          "year": {year},
          "doi": "{doi}",
          "keywords": ["{kw1}", "..."],
          "summary": "{summary}",
          "quality_level": "{quality_level}",
          "source_type": "{source_type}"
        }
      }
      ```
      The script moves the file to `{bibliography_path}/{type}s/{id}{ext}` and updates the index.
   c. Log: `"Saved: {source_id} → {bibliography_path}/{save_as}"`
   d. If file not found, log: `"WARNING: {source_id} — file not found at download location, skipping"`

3. Process `reused_local` — for each entry:
   a. Verify `source_id` exists in the index by querying.
   b. Update sessions_used:
      ```
      exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py update-sessions --base-dir {bibliography_path} --id {source_id} --session {slug}")
      ```
   c. Log: `"Reused: {source_id} (session: {slug})"`

4. Emit summary: `"Corpus updated: {N} new sources saved, {M} local sources reused."`

5. Update checklist: Stage 2.5 → done.

---

### Stage 3: Source Verification

**Who:** Orchestrator (Pro, `reasoning_effort="auto"`) + optional RLM for batch verification
**Output:** `{output_dir}/{date}-{slug}/03-source-verification.md`

Skip if Stage 2 found 0 sources.

1. Verify web sources: `fetch_url(url, format="text")` — if returns text (non-empty, not error page), source is accessible. If fails: flag "UNVERIFIABLE — URL not accessible".
2. Verify bibliography sources: `read_file(path, max_lines=5)` — if fails: "UNVERIFIABLE — file not found".
3. Verify codebase references: `read_file(path, start_line=N, max_lines=5)` + `grep_files` for presence.
4. Credibility assessment:

| Tier | Criteria |
|------|----------|
| High | Peer-reviewed paper, industry standard, experimentally validated, official docs of established project |
| Medium | Textbook, technical report, established codebase pattern, internal project docs |
| Low | Web article, blog post, single-source claim, AI-generated docs without cross-reference |

5. COI flagging: author-is-creator, vendor self-report, AI-generated docs, internal doc evaluating own architecture.
6. If >20 sources: use RLM with `sub_query_batch(dependency_mode="independent")`:
   ```
   rlm_open(name="dsr-verify", content=<sources JSON>)
   rlm_configure(name="dsr-verify", output_feedback="metadata", sub_query_timeout_secs=60)
   rlm_eval(name="dsr-verify", code=sub_query_batch(...))
   // handle_read for results
   rlm_close(name="dsr-verify")
   ```
7. Write `03-source-verification.md`: credibility matrix + COI register.
8. Update checklist: Stage 3 → done.

---

### Stage 4: Synthesis

**Who:** Orchestrator (Pro, `reasoning_effort="high"`)
**Output:** `{output_dir}/{date}-{slug}/04-synthesis.md`

1. **Deduplicate findings.** Heuristics:
   - Same numerical value (±1% same unit) across sources → same finding, keep highest-credibility source
   - Same semantic claim (e.g., "X is O(n log n)" in two sources) → same finding, cite both as converging
   - Contradictory claims → do NOT deduplicate; document as divergence
   - Same source cited with different sections → complementary, not duplicate

2. **Cross-reference:** web finding consistent with codebase → document link with specific file:line.

3. **Extract constants:** all numerical values with units and sources. If RQ is qualitative, leave table empty with note:
   > "This research question is qualitative. No numerical constants were extracted. See Findings for qualitative results."

   | Symbol | Value | Unit | Source | Confidence |
   |--------|-------|------|--------|------------|

4. **Extract algorithms/patterns:** methods with complexity and domain assumptions. For qualitative RQs, adapt to "Patterns" table.

5. **Assess consensus:**

   | Question | Consensus | Confidence |
   |----------|-----------|------------|
   | ...      | YES/NO/DIVERGENT | HIGH/MEDIUM/LOW |

6. **Flag gaps:** what remains unknown? Severity (BLOCKING/SIGNIFICANT/MINOR) + concrete next steps.

7. **Content density rule:** do not repeat >20% of content from prior stages. Use forward references: "see S5 in 03-source-verification.md §Credibility".

8. Write `04-synthesis.md`. Update checklist: Stage 4 → done.

---

### Stage 4.5: Devil's Advocate Checkpoint

**Who:** Sub-agent (Pro, `reasoning_effort="high"`) — orchestrator dispatches and waits
**Output:** `{output_dir}/{date}-{slug}/04a-devils-advocate.md`

1. Dispatch sub-agent:

```
agent_open(name="dsr-da", model="deepseek-v4-pro",
  allowed_tools=["read_file","write_file"],
  prompt="Read {session_dir}/04-synthesis.md using read_file.
  Review against the Devil's Advocate checklist below.
  Write findings to {session_dir}/04a-devils-advocate.md.

  ## Cherry-picking
  - Contradictory sources excluded or downweighted?
  - If DIVERGENT consensus, minority view given fair space?
  - Negative evidence found but not reported?

  ## Overconfidence
  - Bare 'validated', 'confirmed', 'proved' without qualifiers?
  - Credibility tiers propagated into claim language?
  - Would a hostile reviewer find confidence disproportionate to evidence?

  ## Gap honesty
  - Gaps with severity (BLOCKING/SIGNIFICANT/MINOR) + concrete next steps?
  - Absence of evidence distinguished from evidence of absence?
  - 'Open questions' genuinely open, or rhetorical?

  ## Bias
  - Synthesis favors project-internal sources over external?
  - Reference frameworks evaluated by same standard as project?
  - Confirmation bias toward pre-existing architectural decisions?

  ## Verdict
  - PASS / MINOR (cosmetic fixes) / REVISE (substantive — list required revisions with line references)")
```

2. Wait for `<deepseek:subagent.done>`.

3. **Orchestrator** reads `04a-devils-advocate.md`:
   - PASS → proceed to Stage 5
   - MINOR → orchestrator applies cosmetic fixes to `04-synthesis.md`, then Stage 5
   - REVISE → orchestrator applies listed revisions to `04-synthesis.md`, then Stage 5
   - The sub-agent NEVER modifies `04-synthesis.md` directly.

4. Update checklist: Stage 4.5 → done.

---

### Stage 5: Terminal Report

**Who:** Orchestrator (Pro, `reasoning_effort="auto"`)
**Output:** `{output_dir}/{date}-{slug}/05-report.md`

1. Write terminal report: RQ, Key Findings (K1, K2, ...), Numerical Constants table, Algorithms/Patterns table, Sources (with credibility + COI), Open Questions (with severity).
2. **IRON RULE C enforcement** — every claim must use qualified language. See §IRON RULE C.
3. **Update session index:** use `code_execution` (Python) to append to JSON array:
   ```python
   import json
   with open(session_index) as f:
       sessions = json.load(f)
   sessions.append({"slug": slug, "date": date, "rq": rq_summary, "verdict": verdict_summary, "sources_used": sources_count})
   with open(session_index, 'w') as f:
       json.dump(sessions, f, indent=2)
   ```
   Entry ≤ 280 chars in `rq` field. `sources_used` counts unique sources in inventory (bibliography local + new + web + codebase).
4. **No knowledge entity creation.** Report is the final artifact.
5. **No self-assessment checklist in report.** Verification happens at Close.
6. Update checklist: Stage 5 → done.

---

### Close: Verification

**Who:** Orchestrator (Pro, `reasoning_effort="low"`)

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
If Stage 3 skipped, 03-source-verification is excluded. `04a` optional if skipped.

**GATE-2 — Session index.** Verify slug appears: `grep_files(pattern="{slug}", path="$SESSION_INDEX")`

**GATE-3 — IRON RULE C (two-pass).** See §IRON RULE C.
- Pass 1: `grep_files(pattern="\\b(validated|proved|confirmed)\\b", path="{session_dir}/05-report.md")`
- Pass 2: for each match, check for qualifying context ("verified by", "confirmed by"). Report only unqualified matches.

**GATE-4 — Integration checks (optional).** Run `$INTEGRATION_CHECKS` sequentially:
```
for cmd in $INTEGRATION_CHECKS; do
  exec_shell(cmd) || echo "WARNING: $cmd failed — review output"
done
```
GATE-4 failure does NOT block — project-specific checks. Report warnings.

**GATE-5 — Persistence manifest integrity.** If bibliography axis was active:
```
grep_files(pattern="persistence_manifest", path="{session_dir}/")
```
Verifies the dsr-bibliography sub-agent emitted the manifest block. If bibliography was NOT in source_axes, skip this gate.

**GATE-6 — Corpus index validity.** If `$PERSIST_SOURCES == true` AND `{bibliography_path}/index/` exists:
```
validate_data(path="{bibliography_path}/index/papers.json", format="json")
validate_data(path="{bibliography_path}/index/reports.json", format="json")
validate_data(path="{bibliography_path}/index/books.json", format="json")
```
If the `index/` directory doesn't exist (first run), GATE-6 returns SKIP not FAIL.

**GATE-7 — Unindexed files check.** If `$PERSIST_SOURCES == true` (informational, never FAIL):
```
exec_shell(command: "python3 {SKILL_DIR}/scripts/index_sources.py scan-unindexed --base-dir {bibliography_path}")
```
If unindexed files found, emit warning; do not block.

Emit PASS/FAIL/WARNING/UNVERIFIABLE per gate. GATE-1/2/3/5 failures must be resolved.

Update checklist: Close → done.

---

## IRON RULE C

Every confidence claim in `05-report.md` must use qualified language. Bare claims are forbidden.

**Detection (Close, GATE-3):**
- Pass 1: find `validated`, `proved`, `confirmed`
- Pass 2: exclude matches with qualifiers (`verified by [X]`, `confirmed by [X]`)

**Replacements:**

| Bare claim | Qualified form |
|---|---|
| validated | supported by converging evidence from [sources] |
| confirmed | consistent with [source] under [conditions] |
| proved | demonstrated by [method] in [context] |
| verified | verified by [specific verifier and method] |

---

## Model matrix

| Stage | Executor | Model | Thinking | Est. cost |
|---|---|---|---|---|
| 1 — RQ Formulation | Orchestrator | Pro | `high` | — |
| 1.5 — Local Corpus Triage | Orchestrator | Pro | `low` | — |
| 2 — Discovery (1-3×) | Sub-agents | **Flash** | `low` | ~$0.001-0.003 |
| 2.5 — Persistence | Orchestrator | Pro | `low` | — |
| 3 — Verification | Orchestrator + RLM | Pro + Flash | `auto` | — |
| 4 — Synthesis | Orchestrator | Pro | `high` | — |
| 4.5 — Devil's Advocate | Sub-agent | **Pro** | `high` | ~$0.02-0.05 |
| 5 — Terminal Report | Orchestrator | Pro | `auto` | — |
| Close — Verification | Orchestrator | Pro | `low` | — |

---

## Anti-patterns

| # | Anti-pattern | Cost | Correction |
|---|---|---|---|
| 1 | Pro sub-agent for discovery | 12× cost, >120s timeout | Use Flash |
| 2 | `read_file` of bibliography >10KB | 15-25K tokens | Use RLM |
| 3 | Re-reading prior stage files | Breaks prefix cache | Reference by § |
| 4 | `grep -P` for IRON RULE C | PCRE dependency | Use `grep_files` |
| 5 | `fork_context: true` | +50K tokens copied | Always `false` |
| 6 | Sub-agent for 1 read (generic) | +2K overhead | Do inline. **Exception:** Devil's Advocate — adversarial reasoning justifies overhead. |
| 7 | Not closing RLM sessions | Resource leak | `rlm_close` after use |
| 8 | Full `checklist_write` each step | Array rewrite | `checklist_update(id, status)` |
| 9 | Skipping Stage 1.5 when bibliography axis active | Local sources not reused | Always run 1.5 if bibliography is in source_axes |
| 10 | Forgetting persistence_manifest in dsr-bibliography prompt | GATE-5 fails | Include manifest format in sub-agent prompt |
| 11 | Escaping shell for `add` stdin JSON | Shell injection risk | Use heredoc or python stdin pipe |

---

## Error recovery

| Symptom | Action |
|---|---|
| Web search returns low-quality results | Narrow query; add `site:edu` or `site:org` |
| Source URL 404/403/network error | Flag "UNVERIFIABLE"; credibility → Low for permanent errors (404/403), unchanged for transient errors (timeout, DNS) |
| Flash sub-agent timeout (>120s) | Reduce scope; shorter prompt; retry 1× |
| Flash sub-agent failure | Try alternative axis; continue with successful axes |
| Pro sub-agent timeout (Devil's Advocate) | Split checklist into 2 prompts; or orchestrator applies inline |
| IRON RULE C violation | Replace specific claims with qualified forms |
| Close GATE-1/2/3/5 failure | Resolve before finalizing |
| Close GATE-4 failure | Report warning; do not block |
| Context budget reached | `/compact` + "continue deep research {slug}" |
| `bibliography_path` not found | Remove "bibliography" from axes; continue with codebase + web |
| Offline environment (no internet) | Stage 1 detects; remove "web" axis; report notes "web axis unavailable — offline" |
| 0 sources found (all axes) | Skip Stages 2.5, 3; Stage 4 → "insufficient evidence"; Stage 5 → negative report |
| `index_sources.py` not found at `{SKILL_DIR}/scripts/` | Skip Stage 1.5 and 2.5; log warning; continue without persistence |
| `add_source` fails (duplicate ID) | Log warning; skip that entry; continue with remaining sources |
| `update-sessions` fails (ID not found) | Log warning; index may be out of sync; continue |
| Corpus index JSON corrupt | GATE-6 fails; manually run `index_sources.py init` to recreate (WARNING: overwrites!) |

---

## Session directory structure

```
{output_dir}/{date}-{slug}/
├── 01-rq-brief.md
├── 01a-local-corpus-triage.md    # only if bibliography axis active
├── 02-source-inventory.md
├── 03-source-verification.md     # omitted if 0 sources
├── 04-synthesis.md
├── 04a-devils-advocate.md
└── 05-report.md
```

**Bibliography corpus (persisted cross-session):**
```
{bibliography_path}/
├── papers/           # full-text (PDF, txt, md)
├── reports/
├── books/
└── index/
    ├── papers.json
    ├── reports.json
    └── books.json
```

---

## Integration with host project

The skill reads `.deepseek/deepseek-research.toml` in Stage 1. If absent, defaults are used. Example:

```toml
# .deepseek/deepseek-research.toml
source_axes = ["bibliography", "codebase", "web"]
bibliography_path = "bibliography/"
output_dir = "research-reports/"
session_index = "deep-search-sessions.json"
persist_sources = true
integration_checks = ["cargo test --workspace"]
```

For projects without bibliography:
```toml
source_axes = ["codebase", "web"]
output_dir = "research-reports/"
session_index = "deep-search-sessions.json"
persist_sources = false
integration_checks = ["npm test", "npm run lint"]
```
