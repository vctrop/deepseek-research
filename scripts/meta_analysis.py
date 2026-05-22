#!/usr/bin/env python3
"""meta_analysis.py — Meta-analysis engine for deepseek-research.

Pure Python + scipy. No numpy dependency (uses list comprehensions for arrays).
Implements DerSimonian-Laird random-effects, inverse-variance fixed-effects,
heterogeneity statistics, and ASCII forest plot.

Usage:
    from meta_analysis import random_effects_pool, forest_plot_text
    result = random_effects_pool([0.1, 0.2, 0.15], [0.01, 0.02, 0.015])
    print(forest_plot_text(result))

Self-test:
    python3 meta_analysis.py --self-test
"""

from __future__ import annotations

import json
import math
import sys

try:
    from scipy import stats as scipy_stats  # type: ignore[import-untyped]

    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ---------------------------------------------------------------------------
# Core meta-analysis functions
# ---------------------------------------------------------------------------


def inverse_variance_weights(variances: list[float]) -> list[float]:
    """Compute inverse-variance weights w_i = 1 / v_i."""
    return [1.0 / v if v > 0 else 0.0 for v in variances]


def fixed_effects_pool(
    effects: list[float], variances: list[float]
) -> dict:
    """Fixed-effects meta-analysis (inverse-variance weighted).

    Returns dict with pooled_estimate, ci_lower, ci_upper, se_pooled,
    weights, Q, Q_df, Q_pvalue.
    """
    n = len(effects)
    if n == 0:
        return {"pooled_estimate": 0.0, "ci_lower": 0.0, "ci_upper": 0.0,
                "se_pooled": 0.0, "weights": [], "I2": 0.0, "tau2": 0.0,
                "Q": 0.0, "Q_df": 0, "Q_pvalue": 1.0, "method": "fixed",
                "k": 0}
    if n == 1:
        se = math.sqrt(variances[0])
        ci_lo = effects[0] - 1.96 * se
        ci_hi = effects[0] + 1.96 * se
        return {"pooled_estimate": effects[0], "ci_lower": ci_lo,
                "ci_upper": ci_hi, "se_pooled": se,
                "weights": [1.0], "I2": 0.0, "tau2": 0.0,
                "Q": 0.0, "Q_df": 0, "Q_pvalue": 1.0,
                "method": "fixed", "k": 1}

    w = inverse_variance_weights(variances)
    w_sum = sum(w)
    pooled = sum(e * wi for e, wi in zip(effects, w)) / w_sum
    se_pooled = math.sqrt(1.0 / w_sum)

    # Cochran's Q
    Q = sum(wi * (e - pooled) ** 2 for e, wi in zip(effects, w))
    Q_df = n - 1
    Q_pvalue = _chi2_sf(Q, Q_df) if Q_df > 0 else 1.0

    # I²
    I2 = max(0.0, (Q - Q_df) / Q * 100) if Q > 0 else 0.0

    ci_lo = pooled - 1.96 * se_pooled
    ci_hi = pooled + 1.96 * se_pooled

    return {"pooled_estimate": pooled, "ci_lower": ci_lo, "ci_upper": ci_hi,
            "se_pooled": se_pooled, "weights": w, "I2": I2, "tau2": 0.0,
            "Q": Q, "Q_df": Q_df, "Q_pvalue": Q_pvalue, "method": "fixed",
            "k": n}


