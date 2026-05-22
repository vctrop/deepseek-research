---
target: deepseek-research skill v2.0
status: draft
created: 2026-05-21
author: deepseek-tui (DeepSeek V4 Pro)
skill_version_target: 2.0.0
---

# SPEC-001: Professional Research Team Parity

## 1. Executive Summary

The current skill delivers a **rapid evidence assessment** — structured but
single-reviewer, single-method, single-output. A professional research group
(e.g., Cochrane, Campbell, Stanford METRICS) would deliver a **systematic review
with meta-analytic components**. This spec identifies 13 capability gaps,
organized into 3 tiers: foundational (must-have for credibility), advanced
(professional-grade), and aspirational (cutting-edge).

---

## 2. Capability Gap Matrix

### Tier 1 — Foundational (credibility floor for "systematic review" label)

| # | Gap | Current state | Professional standard | Priority |
|---|-----|--------------|----------------------|----------|
| F1 | **Protocol pre-registration** | SHA256 hash stored locally | PROSPERO/OSF registration with public DOI | HIGH |
| F2 | **Dual independent screening** | Single LLM screens all sources | Two independent reviewers; disagreements resolved by third | HIGH |
| F3 | **Structured risk of bias** | Ad-hoc COI flags (Minor/Moderate) | ROBIS / ROBINS-I / QUADAS-2 checklist per study design | HIGH |
| F4 | **PRISMA flow diagram** | No screening audit trail | PRISMA 2020 flow diagram (records → screened → eligible → included) | MEDIUM |
| F5 | **Search strategy peer review** | Queries not validated | PRESS 2015 checklist applied to each search string | MEDIUM |

### Tier 2 — Advanced (professional-grade evidence synthesis)

| # | Gap | Current state | Professional standard | Priority |
|---|-----|--------------|----------------------|----------|
| A1 | **Meta-analysis** | Flat table of constants, no pooling | Weighted pooled effect sizes, heterogeneity (I², τ²), forest plots | HIGH |
| A2 | **GRADE / certainty of evidence** | Source credibility tier only (HIGH/MEDIUM/LOW) | GRADE domains: risk of bias, inconsistency, indirectness, imprecision, publication bias → overall certainty (High/Moderate/Low/Very Low) | HIGH |
| A3 | **Sensitivity analysis** | None | Leave-one-out, subgroup analysis, meta-regression, exclusion of low-quality studies | MEDIUM |
| A4 | **Publication bias detection** | None | Funnel plot asymmetry, Egger's test, trim-and-fill, p-curve analysis | MEDIUM |
| A5 | **Grey literature search** | Generic web search only | Theses (ProQuest), preprints (arXiv/techrxiv), trial registries, conference proceedings, institutional repositories | LOW |

### Tier 3 — Aspirational (cutting-edge research group practices)

| # | Gap | Current state | Professional standard | Priority |
|---|-----|--------------|----------------------|----------|
| C1 | **Living systematic review** | One-shot report | Scheduled updates (surveillance searches, re-synthesis triggers) | LOW |
| C2 | **Multiple output formats** | Single report (05-report.md) | Technical report + plain-language summary + 1-pager + data supplement + interactive evidence table | LOW |
| C3 | **Stakeholder review panel** | `request_user_input` at Stage 1 only | Domain experts review draft findings before finalization | LOW |

---

## 3. Detailed Design — Tier 1

### F1: Protocol Pre-registration

**Problem:** The SHA256 hash proves the file hasn't changed, but doesn't make
the protocol publicly discoverable or citable.

**Design:**
- Stage 1 generates `01-rq-brief.md` as the protocol
- New sub-stage 1.6: `protocol_finalize`
  - If OSF token configured: push protocol JSON to OSF API via `fetch_url`
  - If no token: generate a Zenodo-like metadata block and instruct user to deposit manually
  - Record DOI/URL in `MANIFEST.txt`
