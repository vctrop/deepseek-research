---
target: deepseek-research skill v3.1 → v3.2
status: refined-draft
created: 2026-05-26
revised: 2026-05-26 (iterative improvement pass: added dependency graph,
  acceptance criteria, rollback strategy, validation protocol, risk triggers,
  Flash testing strategy, measurement indicators, cross-references, glossary)
author: deepseek-tui (DeepSeek V4 Pro)
supersedes: findings from analysis-10-stale-reports.md + review of v3.1
skill_version_target: 3.2.0
---

# Improvement Plan: deepseek-research v3.1 → v3.2

## 1. Executive Summary

A critical review of v3.1 identified the skill as **best-in-class for LLM-assisted
research** (B+, 87/100) with a clear path to A+ (95/100). The review confirmed
findings from `research-reports/analysis-10-stale-reports.md`: the fundamental
architectural tension is that the pipeline executor is a non-deterministic LLM,
and the most critical verification step (GATE-0 title match) depends entirely
on LLM discipline rather than deterministic enforcement.

This plan defines **10 improvements** across 3 sprints, prioritized by
risk-reduction-per-engineering-hour. The theme: **shift verification from
LLM instructions to deterministic Python gates wherever possible.**

Total estimated effort: ~12 engineering hours (see Priority Matrix for per-item
breakdown). Risk: low (all changes are additive — new scripts and gates, not
pipeline rewrites).

---

## 2. Architecture Decision

### 2.1 The Fundamental Tension

```
┌──────────────────────────────────────────────────────┐
│  Pipeline Executor = LLM (non-deterministic)          │
│                                                       │
│  Instructions in SKILL.md are ADVICE, not CODE.       │
│  The LLM can skip, rationalize, or hallucinate        │
│  compliance with any instruction.                     │
│                                                       │
│  Only Python scripts in code_execution are            │
│  DETERMINISTIC ENFORCEMENT.                           │
└──────────────────────────────────────────────────────┘
```

### 2.2 Design Principle

> Every verification that matters for report credibility must be a
> deterministic Python script, not an LLM instruction.

**Current state:** 4 of 10 gates are deterministic (GATE-2, -6, -7, -8).
**Target:** 8 of 12 gates deterministic. Only GATE-1 (file integrity),
GATE-3 (textual evidence), GATE-4 (RoB completeness), and GATE-5 (placeholder
resolution) remain manual — and those are inherently judgment calls.

### 2.3 What We Will NOT Do

- We will NOT rewrite the pipeline architecture. v3.1 works.
- We will NOT add new pipeline stages. The 5-stage structure is correct.
- We will NOT add meta-analysis, GRADE, PRISMA, or any v2.x feature.
- We will NOT attempt to make the LLM deterministic (impossible).

---

## 3. Priority Matrix

| # | Improvement | Sprint | Effort | Impact | Risk Reduction |
|---|------------|--------|--------|--------|----------------|
| I-1 | GATE-0: Title Match JSON checkpoint + verify script | 1 🔴 | 2h | HIGH | Eliminates single point of LLM failure |
| I-2 | GATE-9: Promote coverage-grade consistency to automatic | 1 🔴 | 0.5h | HIGH | Closes verification gap already coded |
| I-3 | Sub-agent Flash for batch title verification | 1 🔴 | 1.5h | HIGH | Removes LLM bottleneck + bias |
| I-4 | Test fixtures for verify_*.py scripts | 2 🟡 | 2h | MEDIUM | Prevents regression in gates |
| I-5 | Header-based schema detection for source tables | 2 🟡 | 0.5h | MEDIUM | Eliminates fragile heuristics |
| I-6 | topic_extractor validation suite (10 RQs) | 2 🟡 | 1h | MEDIUM | Improves negative query quality |
| I-7 | Session-specific limitations in Methodological Note | 2 🟡 | 0.5h | LOW | Increases epistemic honesty |
| I-8 | Example session in examples/ directory | 3 🟢 | 1.5h | LOW | Improves onboarding + regression testing |
| I-9 | Stage completion markers + stage_status.py | 3 🟢 | 1.5h | LOW | Robust resume from interruption |
| I-10 | Pipeline metrics in MANIFEST.txt | 3 🟢 | 1h | LOW | Visibility into skill quality over time |

---

### 3.1 Improvement Dependencies

```
I-1 (GATE-0b checkpoint)
 ├── I-3 (dsr-verify-titles) — I-3 produces the JSON that I-1 consumes.
 │    I-1 can be implemented standalone; I-3 is the preferred producer.
 │    I-1 is compatible with both manual GATE-0 and I-3 output.
 └── I-10 (pipeline metrics) — metrics read 03-gate0-results.json.

I-2 (GATE-9 auto) — independent (no deps).

I-4 (test fixtures) — depends on I-1, I-2 being code-complete so fixtures
     can be written against final gate signatures.

I-5 (schema header) — independent. Touches same files as I-1 (verify_completeness.py,
     verify_source_refs.py) but changes are orthogonal.

I-6 (topic_extractor suite) — independent.

I-7 (session-specific limitations) — independent (template + instruction only).

I-8 (example session) — depends on Sprint 1 + Sprint 2 being merged so the
     example reflects the final pipeline.

I-9 (stage_status.py) — independent. Touches templates (adds STAGE_COMPLETE
     markers) which may conflict with I-7 template changes. Merge order:
     I-7 first, then I-9.

I-10 (pipeline metrics) — depends on I-1 (reads 03-gate0-results.json).
     Also reads all stage outputs, so benefits from I-9 markers for
     wall-time accuracy.
```

