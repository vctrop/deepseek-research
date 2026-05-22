# GRADE Certainty of Evidence — Engineering Adaptation

Loaded by the orchestrator at Stage 4. Rates the overall certainty of evidence
for each key finding using an adapted GRADE (Grading of Recommendations,
Assessment, Development, and Evaluation) framework.

> **⚠ EXPERIMENTAL ADAPTATION NOTICE**
>
> Original GRADE: clinical medicine (BMJ, WHO, Cochrane) — validated through
> decades of use, endorsed by >100 organizations worldwide.
>
> This adaptation: engineering/simulation evidence, with modified evidence
> hierarchy and domain criteria. **This adaptation has not been validated by
> any external body.** It is a structured thinking tool, not an authoritative
> rating system. Use it to organize your reasoning about evidence quality,
> not to claim GRADE-certified certainty.
>
> See `references/epistemic-limitations.md` §L5 for the full disclosure.

Original GRADE: clinical medicine (BMJ, WHO, Cochrane).
This adaptation: engineering/simulation evidence, with modified evidence
hierarchy and domain criteria.

---

## Evidence Hierarchy (Starting Point)

For engineering research, the starting certainty depends on study design:

| Study design | Starting certainty | Rationale |
|-------------|-------------------|-----------|
| Formal verification (proof, model checking) | ⊕⊕⊕⊕ HIGH | Mathematical certainty within stated assumptions |
| Multiple independent controlled experiments | ⊕⊕⊕⊕ HIGH | Replicated empirical evidence |
| Single controlled experiment + simulation validation | ⊕⊕⊕⊝ MODERATE | Empirical + computational convergence |
| Simulation with rigorous V&V (ASME V&V 40) | ⊕⊕⊕⊝ MODERATE | Validated computational model |
| Simulation without V&V / observational data | ⊕⊕⊝⊝ LOW | Unvalidated model; association not causation |
| Expert opinion, blog post, single-source | ⊕⊝⊝⊝ VERY LOW | Anecdotal; no systematic evidence |

---

## Downgrade Domains (-1 or -2 per domain)

| Domain | -1 (Serious) | -2 (Very Serious) |
|--------|-------------|-------------------|
| **Risk of bias** | Overall RoB = High for ≥1 contributing study | Overall RoB = Critical for ≥1 contributing study |
| **Inconsistency** | I² > 75% OR point estimates in opposite directions | I² > 90% with no identifiable subgroup explanation |
| **Indirectness** | Different population, intervention, or outcome than RQ (minor mismatch) | Substantially different context (major mismatch) |
| **Imprecision** | CI crosses decision threshold OR total N < 50 | CI includes both appreciable benefit and harm |
| **Publication bias** | ≥50% sources from same group OR funnel asymmetry suspected | Strong evidence of selective reporting (Egger p < 0.05, or all studies from same funding source) |

---

## Upgrade Domains (+1 or +2 per domain)

| Domain | +1 (Large effect) | +2 (Very large effect) |
|--------|-------------------|----------------------|
| **Large effect** | Pooled effect > 2× baseline with no plausible confounders | Pooled effect > 5× baseline |
| **Dose-response** | Gradient consistent across ≥3 fidelity levels | Monotonic dose-response in ≥5 levels |
| **Opposing confounding** | All plausible confounders would reduce the effect (i.e., true effect likely larger) | Confounders would reverse the direction |

---

## Final GRADE Rating

| Certainty | Symbol | Meaning |
|-----------|--------|---------|
| **High** | ⊕⊕⊕⊕ | Very confident the true effect lies close to the pooled estimate |
| **Moderate** | ⊕⊕⊕⊝ | Moderately confident; true effect likely close but may be substantially different |
| **Low** | ⊕⊕⊝⊝ | Limited confidence; true effect may be substantially different |
| **Very Low** | ⊕⊝⊝⊝ | Very little confidence; the true effect is likely substantially different |

---

## Application Procedure (Stage 4)

1. After meta-analysis (or after consensus assessment for qualitative findings):
   a. For each key finding, determine starting certainty from study design.
   b. Apply downgrades based on RoB (Stage 3), I² (meta-analysis), indirectness.
   c. Apply upgrades if warranted (large effect, dose-response, opposing confounding).
   d. Record final GRADE rating with justification.

2. Thinking: moderate — judgment required for indirectness and publication bias.

3. Write GRADE rating per finding in `04-synthesis.md` and `05-report.md`.

---

## Template Output

```markdown
### K1: {finding_title}
...
**GRADE Certainty:** ⊕⊕⊕⊝ MODERATE
**Starting point:** ⊕⊕⊕⊕ HIGH (multiple controlled experiments)
**Downgraded for:** risk of bias (-1, S3 had incomplete blinding)
**Upgraded for:** — none
```
