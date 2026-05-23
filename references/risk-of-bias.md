# Risk of Bias Assessment

Loaded by the orchestrator at Stage 3. Replaces the ad-hoc COI Register with a
structured, domain-appropriate risk of bias matrix. Each source is classified by
study type, then assessed on type-specific domains.

---

## Study Type Classification

The orchestrator classifies each source in Stage 3. The study type determines
which RoB tool to apply:

| Study type | RoB tool | Domains |
|-----------|----------|---------|
| **Algorithm / computation paper** | Custom (adapted from ROBIS) | D1: Benchmark selection bias, D2: Confounding methods, D3: Outcome measurement, D4: Selective reporting |
| **Empirical / experimental study** | ROBINS-I adapted | D1: Confounding, D2: Selection of participants, D3: Classification of interventions, D4: Deviations from intended interventions, D5: Missing data, D6: Measurement of outcomes, D7: Selection of reported result |
| **Simulation study** | Custom (adapted from ASME V&V 40) | D1: Model validity (conceptual model), D2: Parameter uncertainty, D3: Verification (code), D4: Validation (results vs. reality), D5: Sensitivity analysis |
| **Survey / review / meta-analysis** | ROBIS | D1: Study eligibility criteria, D2: Identification and selection of studies, D3: Data collection and study appraisal, D4: Synthesis and findings |
| **Documentation / standard** | Custom (lightweight) | D1: Authority (recognized body?), D2: Currency (last updated?), D3: Versioning (change history?) |
| **Open-source repository** | Custom (adapted from OpenSSF Scorecard) | D1: License & governance, D2: Activity & maintenance, D3: Test coverage & CI, D4: Documentation quality, D5: Community adoption |

---

---

### Open-Source Repository Domains

| Domain | Low | Some concerns | High | Critical |
|--------|-----|---------------|------|----------|
| **D1: License & governance** | OSI-approved license (MIT, Apache-2.0, GPL, etc.); clear governance model (CLA/DCO, CODEOWNERS) | License present but non-standard; governance informal but functional | No license file; unclear copyright ownership | Explicitly proprietary or license prohibits use |
| **D2: Activity & maintenance** | Last commit < 1 month; issues responded to within 2 weeks; recent release < 3 months | Last commit 1-6 months; slow issue response; release within 1 year | Last commit 6-12 months; many stale issues/PRs | Last commit > 1 year; repository appears abandoned |
| **D3: Test coverage & CI** | CI configured and passing; test coverage ≥ 70% documented; integration/benchmark tests present | CI present but flaky; test coverage unclear or < 70% | No CI; tests exist but not automated | No tests at all; no way to verify correctness |
| **D4: Documentation quality** | Comprehensive README with examples; API docs generated; architecture/tutorial docs present | README present with usage; API docs partial or outdated | Minimal README only; no usage examples | No documentation beyond auto-generated template |
| **D5: Community adoption** | > 1,000 stars; > 100 dependents; cited in ≥ 3 papers; used by recognized organizations | 100-1,000 stars; 10-100 dependents; cited in 1-2 papers | < 100 stars; < 10 dependents; no academic citations | Zero stars; single-user project; no external usage |
| **D6: Algorithmic fidelity** *(only when canonical reference exists)* | Implementation matches canonical description exactly (verified by cross-reference with V-grade paper claim); constants, formulas, and algorithm structure are consistent | Minor discrepancies: different constants, undocumented optimizations, or simplified formula that preserves core behavior | Significant deviations: missing steps, different algorithm variant, or optimization that changes output semantics | Implements a different algorithm than claimed; docstring says "Le Gratiet (2013)" but code shows Kennedy & O'Hagan (2000) formulation |

**D6 applicability:** This domain only applies when a canonical reference (paper with V-grade claim) exists for comparison. Without a canonical reference, mark D6 as "Unverifiable — no canonical reference." D6 is the primary gating domain for E-grade STRONG: a repository must score Low on D6 for its E-grade claims to reach STRONG (see `references/deep-reading.md` §Rule for synthesis).

---

## Domain Ratings

Each domain is rated on a 4-level scale:

| Rating | Meaning |
|--------|---------|
| **Low** | No concerns — the study is well-conducted on this domain |
| **Some concerns** | Potential issues that may affect confidence but are unlikely to change conclusions |
| **High** | Serious issues that substantially weaken confidence in the finding |
| **Critical** | Fatal flaw — the finding from this study should not be used for this domain |

---

## Overall Risk of Bias

The overall RoB is the **highest** rating across all domains (worst-case propagation).
Exception: if ≥3 domains are "Some concerns" but none are "High", overall may be "Some concerns".

| Overall RoB | Action in synthesis |
|------------|-------------------|
| **Low** | Use without reservation |
| **Some concerns** | Use but note limitation; may downgrade GRADE certainty |
| **High** | Use with caution; downgrade GRADE certainty by 1 level |
| **Critical** | Exclude from quantitative synthesis; may use qualitatively with explicit caveat |

---

## Methodological Quality vs. Reporting Quality

Distinguish these two dimensions:

- **Methodological quality:** Was the study well-conducted? (internal validity, appropriate methods, correct analysis)
- **Reporting quality:** Was the study well-described? (enough detail to reproduce, transparent about limitations)

A study can be well-conducted but poorly reported (RoB = "Some concerns" for reporting),
or well-reported but poorly conducted (RoB = "High" for methodology).

When reporting quality is the issue, the orchestrator should note:
> "Insufficient detail to fully assess {domain} — assumed Some concerns unless evidence of problems."

---

## Application Procedure (Stage 3)

1. After source verification (file accessibility) and before template fill:
   a. Classify each source into one of the 5 study types.
   b. Load the appropriate domain checklist.
   c. For each domain, read the source's methodology section and rate.
   d. Record the overall RoB and rationale.

2. Thinking: moderate — domain rating requires judgment about study quality.

3. Write results to `03-source-verification.md` using the Risk of Bias Assessment table.

---

## Template Output

```markdown
## Risk of Bias Assessment

### S{n}: {title} — Study type: {simulation/empirical/algorithm/review/documentation}

| Domain | Rating | Evidence |
|--------|--------|----------|
| D1: {domain_name} | Low / Some concerns / High / Critical | {specific evidence from the source supporting this rating} |
| D2: {domain_name} | ... | ... |
| ... | ... | ... |
| **Overall RoB** | **{Low / Some concerns / High / Critical}** | **{rationale: highest domain rating with justification}** |

### RoB Summary Table (all sources)

| Source ID | Study type | Overall RoB | Key concern | Methodological quality | Reporting quality |
|-----------|-----------|------------|-------------|----------------------|-------------------|
| S{n} | {type} | {Low/Some concerns/High/Critical} | {one-line summary} | {Adequate/Concerning/Poor} | {Adequate/Incomplete/Poor} |
```

---

## RoB → Evidence Strength Mapping

Per `references/epistemology.md` §Evidence Strength Matrix, the RoB assessment
modifies the evidence strength of claims from this source:

| RoB | Evidence strength modifier |
|-----|--------------------------|
| Low | No change |
| Some concerns | Drop one level (STRONG → MODERATE, MODERATE → WEAK) |
| High | Drop two levels; use only if corroborated |
| Critical | Exclude from evidence; cite only as "noted but not relied upon" |