### 3.2 Acceptance Criteria per Improvement

| # | Acceptance Criteria |
|---|---------------------|
| I-1 | `verify_title_match.py` exits 0 when every source with URL has an entry in `03-gate0-results.json` and all verdict/match_pct pairs are consistent. Exits non-zero with a violation list otherwise. Backward-compatible: missing checkpoint → WARN, not FAIL. |
| I-2 | `check_coverage_grade_consistency()` runs automatically during Close. Gate table in SKILL.md lists GATE-9 as "Automático". Smoke test covers the function. |
| I-3 | Flash sub-agent `dsr-verify-titles` completes verification of 40 sources within 900s. Output JSON passes I-1 validation. Prompt prevents hallucinated page titles (enforced by I-1 cross-check). |
| I-4 | `smoke_test.py` runs all gate fixtures and exits 0 when all gates produce expected results. ≥80% line coverage on verify_*.py scripts. Fixtures cover: all-pass, each failure mode, and edge cases (empty inventory, malformed JSON). |
| I-5 | Scripts parse v2 schema header correctly when present; fall back to v1 heuristics when absent. No regression on existing inventory files. |
| I-6 | `test_topic_extractor.py` passes with ≥80% recall on 10 validation RQs. Extracted topics satisfy: length ≥2 chars, ≤5 words, no standalone stopwords. |
| I-7 | `05-report.md` Methodological Note includes ≥2 session-specific paragraphs. Generic template text is present but supplemented with concrete session data. |
| I-8 | `examples/example-session/` contains all 8 output files + bibliography index. All files are syntactically valid. Smoke test confirms the example session passes all gates. |
| I-9 | `stage_status.py` correctly reports the next incomplete stage for: fresh session, mid-pipeline session (partial files), completed session, and truncated file (missing STAGE_COMPLETE marker). |
| I-10 | `pipeline_metrics.py` produces valid metrics block for: complete session, partial session (missing stages), and empty session directory. Metrics are appended to MANIFEST.txt during Close. |

### 3.3 Rollback Strategy

Each improvement is independently revertible:

| # | Rollback Method |
|---|-----------------|
| I-1 | Remove `verify_title_match.py` and delete GATE-0b from SKILL.md gate table. Old sessions without the JSON checkpoint are unaffected (backward-compatible WARN). |
| I-2 | Revert GATE-9 to "Manual" in SKILL.md gate table. Remove the code_execution block from Close section. |
| I-3 | Remove `dsr-verify-titles` prompt from `prompts.py` and revert pipeline-detail.md to manual GATE-0 instructions. |
| I-4 | Test fixtures are additive; no rollback needed. If they break, fix the script, not the fixture (fixtures encode expected behavior). |
| I-5 | Schema header is ignored by old scripts (no parsing of `<!-- schema:` comments). Removing it from the template restores pure heuristic mode. |
| I-6 | Validation suite is additive. Remove the `test_topic_extractor.py` import from smoke_test.py if the suite is noisy. |
| I-7 | Remove `{session_specific_limitations}` placeholder from template. Pipeline instruction to write session-specific limitations is advisory only. |
| I-8 | Example session is static data; no runtime impact. Delete directory to remove. |
| I-9 | Remove `STAGE_COMPLETE` markers from templates. `stage_status.py` gracefully handles missing markers (reports "unknown"). |
| I-10 | Remove `pipeline_metrics.py` call from Close section. MANIFEST.txt is optional; missing metrics block is harmless. |

---

## 4. Sprint 1: Critical (target: 2026-06-02)

These three improvements close the biggest verification gaps. Without them,
the skill cannot guarantee that sources were actually verified.

### I-1: GATE-0 Title Match JSON Checkpoint + verify_title_match.py

**Problem:** GATE-0 is executed by the orchestrator LLM. There is no
deterministic record of per-source verification results — only prose in
`03-source-verification.md`. The `verify_completeness.py` gate (GATE-6)
explicitly does NOT check whether titles actually matched.

