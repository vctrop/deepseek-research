#!/usr/bin/env python3
"""grade.py — GRADE certainty of evidence rating for deepseek-research.

Adapted GRADE framework for engineering/simulation evidence (see
references/grade-framework.md). Pure Python, no external dependencies.

Usage:
    from grade import rate_certainty
    result = rate_certainty(
        finding_id="K1",
        study_designs=["controlled_experiment", "simulation_with_vv"],
        rob_scores=["Low", "Some concerns"],
        i2=42.0,
        indirectness="direct",
        imprecision={"ci_crosses_threshold": False, "total_n": 120},
        pub_bias={"same_group_pct": 25.0, "funnel_asymmetry": False},
    )
    print(result["final_symbol"], result["final_certainty"])
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Starting certainty from study design
# ---------------------------------------------------------------------------

_STARTING_CERTAINTY = {
    "formal_verification": ("HIGH", 4),       # ⊕⊕⊕⊕
    "controlled_experiment": ("HIGH", 4),     # ⊕⊕⊕⊕
    "simulation_with_vv": ("MODERATE", 3),    # ⊕⊕⊕⊝
    "simulation_without_vv": ("LOW", 2),      # ⊕⊕⊝⊝
    "observational": ("LOW", 2),              # ⊕⊕⊝⊝
    "expert_opinion": ("VERY_LOW", 1),        # ⊕⊝⊝⊝
}

_SYMBOLS = {4: "⊕⊕⊕⊕", 3: "⊕⊕⊕⊝", 2: "⊕⊕⊝⊝", 1: "⊕⊝⊝⊝", 0: "⊝⊝⊝⊝"}


def _starting_level(study_designs: list[str]) -> tuple[int, str]:
    """Determine starting certainty from the highest-quality study design."""
    max_level = 1
    max_design = "expert_opinion"
    for design in study_designs:
        if design in _STARTING_CERTAINTY:
            cert, level = _STARTING_CERTAINTY[design]
            if level > max_level:
                max_level = level
                max_design = design
    return max_level, max_design


def _apply_downgrades(
    level: int,
    rob_scores: list[str],
    i2: float,
    indirectness: str,
    imprecision: dict | None,
    pub_bias: dict | None,
) -> tuple[int, list[str]]:
    """Apply downgrade domains (-1 or -2 each). Returns (new_level, reasons)."""
    reasons = []

    # Risk of bias: use worst score across all contributing studies
    rob_map = {"Critical": -2, "High": -1, "Some concerns": 0, "Low": 0}
    worst_rob = min((rob_map.get(r, 0) for r in rob_scores), default=0)
    if worst_rob == -2:
        level += worst_rob
        reasons.append(f"Risk of bias: Critical (-2)")
    elif worst_rob == -1:
        level += worst_rob
        reasons.append(f"Risk of bias: High (-1)")

    # Inconsistency (I²)
    if i2 > 90:
        level -= 2
        reasons.append(f"Inconsistency: I²={i2:.0f}% > 90% (-2)")
    elif i2 > 75:
        level -= 1
        reasons.append(f"Inconsistency: I²={i2:.0f}% > 75% (-1)")

    # Indirectness
    if indirectness == "major_mismatch":
        level -= 2
        reasons.append("Indirectness: major mismatch (-2)")
    elif indirectness == "minor_mismatch":
        level -= 1
        reasons.append("Indirectness: minor mismatch (-1)")

    # Imprecision
    if imprecision:
        if imprecision.get("ci_crosses_threshold"):
            level -= 1
            reasons.append("Imprecision: CI crosses decision threshold (-1)")
        if imprecision.get("total_n", 100) < 50:
            level -= 1
            reasons.append(f"Imprecision: small sample N={imprecision['total_n']} (-1)")

    # Publication bias
    if pub_bias:
        if pub_bias.get("funnel_asymmetry"):
            level -= 1
            reasons.append("Publication bias: funnel asymmetry suspected (-1)")
        if pub_bias.get("same_group_pct", 0) >= 50:
            level -= 1
            reasons.append(f"Publication bias: {pub_bias['same_group_pct']:.0f}% from same group (-1)")

    return max(0, level), reasons


def _apply_upgrades(
    level: int,
    pooled_effect: float | None = None,
    baseline: float = 0.0,
    dose_response_levels: int = 0,
    opposing_confounding: bool = False,
) -> tuple[int, list[str]]:
    """Apply upgrade domains (+1 or +2 each). Returns (new_level, reasons)."""
    reasons = []

    # Large effect
    if pooled_effect is not None and baseline != 0:
        ratio = abs(pooled_effect / baseline) if baseline != 0 else float("inf")
        if ratio > 5:
            level += 2
            reasons.append(f"Large effect: {ratio:.1f}× baseline (+2)")
        elif ratio > 2:
            level += 1
            reasons.append(f"Large effect: {ratio:.1f}× baseline (+1)")

    # Dose-response gradient
    if dose_response_levels >= 5:
        level += 2
        reasons.append(f"Dose-response: {dose_response_levels} levels (+2)")
    elif dose_response_levels >= 3:
        level += 1
        reasons.append(f"Dose-response: {dose_response_levels} levels (+1)")

    # Opposing confounding
    if opposing_confounding:
        level += 1
        reasons.append("Opposing confounding would increase effect (+1)")

    return min(4, level), reasons


def _level_to_certainty(level: int) -> str:
    """Map numeric level to certainty label."""
    if level >= 4:
        return "HIGH"
    elif level == 3:
        return "MODERATE"
    elif level == 2:
        return "LOW"
    else:
        return "VERY_LOW"


def rate_certainty(
    finding_id: str,
    study_designs: list[str],
    rob_scores: list[str],
    i2: float = 0.0,
    indirectness: str = "direct",
    imprecision: dict | None = None,
    pub_bias: dict | None = None,
    pooled_effect: float | None = None,
    baseline: float = 0.0,
    dose_response_levels: int = 0,
    opposing_confounding: bool = False,
) -> dict:
    """Rate the overall certainty of evidence for a key finding using GRADE.

    Args:
        finding_id: Key finding identifier (e.g., "K1").
        study_designs: List of study designs across contributing sources.
            Valid: "formal_verification", "controlled_experiment",
            "simulation_with_vv", "simulation_without_vv",
            "observational", "expert_opinion".
        rob_scores: Risk of bias scores per contributing source.
            Valid: "Low", "Some concerns", "High", "Critical".
        i2: Heterogeneity I² percentage (0-100).
        indirectness: "direct", "minor_mismatch", or "major_mismatch".
        imprecision: {"ci_crosses_threshold": bool, "total_n": int} or None.
        pub_bias: {"same_group_pct": float, "funnel_asymmetry": bool} or None.
        pooled_effect: Pooled effect estimate (for upgrade assessment).
        baseline: Baseline value for effect ratio calculation.
        dose_response_levels: Number of fidelity levels with gradient.
        opposing_confounding: Whether confounders would increase effect.

    Returns:
        dict with keys: finding_id, starting_certainty, starting_symbol,
        starting_design, downgrades, upgrades, final_certainty,
        final_symbol, final_level, rationale.
    """
    start_level, start_design = _starting_level(study_designs)
    start_certainty = _level_to_certainty(start_level)
    start_symbol = _SYMBOLS.get(start_level, "?")

    level, downgrades = _apply_downgrades(
        start_level, rob_scores, i2, indirectness, imprecision, pub_bias
    )
    downgrade_level = level  # after downgrades

    level, upgrades = _apply_upgrades(
        level, pooled_effect, baseline, dose_response_levels, opposing_confounding
    )

    level = max(0, min(4, level))  # clamp
    final_certainty = _level_to_certainty(level)
    final_symbol = _SYMBOLS.get(level, "?")

    # Build rationale
    parts = [f"Starting: {start_certainty} ({start_symbol}) from {start_design}"]
    if downgrades:
        parts.append(f"Downgraded: {'; '.join(downgrades)}")
    if upgrades:
        parts.append(f"Upgraded: {'; '.join(upgrades)}")
    parts.append(f"Final: {final_certainty} ({final_symbol})")
    rationale = ". ".join(parts)

    return {
        "finding_id": finding_id,
        "starting_certainty": start_certainty,
        "starting_symbol": start_symbol,
        "starting_design": start_design,
        "downgrades": downgrades,
        "upgrades": upgrades,
        "final_certainty": final_certainty,
        "final_symbol": final_symbol,
        "final_level": level,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    """Run self-test on known scenarios. Returns 0 on success, 1 on failure."""
    errors = 0

    # Test 1: High-quality evidence, no downgrades
    r = rate_certainty(
        finding_id="K1",
        study_designs=["controlled_experiment", "controlled_experiment"],
        rob_scores=["Low", "Low"],
        i2=10.0,
        indirectness="direct",
        imprecision={"ci_crosses_threshold": False, "total_n": 200},
        pub_bias={"same_group_pct": 20.0, "funnel_asymmetry": False},
    )
    assert r["final_certainty"] == "HIGH", f"Expected HIGH, got {r['final_certainty']}"
    assert r["final_level"] == 4, f"Expected level 4, got {r['final_level']}"
    print(f"  K1: {r['final_symbol']} {r['final_certainty']} — {r['rationale']}")

    # Test 2: Serious RoB + high I²
    r = rate_certainty(
        finding_id="K2",
        study_designs=["simulation_with_vv"],
        rob_scores=["High"],
        i2=80.0,
        indirectness="direct",
    )
    assert r["final_certainty"] in ("LOW", "VERY_LOW"), f"Expected LOW/VERY_LOW, got {r['final_certainty']}"
    print(f"  K2: {r['final_symbol']} {r['final_certainty']} — {r['rationale']}")

    # Test 3: Critical RoB drops to VERY_LOW
    r = rate_certainty(
        finding_id="K3",
        study_designs=["controlled_experiment"],
        rob_scores=["Critical"],
        i2=0.0,
        indirectness="direct",
    )
    assert r["final_certainty"] == "LOW", f"Expected LOW after Critical, got {r['final_certainty']}"
    print(f"  K3: {r['final_symbol']} {r['final_certainty']} — {r['rationale']}")

    # Test 4: Large effect upgrades
    r = rate_certainty(
        finding_id="K4",
        study_designs=["simulation_with_vv"],
        rob_scores=["Low"],
        i2=15.0,
        indirectness="direct",
        pooled_effect=0.45,
        baseline=0.10,
    )
    assert r["final_certainty"] == "HIGH", f"Expected HIGH after upgrade, got {r['final_certainty']}"
    print(f"  K4: {r['final_symbol']} {r['final_certainty']} — {r['rationale']}")

    # Test 5: Expert opinion with no upgrades stays VERY_LOW
    r = rate_certainty(
        finding_id="K5",
        study_designs=["expert_opinion"],
        rob_scores=["Some concerns"],
        i2=0.0,
        indirectness="direct",
    )
    assert r["final_certainty"] == "VERY_LOW", f"Expected VERY_LOW, got {r['final_certainty']}"
    print(f"  K5: {r['final_symbol']} {r['final_certainty']} — {r['rationale']}")

    print(f"\nAll self-tests {'passed' if errors == 0 else 'FAILED'}.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    else:
        print("grade.py — Use --self-test to validate, or import as module.")
        print("Function: rate_certainty(finding_id, study_designs, rob_scores, ...)")