- The protocol includes: RQ, sub-questions, knowledge types, operational definitions, inclusion/exclusion criteria, search strategy, data extraction plan, analysis plan
- Gate: verify DOI resolves before proceeding to Stage 2

**Config additions:**
```toml
protocol_registry = "osf"  # osf | zenodo | none
osf_token = "..."          # only if osf
osf_project_id = "..."     # only if osf
```

---

### F2: Dual Independent Screening

**Problem:** A single LLM screens all sources — no inter-rater reliability, no
disagreement resolution.

**Design:**
- Stage 2 dispatches **2 bibliographic sub-agents** (`dsr-bib-1`, `dsr-bib-2`) instead of 1
  - Both receive the same prompt but different random seeds for independence
- Stage 2.1 (new): **Reconciliation**
  - Orchestrator compares both outputs
  - Sources where both agree "include": automatically included
  - Sources where both agree "exclude": automatically excluded
  - Disagreements: dispatched to a third sub-agent (`dsr-bib-tiebreak`) for resolution
  - Compute inter-rater reliability: Cohen's kappa or simple agreement %
  - Report in `02-source-inventory.md` under "Screening Reliability"

**Config additions:**
```toml
dual_screening = true          # default: false (cost impact: +1 Flash sub-agent)
agreement_threshold = 0.80     # kappa threshold; below this → manual review needed
```

**Cost impact:** +1 Flash sub-agent per bibliography axis. For typical session:
~$0.001 additional. Trivial.

---

### F3: Structured Risk of Bias

**Problem:** Current COI flags (Minor/Moderate) are generic and don't
distinguish between study design limitations and reporting quality.

**Design:**
- Replace COI Register in `03-source-verification.md` with **Risk of Bias Matrix**
- Apply domain-appropriate RoB tool:

| Study type | Tool | Domains |
|-----------|------|---------|
| Algorithm/computation paper | Custom checklist | Selection of benchmarks, confounding methods, measurement of outcome, selective reporting |
| Empirical/experimental | ROBINS-I adapted | Confounding, selection, classification, deviations, missing data, measurement, reporting |
| Simulation study | Custom checklist | Model validity, parameter uncertainty, verification, validation, sensitivity |
| Survey/review | ROBIS | Study eligibility, identification, data collection, synthesis |

- Each domain rated: Low / Some concerns / High / Critical risk of bias
- Overall RoB: same scale, with justification
- Distinguish **methodological quality** (was study well-conducted?) from **reporting quality** (was it well-described?)

**Template addition to `03-source-verification.md`:**
```markdown
## Risk of Bias Assessment

| Source ID | Study type | Domain 1 | Domain 2 | ... | Overall RoB | Rationale |
|-----------|-----------|----------|----------|-----|------------|-----------|
| S{n} | simulation | Low | Some concerns | ... | Some concerns | {why} |
```

---

### F4: PRISMA Flow Diagram

**Problem:** No transparent record of how many sources were screened at each stage.

**Design:**
- `02-source-inventory.md` gains a PRISMA flow section:

```markdown
## PRISMA 2020 Flow Diagram

Records identified from:
  Bibliography .................... n = {N}
  Web search ...................... n = {N}
  Codebase ........................ n = {N}
  Citation chasing (snowball) ..... n = 0 (not implemented)
  Grey literature ................. n = 0 (not implemented)
                                    ---------
Total records ..................... n = {TOTAL}

Records after deduplication ....... n = {DEDUPED}
  Excluded (duplicate) ............ n = {TOTAL - DEDUPED}

Records screened (title/abstract) . n = {DEDUPED}
  Excluded (irrelevant) ........... n = {EXCLUDED_IRRELEVANT}

Full-text assessed for eligibility  n = {FULL_TEXT}
  Excluded with reasons ........... n = {FULL_TEXT - INCLUDED}
    Reason 1: insufficient detail   n = {N}
    Reason 2: wrong population      n = {N}
    Reason 3: retracted             n = {N}

Studies included in synthesis ..... n = {INCLUDED}
  Quantitative synthesis ........... n = {QUANT}
  Qualitative synthesis ............ n = {QUAL}
```