**Solution:**
1. Add a structured checkpoint that the orchestrator MUST write before
   proceeding past Stage 3:
   ```
   {session_dir}/03-gate0-results.json
   ```
   Schema:
   ```json
   {
     "gate": "GATE-0",
     "timestamp_utc": "2026-05-26T...",
     "verifications": [
       {
         "source_id": "S1",
         "reported_title": "ChatQA 2: Bridging the Gap to GPT-4",
         "fetched_url": "https://arxiv.org/abs/2407.16833",
         "page_title": "ChatQA 2: Bridging the Rag to GPT-4V",
         "match_keywords_reported": ["chatqa", "bridging", "gap"],
         "match_keywords_found": ["chatqa", "bridging"],
         "match_pct": 66.7,
         "verdict": "MATCH",
         "notes": "Minor title variation (Rag vs Gap)"
       }
     ],
     "summary": {
       "total_with_url": 6,
       "match": 4,
       "mismatch": 1,
       "unverifiable": 1
     }
   }
   ```

2. New script: `scripts/verify_title_match.py`
   - Reads `02-source-inventory.md` → extracts sources with URLs
   - Reads `03-gate0-results.json` → verifies every source with URL has an entry
   - Verifies `match_pct` is consistent with `verdict`:
     - `verdict == "MATCH"` → `match_pct >= 50`
     - `verdict == "MISMATCH"` → `match_pct < 50`
     - Threshold rationale: ≥50% of ≥5-char non-stopword keywords must
       match. Intentionally lenient — academic titles often vary
       (e.g., "X: A Novel Approach to Y" vs "X: New Method for Y").
       Calibrated against real title variations in arXiv/PubMed/OpenReview
       where 50–70% keyword overlap is common for genuine matches.
       False MATCH below 50% is empirically rare.
   - Reports: PASS if all sources covered and consistent; FAIL with violation list
   - Added as **GATE-0b** (automatic) in Close phase

3. Update `pipeline-detail.md` §Stage 3.0:
   - After completing GATE-0, orchestrator MUST write `03-gate0-results.json`
   - Template provided via `write_file` with structured schema

**Files changed:** `scripts/verify_title_match.py` (new, ~100 lines),
`references/pipeline-detail.md` (update §Stage 3.0),
`SKILL.md` (add GATE-0b to Close table)

**Risk:** If orchestrator fabricates the JSON, the gate still passes.
Mitigation: the JSON contains `fetched_url` and `page_title` — fabricating
realistic values for 30 sources is more work than actually doing the verification.
The gate also cross-references `fetched_url` against the inventory to detect
mismatched source IDs.

---

### I-2: Promote GATE-9 to Automatic (Coverage-Grade Consistency)

**Problem:** `check_coverage_grade_consistency()` exists in `helpers.py`
(lines 145-210) and works correctly, but GATE-9 is listed as "Manual" in
the SKILL.md gate table. This means the gate is never executed.

**Solution:**
1. Update SKILL.md gate table: GATE-9 → **Automático**
2. Add `code_execution` block to SKILL.md Close section:
   ```
   code_execution(code='''
   import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
   from helpers import check_coverage_grade_consistency
   print(check_coverage_grade_consistency(
       "{session_dir}/deep-reads/",
       "{session_dir}/04-synthesis.md"
   ))
   ''')
   ```
3. Update `pipeline-detail.md` §Close to include the execution command
4. Add `check_coverage_grade_consistency` to smoke_test.py

**Note:** The function internally labels itself "GATE-5x" — rename to
"GATE-9" in the JSON output for consistency.

**Files changed:** `SKILL.md` (~5 lines), `references/pipeline-detail.md`
(~5 lines), `scripts/helpers.py` (1 line: rename GATE-5x → GATE-9),
`scripts/smoke_test.py` (~5 lines)

---

### I-3: Sub-agent Flash for Batch Title Verification (dsr-verify-titles)

**Problem:** The orchestrator LLM must sequentially `fetch_url` for every
source — up to 40 calls. Each call takes 2-15s. Total: 5-10 minutes of
monotonous work. The orchestrator may skip sources, mark unverified sources
as ACCESSIBLE, or hallucinate verification results. Context budget
accumulates during this phase, degrading quality for subsequent stages.

**Solution:**
1. New sub-agent type: `dsr-verify-titles` (Flash)
   - Receives: JSON array of `{source_id, reported_title, url}`
   - For each source: `fetch_url(url)` → extract page title → compare
   - Writes results to `/tmp/dsr-verify-results.json` with the same
     schema as `03-gate0-results.json`
   - Tool allowlist: `fetch_url`, `write_file`
   - Timeout: 900s (15 min). Rationale: 40 sources × 15s network timeout + 5s extraction = 800s worst case; +100s safety margin → 900s. The orchestrator waits with `agent_eval(block=true, timeout_ms=900000)`.

2. New prompt builder in `scripts/prompts.py`: `_build_verify_titles_prompt()`
   - Includes the title match heuristic (≥50% of 5+ char words, ignoring
     stopwords)
   - Includes anti-hallucination rules (never fabricate page titles)
   - Requires structured JSON output

3. Update `build_subagent_prompt()` in `helpers.py` to support
   `"dsr-verify-titles"` template

