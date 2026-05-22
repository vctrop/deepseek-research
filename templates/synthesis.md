---
session: {date}-{slug}
stage: 4
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Synthesis

**Session:** `{date}-{slug}`
**Stage:** 4 — Synthesis

## Placeholders

| Placeholder | Populated by | Source |
|---|---|---|
| `{date}` | Orchestrator | System date |
| `{slug}` | Orchestrator | From Stage 1 |
| `{RQ_TEXT}` | Orchestrator | From `01-rq-brief.md` |
| `{DEDUP_NOTES}` | Orchestrator | Deduplication pass on source claims |
| All findings (K1, K2, ...) | Orchestrator | Cross-source analysis |

## Deduplication Notes

{DEDUP_NOTES: which sources were merged, which were kept as converging evidence, which contradictions were preserved}

## Cross-References

| Finding | Web source | Codebase source | Consistency |
|---------|------------|-----------------|-------------|
| {finding} | S{n} | S{m} (:line) | CONSISTENT / PARTIAL / CONTRADICTS |

## Key Findings

### K1: {finding_title}

**Claim:** {qualified claim — see `references/iron-rule-c.md` §Qualified Replacements}

**Supporting sources:** S{n} (source tier: HIGH/MEDIUM/LOW), S{m} (source tier: HIGH/MEDIUM/LOW)

**Evidence strength:** STRONG / MODERATE / WEAK — {rationale per `references/epistemology.md` §Evidence Strength Matrix}

**Confidence:** HIGH / MEDIUM / LOW / SPECULATIVE — {rationale per `references/iron-rule-c.md` §Confidence Language Scale}

---

### K2: {finding_title}

...

---

## Quantitative Synthesis (Meta-Analysis)

*Only when RQ is predictive/causal AND ≥3 sources report same effect with variance. Otherwise omit this section.*

### Pooled Estimate (Random-Effects, DerSimonian-Laird)

{forest_plot_text}

**Heterogeneity:** I² = {I2}% ({heterogeneity_interpretation}), τ² = {tau2}, Q({Q_df}) = {Q}, p = {Q_pvalue}

---

## Numerical Constants

*If RQ is qualitative, leave this section with the note below:*

> This research question is qualitative. No numerical constants were extracted. See Key Findings for qualitative results.

| Symbol | Value | Unit | Source | Evidence strength | Confidence |
|--------|-------|------|--------|-------------------|------------|
| {symbol} | {value} | {unit} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

## Algorithms / Patterns

*If RQ is qualitative, adapt to "Patterns" instead of "Algorithms".*

| Name | Complexity / Structure | Domain Assumptions | Source | Evidence strength | Confidence |
|------|------------------------|--------------------|--------|-------------------|------------|
| {name} | {O(...) or pattern desc} | {assumptions} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

## Consensus Assessment

See `references/epistemology.md` §Consensus Assessment Rules.

| Question | Consensus | Confidence | Notes |
|----------|-----------|------------|-------|
| {question} | CONSENSUS / MAJORITY / DIVERGENT / INSUFFICIENT | HIGH / MEDIUM / LOW | {if DIVERGENT: which sources disagree and why} |

## Gaps

| Gap | Severity | Next Step |
|-----|----------|-----------|
| {description} | BLOCKING / SIGNIFICANT / MINOR | {concrete action} |

**Severity:**
- **BLOCKING:** Cannot answer RQ without this information
- **SIGNIFICANT:** Substantially weakens confidence or completeness
- **MINOR:** Would improve answer but not essential

## Source Usage

| Source ID | Source Tier | P/S/T | RoB | Used in Findings | Evidence Strength Contribution | Notes |
|-----------|-------------|-------|-----|------------------|-------------------------------|-------|
| S{n} | HIGH/MEDIUM/LOW | P/S/T | Low/Some concerns/High/Critical | K1, K2 | STRONG/MODERATE/WEAK | {any caveats} |