def random_effects_pool(
    effects: list[float],
    variances: list[float],
    method: str = "DL",
    max_iter: int = 20,
    tol: float = 1e-6,
) -> dict:
    """Random-effects meta-analysis using DerSimonian-Laird estimator.

    Args:
        effects: List of study effect estimates.
        variances: Within-study variances (v_i).
        method: "DL" for DerSimonian-Laird (only method currently).
        max_iter: Maximum iterations for convergence.
        tol: Convergence tolerance for tau².

    Returns:
        dict with pooled_estimate, ci_lower, ci_upper, se_pooled,
        weights, I2, tau2, Q, Q_df, Q_pvalue, method, k, iteration_count.
    """
    n = len(effects)
    if n == 0:
        return {"pooled_estimate": 0.0, "ci_lower": 0.0, "ci_upper": 0.0,
                "se_pooled": 0.0, "weights": [], "I2": 0.0, "tau2": 0.0,
                "Q": 0.0, "Q_df": 0, "Q_pvalue": 1.0, "method": "DL",
                "k": 0, "iteration_count": 0}
    if n == 1:
        se = math.sqrt(variances[0])
        ci_lo = effects[0] - 1.96 * se
        ci_hi = effects[0] + 1.96 * se
        return {"pooled_estimate": effects[0], "ci_lower": ci_lo,
                "ci_upper": ci_hi, "se_pooled": se,
                "weights": [1.0], "I2": 0.0, "tau2": 0.0,
                "Q": 0.0, "Q_df": 0, "Q_pvalue": 1.0,
                "method": "DL", "k": 1, "iteration_count": 0}

    # Step 1: Fixed-effects to get initial pooled estimate
    fe = fixed_effects_pool(effects, variances)
    Q = fe["Q"]
    Q_df = fe["Q_df"]

    # Step 2: DerSimonian-Laird tau²
    w_fe = inverse_variance_weights(variances)
    w_sum = sum(w_fe)
    C = w_sum - sum(wi**2 for wi in w_fe) / w_sum
    tau2 = max(0.0, (Q - Q_df) / C) if C > 0 and Q > Q_df else 0.0

    # Step 3: Iterative refinement
    iteration_count = 1
    for _ in range(max_iter):
        w_re = [1.0 / (v + tau2) for v in variances]
        w_sum_re = sum(w_re)
        pooled_re = sum(e * wi for e, wi in zip(effects, w_re)) / w_sum_re

        # Recompute Q with new pooled estimate
        Q_new = sum(wi * (e - pooled_re) ** 2 for e, wi in zip(effects, w_fe))
        C_new = w_sum - sum(wi**2 for wi in w_fe) / w_sum
        tau2_new = max(0.0, (Q_new - Q_df) / C_new) if C_new > 0 and Q_new > Q_df else 0.0

        if abs(tau2_new - tau2) < tol:
            tau2 = tau2_new
            break
        tau2 = tau2_new
        iteration_count += 1

    # Step 4: Final random-effects estimate
    w_re = [1.0 / (v + tau2) for v in variances]
    w_sum_re = sum(w_re)
    pooled_re = sum(e * wi for e, wi in zip(effects, w_re)) / w_sum_re
    se_re = math.sqrt(1.0 / w_sum_re)

    # t-based CI (more conservative than z for small k)
    t_crit = _t_critical_value(0.975, n - 1) if n > 1 else 1.96
    ci_lo = pooled_re - t_crit * se_re
    ci_hi = pooled_re + t_crit * se_re

    # I²
    I2 = max(0.0, (Q - Q_df) / Q * 100) if Q > 0 else 0.0

    Q_pvalue = _chi2_sf(Q, Q_df) if Q_df > 0 else 1.0

    return {"pooled_estimate": pooled_re, "ci_lower": ci_lo,
            "ci_upper": ci_hi, "se_pooled": se_re, "weights": w_re,
            "I2": I2, "tau2": tau2, "Q": Q, "Q_df": Q_df,
            "Q_pvalue": Q_pvalue, "method": "DL", "k": n,
            "iteration_count": iteration_count}