4. Update `pipeline-detail.md` §Stage 3.0:
   - Alternative path: instead of orchestrator doing GATE-0 manually,
     dispatch `dsr-verify-titles`, wait for `/tmp/dsr-verify-results.json`,
     copy to `{session_dir}/03-gate0-results.json`, then use results
     to fill the verification table.

5. The orchestrator still reviews results and handles edge cases
   (Cloudflare blocks, unusual title formats), but the bulk work is
   offloaded.

6. **Testing strategy for dsr-verify-titles:**
    - **Unit test:** `tests/test_verify_titles_prompt.py` — feed
      `_build_verify_titles_prompt()` a known source list and verify the
      output prompt contains all source IDs, URLs, and the match heuristic.
    - **Integration test (dry-run):** Run dsr-verify-titles against 3 known
      URLs (arxiv.org, wikipedia.org, github.com) and verify the JSON output
      schema, verdict consistency, and match_pct calculation.
    - **Smoke test gate:** Add a `test_dsr_verify_titles_schema()` to
      smoke_test.py that validates the output JSON against the expected
      schema using the same validator as `verify_title_match.py`.
    - **Hallucination detection test:** Feed dsr-verify-titles a list with
      1 known-accessible URL + 1 intentionally broken URL (e.g.,
      `https://example.com/nonexistent-99999`). Verify the agent reports
      UNVERIFIABLE (not MATCH with fabricated title).

**Cost impact:** ~$0.002 per session (1 Flash sub-agent, 40 fetch_url calls).

**Files changed:** `scripts/prompts.py` (~50 lines), `scripts/helpers.py`
(~3 lines), `references/subagent-prompts.md` (~20 lines),
`references/pipeline-detail.md` (~30 lines)

---

## 5. Sprint 2: High (target: 2026-06-09)

### I-4: Test Fixtures for Verification Scripts

**Problem:** `verify_completeness.py`, `verify_evidence_grades.py`,
`verify_source_refs.py`, and `check_iron_rule_c_deterministic()` have
zero automated tests. Regressions are undetectable.

**Solution:**
1. Create `tests/fixtures/` directory with synthetic `.md` files:
   - `tests/fixtures/complete-pass/` — all gates should PASS
   - `tests/fixtures/missing-status/` — GATE-6 should FAIL
   - `tests/fixtures/snippet-v-grade/` — GATE-7 should FAIL
   - `tests/fixtures/ghost-source/` — GATE-8 should FAIL
   - `tests/fixtures/bare-claim/` — GATE-2 should FAIL
   - `tests/fixtures/low-coverage-strong/` — GATE-9 should FAIL

2. Extend `smoke_test.py` with `test_verification_gates()`:
   - For each fixture, run the corresponding gate and assert
     `pass == expected_pass`
   - Assert specific violation messages contain expected substrings

3. Add to `AGENTS.md` development workflow:
   > After changing any verify_*.py script, run smoke_test.py and verify
   > all gate fixtures still produce expected results.

**Files changed:** `tests/fixtures/*/` (new, ~10 files, ~200 lines total),
`scripts/smoke_test.py` (~60 lines), `AGENTS.md` (~3 lines)

---

### I-5: Header-Based Schema Detection for Source Tables

**Problem:** The source inventory table has two formats (5-column v1 and
6-column v2 with DOI). Detection heuristics in `fulltext.py:resolve_all_fulltext()`
and `verify_completeness.py` can fail on edge cases (title starting with
"10.", "N/A" as a title word, relevance numbers in unexpected positions).

**Solution:**
1. Add an HTML-style comment immediately before the consolidated sources
   table in `templates/source-inventory.md`:
   ```
   <!-- schema: v2 cols=6 -->
   ```

2. All parsing scripts read this header and use the correct column mapping:
   - `v1 cols=5`: ID | Location | Type | Relevance | Why
   - `v2 cols=6`: ID | Location | Type | DOI | Relevance | Why

3. Update `fulltext.py:resolve_all_fulltext()`:
   - First, scan for `<!-- schema:` comment
   - If `v2`, extract DOI from column 4 directly (no heuristics)
   - If `v1` or absent, use existing regex fallback (backward compat)

4. Update `verify_completeness.py` and `verify_source_refs.py`:
   - Parse schema header; adjust column indices accordingly

**Files changed:** `templates/source-inventory.md` (+1 line),
`scripts/fulltext.py` (~20 lines), `scripts/verify_completeness.py`
(~10 lines), `scripts/verify_source_refs.py` (~5 lines)

---

### I-6: topic_extractor Validation Suite

**Problem:** `topic_extractor.py` uses 3 regex heuristics with no validation
against ground truth. Bad topics → bad negative queries → missed contrary
evidence → biased synthesis.

