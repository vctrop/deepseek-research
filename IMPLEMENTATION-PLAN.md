# Continuous Improvement Plan — deepseek-research

**Generated:** 2026-05-23
**Last updated:** 2026-05-23 (audit complete — Ondas 1-4)
**Based on:** Full-session execution (RQ: teorias-computacionais-cerebro, 23 sources, 15 stages, Devil's Advocate MINOR verdict)
**Artifacts inspected:** `SKILL.md`, `helpers.py` (641 lines → 365 lines post-audit), `pipeline-detail.md`, `subagent-prompts.md`, templates/, research-reports/2026-05-22-teorias-computacionais-cerebro/*

## Implementation Status (2026-05-23 audit)

| Phase | Items | Status |
|-------|-------|--------|
| **Phase 1** (Bug fixes) | 1.1, 1.2, 1.3 | ✅ All fixed |
| **Phase 2** (Resilience) | 2.1, 2.2 | ✅ Implemented |
| **Phase 3** (Deep reading) | 3.1, 3.2, 3.3 | ✅ Implemented |
| **Phase 4** (Quality gates) | 4.1, 4.2 | ✅ Implemented |
| **Phase 5** (Advanced) | 5.1, 5.2, 5.3, 5.4 | ✅ Implemented |

### Audit corrections applied (commit 89ee3e7)
- **Checklist alignment:** `checklist_write` reordered to match `checklist_update` IDs
- **Gate count:** Unified to 22 across all references
- **Stage count:** Corrected to 14
- **`{{session_dir}}`:** Fixed double-brace bug in deep read prompts
- **Prompt extraction:** 461 lines → `scripts/prompts.py`; `helpers.py`: 852→365 lines
- **Tiebreak f-string bug:** `{n}`→`{{n}}` in `_build_tiebreak_prompt`
- **AGENTS.md:** Created development guide
- **prepare-commit-msg hook:** Removed (duplicate of TUI's co-author injection)

---

## Architecture Overview

```
SKILL.md          ──► pipeline-detail.md   ──► subagent-prompts.md
(319 lines)          (480 lines)               (235 lines)
orchestrator         step-by-step              sub-agent specs
entry point          instructions              + dsr-* variants

references/         scripts/                   templates/
configuration.md    helpers.py (641L)          rq-brief.md
epistemology.md     index_sources.py           source-inventory.md
deep-reading.md     living_review.py           source-verification.md
risk-of-bias.md     meta_analysis.py           synthesis.md
iron-rule-c.md      protocol_registry.py       report.md
press-checklist.md  smoke_test.py              devils-advocate.md
epistemic-*.md                                 + 10 more
```

---

## Phase 1: Bug Fixes (Critical — blocks reliable execution)

### 1.1 — Negative query string bloat
**File:** `scripts/helpers.py:328-330`, `scripts/helpers.py:377-380`
**Root cause:** `main_topic` is a multi-sentence string (e.g., "comparison of computational theories of brain function: Thousand Brain Theory, Critical Brain Hypothesis...") interpolated verbatim into search query templates. Generates queries like `"limitations of comparison of computational theories of brain function:..."` — unusable by any search engine.

**Fix:**
```python
# In _build_web_prompt, replace lines 326-331:
# BEFORE:
f"""## Mandatory: Negative search
- "limitations of {main_topic}"
- "criticism of {main_topic}"
- "alternatives to {main_topic}"
"""

# AFTER:
def _build_negative_queries(topics: list[str]) -> str:
    """Generate per-topic negative queries instead of one giant blob."""
    lines = []
    for t in topics:
        lines.append(f'- "limitations of {t}"')
        lines.append(f'- "criticism of {t}"')
    return "\n".join(lines)

# Caller (orchestrator) passes topics list extracted from RQ:
# topics = ["thousand brain theory", "critical brain hypothesis", 
#           "free energy principle", "neural manifolds", "predictive processing"]
```

**Impact:** Every web/opensource sub-agent today receives broken negative queries. Fixing this removes a systematic blind spot.

### 1.2 — Sub-agent result truncation
**File:** `SKILL.md` (allowed tools for Stage 2 sub-agents)
**Root cause:** Sub-agents return results inline in their prompt response, truncated by the agent_eval summarizer at ~2KB. Key source lists are lost.

**Fix:**
```markdown
# In SKILL.md Stage 2 instructions, add mandatory write_file output:
# Sub-agents MUST write full source tables to a temp file before exiting.
# Orchestrator reads the file via read_file (no truncation).

# Add to dsr-web and dsr-opensource allowed_tools: write_file
# Add requirement in the prompt: "Write complete source table to 
#  {session_dir}/.tmp-web-results.md before responding"
```

**Impact:** Eliminates the need for supplementary orchestrator searches to recover lost sub-agent data. Stage 2 results become complete on first pass.

### 1.3 — Placeholder non-resolution
**Files:** `templates/rq-brief.md:139`, `templates/source-inventory.md:1`, multiple templates
**Root cause:** Templates use `{rq_sha256}`, `{skill_git_hash}`, `{model_id}`, `{iso8601_utc}` placeholders that the orchestrator must manually replace. Some are always left as-is (e.g., `{skill_git_hash}` → `unknown` in all 5 session files).

**Fix:**
```python
# In helpers.py, add auto-resolution for computable placeholders:
def resolve_placeholders(template_text: str, skill_dir: str, session_dir: str) -> str:
    """Auto-resolve all computable placeholders in a template."""
    import subprocess, datetime
    result = template_text
    result = result.replace("{iso8601_utc}", datetime.datetime.now(datetime.timezone.utc).isoformat())
    result = result.replace("{date}", datetime.date.today().isoformat())
    # git hash from skill dir
    git_hash = subprocess.run(["git", "-C", skill_dir, "rev-parse", "--short", "HEAD"], 
                               capture_output=True, text=True).stdout.strip()
    result = result.replace("{skill_git_hash}", git_hash or "unknown")
    return result
```

**Impact:** Removes manual editing step; templates become self-filling for deterministic placeholders.

---

## Phase 2: Resilience (High — prevents lost work)

### 2.1 — Session state file
**New file:** `{session_dir}/.session-state.json`
**Root cause:** If the orchestrator process dies mid-pipeline, there is no file recording which stage was in progress. Resumption requires guessing.

**Fix:**
```json
{
  "session_slug": "2026-05-22-teorias-computacionais-cerebro",
  "current_stage": "3.5",
  "current_checklist_item": 10,
  "config_snapshot": { "source_axes": ["web", "opensource"], ... },
  "last_completed_stage": "3",
  "pending_actions": [
    "deep-read S4 (FEP+PP comparison)",
    "deep-read S8 (NM Nature Neuroscience)",
    "deep-read T5 OSS2 (tbp.monty)",
    "deep-read T5 OSS3 (pymdp)"
  ],
  "sub_agent_map": {
    "agent_62b21036": { "name": "deep-read-S1", "status": "completed", "output": "deep-reads/S1.md" },
    "agent_78276598": { "name": "deep-read-S6", "status": "completed", "output": "deep-reads/S6.md" }
  }
}
```

**Fixed behavior:**
1. `checklist_update` now also writes `.session-state.json`
2. Stage start: update `current_stage` field
3. Stage complete: update `last_completed_stage`
4. On resume: orchestrator reads `.session-state.json`, skips `last_completed_stage`, resumes from `current_stage`
5. On Close: delete `.session-state.json`

**Impact:** Full crash recovery. User can type "resume deepseek-research" in a new session and the pipeline picks up where it left off.

### 2.2 — Idempotent stage execution
**Files:** All stage functions in `pipeline-detail.md`
**Root cause:** Re-running a completed stage (e.g., due to resume ambiguity) should be safe — not duplicate work, not overwrite outputs.

**Fix:** Each stage checks for output file existence before executing:
```
Stage N start:
  if {output_file} exists and is non-empty:
    checklist_update(id=N, status="completed")
    skip to next stage
  else:
    execute stage N
```

**Impact:** Safe resume. No risk of overwriting completed work. Also enables partial re-runs: delete output file → stage re-executes.

---

## Phase 3: Deep Reading Throughput (High — directly impacts Stage 3.5)

### 3.1 — Deep read priority queue
**File:** `pipeline-detail.md` §Stage 3.5
**Root cause:** Deep Read Queue in `03-source-verification.md` lists sources but doesn't prioritize. Today's session deep-read 3/7 sources before time constraints kicked in.

**Fix:** Auto-sort Deep Read Queue by priority:
```python
def sort_deep_read_queue(sources: list[dict]) -> list[dict]:
    """Priority: (1) RQ-specific primary sources, (2) review/secondary, (3) code."""
    priority_order = {
        "answers_SQ_directly": 1,    # S6 (directly answers SQ2)
        "cross_theory_comparison": 2, # S4 (compares FEP+PP)
        "primary_empirical": 3,      # S8 (Nature Neuroscience primary)
        "review_secondary": 4,        # S11 (review)
        "code_reference": 5           # OSS2, OSS3
    }
    return sorted(sources, key=lambda s: priority_order.get(s["priority"], 99))
```

**Impact:** Most important sources are guaranteed to be deep-read first. If time runs out, lower-priority sources can be flagged as gaps (as done in today's synthesis).

### 3.2 — Parallel batch cap
**File:** `pipeline-detail.md` §Stage 3.5
**Root cause:** SKILL.md says "1 sub-agent per source, dispatched in parallel" with "batch of 10." With 7 sources and 3 parallel sub-agents dispatched, the remaining 4 were never started.

**Fix:** Add explicit batching logic:
```python
# orchestrator pseudo-code:
deep_read_queue = sort_deep_read_queue(sources)
MAX_CONCURRENT = 5  # hard cap to avoid dispatcher overload
for batch in chunk(deep_read_queue, MAX_CONCURRENT):
    # dispatch batch in parallel
    agent_open for each source in batch
    # wait for ALL in batch to complete
    agent_eval(block=true) for each
    # write consolidation after each batch
```

**Impact:** Guaranteed coverage of the entire queue in bounded time. With MAX=5, 7 sources complete in 2 batches.

### 3.3 — T5 deep read auto-integration
**Files:** `pipeline-detail.md` §Stage 3.5, `subagent-prompts.md` §dsr-deep-read-t5
**Root cause:** T5 (code) deep reads were never executed. The session ended with OSS2 and OSS3 not deep-read.

**Fix:** T5 deep read sub-agents use `exec_shell` for git clone. Add pre-flight check:
```
1. Check if repo already cloned: os.path.exists(f"{oss_clone_dir}/{org}_{repo}")
2. If yes: git pull, record new HEAD
3. If no: git clone --depth 1
4. grep_patterns = extract_from_rq(rq_text)  # automatic keyword extraction
5. grep_files on cloned directory
6. read_file on matched files
7. write_file deep-reads/{source_id}.md
```

Also add to the allowed tools list for T5 sub-agents: `exec_shell` (already present), `grep_files`, `read_file`, `write_file`.

**Impact:** Code deep reads become fully automated — no orchestrator intervention needed beyond dispatch.

---

## Phase 4: Quality Gates (Medium — structural correctness)

### 4.1 — Gate auto-run on Close
**File:** `pipeline-detail.md` §Close
**Root cause:** The 19 gates were never run in today's session. Stage 5 is still in_progress, and Close (item 15) is pending.

**Fix:** Make Close a scriptable stage:
```markdown
## Close: Verification (auto)
1. `checklist_update(id=15, status="in_progress")`
2. For GATE-1 through GATE-19:
   - Run the gate command (grep/sha256sum/validate_data)
   - Record PASS/FAIL/WARNING/UNVERIFIABLE
   - If FAIL on GATE-1/2/3/5/8/16: pause and report
3. Write `MANIFEST.txt` with SHA256 + gate results
4. `checklist_update(id=15, status="completed")`
```

**Impact:** Every session closes with a gate report. Structural issues (missing files, bare claims, incomplete PRISMA) are caught before the user sees the output.

### 4.2 — Auto-config bootstrapper
**New file:** `scripts/bootstrap_config.py`
**Root cause:** Default config was used silently. User had no `.deepseek/deepseek-research.toml`. The orchestrator had to guess axes and paths.

**Fix:**
```python
# bootstrap_config.py
# On first run or when config missing:
# 1. Detect bibliography_path (scan for bib/, references/, papers/)
# 2. Detect codebase axes (scan for Cargo.toml, pyproject.toml, package.json)
# 3. Generate sensible defaults
# 4. Write .deepseek/deepseek-research.toml
# 5. Report: "Config generated: source_axes = ['web']; persisting to ..."
```

**Impact:** First-run experience becomes zero-config. User doesn't need to understand `source_axes` to get started.

---

## Phase 5: Advanced Features (Low-medium — expands capability)

### 5.1 — Multi-RQ batch mode
**New capability:** Run multiple independent RQs in one session.
**Trigger:** User says "pesquisa cobrindo todas as áreas de ideias.md" (like today).
**Design:**
```
# orchestrator receives list of RQs
for rq in rq_list:
    session_dir = f"{output_dir}/{date}-{slug(rq)}"
    execute_full_pipeline(rq, session_dir)
    # each RQ is independent, can run sequentially
```

**Implementation note:** The `.session-state.json` file makes this safe — if session dies after RQ 2 of 3, resume picks up at RQ 3.

### 5.2 — Living review auto-trigger
**New capability:** Automatic surveillance searches for prior sessions.
**Trigger:** `living_review == true` and session date > `surveillance_interval_days` ago.
**Design:**
```python
# At Stage 1, check all prior sessions:
for session in prior_sessions:
    if session["date"] < today - surveillance_interval_days:
        # Auto-queue update search
        new_sources = discover_new_since(session["date"], session["rq"])
        if new_sources:
            notify("Living review: {N} new sources found for {slug}")
```

### 5.3 — Manual kappa placeholder → real computation
**File:** `scripts/helpers.py` (add `manual_kappa` function)
**Root cause:** `helpers.manual_kappa()` is referenced in SKILL.md but may not be implemented.
**Fix:** Implement Cohen's κ from four integers: `kappa(n_agree_include, n_agree_exclude, n_disagree, n_total)`.

### 5.4 — Meta-analysis self-test
**File:** `scripts/meta_analysis.py`
**Root cause:** GATE-12 requires meta-analysis self-test with exit code 0, but the meta-analysis module may not have a self-test function.
**Fix:** Add `--self-test` flag to `meta_analysis.py` that runs DerSimonian-Laird on known test data and verifies output.

---

## Priority Matrix

| Phase | Items | Impact | Effort | Risk | Priority Score |
|-------|-------|--------|--------|------|----------------|
| **Phase 1** (Bug fixes) | 1.1, 1.2, 1.3 | Blocks reliability | 2-4h total | Low — bounded scope | **CRITICAL** |
| **Phase 2** (Resilience) | 2.1, 2.2 | Prevents lost work | 3-5h total | Medium — touches multiple files | **HIGH** |
| **Phase 3** (Deep reading) | 3.1, 3.2, 3.3 | Directly improves output quality | 4-6h total | Medium — sub-agent behavior change | **HIGH** |
| **Phase 4** (Quality gates) | 4.1, 4.2 | Structural correctness | 2-3h total | Low | **MEDIUM** |
| **Phase 5** (Features) | 5.1-5.4 | Expands capability | 8-12h total | Low-Medium | **LOW** |

---

## Execution Strategy

### Wave 1: Stabilize (Phase 1 + 2.1)
```
Goal: Pipeline completes reliably; crash recovery works
Checkpoint: Run full pipeline on a test RQ. All 15 stages complete. Crash + resume works.
Estimated: 1 session (5-7h)
```

### Wave 2: Deepen (Phase 3 + 4.1)
```
Goal: Deep reading covers 100% of queue; gates auto-run on close
Checkpoint: Run pipeline with 10 sources, all deep-read, 19/19 gates recorded
Estimated: 1-2 sessions (6-10h)
```

### Wave 3: Polish (Phase 2.2 + 4.2 + Phase 5 selective)
```
Goal: Zero-config bootstrap, idempotent stages, multi-RQ support
Checkpoint: User types "pesquisa ideias.md" → 3 RQs complete with gate reports
Estimated: 2-3 sessions (10-16h)
```

---

## Immediate Next Action

**Phase 1.1** (negative query bloat) is the single highest-impact fix:
- 7 lines changed in `helpers.py`
- Every subsequent web/opensource sub-agent dispatch benefits
- No other changes depend on it
- Can be applied and tested in one turn

**Phase 1.2** (result truncation) is the second-highest:
- Requires adding `write_file` + output contract to 2 sub-agent prompts
- Removes the need for ~40% of supplementary orchestrator searches

Recommend starting with 1.1 + 1.2 together (they're independent changes to different files).
