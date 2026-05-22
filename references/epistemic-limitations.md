# Epistemic Limitations

Loaded by the orchestrator at the start of every session (Stage 1).
Displayed in the final report under a mandatory `## Epistemic Limitations` section.
Do NOT inline this content in SKILL.md.

---

## What This Skill Is

`deepseek-research` is a **rapid evidence assessment** pipeline executed by a
large language model (DeepSeek V4). It is designed to be the best LLM-assisted
research system achievable within current model capabilities — but it is not a
human research team, and it is not a systematic review.

---

## Core Limitations

### L1 — LLM Judgment Replaces Human Judgment

Every stage of the pipeline involves LLM judgment calls: relevance screening
(Stage 1.5), risk-of-bias assessment (Stage 3), evidence grading (Stage 3.5),
and synthesis (Stage 4). The LLM:

- **Does not read papers the way a human does.** It processes text chunks and
  extracts patterns. It can miss nuances, context, and methodological flaws
  that a domain expert would catch.
- **Cannot verify mathematics.** When a source claims a theorem or proof, the
  LLM can report the claim but cannot verify its correctness. All M-grade
  (mathematical) claims are flagged with `⚠ MATHEMATICAL — requires human
  verification` and capped at LOW confidence.
- **Confabulates plausibility.** The LLM may rate a well-written but flawed
  methodology as higher quality than a poorly-written but sound one. The
  distinction between methodological quality and reporting quality is
  acknowledged but cannot be reliably detected by the LLM alone.

### L2 — Synthesis Gates Verify Form, Not Truth

All 18 verification gates (GATE-1 through GATE-18) check **structural
completeness**, not semantic correctness:

| Gate checks | Gate does NOT check |
|-------------|---------------------|
| Every claim has a confidence label | The confidence label is correct |
| Every STRONG claim has a verbatim citation | The verbatim quote actually supports the claim |
| No bare "validated" claims (Iron Rule C) | Qualified claims are actually supported by evidence |
| PRISMA flow diagram is present | The numbers in the diagram are accurate |
| Every source has a RoB rating | The RoB rating reflects actual bias |

A report can pass all 18 gates and still be substantively wrong. The gates
ensure the report is *well-formed*, not that it is *true*.

### L3 — Dual Screening Does Not Guarantee Independence

Stage 2.1 (Reconciliation) uses two sub-agents to independently screen sources,
with a tiebreak sub-agent for disagreements. However:

- All three sub-agents use the same base model (DeepSeek Flash).
- They share the same training data, inductive biases, and failure modes.
- True inter-rater independence requires *different raters with different
  perspectives*, which is approximated but not achieved by running the same
  model at different temperatures.

Cohen's κ reported in Stage 2.1 measures agreement between two instances of
the same model, not between independent raters. Interpret accordingly.

### L4 — Meta-Analysis Is Exploratory, Not Conclusive

When the pipeline performs quantitative synthesis (meta-analysis in Stage 4):

- **Effect sizes are extracted textually by the LLM**, not from structured data.
  The LLM reads "23.4% improvement" and extracts 23.4 — but the metric,
  baseline, and variance may not be comparable across studies.
- **Heterogeneity is estimated from reported numbers**, not from raw data.
  I² and τ² statistics are computed correctly by `meta_analysis.py`, but the
  inputs are LLM-extracted, not author-provided.
- **Forest plots are illustrative.** The `forest_plot_text` in the synthesis
  template is a visualization of the LLM's extraction, not a validated meta-
  analytic result.

**Labeling requirement:** Every meta-analytic output MUST carry the label:
> *"Exploratory quantitative synthesis — not a validated meta-analysis.
> Effect sizes extracted by LLM from heterogeneous sources. Heterogeneity
> may be underestimated. Verify individual study results before citing."*

### L5 — GRADE-for-Engineering Is an Experimental Adaptation

The GRADE framework used in Stage 4 (`references/grade-framework.md`) adapts
the GRADE system (developed for clinical medicine by BMJ, WHO, and Cochrane)
to engineering and simulation evidence. This adaptation:

- Has not been validated by an external body.
- Modifies the evidence hierarchy and domain criteria for engineering contexts.
- Should be treated as a structured thinking tool, not an authoritative rating
  system.

### L6 — Pre-registration Is a Protocol Freeze, Not a Research Protocol

The SHA256 hash of `01-rq-brief.md` recorded in MANIFEST.txt serves as a
pre-registration that prevents post-hoc changes to the research question.
However:

- It does not pre-specify the analysis plan, statistical tests, or inclusion/
  exclusion thresholds at the level expected in human research pre-registration
  (e.g., OSF, AsPredicted).
- Post-hoc refinements (new sub-questions, expanded scope) are documented but
  not prevented.
- The hash proves the RQ text didn't change — it does not prove the research
  was conducted without bias.

### L7 — The Living Corpus Accumulates Bias

When `persist_sources == true`, sources are saved to `{bibliography_path}` and
reused across sessions. If a source was misclassified as "relevant" in one
session, it persists in future sessions. The corpus has no periodic quality
audit, and GATE-7 (unindexed files) is informational only.

### L8 — Scope: Rapid Evidence Assessment, Not Systematic Review

This pipeline performs **rapid evidence assessments**, not full systematic
reviews. Key differences:

| | Systematic review | This pipeline |
|---|---|---|
| Database coverage | Multiple curated databases (Scopus, WoS, PubMed, etc.) | Web search + local bibliography + codebase |
| Screening | Dual human screening by domain experts | Dual LLM screening |
| Full-text review | Every included paper read in full by ≥1 human | Deep reading via RLM chunking (T3/T4) or direct read (T1/T2) |
| Data extraction | Structured by ≥2 independent human extractors | Single LLM extraction per source |
| Time to complete | 6–18 months | Minutes to hours |
| Confidence in conclusions | High, with remaining uncertainty explicitly characterized | Moderate — suitable for informing decisions, not for regulatory submission |

**The pipeline's conclusions are suitable for informing engineering decisions
and guiding further investigation. They are not suitable for regulatory
submission, safety-critical decisions without human review, or claims of
systematic exhaustiveness.**

---

## Report Integration

The final report (`05-report.md` or equivalent) MUST include a section
summarizing these limitations, adapted to the specific session:

```markdown
## Epistemic Limitations

*See `references/epistemic-limitations.md` for full documentation.*

This report was generated by an LLM-based rapid evidence assessment pipeline
(deepseek-research v{version}). Key limitations:

1. All relevance judgments, risk-of-bias assessments, and evidence grading
   were performed by LLM sub-agents, not human domain experts.
2. Mathematical claims from sources are flagged but not independently verified.
3. All 18 verification gates check structural completeness, not semantic
   correctness. A passing report may still contain errors.
4. Dual screening was performed by two instances of the same model —
   inter-rater independence is approximate.
5. Meta-analytic outputs (if any) are exploratory and use LLM-extracted
   effect sizes from heterogeneous sources.
6. The GRADE framework used is an experimental engineering adaptation,
   not a validated rating system.

**Suitable for:** informing engineering decisions, guiding further
investigation. **Not suitable for:** regulatory submission, safety-critical
decisions without human review.
```
