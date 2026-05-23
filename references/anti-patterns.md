# Anti-patterns

Loaded at pipeline start and referenced inline. Do NOT duplicate in SKILL.md.

| # | Anti-pattern | Cost | Correction |
|---|---|---|---|
| 1 | Pro sub-agent for discovery | 12× cost, >120s timeout | Use Flash |
| 2 | `read_file` of bibliography >10KB | 15-25K tokens | Use RLM |
| 3 | Re-reading prior stage files | Breaks prefix cache | Reference by § |
| 4 | `grep -P` for IRON RULE C | PCRE dependency | Use `grep_files` |
| 5 | `fork_context: true` | +50K tokens copied | Always `false` |
| 6 | Sub-agent for 1 read (generic) | +2K overhead | Do inline. **Exception:** Devil's Advocate — adversarial reasoning justifies overhead. |
| 7 | Not closing RLM sessions | Resource leak | `rlm_close` after use |
| 8 | `checklist_write` on every status update | Array rewrite | One `checklist_write` at pipeline start; `checklist_update(id, status)` for incremental progress |
| 9 | Skipping Stage 1.5 when bibliography axis active | Local sources not reused | Always run 1.5 if bibliography is in source_axes |
| 10 | Forgetting persistence_manifest in dsr-bibliography prompt | GATE-5 fails | Include manifest format in sub-agent prompt |
| 11 | Shell interpolation of user-controlled strings | Shell injection risk | Use `code_execution` (Python) for any command interpolating user/RQ/LLM-generated strings |
| 12 | Confusing source credibility with evidence strength | Claims inherit source tier without independent assessment | Use 2×2 Evidence Strength Matrix from `references/epistemology.md` |
| 13 | No negative search queries | Confirmation bias; missing contrary evidence | Include mandatory negative queries in Stage 2 per `references/epistemology.md` |
| 14 | Qualitative RQ forced into quantitative templates | Extracted constants table with "N/A" entries is noise | Adapt templates to RQ type; omit inapplicable sections |
| 15 | `reasoning_effort` passed as API parameter | Not a supported parameter in `agent_open` or tool calls | Use as thinking directive within the prompt body: "Think carefully about..." instead |
| 16 | **Batch fatigue — >3 RQs without inter-RQ compaction** | Context saturation by RQ 4+ causes silent degradation to hallucinated "rapid assessment" mode (skips discovery, verification, deep reading, DA — writes MANIFEST + synthesis from memory). Output files evaporate. | After every 3 RQs in batch mode, request `/compact` + "continue deep research batch". Never run >3 RQs without context reset. If context indicator ≥60% mid-batch, compact immediately. |
| 17 | **"Rapid assessment" as pipeline escape hatch** | Orchestrator invents a non-existent "rapid assessment" shortcut when context is exhausted, skipping Stages 2-5 and declaring "complete." This mode is NOT defined in SKILL.md. | There is no "rapid assessment" mode. If the pipeline cannot execute all stages, it MUST either (a) compact and resume, or (b) produce an honest INCOMPLETE manifest. Never write "complete (rapid assessment)" — this is a hallucinated status. |
| 18 | **MANIFEST written before output files verified** | Batch manifest or session MANIFEST claims "completed" with source/finding counts that don't match disk. Files claimed present are actually missing. | Write MANIFEST only AFTER all output files are written and verified non-empty. In batch mode, update `_batch-manifest.json` only after `list_dir` confirms expected files exist. |
| 19 | **Deep reading skipped without consequence** | `deep_reading=true` in config but `deep-reads/` is empty or absent. Orchestrator writes "deep reading skipped" in MANIFEST and passes GATE-18 anyway. | If `deep_reading != false`, GATE-1 must check that `deep-reads/_consolidation.md` exists and is non-empty. Absent deep reads when required → FAIL. |
| 20 | **Midnight timestamps and literal placeholders in outputs** | `timestamp_utc: 2026-05-23T00:00:00Z`, `skill_version: SKILL_DIR_HASH`, PRISMA `(Placeholder)` survive into final outputs. | Run `helpers.resolve_placeholders()` at Stage 1 and verify all braces are gone. Add a gate that greps for unresolved `{`, `PLACEHOLDER`, and `T00:00:00Z` in output files. |
