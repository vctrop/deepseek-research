---
name: deepseek-research
description: Multi-source research pipeline with adversarial review. RQ formulation → discovery → verification → deep reading → synthesis → Devil's Advocate → report. Triggered by "deep research X", "/deep-research Z", "investigate deeply Y", "foundational research W".
---

# deepseek-research

Deep multi-source research pipeline: 14 stages + adversarial checkpoint + 23 verification gates.
Deep reading (Stage 3.5) processes full source documents via RLM chunking,
extracting claims with verbatim textual evidence for human-verifiable synthesis.

**Epistemic scope:** This is a rapid evidence assessment pipeline, not a
systematic review. All judgments (relevance, bias, evidence grading) are
performed by LLM sub-agents. The 23 gates verify structural completeness,
not truth. See `references/epistemic-limitations.md` for full documentation.
Every final report MUST include an Epistemic Limitations section.
Corpus vivo: web-discovered sources are persisted and reused cross-session.
Generic — no project-specific infrastructure dependencies.

## Allowed tools

**Orchestrator (all inline stages):**
`request_user_input`, `agent_open`, `agent_eval`, `handle_read`, `rlm_open`, `rlm_eval`, `rlm_configure`, `rlm_close`, `grep_files`, `read_file`, `write_file`, `exec_shell`, `web_search`, `fetch_url`, `checklist_write`, `checklist_update`, `validate_data`, `code_execution`

**Sub-agent tool lists (canonical):** See `references/subagent-prompts.md` for the authoritative tool list per sub-agent type. The SKILL.md lists below are a summary for quick reference; `subagent-prompts.md` is canonical.

**Stage 2 sub-agents (discovery + opensource + tiebreak):**
`web_search`, `fetch_url`, `grep_files`, `read_file`, `file_search`, `write_file` (opensource also: `web_search`, `fetch_url`, `write_file`; tiebreak: `grep_files`, `read_file`, `file_search`, `write_file`)

**Stage 3.5 sub-agents (deep reading — non-T5):**
`rlm_open`, `rlm_eval`, `rlm_configure`, `rlm_close`, `read_file`, `fetch_url`, `handle_read`, `write_file`, `grep_files`

**Stage 3.5 sub-agents (deep reading — T5 source code):**
`exec_shell`, `grep_files`, `read_file`, `write_file`, `fetch_url`, `handle_read`

