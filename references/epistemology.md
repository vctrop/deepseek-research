# Epistemology Reference

Loaded by the orchestrator in Stage 1 (RQ formulation) and Stage 3 (verification).
Do NOT inline this content in SKILL.md — reference by path.

---

## Knowledge Type Taxonomy

Every research question falls into one or more categories. Classify the RQ before
formulating sub-questions — the category determines what counts as valid evidence.

| Category | Question shape | Valid evidence | Invalid inference |
|----------|---------------|----------------|-------------------|
| **Declarative** | "What is X?" / "What properties does X have?" | Empirical measurement, formal definition, authoritative taxonomy | Opinion without measurement |
| **Procedural** | "How to do X?" / "What algorithm solves Y?" | Working implementation, benchmarked comparison, convergence proof | Claimed capability without demonstration |
| **Causal** | "Does X cause Y?" / "What is the effect of X on Y?" | Controlled experiment, natural experiment, Granger test, do-calculus | Correlation without mechanism or control |
| **Predictive** | "How much Y given X?" / "What is the probability of Z?" | Out-of-sample validation, proper scoring rules, calibration plots | In-sample fit without holdout |

**Procedure:** In Stage 1, after FINER scoring, classify the RQ. If spanning multiple
categories, each sub-question gets its own classification.

---

## Evidence Strength Matrix (claim-level, not source-level)

Source credibility and evidence strength are **orthogonal**. A high-tier source can
contain weak claims; a low-tier source can contain strong claims.

Evaluate each claim extracted in Stage 4 with this 2×2 matrix:

|  | **Peer-reviewed venue** | **Not peer-reviewed** |
|--|------------------------|----------------------|
| **Empirical evidence** (measurements, experiments, benchmarks) | **STRONG** — converges with scientific consensus | **MODERATE** — requires independent replication to upgrade |
| **Theoretical evidence** (proofs, derivations, formal analysis) | **STRONG** — verified by peer math review | **MODERATE** — verifiable by reader; flag if proof is incomplete |
| **Assertion without evidence** (opinion, "known fact", citation without data) | **WEAK** — expert opinion, not evidence | **WEAK** — single-source claim, requires cross-reference |

**Usage:** In Stage 4 synthesis, each K-finding must cite its evidence strength
independently from source credibility:

```
### K1: Gravitational acceleration near Earth surface is ~9.81 m/s²
**Sources:** S3 (blog post, LOW source tier), S7 (textbook, MEDIUM source tier)
**Evidence strength:** STRONG — converged measurement across 5 independent methods, all peer-reviewed primary sources cited by S7
```

---

## Primary vs. Secondary vs. Tertiary Sources

| Level | Definition | Credibility implication |
|-------|-----------|------------------------|
| **Primary** | Original research reporting new data/analysis | Can be evaluated on its own methodology |
| **Secondary** | Review, synthesis, or meta-analysis of primary sources | Credibility depends on selection method and primary sources cited |
| **Tertiary** | Textbook, encyclopedia, documentation summarizing secondary sources | Useful for consensus; not evidence for novel claims |

**Procedure:** In Stage 3 verification, classify each source as primary/secondary/tertiary.
Primary sources receive higher weight for novel claims; secondary sources for consensus claims.

---

## Operationalization

Every RQ construct must have **observable criteria** of satisfaction. Abstract
concepts without operational definitions produce unverifiable findings.

**Template (add to 01-rq-brief.md):**
```markdown
## Operational Definitions

| Construct | Observable criterion | Measurement method |
|-----------|---------------------|-------------------|
| "state of the art" | Most cited method in last 3 years OR best benchmark score on standard dataset | Citation count (Semantic Scholar) OR PapersWithCode benchmark |
| "efficient" | Time complexity ≤ O(n log n) OR throughput ≥ X ops/sec on reference hardware | Asymptotic analysis OR benchmark |
| "robust" | Maintains ≥90% performance under ±30% input perturbation | Sensitivity analysis |
```

If a construct cannot be operationalized, flag it in the RQ brief as a limitation.

---

## Active Search for Contrary Evidence

Confirmation bias is the dominant failure mode in LLM-assisted research.
The pipeline MUST actively search for evidence that contradicts the working hypothesis.

