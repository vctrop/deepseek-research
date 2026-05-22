# Configuration

The host project defines variables in `.deepseek/deepseek-research.toml`.
If absent, defaults are used. User can override per-session in the prompt.

## Variables

| Variable | Default | Description |
|---|---|---|
| `source_axes` | `["bibliography", "codebase", "web"]` | Discovery axes. Add `"grey"` for grey literature (arxiv, techrxiv, theses, conferences) |
| `bibliography_path` | `"bibliography/"` | Path to bibliography index |
| `output_dir` | `"research-reports/"` | Session output directory |
| `session_index` | `"deep-search-sessions.json"` | JSON array of session history |
| `persist_sources` | `true` | When `true`, web-discovered sources are persisted to the local corpus |
| `integration_checks` | `[]` | Shell commands for final verification |
| `max_sources_per_axis` | `30` | Hard ceiling on sources per discovery axis |
| `saturation_window` | `5` | Consecutive sources with no new claims before declaring saturation |
| `dual_screening` | `false` | When `true`, bibliography axis dispatches 2 independent screeners with tiebreak resolution |
| `agreement_threshold` | `0.60` | Cohen's κ threshold for inter-rater reliability WARNING (0.0-1.0) |
| `protocol_registry` | `"local"` | Protocol pre-registration target: `"osf"`, `"local"`, or `"none"` |
| `osf_token` | `""` | OSF personal access token (required if `protocol_registry = "osf"`) |
| `osf_project_id` | `""` | OSF project GUID (required if `protocol_registry = "osf"`) |
| `meta_analysis` | `"auto"` | `"auto"` (trigger on ≥3 quantitative sources), `"always"`, or `"never"` |
| `stakeholder_review` | `false` | When `true`, prompt user for feedback on draft findings before final report |
| `living_review` | `false` | When `true`, enable update cycles with surveillance searches |
| `surveillance_interval_days` | `90` | Days between surveillance searches for living reviews |

## Session Index Format

```json
[
  {
    "slug": "co-kriging-estado-da-arte",
    "date": "2026-05-21",
    "rq": "Estado da arte em co-kriging para multi-fidelity surrogates?",
    "verdict": "K1: Co-kriging dominates for ≤3 fidelity levels; K2: NARGP better for high-dimensional inputs",
    "sources_used": 12,
    "review_type": "rapid_evidence_assessment",
    "rq_sha256": "abc123def456..."
  }
]
```

Entry ≤ 280 chars in `rq` field.

## Example: Full Config

```toml
# .deepseek/deepseek-research.toml
source_axes = ["bibliography", "codebase", "web"]
bibliography_path = "bibliography/"
output_dir = "research-reports/"
session_index = "deep-search-sessions.json"
persist_sources = true
integration_checks = ["cargo test --workspace"]
max_sources_per_axis = 30
saturation_window = 5
```

## Example: Project Without Bibliography

```toml
source_axes = ["codebase", "web"]
output_dir = "research-reports/"
session_index = "deep-search-sessions.json"
persist_sources = false
integration_checks = ["npm test", "npm run lint"]
```

## Loading Procedure (Stage 1)

1. Check for `.deepseek/deepseek-research.toml`.
2. If present, parse with `read_file` and extract variables.
3. If absent, use defaults.
4. User overrides from the prompt take precedence.
5. Store resolved config as a Python dict via `code_execution` for use in
   template interpolation throughout the pipeline.