**Stage 4.5 sub-agent (Devil's Advocate):**
`read_file`, `write_file`

---

## Assumptions

- Orchestrator is **DeepSeek V4 Pro**. Sub-agents use **Flash** for discovery, **Pro** for Devil's Advocate and deep reading.
- `request_user_input` only works in the orchestrator (parent) context — never from sub-agents.
- Internet access expected for web axis. Offline degrades gracefully (see `references/error-recovery.md`).
- **Variable interpolation:** Placeholders in braces (`{output_dir}`, `{date}-{slug}`, `{RQ}`, `{bibliography_path}`, `{session_dir}`, `{SKILL_DIR}`, `{session_index}`) must be interpolated by the orchestrator from config or Stage 1 output.
- `{SKILL_DIR}` resolves to the skill installation directory (typically `~/.deepseek/skills/deepseek-research/`; may vary by runtime configuration). Use `read_file` on any file in the skill to confirm the actual path if uncertain.
- Complete placeholder resolution table: `references/placeholders.md`.

---

## Quick Reference

| Resource | Path |
|----------|------|
| Configuration | `references/configuration.md` |
| Epistemology (evidence matrix, knowledge types, saturation, negative search, textual evidence) | `references/epistemology.md` |
| Deep reading (RLM chunking, evidence taxonomy, consistency checks) | `references/deep-reading.md` |
| Epistemic limitations (full disclosure) | `references/epistemic-limitations.md` |
| Pipeline detail (step-by-step instructions) | `references/pipeline-detail.md` |
| Placeholder resolution table | `references/placeholders.md` |
| IRON RULE C (qualified language) | `references/iron-rule-c.md` |
| Anti-patterns | `references/anti-patterns.md` |
| Error recovery | `references/error-recovery.md` |
| Model matrix + thinking budget | `references/model-matrix.md` |
| Context budget + RLM thresholds | `references/context-budget.md` |
| Sub-agent prompts (incl. dsr-opensource, dsr-deep-read-t5) | `references/subagent-prompts.md` |
| Python helpers (SHA256, index ops, kappa, prompt builder, placeholder resolver, session state) | `scripts/helpers.py` |
| Auto-config bootstrapper | `scripts/bootstrap_config.py` |
| PRESS search strategy peer review | `references/press-checklist.md` |
| Risk of Bias assessment (incl. opensource repository domains) | `references/risk-of-bias.md` |
| Open-Source applicability decision template | `templates/opensource-decision.md` |
| Protocol registry (OSF/local) | `scripts/protocol_registry.py` |
| Meta-analysis engine (DerSimonian-Laird, forest plot) | `scripts/meta_analysis.py` |
| GRADE certainty framework (engineering adaptation — experimental) | `references/grade-framework.md` |

Each reference is loaded by the pipeline at the stage(s) documented in `pipeline-detail.md`. **Templates** live in `{SKILL_DIR}/templates/`. Load with `read_file` at the start of each stage. Never inline template content in SKILL.md.

---

## Pipeline

### Stage 1: Research Question Formulation

**Who:** Orchestrator (Pro — think carefully about question decomposition and operationalization)
**Output:** `01-rq-brief.md`, MANIFEST entry
**Template:** `{SKILL_DIR}/templates/rq-brief.md`
**Config vars:** `output_dir`, `bibliography_path`, `persist_sources`, `source_axes`, `deep_reading`, `agreement_threshold`, `living_review`, `surveillance_interval_days`, `protocol_registry`, `stakeholder_review`
**References:** `configuration.md`, `epistemology.md`, `epistemic-limitations.md`
**Auto-config:** If `.deepseek/deepseek-research.toml` is missing, `scripts/bootstrap_config.py` auto-detects available axes and writes a default config.

> **Detailed steps:** `references/pipeline-detail.md` §Stage 1
> **Initialize tracking:** The first step in pipeline-detail.md sets up `checklist_write` — this MUST be called before any `checklist_update`.

Key decisions: RQ text, knowledge type classification, operational definitions, analysis plan (pre-registered), FINER scoring, review type declaration, pre-registration SHA256.

### Stage 1 Safety Check: Output Isolation

**CRITICAL — Run BEFORE any output is written.** Verify that `{output_dir}` and `{oss_clone_dir}`
resolve to paths **outside** `{SKILL_DIR}`. The skill installation directory must never contain
session artifacts, cloned repositories, or research reports.

Resolve both paths relative to the **project working directory** (where the skill was invoked),
NOT relative to `{SKILL_DIR}`.

```python
import os, sys

skill_dir = os.path.abspath("{SKILL_DIR}")
project_cwd = os.getcwd()
output_dir = os.path.abspath(os.path.join(project_cwd, "{output_dir}"))
oss_clone_dir = os.path.abspath(os.path.join(project_cwd, "{oss_clone_dir}"))

# Verify output_dir and oss_clone_dir do NOT resolve inside SKILL_DIR.
def inside(parent, child):
    return child == parent or child.startswith(parent + os.sep)

errors = []
if inside(skill_dir, output_dir):
    errors.append(f"output_dir ({output_dir}) resolves inside SKILL_DIR ({skill_dir})")
if inside(skill_dir, oss_clone_dir):
    errors.append(f"oss_clone_dir ({oss_clone_dir}) resolves inside SKILL_DIR ({skill_dir})")

if errors:
    print("FATAL: Output isolation violated:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print("\nCreate .deepseek/deepseek-research.toml in your project root and re-run from there.",
          file=sys.stderr)
    sys.exit(1)

print(f"output_dir={output_dir}")
print(f"oss_clone_dir={oss_clone_dir}")
```

Run this via `code_execution` or `exec_shell python -c '...'`. Use `{SKILL_DIR}`, `{output_dir}`,
and `{oss_clone_dir}` from the resolved configuration.

**If the check fails:** Abort immediately. Tell the user:
> "FATAL: The output directory resolves inside the skill installation directory.
> Create a `.deepseek/deepseek-research.toml` in your project with `output_dir` set
> (e.g., `output_dir = \"research-reports/\"`), then re-run from the project root."

---

### Stage 1.6: Protocol Finalize

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** `protocol-registration.json` (if local) or OSF registration
**Condition:** Skip if `protocol_registry == "none"`.
**Config vars:** `protocol_registry`, `osf_token`, `osf_project_id`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 1.6

---

### Stage 1.7: Open-Source Applicability Decision

**Who:** Orchestrator (Pro — think carefully about RQ classification and domain mapping)
**Output:** `01b-opensource-decision.md`
**Template:** `{SKILL_DIR}/templates/opensource-decision.md`
**Condition:** Run ALWAYS. Determines whether `opensource` axis should be active.

> **Detailed steps:** `references/pipeline-detail.md` §Stage 1.7

Key decisions: Scores RQ against 6 criteria. RECOMMEND if ≥ 6. Penalty of -2 if no known OSS repositories (C6=0). In YOLO mode, auto-enables `opensource` axis when recommended. In interactive mode, prompts user.

---

### Stage 1.5: Local Corpus Triage

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** `01a-local-corpus-triage.md`
**Template:** `{SKILL_DIR}/templates/local-corpus-triage.md`
**Condition:** Run ONLY if `"bibliography"` is in `source_axes` AND `persist_sources == true`. Otherwise skip.
**Config vars:** `bibliography_path`, `persist_sources`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 1.5

---

### Stage 2: Source Discovery (parallel)

**Who:** 1-2 sub-agents per available axis (Flash — minimal thinking)
**Output:** `02-source-inventory.md`
**Template:** `{SKILL_DIR}/templates/source-inventory.md`
**Config vars:** `source_axes`, `dual_screening`, `agreement_threshold`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 2
> **Sub-agent prompts:** `references/subagent-prompts.md` §Stage 2

**Dispatch pattern (all sub-agents):**
```
1. code_execution → helpers.build_subagent_prompt('dsr-web', rq_text='{RQ_TEXT}', main_topic='{main_topic}', topics='{topics}')
2. agent_open(name="dsr-web", model="deepseek-v4-flash", allowed_tools=[...], prompt=<output from step 1>)
3. agent_eval(agent_id="...", block=true, timeout_ms=180000)
4. read_file("/tmp/dsr-web-results.md")  # full results, no truncation
```
Sub-agents MUST write complete output to `/tmp/dsr-{axis}-results.md` before responding. The orchestrator reads these files after `agent_eval` — never rely on the inline response which may be truncated.

Key decisions: keyword extraction (via code_execution, never shell), topic extraction for per-topic negative queries, parallel dispatch (bibliography + web + code + opensource + grey), mandatory negative search queries, saturation declaration. Grey axis searches arxiv, techrxiv, ProQuest Dissertations, Google Scholar, and institutional repositories (≥4 relevance threshold).

---

### Stage 2.1: Reconciliation

**Who:** Orchestrator + tiebreak sub-agent (Flash)
**Output:** Reconciliation section appended to `02-source-inventory.md`
**Condition:** Run ONLY if `source_axes` has ≥2 axes that returned sources.

> **Detailed steps:** `references/pipeline-detail.md` §Stage 2.1

Key decisions: Cohen's κ from `helpers.manual_kappa()`, dual screening report, WARNING if κ < `agreement_threshold`.

---

### Stage 2.2: PRESS Review

**Who:** Orchestrator (Pro — minimal thinking)
**Output:** PRESS Review section appended to `02-source-inventory.md`
**Condition:** Run ONLY if `"web"` is in `source_axes`.
**Reference:** `references/press-checklist.md`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 2.2

---

### Stage 2.5: Persistence

**Who:** Orchestrator (Flash or Pro — minimal thinking)
**Output:** Updated bibliography index
**Condition:** Run ONLY if `persist_sources == true`.
**Config vars:** `persist_sources`, `bibliography_path`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 2.5

---

### Stage 3: Source Verification

**Who:** Orchestrator (Pro — think carefully about RoB assessment)
**Output:** `03-source-verification.md`
**Template:** `{SKILL_DIR}/templates/source-verification.md`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 3

Key decisions: accessibility classification, primary/secondary/tertiary, RoB across 5 domains, RoB→Evidence Strength modifier, Deep Read Queue preparation.

---

### Stage 3.5: Deep Source Reading

**Who:** 1 sub-agent per source (Pro — think carefully about claim extraction and evidence grading), dispatched in parallel
**Output:** `deep-reads/{source_id}.md` per source + `deep-reads/_consolidation.md`
**Template:** `{SKILL_DIR}/templates/source-deep-read.md`
**Condition:** Skip if `deep_reading == false` OR 0 sources after Stage 2.
**Config vars:** `deep_reading`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 3.5
> **Methodology:** `references/deep-reading.md`
> **Sub-agent spec:** `references/subagent-prompts.md` §Stage 3.5

Key decisions: document tier (T1/T2/T3/T4) per source, RLM chunking for T3/T4, claim extraction with V/P/I/M grades, internal consistency check, mathematical claim flagging.

---

### Stage 4: Synthesis

**Who:** Orchestrator (Pro — think carefully about evidence evaluation and IRON RULE C)
**Output:** `04-synthesis.md`
**Template:** `{SKILL_DIR}/templates/synthesis.md`
**Config vars:** `deep_reading`, `meta_analysis`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 4

Key decisions: cross-source deduplication, evidence strength per claim (2×2 matrix + textual evidence cap), GRADE certainty assessment, consensus labeling, exploratory meta-analysis (if quantitative), PRISMA flow diagram, gap identification.

---

### Stage 4.5: Devil's Advocate Checkpoint

**Who:** 1 sub-agent (Pro — think carefully about adversarial critique)
**Output:** `04a-devils-advocate.md`
**Template:** `{SKILL_DIR}/templates/devils-advocate.md`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 4.5
> **Sub-agent spec:** `references/subagent-prompts.md` §Stage 4.5

---

### Stage 4.6: Stakeholder Review

**Who:** Orchestrator (interactive — `request_user_input`)
**Output:** Feedback incorporated into `04-synthesis.md`
**Condition:** Skip if `stakeholder_review == false`.
**Config vars:** `stakeholder_review`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 4.6

---

### Stage 5: Terminal Report

**Who:** Orchestrator (Pro — think carefully about narrative clarity)
**Output:** `05-report.md` + `05-plain-summary.md` + `05-decision-brief.md` + optional `05-data-supplement.json`
**Template:** `{SKILL_DIR}/templates/report.md`

> **Detailed steps:** `references/pipeline-detail.md` §Stage 5

Key output: Final report includes Epistemic Limitations section (mandatory), decision brief, and plain-language summary.

---

### Close: Verification

**Who:** Orchestrator (Pro — minimal thinking)

Run all 22 gates on the session directory. Each gate is a structural integrity check.
Gates verify form, not truth — see `references/epistemic-limitations.md` §L2.
Emit PASS/FAIL/WARNING/UNVERIFIABLE per gate. GATE-1/2/3/5/8/16/20/21/22 failures must be resolved.

| Gate | Scope | Condition |
|------|-------|-----------|
| GATE-1 | File integrity — all expected outputs exist and are non-empty | Always |
| GATE-2 | Session index — slug recorded | Always |
| GATE-3 | IRON RULE C — no bare unqualified claims | Always |
| GATE-4 | Integration checks — project-specific (optional) | If `integration_checks` non-empty |
| GATE-5 | Persistence manifest integrity | If `"bibliography"` in `source_axes` |
| GATE-6 | Corpus index validity | If `persist_sources == true` |
| GATE-7 | Unindexed files check (informational) | If `persist_sources == true` |
| GATE-8 | PRISMA + PRESS compliance (thresholds: 80%/50%) | If `"web"` in `source_axes` |
| GATE-9 | Risk of Bias completeness — every source rated | If sources ≥ 1 |
| GATE-10 | Inter-rater reliability — κ reported | If `dual_screening == true` |
| GATE-11 | Protocol registration recorded | If `protocol_registry != "none"` |
| GATE-12 | Meta-analysis self-test — exit code 0 | If `meta_analysis != "never"` |
| GATE-13 | GRADE completeness — every K-finding rated | If RQ type is predictive or causal |
| GATE-14 | Sensitivity flagging — leave-one-out, fail-safe N | If meta-analysis ran |
| GATE-15 | Output format completeness — all 4 output files (5 if data supplement generated) | Always |
| GATE-16 | Stakeholder review output present | If `stakeholder_review == true` |
| GATE-17 | Living review cadence — surveillance date | If `living_review == true` |
| GATE-18 | Textual evidence + human verifiability | If `deep_reading != false` |
| GATE-19 | Session MANIFEST integrity — SHA256 + stage log | Always |
| GATE-20 | Placeholder resolution — no unresolved braces, literal `PLACEHOLDER`, or midnight timestamps | Always |
| GATE-21 | Minimum file count — session must have ≥ 7 core files to claim "completed" | Always |
| GATE-22 | Deep reading enforcement — `deep-reads/_consolidation.md` exists and non-empty if `deep_reading != false` | If `deep_reading != false` |
| GATE-23 | Publication bias flagged — diversity check present in source verification | If sources ≥ 5 |

> **Executable gate commands:** `references/pipeline-detail.md` §Close: Verification — contains the full
> `grep_files`, `exec_shell`, `validate_data`, and shell script commands for each gate.
> **Auto-run procedure:** Gates are executed systematically per the Auto-Run Procedure in pipeline-detail.md.
> Results are recorded in MANIFEST.txt under `## Gate Results`.

`checklist_update(id=14, status="completed")`.

---

## Session directory structure

```
{output_dir}/{date}-{slug}/
├── MANIFEST.txt                     # SHA256 + protocol DOI + stage completion log
├── 01-rq-brief.md
├── 01b-opensource-decision.md       # Stage 1.7 output (always)
├── protocol-registration.json       # only if protocol_registry != "none"
├── 01a-local-corpus-triage.md       # only if bibliography axis active
├── 02-source-inventory.md           # omitted if 0 sources
├── 03-source-verification.md        # omitted if 0 sources
├── deep-reads/                      # Stage 3.5 output; omitted if deep_reading == false
│   ├── _consolidation.md
│   ├── S1.md
│   ├── S3.md
│   └── ...
├── 04-synthesis.md
├── 04a-devils-advocate.md
├── 04b-stakeholder-review.md        # only if stakeholder_review == true
├── 05-report.md
├── 05-plain-summary.md
├── 05-decision-brief.md
├── 05-data-supplement.json          # omitted if no quantitative data extracted
├── .session-state.json              # crash recovery state (auto-managed, deleted at Close)
```