def forest_plot_text(
    result: dict,
    labels: list[str] | None = None,
    effects: list[float] | None = None,
    variances: list[float] | None = None,
) -> str:
    """Generate an ASCII forest plot as a Markdown code block.

    Args:
        result: Output from random_effects_pool or fixed_effects_pool.
        labels: Study labels (defaults to S1, S2, ...).
        effects: Original effects (for per-study rows).
        variances: Original variances (for per-study rows).

    Returns:
        Formatted string suitable for Markdown.
    """
    k = result.get("k", 0)
    if k == 0:
        return "```\nNo studies to plot.\n```"

    if labels is None:
        labels = [f"S{i+1}" for i in range(k)]
    if effects is None or variances is None:
        # Can only show pooled
        lines = ["```",
                 "Forest Plot (pooled estimate only — per-study data not provided)",
                 "",
                 f"  Pooled ({result['method']})    {result['pooled_estimate']:.3f} [{result['ci_lower']:.3f}, {result['ci_upper']:.3f}]",
                 f"  Heterogeneity: I² = {result['I2']:.1f}%, τ² = {result.get('tau2', 0):.4f}, Q({result.get('Q_df', 0)}) = {result['Q']:.2f}, p = {result['Q_pvalue']:.3f}",
                 "```"]
        return "\n".join(lines)

    lines = ["```",
             "Study          Effect  [95% CI]        Weight",
             "-" * 55]

    w_sum = sum(result["weights"])
    max_label_len = max(len(lbl) for lbl in labels)

    for i in range(k):
        lbl = labels[i].ljust(max_label_len)
        e = effects[i]
        se_i = math.sqrt(variances[i])
        ci_lo_i = e - 1.96 * se_i
        ci_hi_i = e + 1.96 * se_i
        wt = result["weights"][i] / w_sum * 100
        lines.append(
            f"{lbl}  {e:+.3f} [{ci_lo_i:+.3f}, {ci_hi_i:+.3f}]  {wt:.1f}%"
        )

    lines.append("-" * 55)
    lbl = f"Pooled ({result['method']})".ljust(max_label_len)
    lines.append(
        f"{lbl}  {result['pooled_estimate']:+.3f} [{result['ci_lower']:+.3f}, {result['ci_upper']:+.3f}]  100%"
    )
    lines.append("")
    lines.append(
        f"Heterogeneity: I² = {result['I2']:.1f}%, τ² = {result.get('tau2', 0):.4f}, "
        f"Q({result.get('Q_df', 0)}) = {result['Q']:.2f}, p = {result['Q_pvalue']:.3f}"
    )
    lines.append("```")
    return "\n".join(lines)


def heterogeneity_interpretation(I2: float) -> str:
    """I² interpretation per Cochrane guidelines."""
    if I2 <= 0:
        return "Not observed"
    elif I2 <= 40:
        return "Low"
    elif I2 <= 60:
        return "Moderate"
    elif I2 <= 75:
        return "Substantial"
    elif I2 <= 90:
        return "Considerable"
    else:
        return "Very high"


def fail_safe_n(
    effects: list[float], variances: list[float], alpha: float = 0.05
) -> dict:
    """Rosenthal's fail-safe N for publication bias.

    Returns dict with fail_safe_N, critical_Z, mean_Z, alpha.
    """
    k = len(effects)
    if k < 2:
        return {"fail_safe_N": 0, "critical_Z": 1.96, "mean_Z": 0, "alpha": alpha, "k": k}

    # Convert each effect to a Z-score
    z_scores = [e / math.sqrt(v) if v > 0 else 0.0 for e, v in zip(effects, variances)]
    mean_z = sum(z_scores) / k
    avg_z = abs(mean_z)

    # Critical Z for alpha
    critical_z = _norm_ppf(1.0 - alpha)  # one-tailed at alpha

    # Rosenthal: N_fs = (k * (mean_z - critical_z)²) / critical_z²
    # Corrected: N_fs = (ΣZ_i / critical_z)² - k
    sum_z = sum(z_scores)
    if critical_z > 0:
        n_fs = (sum_z / critical_z) ** 2 - k
    else:
        n_fs = 0
    n_fs = max(0, round(n_fs))

    return {"fail_safe_N": n_fs, "critical_Z": round(critical_z, 3),
            "mean_Z": round(mean_z, 3), "alpha": alpha, "k": k}


