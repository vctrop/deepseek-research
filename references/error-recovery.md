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
