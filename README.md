# DeepSeek Research Skill

Literature review skill for DeepSeek-V4 models in the deepseek-tui environment.
Inspired by the Deep Research skill from `Imbad0202/academic-research-skills`.

## What it does

Produces a structured rapid evidence assessment from multiple source axes:

- **5 discovery axes:** bibliography, codebase, web, opensource (GitHub/GitLab), grey (arxiv, theses)
- **Deep reading:** full-document processing via RLM chunking with verbatim claim extraction
- **Professional synthesis:** meta-analysis, GRADE certainty ratings, sensitivity analysis, publication bias detection
- **Adversarial review:** Devil's Advocate checkpoint before finalization
- **Living review:** scheduled surveillance searches to keep findings current
- **23 verification gates:** structural integrity checks at pipeline close

## Quick Start

```
deep research How does in-context learning work in large language models?
```

The skill will:
1. Formulate and pre-register your research question
2. Discover sources across 3 axes (web, codebase, bibliography)
3. Verify accessibility and assess risk of bias
4. Deep-read sources with verbatim evidence extraction
5. Synthesize findings with meta-analysis and GRADE ratings
6. Run Devil's Advocate adversarial review
7. Produce a final report with plain-language summary and decision brief

**Output:** `research-reports/YYYY-MM-DD-slug/` containing 10+ files including full
reports, deep reads, and verification manifest.

## Configuration

Create `.deepseek/deepseek-research.toml` in your project root:

```toml
# Discovery axes
source_axes = ["web", "bibliography", "codebase", "opensource", "grey"]

# Output directory
output_dir = "research-reports/"

# Meta-analysis
meta_analysis = "auto"     # auto | always | never

# Deep reading
deep_reading = true

# Living review (surveillance searches)
living_review = true
surveillance_interval_days = 90

# Protocol pre-registration
protocol_registry = "local"  # local | osf | none
```

All variables have sensible defaults. See `references/configuration.md` for the full list.

## Architecture

```
SKILL.md (383L)              → Orchestrator entry point
  references/pipeline-detail.md (789L) → Step-by-step instructions
    references/subagent-prompts.md     → Sub-agent dispatch specs (canonical)
    scripts/helpers.py (367L)          → Utilities, kappa, session state
    scripts/prompts.py (502L)          → 9 sub-agent prompt builders
    scripts/meta_analysis.py (478L)    → DerSimonian-Laird, forest plot
    scripts/grade.py (313L)            → GRADE certainty ratings
    scripts/living_review.py (240L)    → Surveillance search engine
  references/                          → Epistemology, risk of bias, error recovery, ...
  templates/                           → Stage templates (rq-brief, synthesis, report, ...)
```

## Pipeline Stages

| # | Stage | Output | Condition |
|---|-------|--------|-----------|
| 1 | RQ Formulation | `01-rq-brief.md` | Always |
| 1.7 | Open-Source Decision | `01b-opensource-decision.md` | Always |
| 1.6 | Protocol Finalize | `protocol-registration.json` | `protocol_registry != "none"` |
| 1.5 | Local Corpus Triage | `01a-local-corpus-triage.md` | bibliography axis + persist_sources |
| 2 | Source Discovery | `02-source-inventory.md` | Always |
| 2.1 | Reconciliation | appended to `02-source-inventory.md` | ≥2 axes returned sources |
| 2.2 | PRESS Review | appended to `02-source-inventory.md` | web axis active |
| 2.5 | Persistence | index update | `persist_sources == true` |
| 3 | Source Verification | `03-source-verification.md` | sources ≥ 1 |
| 3.5 | Deep Source Reading | `deep-reads/*.md` | `deep_reading != false` |
| 4 | Synthesis | `04-synthesis.md` | Always |
| 4.5 | Devil's Advocate | `04a-devils-advocate.md` | Always |
| 4.6 | Stakeholder Review | `04b-stakeholder-review.md` | `stakeholder_review == true` |
| 5 | Terminal Report | `05-report.md` + plain-summary + decision-brief | Always |
| Close | Verification | 23 gates recorded in `MANIFEST.txt` | Always |

## Output Structure

```
research-reports/YYYY-MM-DD-slug/
├── MANIFEST.txt
├── 01-rq-brief.md
├── 01b-opensource-decision.md
├── 01a-local-corpus-triage.md       # only if bibliography axis active
├── protocol-registration.json       # only if protocol_registry != "none"
├── 02-source-inventory.md
├── 03-source-verification.md
├── deep-reads/                      # only if deep_reading != false
│   ├── _consolidation.md
│   └── S{id}.md
├── 04-synthesis.md
├── 04a-devils-advocate.md
├── 04b-stakeholder-review.md        # only if stakeholder_review == true
├── 05-report.md
├── 05-plain-summary.md
├── 05-decision-brief.md
├── 05-data-supplement.json          # only if quantitative data extracted
└── .session-state.json
```

## Development

See `AGENTS.md` for the development guide, architecture constraints, and common pitfalls.

Run the smoke test after changes:

```bash
python3 scripts/smoke_test.py
```

## Epistemic Scope

This is a **rapid evidence assessment**, not a systematic review. All judgments
(relevance, bias, evidence grading) are performed by LLM sub-agents. The 23
verification gates check structural completeness, not truth. Every report
includes an Epistemic Limitations section.

See `references/epistemic-limitations.md` for full disclosure.

## License

MIT — see `LICENSE.txt`.
