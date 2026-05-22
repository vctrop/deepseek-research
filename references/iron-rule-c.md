# IRON RULE C — Qualified Language

Every confidence claim in `05-report.md` and `04-synthesis.md` must use qualified
language. Bare claims are forbidden — they create an illusion of certainty that
the evidence does not support.

Loaded at Stage 4 (synthesis), applied at Stage 5 (report), verified at Close (GATE-3).

---

## Bare Claims (forbidden)

These words and their variants are NEVER allowed without a qualifying clause
specifying the source, method, and conditions:

| Bare claim word | Why forbidden |
|----------------|---------------|
| `validated` | By whom? Using what method? Under what conditions? |
| `proved` | Proofs exist only in closed formal systems; empirical claims are never "proved" |
| `confirmed` | Science confirms nothing — it fails to reject |
| `demonstrated` | In what context? With what limitations? |
| `ensures` | Nothing in engineering "ensures" — it reduces probability |
| `guarantees` | See "ensures" |
| `always` | Universal quantifier — almost never true in empirical domains |
| `never` | Universal negative — even harder to evidence than "always" |
| `optimal` | Optimal under which objective function? Pareto-optimal? Globally optimal? |
| `definitive` | No single study is definitive |
| `conclusive` | Conclusions are always provisional |
| `certainly` | Certainty is not a scientific category |
| `undoubtedly` | Doubt is the engine of science |
| `obviously` | If it were obvious, you wouldn't need research |
| `clearly` | Clarity is in the eye of the beholder; cite evidence instead |

---

## Detection (Close, GATE-3)

**Pass 1:** Find any of the bare claim words in report/synthesis:
```
grep_files(pattern="\\b(validated|proved|confirmed|demonstrated|ensures|guarantees|always|never|optimal|definitive|conclusive|certainly|undoubtedly|obviously|clearly)\\b", path="{session_dir}/")
```

**Pass 2:** For each match, check for qualifying context (source + method + conditions).
Report only unqualified matches as violations.

---

## Qualified Replacements

| Bare claim | Qualified form |
|---|---|
| validated | supported by converging evidence from [sources: S1, S2] under [conditions: low-altitude subsonic flight] |
| proved | demonstrated by [method: formal proof in Coq] within [assumptions: classical logic, no floating-point] |
| confirmed | consistent with [source: S3] under [conditions: standard atmosphere, sea level]; not independently replicated |
| demonstrated | shown by [source: S4] in [context: simulation with N=100 Monte Carlo samples]; experimental validation pending |
| ensures | reduces probability of [failure mode] from [baseline: X] to [target: Y] in [source: S5] under [assumptions: independent failures] |
| guarantees | provides [bound: 95% confidence] under [conditions: i.i.d. samples, no distribution shift] |
| always | observed in all N={count} trials in [source: S6]; generalization to untested conditions is not warranted |
| never | not observed in N={count} trials in [source: S7]; absence of evidence ≠ evidence of absence |
| optimal | minimizes [objective: mean squared error] among [comparison set: 5 methods] in [source: S8]; global optimality not established |
| definitive | represents current best evidence as of [date]; subject to revision with new data |

---

## Confidence Language Scale

Use these terms with explicit definitions in the report:

| Confidence label | Meaning | Evidence threshold |
|-----------------|---------|-------------------|
| **HIGH** | Would bet significantly on this being correct | ≥2 STRONG sources, no dissent, multiple independent teams |
| **MEDIUM** | Reasonable basis for decision, but seek confirmation | ≥1 STRONG or ≥2 MODERATE sources, minor dissent |
| **LOW** | Use as hypothesis only; do not base irreversible decisions | Only WEAK sources, or single MODERATE source, or significant dissent |
| **SPECULATIVE** | Plausible but unevidenced; explicitly labeled as conjecture | No direct evidence; extrapolation or expert intuition |

Never use "PROVEN" or "ESTABLISHED" as confidence labels. They are not confidence
categories — they are rhetorical moves that short-circuit critical evaluation.
