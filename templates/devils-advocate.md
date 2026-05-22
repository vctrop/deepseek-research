---
session: {date}-{slug}
stage: 4.5
skill_version: {skill_git_hash}
model: deepseek-v4-pro
timestamp_utc: {iso8601_utc}
---

# Devil's Advocate Checkpoint

**Session:** `{date}-{slug}`
**Stage:** 4.5 — Devil's Advocate
**Reviewed file:** `04-synthesis.md`

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| All findings (PASS/ISSUE) | dsr-da sub-agent | Adversarial review of `04-synthesis.md` |

## Cherry-picking

| Question | Finding | Evidence (line ref) |
|----------|---------|---------------------|
| Contradictory sources excluded or downweighted? | {PASS / ISSUE} | {04-synthesis.md:line} |
| If DIVERGENT consensus, minority view given fair space? | {PASS / ISSUE / N/A} | {ref} |
| Negative evidence found but not reported? | {PASS / ISSUE} | {ref} |
| Negative search results from Stage 2 acknowledged in synthesis? | {PASS / ISSUE} | {ref} |

## Overconfidence

| Question | Finding | Evidence |
|----------|---------|----------|
| Bare claims (validated, proved, confirmed, ensures, always, never, optimal, definitive, etc.) without qualifiers? | {PASS / ISSUE} | {ref} |
| Evidence strength propagated into claim language? | {PASS / ISSUE} | {ref} |
| Would hostile reviewer find confidence disproportionate to evidence? | {PASS / ISSUE} | {ref} |
| Source credibility tier conflated with evidence strength? | {PASS / ISSUE} | {ref} |

## Gap Honesty

| Question | Finding | Evidence |
|----------|---------|----------|
| Gaps acknowledged with severity + concrete next steps? | {PASS / ISSUE} | {ref} |
| Absence of evidence distinguished from evidence of absence? | {PASS / ISSUE} | {ref} |
| "Open questions" genuinely open, or rhetorical? | {PASS / ISSUE} | {ref} |

## Bias

| Question | Finding | Evidence |
|----------|---------|----------|
| Synthesis favors project-internal sources over external? | {PASS / ISSUE} | {ref} |
| Reference frameworks evaluated by same standard as project? | {PASS / ISSUE / N/A} | {ref} |
| Confirmation bias toward pre-existing architectural decisions? | {PASS / ISSUE} | {ref} |
| All agreeing sources share same author group/institution/funding? (consensus contamination) | {PASS / ISSUE / N/A} | {ref} |

## Verdict

{Choose exactly one: PASS / MINOR / REVISE}

**Verdict: {PASS / MINOR / REVISE}**

### If MINOR
{list cosmetic fixes}

### If REVISE
{list required revisions with line references to 04-synthesis.md}

**Revisions applied by:** Orchestrator (before Stage 5). The sub-agent NEVER modifies `04-synthesis.md` directly.
