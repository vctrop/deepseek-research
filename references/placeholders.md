# Placeholder Resolution Table

Loaded by the orchestrator at Stage 1 for reference. Documents every
placeholder used across the pipeline — which stage populates it, and from where.

Do NOT inline this content in SKILL.md.

---

## Stage 1 — RQ Formulation

| Placeholder | Populated by | Source |
|---|---|---|
| `{output_dir}` | Config | `.deepseek/deepseek-research.toml` or `"research-reports/"` |
| `{date}` | Orchestrator | System date (ISO 8601 YYYY-MM-DD) |
| `{slug}` | Orchestrator | Generated from RQ: lowercase, hyphens, ≤50 chars |
| `{session_dir}` | Orchestrator | `{output_dir}/{date}-{slug}/` |
| `{RQ}` / `{RQ_TEXT}` | Orchestrator | `request_user_input` — full research question |
| `{SQ1}`, `{SQ2}`, ... | Orchestrator | Derived from RQ decomposition |
| `{bibliography_path}` | Config | `.deepseek/deepseek-research.toml` |
| `{source_axes}` | Config | `.deepseek/deepseek-research.toml` |
| `{persist_sources}` | Config | `.deepseek/deepseek-research.toml` |
| `{deep_reading}` | Config | `.deepseek/deepseek-research.toml` (default: `true`) |
| `{agreement_threshold}` | Config | `.deepseek/deepseek-research.toml` (default: `0.6`) |
| `{living_review}` | Config | `.deepseek/deepseek-research.toml` |
| `{surveillance_interval_days}` | Config | `.deepseek/deepseek-research.toml` (default: `90`) |
| `{stakeholder_review}` | Config | `.deepseek/deepseek-research.toml` |
| `{SKILL_DIR}` | Orchestrator | `~/.deepseek/skills/deepseek-research/` |
| `{skill_git_hash}` | Orchestrator | `git rev-parse HEAD` in `{SKILL_DIR}` |
| `{model_id}` | Orchestrator | Runtime model identifier |
| `{iso8601_utc}` | Orchestrator | System clock |
| `{session_index}` | Config | `.deepseek/deepseek-research.toml` or `"deep-search-sessions.json"` |

## Stage 1.6 — Protocol Finalize

| Placeholder | Populated by | Source |
|---|---|---|
| `{protocol_registry}` | Config | `.deepseek/deepseek-research.toml` (`"none"`, `"osf"`, or `"local"`) |
| `{osf_token}` | Config | `.deepseek/deepseek-research.toml` (if osf) |
| `{osf_project_id}` | Config | `.deepseek/deepseek-research.toml` (if osf) |
| `{protocol_dict}` | Orchestrator | Built from `01-rq-brief.md` content |
| `{rq_sha256}` | Orchestrator | `helpers.compute_sha256()` of `01-rq-brief.md` |

## Stage 1.5 — Local Corpus Triage

| Placeholder | Populated by | Source |
|---|---|---|
| `{comma_separated_keywords}` | Orchestrator | Extracted from RQ via `code_execution` |
| `{local_sources}` | Orchestrator | LLM relevance judgment on index query results |
| `{LOCAL_SOURCES_BLOCK}` | Orchestrator | Formatted `local_sources` for template |
| `{local_sources_json}` | Orchestrator | JSON serialization of `local_sources` |

## Stage 2 — Source Discovery

| Placeholder | Populated by | Source |
|---|---|---|
| `{main_topic}` | Orchestrator | Core topic extracted from RQ |
| `{rq_summary}` | Orchestrator | Concise summary of RQ for sub-agent prompts |
| `{review_type}` | Orchestrator | From `01-rq-brief.md` §Review Type |
| `{sources_count}` | Orchestrator | Count of merged sources after discovery |

## Stage 2.1 — Reconciliation

| Placeholder | Populated by | Source |
|---|---|---|
| `{rater1_ids}` | Orchestrator | Source IDs from rater 1 |
| `{rater2_ids}` | Orchestrator | Source IDs from rater 2 |
| `{all_ids}` | Orchestrator | Union of rater1_ids + rater2_ids |
| `{threshold}` | Config | `agreement_threshold` from config |

## Stage 3 — Source Verification

| Placeholder | Populated by | Source |
|---|---|---|
| `{sources_for_verification}` | Orchestrator | Sources from Stage 2 inventory |
| `{RoB_ratings}` | Orchestrator | Per-source risk-of-bias assessment |

## Stage 3.5 — Deep Source Reading

| Placeholder | Populated by | Source |
|---|---|---|
| `{source_id}` | Orchestrator | Per-source ID from Stage 2 inventory (S1, S3, W7, ...) |
| `{source_title}` | Deep reader sub-agent | From source metadata |
| `{source_path_or_url}` | Orchestrator | File path or URL from Stage 2 inventory |
| `{n_chunks}` / `{total_chunks}` | Deep reader sub-agent | RLM chunking output |
| `{coverage_pct}` | Deep reader sub-agent | Percentage of document processed |
| `{skipped_sections}` | Deep reader sub-agent | Sections skipped (T4 only) |

## Stage 4 — Synthesis

| Placeholder | Populated by | Source |
|---|---|---|
| `{K1}`, `{K2}`, ... | Orchestrator | Key findings (K-findings) |
| `{verdict_summary}` | Orchestrator | Summary verdict on RQ |
| `{I2}` | `meta_analysis.py` | I² heterogeneity statistic |
| `{tau2}` | `meta_analysis.py` | τ² between-study variance |
| `{Q}` | `meta_analysis.py` | Cochrane's Q |
| `{Q_df}` | `meta_analysis.py` | Q degrees of freedom |
| `{Q_pvalue}` | `meta_analysis.py` | Q p-value |

## Stage 4.5 — Devil's Advocate

| Placeholder | Populated by | Source |
|---|---|---|
| `{da_findings}` | DA sub-agent | Adversarial review output |

## Stage 5 — Terminal Report

| Placeholder | Populated by | Source |
|---|---|---|
| `{version}` | Orchestrator | `skill_git_hash` from Stage 1 |
| `{decision_1}`, `{decision_2}` | Orchestrator | From `01-rq-brief.md` §Decisions Depending on This Research |

## Cross-stage

| Placeholder | Populated by | Source |
|---|---|---|
| `{doi_url}` | Orchestrator | OSF registration DOI (if applicable) |
| `{INTEGRATION_CHECKS}` | Config | `.deepseek/deepseek-research.toml` |
| `{available_axes}` | Orchestrator | Human-readable list derived from `source_axes` (e.g. "web, codebase") |
| `{search_engine}` | Orchestrator | Web search backend identifier (e.g. "Bing", "DuckDuckGo") |
