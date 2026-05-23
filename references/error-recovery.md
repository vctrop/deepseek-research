# Error Recovery

Loaded at pipeline start. Referenced inline when an error occurs.

| Symptom | Action |
|---|---|
| Web search returns low-quality results | Narrow query; add `site:edu` or `site:org` |
| Source URL 404/403/network error | Flag "UNVERIFIABLE"; credibility → Low for permanent errors (404/403), unchanged for transient errors (timeout, DNS) |
| Flash sub-agent timeout (>120s) | Reduce scope; shorter prompt; retry 1× |
| Flash sub-agent failure | Try alternative axis; continue with successful axes |
| Pro sub-agent timeout (Devil's Advocate) | Split checklist into 2 prompts; or orchestrator applies inline |
| IRON RULE C violation | Replace specific claims with qualified forms from `references/iron-rule-c.md` |
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
| Sub-agent returns free-text instead of structured table | Re-dispatch with stricter format instruction; if fails twice, orchestrator parses manually |
| RLM session hangs | `rlm_close` and re-open with shorter timeout |
| Config file malformed | Use defaults; warn user |
| `protocol_registry.py` not found (Stage 1.6 crashes with ImportError) | Skip Stage 1.6; log warning; continue with local SHA256-only pre-registration |
| `helpers.py` not found (multiple stages affected) | Fatal — abort pipeline; skill installation is corrupted |
| Scipy not available (kappa computation) | Fall back to manual contingency-table computation in helpers.py (already built-in) |
| **TUI freeze / unresponsive interface** | **Do NOT force-close without reading this.** Progress is auto-saved to `.session-state.json` after every stage. If force-close is unavoidable: (1) kill the process, (2) open a new session, (3) run `deepseek-research` with the same slug — it will auto-resume from the last completed stage. If no `.session-state.json` exists, check MANIFEST.txt for the last completed stage and resume manually. |
| **agent_eval timeout (sub-agent blocked > timeout_ms)** | Orchestrator auto-recovers: (1) reads sub-agent output file if available, (2) re-dispatches ONCE with reduced scope, (3) if still times out, marks axis/source as DEGRADED/FAILED and continues. Pipeline never blocks indefinitely — all `agent_eval(block=true)` calls have `timeout_ms` (120s for tiebreak, 180s for discovery/DA, 300s for deep reading). |
| **Context budget exceeded mid-pipeline (TUI freeze risk)** | Two thresholds: (1) ≥120K tokens → orchestrator warns "Consider `/compact` after this stage." (2) ≥180K tokens → orchestrator PAUSES, writes session state, and requests `/compact`. After compaction: read `.session-state.json`, skip completed stages, resume from current stage. |
| **Deep read batch timeout (Stage 3.5)** | Sub-agent timeout (300s) → source marked FAILED. Orchestrator continues with remaining sources. Failed sources are recorded in `_consolidation.md` with reason "deep-read failed — timeout." Synthesis proceeds with available evidence. |
| **Session state file corrupt** | Delete `.session-state.json`. Pipeline treats as fresh session. Check MANIFEST.txt for last completed stage to avoid re-executing completed work. |
| **Sub-agent returns inline (no write_file output)** | Web/Opensource sub-agents MUST write to `/tmp/dsr-*-results.md`. If file missing: orchestrator attempts to parse sub-agent inline response. If that fails: re-dispatch ONCE. If still fails: mark axis DEGRADED. |
| **Multiple sub-agents timeout in same stage** | If ALL sub-agents in a stage time out: (1) write partial output with what was recovered, (2) note "ALL axes DEGRADED" in session state, (3) skip to next stage. Synthesis will note "insufficient source discovery — {N} axes degraded." |
| **Session has < 5 core output files (pipeline truncated)** | GATE-21 failure. Change MANIFEST status to "DEGRADED — pipeline truncated." Do NOT claim "complete" or "completed." The session is unrecoverable as-is; re-run the RQ from scratch after compaction or in a fresh context. |
| **Deep reading skipped despite `deep_reading=true`** | GATE-22 failure. If context budget was the cause: compact, then re-dispatch Stage 3.5 for remaining sources. If sources are inaccessible: mark them and continue. Never write "deep reading skipped" as an acceptable outcome — it's a pipeline failure that requires either retry or an explicit config change to `deep_reading=false`. |
| **Batch manifest claims completion but files missing** | The manifest was written optimistically (anti-pattern #18). Read each claimed RQ's session dir via `list_dir`. For any with < 5 core files, mark as "DEGRADED" in manifest. Re-run those RQs after compaction. |