def sensitivity_leave_one_out(
    effects: list[float], variances: list[float]
) -> list[dict]:
    """Leave-one-out sensitivity analysis.

    Returns a list of dicts, one per excluded study, with pooled estimate
    and I² after exclusion.
    """
    k = len(effects)
    results = []
    for i in range(k):
        sub_effects = effects[:i] + effects[i + 1:]
        sub_variances = variances[:i] + variances[i + 1:]
        result = random_effects_pool(sub_effects, sub_variances)
        results.append({
            "excluded_index": i,
            "excluded_label": f"S{i+1}",
            "pooled_without": result["pooled_estimate"],
            "ci_lower": result["ci_lower"],
            "ci_upper": result["ci_upper"],
            "I2": result["I2"],
        })
    return results


# ---------------------------------------------------------------------------
# Statistical helpers (scipy or fallback)
# ---------------------------------------------------------------------------


def _chi2_sf(x: float, df: int) -> float:
    """Survival function (1 - CDF) of chi² distribution."""
    if _HAS_SCIPY and df > 0:
        return float(scipy_stats.chi2.sf(x, df))
    # Wilson-Hilferty approximation for chi²
    if df <= 0 or x <= 0:
        return 1.0
    z = ((x / df) ** (1 / 3) - 1 + 2 / (9 * df)) / math.sqrt(2 / (9 * df))
    return _norm_sf(z)


def _norm_sf(z: float) -> float:
    """Standard normal survival function."""
    if _HAS_SCIPY:
        return float(scipy_stats.norm.sf(z))
    # Abramowitz & Stegun 26.2.17 approximation
    def _phi(x):
        return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

    def _norm_cdf(x):
        if x < -8:
            return 0.0
        if x > 8:
            return 1.0
        t = 1 / (1 + 0.2316419 * abs(x))
        b = [0.31938153, -0.356563782, 1.781477937, -1.821255978, 1.330274429]
        poly = t * (b[0] + t * (b[1] + t * (b[2] + t * (b[3] + t * b[4]))))
        phi_x = _phi(abs(x))
        result = phi_x * poly
        return result if x >= 0 else 1.0 - result

    return 1.0 - _norm_cdf(z)


def _norm_ppf(p: float) -> float:
    """Standard normal percent point function (inverse CDF)."""
    if _HAS_SCIPY:
        return float(scipy_stats.norm.ppf(p))
    if p <= 0 or p >= 1:
        return float("inf") if p >= 1 else float("-inf")
    # Rational approximation (Abramowitz & Stegun 26.2.23)
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        num = (((((((2.5090809287301226727e3 * r + 3.3430575583588128105e4) * r
                    + 6.7265770927008700853e4) * r + 4.5921953931549871457e4) * r
                  + 1.3731693765509461125e4) * r + 1.9715909503065514427e3) * r
                + 1.3314166789178437745e2) * r + 3.3871328727963666080e0)
        den = (((((((5.2264952788528545610e3 * r + 2.8729085735721942674e4) * r
                    + 3.9307895800092710610e4) * r + 2.1213794301586595867e4) * r
                  + 5.3941960214247511077e3) * r + 6.8718700749205790830e2) * r
                + 4.2313330701600911252e1) * r + 1.0)
        return q * num / den
    else:
        r = math.sqrt(-math.log(min(p, 1 - p)))
        if r <= 5:
            r -= 1.6
            num = (((((((7.74545014278341407640e-4 * r + 2.27238449892691845833e-2) * r
                        + 2.41780725177450611770e-1) * r + 1.27045825245236838258e0) * r
                      + 3.64784832476320460504e0) * r + 5.76949722146069140550e0) * r
                    + 4.63033784615654529590e0) * r + 1.42343711074968357734e0)
            den = (((((((1.05075007164441684324e-9 * r + 5.47593808499534494600e-4) * r
                        + 1.51986665636164571966e-2) * r + 1.48103976427480074590e-1) * r
                      + 6.89767334985100004550e-1) * r + 1.67638483018380384940e0) * r
                    + 2.05319162663775882187e0) * r + 1.0)
        else:
            r -= 5
            num = (((((((2.01033439929228813265e-7 * r + 2.71155556874348757815e-5) * r
                        + 1.24266094738807843860e-3) * r + 2.65321895265761230930e-2) * r
                      + 2.96560571828504891230e-1) * r + 1.78482653991729133580e0) * r
                    + 5.46378491116411436990e0) * r + 6.65790464350110377720e0)
            den = (((((((2.04426310338993978564e-15 * r + 1.42151175831644588870e-7) * r
                        + 1.84631831751005468180e-5) * r + 7.86869131145613259100e-4) * r
                      + 1.48753612908506148525e-2) * r + 1.36929880922735805310e-1) * r
                    + 5.99832206555887937690e-1) * r + 1.0)
        result = num / den
        if p < 0.5:
            result = -result
        return result


