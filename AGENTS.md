# AGENTS.md — deepseek-research Development Guide

## Architecture

```
SKILL.md (380L)           → Orchestrator entry point. Slim. Never inline templates or
  references/pipeline-detail.md (739L) → Step-by-step instructions per stage. Loaded by ref.
    references/subagent-prompts.md     → Sub-agent dispatch specs + tool lists (canonical).
    scripts/helpers.py (365L)          → Utility functions: SHA256, kappa, session state,
                                         placeholder resolution, prompt dispatcher.
    scripts/prompts.py (496L)          → Sub-agent prompt builders (extracted from helpers).
    scripts/meta_analysis.py (478L)    → DerSimonian-Laird, forest plot, fail-safe N.
    scripts/grade.py (313L)            → GRADE certainty of evidence rating (Tier 2).
    scripts/living_review.py (240L)    → Living systematic review surveillance (Tier 3).
  references/                          → Loaded by orchestrator at specific stages.
    configuration.md, epistemology.md, deep-reading.md, iron-rule-c.md, ...
  templates/                           → Loaded with read_file at stage start.
    rq-brief.md, source-inventory.md, synthesis.md, report.md, ...
```

## Key Constraints

- **SKILL.md ≤ 500 lines.** Extract step-by-step instructions to `pipeline-detail.md`.
- **No inline template content in SKILL.md.** Always `read_file` from `templates/`.
- **`subagent-prompts.md` is canonical for sub-agent tool lists.** SKILL.md is a summary.
- **`checklist_write` order MUST match `checklist_update` IDs.** Items are position-indexed (1-based). Reordering `checklist_write` without updating all `checklist_update` calls breaks progress tracking.
- **Placeholders in braces** (`{output_dir}`, `{session_dir}`, `{SKILL_DIR}`) are interpolated by the orchestrator. See `references/placeholders.md`.
- **Python code runs via `code_execution`**, never `exec_shell`. Paths: `sys.path.insert(0, '{SKILL_DIR}/scripts')`.

## Development Workflow

1. **Read the architecture** above before making changes.
2. **Run the smoke test** after any change to scripts: `python3 scripts/smoke_test.py`
3. **After changing prompt builders**, verify all 9 templates build without error:
   ```python
   import sys; sys.path.insert(0, 'scripts')
   from helpers import build_subagent_prompt
   for name in ['dsr-bibliography','dsr-web','dsr-code','dsr-opensource',
                'dsr-da','dsr-grey','dsr-tiebreak','dsr-deep-read','dsr-deep-read-t5']:
       build_subagent_prompt(name, ...)  # provide minimal kwargs
   ```
4. **Stage additions:** new stages must be added to both `checklist_write` (in execution order matching `checklist_update` IDs) and `pipeline-detail.md`.
5. **Gate additions:** new gates must be documented in the Close table (SKILL.md) and have executable commands in `pipeline-detail.md` §Close.

## Common Pitfalls

- **Checklist ID mismatch:** `checklist_write` creates items by position. If you insert a new stage in the middle, all subsequent `checklist_update` IDs shift. Always verify with the execution-order mapping table in `pipeline-detail.md`.
- **Double braces in f-strings:** `{{var}}` produces literal `{var}`. Use single braces `{var}` when the variable should be interpolated.
- **`main_topic` bloat:** The orchestrator must extract short topic names (1-5 words) and pass as `topics=` to `build_subagent_prompt`. Never pass the full multi-sentence RQ as `main_topic` for negative queries.
- **Sub-agent output truncation:** Always require sub-agents to `write_file` complete results to `/tmp/dsr-{axis}-results.md`. Never rely on inline `agent_eval` responses.

## Commit Conventions

- Prefix: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `audit:`
- Scope in parens: `feat(opensource):`, `fix(checklist):`, `docs(epistemology):`
- The DeepSeek TUI automatically appends `Co-authored-by: DeepSeek V4 <deepseek@deepseek.com>` (v0.8.40 has a bug using `@anthropic.com` — this is a known runtime issue).