---

### F5: Search Strategy Peer Review (PRESS)

**Problem:** Search queries are written ad-hoc by the LLM without validation.

**Design:**
- After Stage 2 search audit is generated, Stage 2.2 (new): **PRESS Review**
- Orchestrator applies PRESS 2015 checklist to each search string:

| PRESS element | Check |
|--------------|-------|
| Translation of RQ into search concepts | Are all PICO/SPICE elements represented? |
| Boolean operators | AND/OR/NOT used correctly? |
| Subject headings | Controlled vocabulary where applicable? |
| Text word searching | Synonyms, acronyms, spelling variants? |
| Spelling and syntax | Any typos? |
| Limits and filters | Date, language, publication type filters justified? |

- Report in `02-source-inventory.md` under "PRESS Review"
- Flag any element rated "inadequate" → re-run search with corrected query

---

## 4. Detailed Design — Tier 2

### A1: Meta-Analysis

**Problem:** Current synthesis lists constants in a flat table but doesn't
synthesize them statistically.

**Design:**
- Stage 4 gains **Quantitative Synthesis** sub-section (conditional on RQ type = predictive/causal)
- When ≥3 sources report the same effect with variance:

1. **Pool effect sizes** using random-effects model (DerSimonian-Laird or REML)
   ```
   code_execution(code="""
   import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
   from meta_analysis import random_effects_pool
   effects = [{value}, {value}, ...]
   variances = [{var}, {var}, ...]
   result = random_effects_pool(effects, variances)
   print(json.dumps(result))  # {pooled_estimate, ci_lower, ci_upper, I2, tau2, Q, Q_pvalue}
   """)
   ```

2. **Heterogeneity assessment:**
   - I²: 0-40% (low), 30-60% (moderate), 50-90% (substantial), 75-100% (considerable)
   - τ²: between-study variance

3. **Forest plot** (ASCII art or text table):
   ```
   Study        Effect [95% CI]     Weight
   S1           -0.15 [-0.30, 0.00] 25.3%
   S2            0.05 [-0.10, 0.20] 28.1%
   S3           -0.08 [-0.22, 0.06] 46.6%
   ────────────────────────────────────────
   Pooled (RE)  -0.06 [-0.16, 0.04] 100%
   Heterogeneity: I² = 42%, τ² = 0.003, Q(2) = 3.45, p = 0.18
   ```

4. **New requirement:** `scripts/meta_analysis.py` (pure Python, stdlib + simple math — no scipy/numpy dependency)

**Config additions:**
```toml
meta_analysis = "auto"  # auto | always | never
```

---

### A2: GRADE Certainty of Evidence

**Problem:** Source credibility tier (HIGH/MEDIUM/LOW) conflates study design,
risk of bias, and reporting quality into one dimension.

**Design:**
- Stage 4 synthesis rates **overall certainty of evidence** for each key finding
  using adapted GRADE domains:

| Domain | Downgrade criteria | Upgrade criteria |
|--------|-------------------|-----------------|
| Risk of bias | RoB assessment = Serious (-1) or Critical (-2) | N/A |
| Inconsistency | I² > 75% (-1), I² > 90% (-2) | Consistent across independent teams |
| Indirectness | Different population/intervention/outcome than RQ (-1) | N/A |
| Imprecision | CI crosses decision threshold (-1), small sample (-1) | Large, precise effect |
| Publication bias | Funnel asymmetry (-1), all studies from same group (-1) | Registered protocols with pre-specified analyses |

- Starting point: source type → initial certainty
  - Multiple RCTs/controlled experiments → High
  - Observational/simulation studies → Low
  - After upgrades/downgrades → final GRADE rating

