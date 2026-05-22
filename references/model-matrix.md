# Model Matrix

Cost estimates are approximate — V4 Flash is ~$0.14/M input tokens, V4 Pro varies.
Actual costs depend on prompt length, thinking budget, and cache hit rate.

| Stage | Executor | Model | Thinking directive | Est. cost |
|---|---|---|---|---|
| 1 — RQ Formulation | Orchestrator | Pro | "Think carefully about the research question structure and FINER criteria" | — |
| 1.5 — Local Corpus Triage | Orchestrator | Pro | Minimal (keyword extraction, relevance scoring) | — |
| 2 — Discovery (1-3×) | Sub-agents | **Flash** | Minimal (mechanical search + table formatting) | ~$0.001-0.003 |
| 2.5 — Persistence | Orchestrator | Pro | Minimal (manifest parsing, script orchestration) | — |
| 3 — Verification | Orchestrator + RLM | Pro + Flash | Moderate (credibility assessment, COI judgment) | — |
| 4 — Synthesis | Orchestrator | Pro | "Think carefully about evidence strength, consensus, and gaps" | — |
| 4.5 — Devil's Advocate | Sub-agent | **Pro** | "Think adversarially — find every weakness in the synthesis" | ~$0.02-0.05 |
| 5 — Terminal Report | Orchestrator | Pro | Minimal (template filling, formatting) | — |
| Close — Verification | Orchestrator | Pro | Minimal (grep, file checks) | — |

**Thinking budget guidance:**

- **"Think carefully about..."** — Deep reasoning: architecture, epistemology, adversarial evaluation
- **Minimal** — Keep thinking tokens sparse; the task is mechanical
- **Moderate** — Judgment calls needed but not deep analysis

These are directives embedded in the prompt body, NOT API parameters.
The `agent_open` tool does not accept a `reasoning_effort` parameter.
