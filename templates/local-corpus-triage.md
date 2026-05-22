---
session: {date}-{slug}
stage: 1.5
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Local Corpus Triage

**Session:** `{date}-{slug}`
**Stage:** 1.5 — Local Corpus Triage

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| `{bibliography_path}` | Config | `.deepseek/deepseek-research.toml` |
| `{keywords}` | Orchestrator | Extracted from RQ + sub-questions |
| `{N}` | Script output | `index_sources.py scan-unindexed` |

## Index Status

- **Initialized:** {yes/no}
- **Unindexed files:** {N} (see scan-unindexed output)
- **Query keywords:** {keywords}

## Query Results

{top_n} candidates from `{bibliography_path}/index/`.

| # | ID | Title | Authors | Year | Score | Relevance | Access |
|---|---|---|-------|---------|------|------|------------|--------|
| 1 | {id} | {title} | {authors} | {year} | {score} | {1-5} | {accessible/unavailable} |

## local_sources (relevance ≥ 3)

```json
[]
```

## Skipped (relevance < 3)

| ID | Title | Rationale |
|----|-------|-----------|

## Note

{0 matches: "No pre-indexed sources matched the RQ keywords. Proceeding to full discovery."}
{index missing: "Index not found. Run init and re-run this stage."}