- Report per finding:
  ```markdown
  ### K1: Finding Title
  **GRADE Certainty:** ⊕⊕⊕⊝ MODERATE
  **Downgraded for:** risk of bias (-1, S3 had incomplete blinding)
  ```

---

### A3: Sensitivity Analysis

**Problem:** No assessment of how sensitive conclusions are to methodological choices.

**Design:**
- Stage 4 gains optional sensitivity analyses (triggered when ≥5 sources + meta-analysis):
  1. **Leave-one-out:** recompute pooled estimate excluding each study in turn
  2. **Subgroup:** by study design (experimental vs. simulation), by fidelity rung, by year
  3. **Exclusion of high RoB:** recompute excluding studies with Critical risk of bias
- Report when any analysis changes the conclusion (direction, significance, or GRADE rating)

---

### A4: Publication Bias Detection

**Problem:** No attempt to detect whether the evidence base is skewed by
selective publication.

**Design:**
- Stage 3 verification gains publication bias assessment (when ≥10 sources on same topic):
  1. **Source diversity check:** what % of sources are from same author group?
  2. **Result distribution:** are negative/null results underrepresented relative to positive?
  3. **Funnel plot text description:** describe symmetry of effect vs. precision
  4. **File-drawer assessment:** N needed to nullify (Rosenthal's fail-safe N)
- Flag when publication bias likely: "Evidence may overestimate effect due to selective reporting."

---

### A5: Grey Literature Search

**Problem:** Web search is generic — misses theses, preprints, trial registries,
conference proceedings, and institutional repositories.

**Design:**
- Stage 2 gains optional grey literature axis via dedicated sub-agent:
  ```
  agent_open(name="dsr-grey", model="deepseek-v4-flash",
    allowed_tools=["web_search","fetch_url","write_file"],
    prompt="Search grey literature for: {RQ_TEXT}
    Search these sources specifically:
    - arxiv.org (preprints)
    - techrxiv.org (engineering preprints)
    - ProQuest Dissertations (theses)
    - Google Scholar (conference papers)
    - institutional repositories (MIT DSpace, etc.)
    Output: same format as dsr-web.")
  ```
- Triggered by config: `source_axes = ["bibliography", "codebase", "web", "grey"]`

---

## 5. Detailed Design — Tier 3 (Aspirational)

### C1: Living Systematic Review

**Problem:** Research is one-shot — becomes stale as new evidence emerges.

**Design (conceptual — not for immediate implementation):**
- `MANIFEST.txt` records search dates and query strings
- `deepseek-research.toml` gains:
  ```toml
  living_review = true
  surveillance_interval_days = 90
  surveillance_queries = ["{original_query}", "{new_query_if_updated}"]
  ```
- On next trigger `"update research {slug}"`, the skill:
  1. Loads prior session artifacts
  2. Re-runs searches with date filter (since last search)
  3. Screens new records against original inclusion criteria
  4. Updates meta-analysis if new data found
  5. Appends to report with "Update N" header
  6. Does NOT re-screen previously screened records

### C2: Multiple Output Formats

**Problem:** Single 05-report.md doesn't serve all audiences.

**Design:**
- Stage 5 generates additional formats:
  - `05-report.md` — full technical report (unchanged)
  - `05-plain-summary.md` — 1-page plain language summary (≤500 words, no jargon)
  - `05-decision-brief.md` — 1-pager for decision-makers (actionable recommendations)
  - `05-data-supplement.json` — machine-readable extracted data
  - Template for each in `templates/`

### C3: Stakeholder Review Panel

**Problem:** Only the initial user (`request_user_input` at Stage 1) provides input.

**Design:**
- Stage 4.6 (new, after Devil's Advocate): **Stakeholder Review**
- Orchestrator presents draft findings via `request_user_input`:
  ```
  "Key findings before finalization: [K1, K2, K3]. Any stakeholder concerns?"
  ```
- Stakeholder feedback is documented in `04b-stakeholder-review.md`
- Orchestrator addresses feedback before Stage 5
- Configurable: `stakeholder_review = true/false`

---

## 6. Implementation Roadmap

### Phase 1: v1.5 — Foundational Credibility (2-3 sessions)

| Task | Effort | Depends on |
|------|--------|------------|
| F1: Protocol pre-registration (OSF API) | Medium | None |
| F2: Dual independent screening | Small | None |
| F3: Risk of bias matrix (ROBIS-adapted) | Medium | None |
| F4: PRISMA flow diagram in 02-source-inventory | Small | None |
| F5: PRESS review checklist in Stage 2.2 | Small | None |

### Phase 2: v1.7 — Professional Synthesis (3-4 sessions)

| Task | Effort | Depends on |
|------|--------|------------|
| A1: Meta-analysis (`scripts/meta_analysis.py` + Stage 4 integration) | Large | F3 (RoB needed for weighting) |
| A2: GRADE certainty framework | Medium | A1 + F3 |
| A3: Sensitivity analysis | Medium | A1 |
| A4: Publication bias detection | Medium | A1 |
| A5: Grey literature axis | Small | None |

### Phase 3: v2.0 — Living & Dissemination (2-3 sessions)

| Task | Effort | Depends on |
|------|--------|------------|
| C1: Living systematic review infrastructure | Large | A1, A2 |
| C2: Multiple output formats (templates) | Small | None |
| C3: Stakeholder review panel | Small | None |

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dual screening with same model yields correlated errors (pseudo-replication) | Underestimates screening errors | Use different models for reviewers (Flash vs. Pro) or different temperature seeds |
| Meta-analysis on heterogeneous simulation studies produces meaningless pools | Misleading quantitative synthesis | GRADE downgrade for inconsistency; flag when I² > 75% |
| GRADE adaptation for engineering research is novel and unvalidated | Framework may not capture domain-specific concerns | Publish GRADE adaptation as part of skill documentation; iterate based on user feedback |
| OSF API dependency breaks | Protocol registration fails | Graceful degradation: fall back to local SHA256-only pre-registration |
| `meta_analysis.py` without scipy/numpy is error-prone | Numerical instability | Use Welford's algorithm for variance; validate against R `metafor` package on test datasets |
| Grey literature sub-agent produces noise | Low-precision results with high false-positive rate | Stricter inclusion criteria for grey literature sources |

---

## 8. Success Criteria

| Criterion | Threshold | Measurement |
|-----------|-----------|-------------|
| Inter-rater reliability (dual screening) | Cohen's κ ≥ 0.60 | Computed in Stage 2.1 |
| PRISMA compliance | ≥80% of PRISMA 2020 checklist items reported | Automated checklist in Close gates |
| Meta-analysis reproducibility | Pooled estimates within ±5% of independent R `metafor` re-analysis | Test suite with known datasets |
| GRADE inter-rater | ≥75% agreement between LLM and human researcher on 10 test findings | Calibration study (future work) |
| Living review freshness | Surveillance gap ≤ 7 days beyond configured interval | MANIFEST.txt timestamps |

---

## 9. Open Questions

1. **Should dual screening use different models, or is same-model-with-different-seed sufficient for independence?** Research question for a meta-research spike.

2. **What is the correct GRADE adaptation for simulation/engineering evidence?** GRADE was designed for clinical medicine. Engineering domains have different evidence hierarchies (formal verification > simulation > experiment > expert opinion).

3. **At what point does meta-analysis become misleading rather than informative?** Need a heuristic: when I² > 90% or when studies use fundamentally different methods, quantitative pooling should be suppressed.

4. **Should the skill refuse to run when inter-rater reliability is critically low (κ < 0.40)?** Professional groups would halt and retrain reviewers. Equivalent for LLM: re-prompt with different instructions.

5. **How to handle the "file drawer" of the LLM itself?** The model's training data may have overrepresented positive results. This is a deeper epistemological problem that no skill can fully solve — only flag.
