# Context Budget

| Trigger | Threshold | Action |
|---|---|---|
| Warning | ~60% TUI context indicator | "Context pressure. Consider `/compact` after this stage." |
| Halt | ~80% TUI context indicator | Pause. Save state. Resume with `/compact` + "continue deep research {slug}" |

## Prefix Cache Discipline

- Reference by path + §, never re-read between stages
- Append, never reorder messages
- Stable sections (evidence strength matrix, credibility tiers, IRON RULE C) are
  loaded once from `references/` and referenced — never re-read
- Never `fork_context: true` — each sub-agent gets a fresh context
- Templates are read once per stage via `read_file`; fill inline without re-reading

## RLM Usage Thresholds

| Input size | Strategy |
|---|---|
| < 5KB | Direct `read_file` |
| 5-50KB | `read_file` with `start_line`/`max_lines` pagination |
| > 50KB or > 20 sources | RLM session: `rlm_open` → `rlm_configure(output_feedback="metadata")` → `rlm_eval` → `rlm_close` |
| > 100 sources | RLM with `sub_query_batch(dependency_mode="independent")` for verification |

## Compact Recovery

After `/compact`, the orchestrator resumes by:
1. Reading the session manifest (`{session_dir}/MANIFEST.txt`)
2. Checking the checklist for last completed stage
3. Continuing from the next pending stage
4. Never re-executing completed stages unless corruption is detected
