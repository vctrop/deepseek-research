---
session: {date}-{slug}
stage: 1.7
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Open-Source Applicability Decision

**Session:** `{date}-{slug}`
**Stage:** 1.7 — Open-Source Applicability Decision

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| `{RQ_TEXT}` | Orchestrator | From `01-rq-brief.md` |
| `{TOTAL_SCORE}` | Orchestrator | Sum of criteria scores |
| `{VERDICT}` | Orchestrator | RECOMMEND / NOT RECOMMENDED |

## Scoring Matrix

Each criterion is evaluated against the research question. The total score determines
whether the `opensource` discovery axis is recommended.

| # | Criterion | Score |
|---|-----------|-------|
| 1 | RQ is **Procedural** ("How to implement X?") or **Causal** ("What is the effect of using Y?") | {0 or 3} |
| 2 | RQ involves **benchmark, performance, latency, throughput, or resource consumption** | {0 or 2} |
| 3 | RQ mentions **specific tools, libraries, frameworks, or programming languages** | {0 or 2} |
| 4 | RQ is **Predictive** and no established public datasets are available | {0 or 1} |
| 5 | Answer depends on **real implementation evidence** (not just theoretical claims) | {0 or 3} |
| 6 | **Known open-source repositories** implement the RQ domain | {0 or 2} |
| | **Total** | **{TOTAL_SCORE}** |

**Threshold:** ≥ 6 → RECOMMEND. < 6 → NOT RECOMMENDED.

**Penalty:** If criterion 6 (Known OSS repositories) scores 0, apply a -2 penalty to the total. An RQ without a mapped open-source ecosystem should not trigger the axis even if it depends on implementation evidence.

## Verdict

**{RECOMMEND / NOT RECOMMENDED}**

## Rationale

{2-3 sentences explaining the score. Example:

"The RQ asks 'How to implement co-kriging for multi-fidelity surrogates?' —
a Procedural question that depends on real implementation evidence (criteria 1
and 5, +6). It also involves performance benchmarks (criterion 2, +2). However,
it does not mention specific libraries (criterion 3, +0) and established
datasets exist (criterion 4, +0). Known repositories like SMT and GPyTorch
implement the domain (criterion 6, +2; no penalty). Total: 13 ≥ 6 → RECOMMEND."}

## Action

{If RECOMMEND and `"opensource"` not in `source_axes`:
  "User prompted to add `opensource` to source_axes. Response: {user_choice}."
If RECOMMEND and `"opensource"` already in `source_axes`:
  "Axis already active. No action needed."
If NOT RECOMMENDED:
  "Open-source axis not recommended for this RQ. Skipping opensource discovery."}
