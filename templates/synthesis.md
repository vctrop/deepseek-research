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

## Deduplication Notes

{Which sources were merged, which were kept as converging evidence, which contradictions were preserved.}

## Cross-References

| Finding | Bibliography source | Codebase source | Consistency |
|---------|--------------------|-----------------|-------------|
| {finding} | S{n} | S{n} (:line) | CONSISTENT / PARTIAL / CONTRADICTS |

## Key Findings

### K1: {finding_title}

**Claim:** {qualified claim — Iron Rule C applies}

**Supporting sources:** S{n} (credibility: HIGH/MEDIUM/LOW, RoB: Low/Medium/High),
S{m} (credibility: HIGH/MEDIUM/LOW, RoB: Low/Medium/High)

**Evidence strength:** STRONG / MODERATE / WEAK — {rationale}

**Confidence:** HIGH / MEDIUM / LOW / SPECULATIVE — {rationale}

**Verbatim evidence:** "{exact quote from source}" — {source_id}, §{section}
*Required for STRONG/MODERATE claims.*

---

### K2: {finding_title}

...

---

## Adversarial Thinking Pass

For each key finding:

| Finding | Contrary evidence found? | Sources independent? | Selection bias risk? | Impact |
|---------|------------------------|---------------------|----------------------|--------|
| K1 | Yes/No — {detail} | Yes (>2 independent) / No | Low/Medium/High | None / Downgrade / Revisit |
| K2 | ... | ... | ... | ... |

**Assessment:** {overall assessment of adversarial robustness — e.g., "No substantial contrary evidence found; findings are corroborated by independent sources."}

## Numerical Constants

*If RQ is qualitative: "This research question is qualitative. No numerical constants were extracted."*

| Symbol | Value | Unit | Source | Evidence strength | Confidence |
|--------|-------|------|--------|-------------------|------------|
| {symbol} | {value} | {unit} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

## Algorithms / Patterns

| Name | Complexity / Structure | Domain Assumptions | Source | Evidence strength | Confidence |
|------|------------------------|--------------------|--------|-------------------|------------|
| {name} | {O(...) or pattern desc} | {assumptions} | S{n} | STRONG/MODERATE/WEAK | HIGH/MEDIUM/LOW |

## Consensus Assessment

| Question | Consensus | Confidence | Notes |
|----------|-----------|------------|-------|
| {question} | CONSENSUS / MAJORITY / DIVERGENT / INSUFFICIENT | HIGH / MEDIUM / LOW | {if DIVERGENT: which sources disagree} |

## Gaps

| Gap | Severity | Next Step |
|-----|----------|-----------|
| {description} | BLOCKING / SIGNIFICANT / MINOR | {concrete action} |

## Source Usage

| Source ID | Credibility | P/S/T | RoB | Used in Findings | Evidence Contribution | Notes |
|-----------|-------------|-------|-----|------------------|----------------------|-------|
| S{n} | HIGH/MEDIUM/LOW | P/S/T | Low/Medium/High | K1, K2 | STRONG/MODERATE/WEAK | {caveats} |

<!-- STAGE_COMPLETE -->
