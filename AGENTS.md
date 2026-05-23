# AGENTS.md — deepseek-research Development Guide (v3.0)

## Architecture

```
SKILL.md (~220L)          → Orchestrator entry point. 5-stage pipeline.
  references/pipeline-detail.md (~290L) → Step-by-step per stage.
    references/subagent-prompts.md (~30L) → 2 sub-agent dispatch specs.
    scripts/helpers.py (~170L)            → SHA256, saturation, placeholder resolution, prompt dispatcher.
    scripts/prompts.py (~70L)             → 2 sub-agent prompt builders (bibliography, code).
  references/                          → Risk of bias, deep reading, error recovery, Iron Rule C.
  templates/                           → rq-brief, source-inventory, source-verification, synthesis, report, source-deep-read.
```

## Key Constraints

- **SKILL.md ≤ 250 lines.** Detail goes in `references/pipeline-detail.md`.
- **No inline template content in SKILL.md.** Always `read_file` from `templates/`.
- **`subagent-prompts.md` is canonical for sub-agent tool lists.**
- **Placeholders in braces** (`{output_dir}`, `{session_dir}`, `{SKILL_DIR}`) are interpolated by the orchestrator.
- **Python code runs via `code_execution`**, never `exec_shell`. Paths: `sys.path.insert(0, '{SKILL_DIR}/scripts')`.
- **Resume from interruption:** Check stage output files — no `.session-state.json`. If `03-source-verification.md` exists, resume from Stage 4.

## Development Workflow

1. **Read the architecture** above before making changes.
2. **Run the smoke test** after any change to scripts: `python3 scripts/smoke_test.py`
3. **After changing prompt builders**, verify both templates build:
   ```python
   import sys; sys.path.insert(0, 'scripts')
   from helpers import build_subagent_prompt
   build_subagent_prompt('dsr-bibliography', rq_text='test', bibliography_path='bib/', main_topic='test')
   build_subagent_prompt('dsr-code', rq_text='test')
   ```
4. **Stage additions:** new stages must be added to both SKILL.md and `pipeline-detail.md`.
5. **Gate additions:** new gates must be documented in the Close table (SKILL.md) and have executable commands in `pipeline-detail.md` §Close.

## Common Pitfalls

- **`main_topic` bloat:** Extract short topic names (1-5 words) and pass as `topics=` to `build_subagent_prompt`. Never pass full RQ as `main_topic`.
- **Sub-agent output truncation:** Always require sub-agents to `write_file` complete results to `/tmp/dsr-{axis}-results.md`.
- **RLM lifecycle:** Sessions must be opened, used, and closed. Max 1 active at a time. Close in cleanup on error.
- **Clone safety:** Verify directory doesn't exist before clone, or use `git pull --ff-only`. Timeout 120s.

## Commit Conventions

- Prefix: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `audit:`
- Scope in parens: `feat(bibliography):`, `fix(pipeline):`, `docs(templates):`