def _t_critical_value(p: float, df: int) -> float:
    """Student's t critical value (two-tailed)."""
    if _HAS_SCIPY:
        return float(scipy_stats.t.ppf(p, df))
    # Approximation for df > 0
    if df <= 0:
        return _norm_ppf(p)
    z = _norm_ppf(p)
    # Adjusted z for t distribution (simple approximation)
    return z * (1 + (z**2 + 1) / (4 * df) + (z**4 + 3 * z**2 + 3) / (96 * df**2))


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

_TEST_DATASET_1 = {
    "name": "Normand 1999 (8 studies, psychotherapy — classical meta-analysis)",
    "effects": [0.10, 0.20, 0.15, 0.05, 0.30, 0.25, 0.18, 0.22],
    "variances": [0.01, 0.02, 0.015, 0.01, 0.03, 0.025, 0.018, 0.020],
}

_TEST_DATASET_2 = {
    "name": "Synthetic homogeneous (5 studies, I² ≈ 0%)",
    "effects": [0.52, 0.48, 0.50, 0.53, 0.49],
    "variances": [0.04, 0.04, 0.04, 0.04, 0.04],
}


def self_test() -> int:
    """Run embedded test datasets. Returns 0 on success, 1 on failure."""
    errors = 0

    for ds in [_TEST_DATASET_1, _TEST_DATASET_2]:
        print(f"Testing: {ds['name']}")
        re = random_effects_pool(ds["effects"], ds["variances"])
        fe = fixed_effects_pool(ds["effects"], ds["variances"])

        # Basic sanity checks
        assert 0 <= re["I2"] <= 100, f"I² out of range: {re['I2']}"
        assert re["tau2"] >= 0, f"tau² negative: {re['tau2']}"
        assert re["ci_lower"] <= re["pooled_estimate"] <= re["ci_upper"], "CI ordering"

        # FE and RE should be close when I² is low
        if ds == _TEST_DATASET_2:
            diff = abs(re["pooled_estimate"] - fe["pooled_estimate"])
            assert diff < 0.01, f"FE/RE divergence in homogeneous data: {diff:.4f}"

        print(f"  RE: {re['pooled_estimate']:.4f} [{re['ci_lower']:.4f}, {re['ci_upper']:.4f}], I²={re['I2']:.1f}%, tau²={re['tau2']:.4f}")
        print(f"  FE: {fe['pooled_estimate']:.4f} [{fe['ci_lower']:.4f}, {fe['ci_upper']:.4f}]")

        # Forest plot
        fp = forest_plot_text(re, effects=ds["effects"], variances=ds["variances"])
        assert "Pooled" in fp, "Forest plot missing pooled estimate"
        print("  Forest plot: OK")

        # Fail-safe N
        fsn = fail_safe_n(ds["effects"], ds["variances"])
        assert fsn["fail_safe_N"] >= 0, "Fail-safe N negative"
        print(f"  Fail-safe N: {fsn['fail_safe_N']}")

        # Leave-one-out
        loo = sensitivity_leave_one_out(ds["effects"], ds["variances"])
        assert len(loo) == len(ds["effects"]), "LOO count mismatch"
        print(f"  Leave-one-out: {len(loo)} iterations OK")

        print()

    print("All self-tests passed." if errors == 0 else f"{errors} errors found.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    else:
        # Interactive usage: print help
        print("meta_analysis.py — Use --self-test to validate, or import as module.")
        print("Functions: random_effects_pool, fixed_effects_pool, forest_plot_text,")
        print("           fail_safe_n, sensitivity_leave_one_out, heterogeneity_interpretation")