**Solution:**
1. Create `tests/test_topic_extractor.py` with 10 RQ → expected_topics pairs:
   - "How does in-context learning work in large language models?"
     → `["in-context learning", "large language models"]`
   - "Comparison of Thousand Brain Theory, Critical Brain Hypothesis, and
      Free Energy Principle in computational neuroscience"
     → `["thousand brain theory", "critical brain hypothesis",
        "free energy principle", "computational neuroscience"]`
   - "What are the failure modes of retrieval-augmented generation for
      factual question answering?"
     → `["retrieval-augmented generation", "factual question answering",
        "failure modes"]`
   - (7 more covering diverse domains: systems, math, chemistry, etc.)

2. Assertions:
   - At least 80% of expected topics are found (recall)
   - No extracted topic has >5 words
   - No extracted topic has <2 characters
   - Extracted topics contain no stopwords as standalone tokens

3. If current heuristics fail, iterate on regex patterns until passing.

4. Add to smoke_test.py: `test_topic_extractor_validation()` that runs
   the 10 validation cases.

**Files changed:** `tests/test_topic_extractor.py` (new, ~80 lines),
`scripts/smoke_test.py` (~15 lines)

---

### I-7: Session-Specific Limitations in Methodological Note

**Problem:** The Methodological Note in `05-report.md` is static — same 5
limitations every time. It doesn't reflect what actually went wrong in
*this* research session.

**Solution:**
1. Add `{session_specific_limitations}` placeholder to `templates/report.md`
   §Methodological Note, between items 4 and 5.

2. In `pipeline-detail.md` §Stage 5.2, add step:
   > 5b. Write 2-3 paragraphs of **session-specific limitations**:
   >   - How many sources were paywalled/inaccessible?
   >   - Which axes failed or underperformed?
   >   - Any sub-agent failures or timeouts?
   >   - Any sources downgraded due to coverage or access method?
   >   - Any mathematical claims requiring human verification?
   >   Be concrete. Do not reuse generic language from the template.

3. Example of good session-specific limitations:
   > **This session:** 3 of 12 bibliography sources were paywalled
   > (Springer, Elsevier) and only abstracts were available. The Sci-Hub
   > fallback was disabled. The codebase axis failed because the primary
   > repository (github.com/example/repo) was private. Source S4 was
   > downgraded from V-grade to I-grade because only 23% of the document
   > was processed (T4 selective reading). Finding K3 contains mathematical
   > claims (M-grade) that require human verification.

**Files changed:** `templates/report.md` (+2 lines),
`references/pipeline-detail.md` (+10 lines)

---

## 6. Sprint 3: Medium (backlog, no target date)

### I-8: Example Session in examples/