**Stage 2 — mandatory negative queries:**

For every research topic T, the discovery sub-agents must include:

| Query pattern | Rationale |
|--------------|-----------|
| `"limitations of {T}"` | Known weaknesses acknowledged by proponents |
| `"criticism of {T}"` | External critique |
| `"failure cases of {T}"` | Documented failures |
| `"{T} does not work"` or `"{T} fails when"` | Negative results |
| `"alternatives to {T}"` | Competing approaches (may be superior) |

**Stage 2 — reporting:** Sub-agents must report a `negative_search` section:
```json
{
  "negative_search": {
    "queries_attempted": ["limitations of co-kriging", "co-kriging fails when"],
    "results_found": 3,
    "results_summary": "Instability with >5 fidelity levels (Le Gratiet 2014), poor extrapolation (Perdikaris 2017)"
  }
}
```

If 0 results: document as "No contrary evidence found for queries X, Y, Z."

---

## Saturation Criterion

When to stop source discovery:

- **Quantitative:** Last N sources (N=5, configurable) add no new claims not already
  covered by previous sources.
- **Qualitative:** Three consecutive keyword variations on the dominant search engine
  return only already-discovered URLs in the top 10.
- **Default ceiling:** 30 sources per axis (configurable). Beyond this, marginal
  contribution is typically negligible for a rapid evidence assessment.

Declare saturation in `02-source-inventory.md`:
```markdown
## Saturation
- **Criterion met:** Last 5 web sources (W12-W16) added no new claims.
- **Sources capped:** No — saturation reached naturally at 16.
```

---

## Reproducibility & Audit Trail

Every stage output SHALL include a metadata header enabling independent reproduction:

```markdown
---
session: {date}-{slug}
stage: N
skill_version: {git_hash_of_skill_dir}
model: {model_id}
model_temperature: {temperature_if_known}
timestamp_utc: {ISO8601}
---
```

**Stage 2 — search log:** `02-source-inventory.md` must include a search audit table:

| Axis | Query | Engine | Date | Results returned | Results used |
|------|-------|--------|------|-----------------|--------------|
| web | "co-kriging multi-fidelity" | Bing | 2026-05-21 | 1.2M | 8 |
| web | "limitations of co-kriging" | Bing | 2026-05-21 | 45K | 3 |

---

## Pre-registration

The `01-rq-brief.md` after Stage 1 completion serves as a pre-registration.
Compute its SHA256 and record it in the session MANIFEST. Any post-Stage-2
changes to RQ, scope, or inclusion criteria must be documented as:

```markdown
## Post-hoc Refinements
- **Original SHA256:** `abc123...`
- **Change:** Expanded scope to include X after discovering source S7
- **Justification:** Source S7 revealed X as prerequisite to answering original RQ
- **Impact:** New sub-question SQ3 added; may require additional discovery
```

---

## Review Type Declaration

Stage 1 must declare the review methodology:

```markdown
## Review Type
- [ ] **Systematic review** — PRISMA-based, exhaustive within defined databases, reproducible
- [x] **Rapid evidence assessment** — Structured search, limited databases, faster turnaround
- [ ] **Scoping review** — Mapping breadth of evidence, not depth
- [ ] **Narrative review** — Expert-led, selective, interpretive
```

The choice constrains the strength of conclusions the report can draw. A rapid
assessment cannot claim systematic exhaustiveness.

---

## Consensus Assessment Rules

| Consensus label | Condition |
|----------------|-----------|
| **CONSENSUS** | ≥3 independent HIGH/STRONG sources agree; ≤1 MODERATE dissenter; 0 STRONG dissenters |
| **MAJORITY** | ≥60% of sources agree; dissent exists but is minority |
| **DIVERGENT** | Competing camps with ≥2 sources each; no clear winner |
| **INSUFFICIENT** | <3 sources total OR all LOW/WEAK |

Never label as CONSENSUS when all agreeing sources share the same author group,
institution, or funding source (COI contamination).

---

## Risk of Bias → Evidence Strength

See `references/risk-of-bias.md` §RoB → Evidence Strength Mapping for the
full modifier table. Summary: Low RoB → no change; Some concerns → drop one
evidence strength level; High → drop two levels; Critical → exclude from evidence.
