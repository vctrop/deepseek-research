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
SKILL.md (381L)              → Orchestrator entry point
  references/pipeline-detail.md (782L) → Step-by-step instructions
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

| # | Stage | Output |
|---|-------|--------|
| 1 | RQ Formulation | `01-rq-brief.md` |
| 1.7 | Open-Source Decision | `01b-opensource-decision.md` |
| 1.6 | Protocol Finalize | `protocol-registration.json` |
| 2 | Source Discovery | `02-source-inventory.md` |
| 3 | Source Verification | `03-source-verification.md` |
| 3.5 | Deep Source Reading | `deep-reads/*.md` |
| 4 | Synthesis | `04-synthesis.md` |
| 4.5 | Devil's Advocate | `04a-devils-advocate.md` |
| 5 | Terminal Report | `05-report.md` + plain-summary + decision-brief |
| Close | Verification | 23 gates recorded in `MANIFEST.txt` |

## Output Structure

```
research-reports/YYYY-MM-DD-slug/
├── MANIFEST.txt
├── 01-rq-brief.md
├── 01b-opensource-decision.md
├── protocol-registration.json
├── 02-source-inventory.md
├── 03-source-verification.md
├── deep-reads/
│   ├── _consolidation.md
│   └── S{id}.md
├── 04-synthesis.md
├── 04a-devils-advocate.md
├── 05-report.md
├── 05-plain-summary.md
├── 05-decision-brief.md
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