Create `examples/example-session/` with a complete, anonymized research
session showing all 8 output files plus `bibliography/index/sources.json`.
Use a well-known CS question (e.g., "What is the state of the art in
speculative decoding for LLM inference?") with 6-8 sources.

This serves as:
- Onboarding reference for new users
- Visual regression test (does a new run look like this?)
- Quality benchmark for prompt changes

**Files changed:** `examples/example-session/*` (new, ~10 files)

---

### I-9: Stage Completion Markers + stage_status.py

**Problem:** Resume from interruption relies on file existence checks.
If a file exists but is truncated (crash during write), the orchestrator
incorrectly skips that stage.

**Solution:**
1. Add `<!-- STAGE_COMPLETE -->` as the last line of every stage output
   file template. The orchestrator writes this marker only after the
   file is fully written.

2. New script: `scripts/stage_status.py`
   - Scans `{session_dir}` for stage output files
   - For each, checks last 50 bytes for `STAGE_COMPLETE` marker
   - Reports: next stage to execute, or "all stages complete"
   - Usage:
     ```
     code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from stage_status import check; print(check('{session_dir}'))")
     ```

3. Update `error-recovery.md` to reference `stage_status.py`

**Files changed:** All 6 templates (+1 line each),
`scripts/stage_status.py` (new, ~60 lines),
`references/error-recovery.md` (~5 lines)

---

### I-10: Pipeline Metrics in MANIFEST.txt

Add a `## Pipeline Metrics` section to MANIFEST.txt with:
- Sources discovered (bibliography / codebase / total)
- Sources verified (accessible / unverifiable / hallucinated / excluded)
- Deep reads completed / attempted
- Coverage stats (min / max / mean coverage %)
- Evidence grade distribution (V / P / I / M / E counts)
- Findings by confidence (STRONG / MODERATE / WEAK counts)
- New sources added to corpus / local sources reused
- Sub-agent success rate (completed / failed)
- Pipeline wall time (Stage 1 start → Close end, from timestamps)

New script: `scripts/pipeline_metrics.py` that reads all session files
and outputs the metrics block. Called during Close phase.

**Files changed:** `scripts/pipeline_metrics.py` (new, ~80 lines),
`SKILL.md` Close section (~5 lines), `references/pipeline-detail.md`
§Close (~5 lines)

---

## 7. Implementation Notes

### 7.1 File Naming Convention

New scripts follow existing convention: `verify_*.py` for verification
gates, `scripts/*.py` for utilities.

### 7.2 Backward Compatibility

All changes are additive. Old sessions without `03-gate0-results.json`
will trigger a WARN in GATE-0b but not FAIL (the gate notes "missing
checkpoint — GATE-0 was not recorded" and suggests re-running Stage 3).

Old `02-source-inventory.md` files without `<!-- schema:` header fall
back to existing heuristics. No breaking change.

### 7.3 Smoke Test Updates

After each sprint, `smoke_test.py` must pass with the new tests.
`smoke_test.py` already runs in CI-like fashion — exit code 0 = pass.

### 7.4 SKILL.md Line Budget

SKILL.md is currently ~220 lines. Target: ≤250 lines after all changes.
New gates are referenced by name + 1-line description in the table;
detailed commands live in `references/pipeline-detail.md`.

### 7.5 File Inventory: Existing vs New

**Existing files modified** (changes are additive, no breaking changes):

| File | Touched by | Type of change |
|------|-----------|----------------|
| `SKILL.md` | I-1, I-2, I-10 | Add GATE-0b and GATE-9 to gate table; add code_execution blocks in Close section |
| `references/pipeline-detail.md` | I-1, I-2, I-3, I-7, I-10 | Add GATE-0 checkpoint instructions; add GATE-9 execution; add dsr-verify-titles path; add session-specific limitations step; add pipeline_metrics call |
| `scripts/helpers.py` | I-2, I-3 | Rename GATE-5x → GATE-9 in check_coverage_grade_consistency(); add dsr-verify-titles template to build_subagent_prompt() |
| `scripts/smoke_test.py` | I-2, I-4, I-6 | Add check_coverage_grade_consistency, gate fixtures, topic_extractor validation |
| `scripts/verify_completeness.py` | I-5 | Parse schema header for column mapping |
| `scripts/verify_source_refs.py` | I-5 | Parse schema header for column mapping |
| `scripts/fulltext.py` | I-5 | Parse schema header for DOI extraction |
| `templates/source-inventory.md` | I-5 | Add `<!-- schema: v2 cols=6 -->` comment |
| `templates/report.md` | I-7 | Add `{session_specific_limitations}` placeholder |
| `references/error-recovery.md` | I-9 | Reference stage_status.py |
| `references/subagent-prompts.md` | I-3 | Add dsr-verify-titles prompt documentation |
| `AGENTS.md` | I-4 | Add smoke test workflow note |

**New files created:**

| File | From | Purpose |
|------|------|---------|
| `scripts/verify_title_match.py` | I-1 | GATE-0b deterministic verification of title match results |
| `scripts/prompts.py` | I-3 | `_build_verify_titles_prompt()` for Flash sub-agent |
| `scripts/stage_status.py` | I-9 | Resume-from-interruption stage detection |
| `scripts/pipeline_metrics.py` | I-10 | Aggregate pipeline metrics for MANIFEST.txt |
| `tests/fixtures/complete-pass/` | I-4 | Synthetic session that passes all gates |
| `tests/fixtures/missing-status/` | I-4 | GATE-6 failure fixture |
| `tests/fixtures/snippet-v-grade/` | I-4 | GATE-7 failure fixture |
| `tests/fixtures/ghost-source/` | I-4 | GATE-8 failure fixture |
| `tests/fixtures/bare-claim/` | I-4 | GATE-2 failure fixture |
| `tests/fixtures/low-coverage-strong/` | I-4 | GATE-9 failure fixture |
| `tests/test_topic_extractor.py` | I-6 | Topic extractor validation suite |
| `examples/example-session/` | I-8 | Complete anonymized example research session |

**Total:** 12 existing files modified, 12 new files/directories created. All new
scripts follow existing conventions: `verify_*.py` for gates, `scripts/*.py` for
utilities, `tests/` for test infrastructure.

### 7.6 Measurement During Implementation

Track these indicators during each sprint to detect problems early:

| Indicator | How to measure | Healthy range | Action if out of range |
|-----------|---------------|---------------|------------------------|
| Gate execution time | Wall clock per gate in Close phase | <5s per gate | Profile and optimize; check for O(n²) behavior |
| GATE-0b WARN rate | % of sessions missing `03-gate0-results.json` | <20% in Sprint 1, 0% by Sprint 3 | Strengthen SKILL.md language; add pre-GATE-0b enforcement |
| Flash sub-agent success rate | % of sources verified within timeout | >90% | Increase timeout; reduce batch size; add retry logic |
| Smoke test pass rate | `smoke_test.py` exit code | 100% (must pass) | Fix failing tests before any other work |
| Pipeline wall time delta | v3.2 session time − v3.1 baseline | <+2 min | Investigate bottleneck; check for redundant fetch_url calls |
| Verification script coverage | Lines covered / total lines in verify_*.py | ≥80% | Add test fixtures for uncovered branches |
| Gate false positive rate | Manual review of 3 sessions per sprint | <10% of gate violations are false positives | Adjust thresholds; add exception patterns |

### 7.7 Cross-References to Existing Documentation

This plan modifies or depends on these existing files. Review them before
implementing each improvement:

| Existing file | Relevant to | What to check |
|---------------|-------------|---------------|
| `SKILL.md` | I-1, I-2, I-10 | Current gate table structure; Close section layout; line budget |
| `references/pipeline-detail.md` | I-1, I-2, I-3, I-7, I-10 | Stage 3.0 instructions; Close phase instructions; Stage 5.2 report structure |
| `references/error-recovery.md` | I-9 | Current resume logic; existing file-existence checks |
| `references/subagent-prompts.md` | I-3 | Existing sub-agent templates; naming conventions |
| `scripts/helpers.py` | I-2, I-3 | Current `check_coverage_grade_consistency()` implementation; `build_subagent_prompt()` signature |
| `scripts/verify_completeness.py` | I-5 | Current table parsing logic; column detection heuristics |
| `scripts/verify_source_refs.py` | I-5 | Source ID extraction; cross-reference logic |
| `scripts/fulltext.py` | I-5 | `resolve_all_fulltext()` DOI extraction |
| `scripts/smoke_test.py` | I-2, I-4, I-6 | Current test structure; import conventions |
| `templates/source-inventory.md` | I-5 | Current table format; template variable placeholders |
| `templates/report.md` | I-7 | Methodological Note section; existing limitation items |
| `research-reports/analysis-10-stale-reports.md` | All | 6 failure modes this plan addresses; root cause analysis |
| `dev-docs/IMPROVEMENT-PLAN.md` | All | This document — keep updated as implementation progresses |

---

## 8. Risk Register

| Risk | P | Impact | Trigger (concrete signal) | Mitigation | Response if triggered |
|------|---|--------|---------------------------|------------|----------------------|
| Flash agent hallucinates title match results | M | High — false MATCH lets fabricated URLs through | GATE-0b reports match_pct ≥50 but spot-check shows unrelated page | Prompt hardening + GATE-0b cross-check + orchestrator spot-checks 20% | Disable I-3; revert to manual GATE-0; harden prompt with explicit anti-fabrication examples |
| `03-gate0-results.json` not written by orchestrator | H | Medium — GATE-0b warns but doesn't block | 2 consecutive sessions without the checkpoint file | Make GATE-0b blocking (FAIL) after 2-session grace period | Add pre-GATE-0b check that aborts Close if file missing; update SKILL.md with stronger language |
| `verify_title_match.py` has a parsing bug | L | High — false PASS or false FAIL on valid JSON | smoke_test.py fixture failures; validation sessions show wrong gate results | Test fixtures cover edge cases; validation protocol catches before merge | Fix the bug; add the failing case to test fixtures |
| `topic_extractor` still fails on edge cases after validation suite | L | Low — affects negative query quality only | `test_topic_extractor.py` recall <80% | Validation suite establishes baseline; future improvements are incremental | Accept current recall; document known failure modes in test file |
| Schema header not added by orchestrator to inventory | M | Low — fallback heuristics still work | verify_completeness.py WARN count increases (heuristic fallback path hit) | Template includes the comment; orchestrator copies template | Monitor WARN rate; if >20% of sessions, add GATE that checks for schema header |
| Coverage-grade gate (GATE-9) false positives on selective reading | M | Low — legitimate STRONG findings flagged | Orchestrator overrides >30% of GATE-9 violations as "reviewed, acceptable" | Gate reports violations but doesn't auto-downgrade; orchestrator reviews | Raise coverage threshold for STRONG from 25% → 40%; or add "selective read" exemption |
| Flash sub-agent times out before completing all sources | M | Medium — incomplete GATE-0 coverage | dsr-verify-titles exits with timeout; partial results in JSON | 900s timeout covers worst case; partial results still useful | Orchestrator completes remaining sources manually; log timeout rate for tuning |
| New gate adds >30s to Close phase | L | Low — user-visible delay | Pipeline wall time metric exceeds baseline by >30s | All gates are O(n) parsers; total <30s expected | Profile gates; optimize slowest one; consider parallel execution |

---

## 9. Success Metrics

After all 3 sprints, measure these metrics across 5 new research sessions:

| Metric | v3.1 Baseline | v3.2 Target |
|--------|--------------|-------------|
| Sources with verified title match (GATE-0) | ~60% (estimated) | 100% |
| GATE-0 title mismatches caught per session | 0 (undetected) | ≥1 if present |
| Automatic gates (deterministic) | 4 of 10 | 8 of 12 |
| Session-specific limitations in report | 0% of reports | 100% of reports |
| Deep reads with coverage <25% producing STRONG findings | Unknown | 0 (blocked by GATE-9) |
| Smoke test coverage (verification scripts) | 0% | ≥80% line coverage |
| Pipeline wall time increase from new gates | — | <30s (all gates are fast parsers) |

### 9.1 Validation Protocol

After each sprint, validate the new gates against **5 real or simulated research
sessions** before considering the sprint complete:

1. **Sprint 1 validation:**
   - Run 3 sessions with 10+ sources each. Verify that `03-gate0-results.json`
     is produced and `verify_title_match.py` passes (or correctly warns on
     missing checkpoint).
   - Verify GATE-9 triggers automatically during Close and catches at least
     one coverage-grade inconsistency in a session with uneven deep reads.
   - Verify dsr-verify-titles completes within 900s and its output is accepted
     by `verify_title_match.py`.

2. **Sprint 2 validation:**
   - Run `smoke_test.py` — must exit 0 with all gate fixtures passing.
   - Run a session with v2 schema header; confirm all parsing scripts work.
   - Run `test_topic_extractor.py` — must achieve ≥80% recall.
   - Generate a report and verify the Methodological Note contains ≥2
     session-specific paragraphs with concrete numbers.

3. **Sprint 3 validation:**
   - Simulate interruption mid-pipeline; verify `stage_status.py` reports
     the correct next stage for each partial state.
   - Run a full session and verify MANIFEST.txt contains the Pipeline Metrics
     block with all fields populated.
   - Verify `examples/example-session/` passes all gates via `smoke_test.py`.

4. **Cross-sprint integration test:**
   - Run 2 end-to-end research sessions with all improvements active.
   - Compare against v3.1 baseline sessions for: gate pass rate, report quality,
     pipeline wall time.
   - All success metrics (table above) must meet or exceed v3.2 targets.

**Gate for proceeding:** No sprint is "done" until its validation protocol
passes. If a validation session reveals a systemic issue, pause implementation
and fix the root cause before continuing.

---

## 10. Sign-off

This plan addresses the 6 failure modes identified in
`research-reports/analysis-10-stale-reports.md` and the 7 structural
weaknesses found in the v3.1 critical review. The theme is consistent:
**determinism where it matters, LLM judgment where it's unavoidable,
and structured checkpoints to make LLM judgment auditable.**

The plan does NOT attempt to solve the fundamental architectural tension
(LLM as pipeline executor) — that would require reimplementing the skill
as a Python program with the LLM as a component, which is a v4.0-level
change. Instead, it applies the maximum-possible deterministic enforcement
within the current architecture.

---

*Next step: approve Sprint 1 (I-1, I-2, I-3) and begin implementation.*

---

## 11. Glossary

| Term | Definition |
|------|------------|
| **GATE** | A verification checkpoint in the pipeline. Numbered GATE-0 through GATE-9 (v3.1) or GATE-0b through GATE-10 (v3.2). Automatic gates are deterministic Python scripts; Manual gates require LLM judgment. |
| **Iron Rule** | An inviolable constraint that, if violated, makes the report invalid. Iron Rule C (every claim must cite a source) is enforced by GATE-8. |
| **Deep read** | A thorough reading of a source that produces evidence snippets with coverage percentages. Contrast with "selective read" (targeted extraction) and "skim" (abstract-only). |
| **Coverage** | The percentage of a source document that was read and analyzed. Low coverage (<25%) combined with STRONG findings triggers GATE-9. |
| **Evidence grade** | Classification of a finding's evidentiary basis: V (verbatim snippet), P (paraphrase with snippet), I (inference from data), M (mathematical claim), E (external/uncited). |
| **Session** | One complete run of the research pipeline, producing 8 output files in a timestamped directory under research-reports/. |
| **Orchestrator** | The LLM that executes the pipeline by following SKILL.md instructions. Non-deterministic; the source of most verification gaps. |
| **Flash sub-agent** | A lightweight, fast-execution child agent (DeepSeek V4 Flash with thinking off) used for bounded, tool-heavy tasks like batch title verification. |
| **Stage** | One of 5 phases in the pipeline: Stage 1 (Setup), Stage 2 (Discovery), Stage 3 (Verification), Stage 4 (Synthesis), Stage 5 (Report). |
| **Close phase** | The final phase after Stage 5 where all automatic gates are executed and MANIFEST.txt is finalized. |
| **Smoke test** | `scripts/smoke_test.py` — a self-contained test suite that validates the skill's Python scripts without requiring a full pipeline run. |
| **SKILL.md** | The main skill definition file (~220 lines) that the orchestrator reads. Contains the gate table, stage instructions, and iron rules. |
| **pipeline-detail.md** | Reference document with detailed per-stage instructions, sub-agent dispatch protocols, and Close phase gate execution commands. |
| **v3.1 / v3.2** | Skill version numbers. v3.1 is current; v3.2 is the target of this improvement plan. |
| **GATE-0b** | New deterministic gate (v3.2) that verifies the JSON checkpoint produced by GATE-0 title matching. Not to be confused with GATE-0 (manual, v3.1). |
| **Schema header** | An HTML-style comment (`<!-- schema: v2 cols=6 -->`) placed before the source inventory table to indicate column layout, replacing fragile heuristic parsing. |
| **STAGE_COMPLETE marker** | A sentinel string (`<!-- STAGE_COMPLETE -->`) appended as the last line of each stage output file to distinguish complete files from truncated ones. |
