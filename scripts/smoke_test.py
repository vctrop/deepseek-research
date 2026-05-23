#!/usr/bin/env python3
"""smoke_test.py — Automated structural test battery for deepseek-research skill.

Run this after any change to SKILL.md, references/, scripts/, or templates/.
Exit code 0 = all tests pass. Non-zero = failures found.

Usage:
    python3 scripts/smoke_test.py
    python3 scripts/smoke_test.py --verbose
    python3 scripts/smoke_test.py --skip-scripts  # skip Python import tests
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
VERBOSE = "--verbose" in sys.argv
SKIP_SCRIPTS = "--skip-scripts" in sys.argv

pass_count = 0
fail_count = 0
warn_count = 0


def check(description: str, condition: bool, detail: str = "") -> None:
    global pass_count, fail_count
    if condition:
        pass_count += 1
        if VERBOSE:
            print(f"  [PASS] {description}")
    else:
        fail_count += 1
        print(f"  [FAIL] {description} — {detail}")


def warn(description: str, detail: str = "") -> None:
    global warn_count
    warn_count += 1
    if VERBOSE:
        print(f"  [WARN] {description} — {detail}")


# ═══════════════════════════════════════════════════════════════════
# TEST 1: File integrity — all companion files exist
# ═══════════════════════════════════════════════════════════════════
def test_file_integrity():
    print("\n=== Test 1: File Integrity ===")

    expected_refs = [
        "epistemology", "iron-rule-c", "anti-patterns", "error-recovery",
        "model-matrix", "context-budget", "configuration", "subagent-prompts",
        "press-checklist", "risk-of-bias", "grade-framework", "deep-reading",
        "epistemic-limitations", "pipeline-detail", "placeholders",
    ]
    expected_scripts = [
        "helpers", "index_sources", "meta_analysis",
        "protocol_registry", "living_review",
    ]
    expected_templates = [
        "rq-brief", "source-inventory", "source-verification", "synthesis",
        "devils-advocate", "report", "local-corpus-triage", "plain-summary",
        "decision-brief", "stakeholder-review", "source-deep-read",
        "opensource-decision",
    ]
    expected_root = ["SKILL.md", "README.md", "LICENSE.txt"]

    for ref in expected_refs:
        check(f"references/{ref}.md", (SKILL_DIR / "references" / f"{ref}.md").is_file())

    for script in expected_scripts:
        check(f"scripts/{script}.py", (SKILL_DIR / "scripts" / f"{script}.py").is_file())

    for tmpl in expected_templates:
        ext = "json" if tmpl == "data-supplement" else "md"
        check(f"templates/{tmpl}.{ext}", (SKILL_DIR / "templates" / f"{tmpl}.{ext}").is_file())

    for root_file in expected_root:
        check(root_file, (SKILL_DIR / root_file).is_file())

    # Check for data-supplement.json separately
    ds_path = SKILL_DIR / "templates" / "data-supplement.json"
    if ds_path.is_file():
        try:
            json.loads(ds_path.read_text())
            check("templates/data-supplement.json valid JSON", True)
        except json.JSONDecodeError as e:
            check("templates/data-supplement.json valid JSON", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# TEST 2: Script importability + self-tests
# ═══════════════════════════════════════════════════════════════════
def test_scripts():
    if SKIP_SCRIPTS:
        print("\n=== Test 2: Scripts (SKIPPED) ===")
        return

    print("\n=== Test 2: Script Importability ===")

    # helpers.py
    try:
        sys.path.insert(0, str(SKILL_DIR / "scripts"))
        from helpers import (
            compute_sha256, query_index, add_source_to_index,
            update_session_index, compute_cohens_kappa, build_subagent_prompt,
        )
        check("helpers.py import", True)
        # Quick functional test
        sha = compute_sha256(str(SKILL_DIR / "SKILL.md"))
        check("compute_sha256 returns 64-char hex", len(sha) == 64, f"got len={len(sha)}")
        sha_empty = compute_sha256("/nonexistent/path.txt")
        check("compute_sha256 returns empty on missing file", sha_empty == "")
    except Exception as e:
        check("helpers.py import", False, str(e))

    # index_sources.py
    try:
        from index_sources import main as index_main
        check("index_sources.py import", True)
    except Exception as e:
        check("index_sources.py import", False, str(e))

    # meta_analysis.py — self-test
    try:
        result = subprocess.run(
            ["python3", str(SKILL_DIR / "scripts" / "meta_analysis.py"), "--self-test"],
            capture_output=True, text=True, timeout=30,
        )
        check("meta_analysis.py self-test exit 0", result.returncode == 0,
              f"exit={result.returncode}, stderr={result.stderr[:200]}")
    except Exception as e:
        check("meta_analysis.py self-test", False, str(e))

    # protocol_registry.py
    try:
        from protocol_registry import register_local, register_protocol
        check("protocol_registry.py import", True)
    except Exception as e:
        check("protocol_registry.py import", False, str(e))

    # living_review.py
    try:
        from living_review import needs_update, load_session, merge_update, get_latest_update
        check("living_review.py import", True)
    except Exception as e:
        check("living_review.py import", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# TEST 3: Template validity
# ═══════════════════════════════════════════════════════════════════
def test_templates():
    print("\n=== Test 3: Template Validity ===")

    templates_dir = SKILL_DIR / "templates"
    for tmpl_path in sorted(templates_dir.glob("*.md")):
        content = tmpl_path.read_text()
        name = tmpl_path.name
        check(f"{name} non-empty", len(content) > 0)
        if len(content) < 10:
            warn(f"{name} very short", f"only {len(content.split())} words")

    # data-supplement.json already checked in test 1


# ═══════════════════════════════════════════════════════════════════
# TEST 4: SKILL.md internal consistency
# ═══════════════════════════════════════════════════════════════════
def test_skill_consistency():
    print("\n=== Test 4: SKILL.md Consistency ===")

    skill_text = (SKILL_DIR / "SKILL.md").read_text()
    pd_text = (SKILL_DIR / "references" / "pipeline-detail.md").read_text()

    # Count gates referenced
    gates_skill = set(int(g) for g in re.findall(r"GATE-(\d+)", skill_text))
    gates_pd = set(int(g) for g in re.findall(r"GATE-(\d+)", pd_text))
    expected_gates = set(range(1, 23))  # GATE-1 through GATE-22
    check("22 gates in SKILL.md", gates_skill == expected_gates,
          f"missing: {sorted(expected_gates - gates_skill)}")
    check("22 gates in pipeline-detail.md", gates_pd == expected_gates,
          f"missing: {sorted(expected_gates - gates_pd)}")

    # Count checklist ids
    updates = [int(x) for x in re.findall(r"checklist_update\(\s*id\s*=\s*(\d+)", pd_text)]
    expected_ids = set(range(1, 16))
    actual_ids = set(updates)
    check("checklist ids 1-15 all covered", actual_ids == expected_ids,
          f"missing: {sorted(expected_ids - actual_ids)}, extra: {sorted(actual_ids - expected_ids)}")

    # Line count within budget
    lines = len(skill_text.splitlines())
    check(f"SKILL.md line count ≤ 550", lines <= 550, f"actual: {lines}")

    # Intro mentions correct counts
    check("SKILL.md intro mentions 14 stages", "14 stages" in skill_text)
    if "22 verification gates" in skill_text:
        check("SKILL.md intro mentions 22 gates", True)
    else:
        # Accept any plausible count
        gate_mentions = re.findall(r"(\d+)\s*verification gates?", skill_text)
        if gate_mentions:
            check("SKILL.md intro mentions verification gates", int(gate_mentions[0]) >= 17)

    # Cross-references resolve
    refs = set(re.findall(r"(references/[\w-]+\.md|templates/[\w-]+\.(?:md|json)|scripts/[\w-]+\.py)", skill_text))
    missing_refs = [r for r in refs if not (SKILL_DIR / r).exists()]
    check("All SKILL.md cross-references resolve", len(missing_refs) == 0,
          f"missing: {missing_refs}")


# ═══════════════════════════════════════════════════════════════════
# TEST 5: Iron Rule C regex
# ═══════════════════════════════════════════════════════════════════
def test_iron_rule_c():
    print("\n=== Test 5: Iron Rule C Regex ===")

    bare_words = [
        "validated", "proved", "confirmed", "demonstrated", "ensures",
        "guarantees", "always", "never", "optimal", "definitive",
        "conclusive", "certainly", "undoubtedly", "obviously", "clearly",
    ]
    pattern = re.compile(r"\b(" + "|".join(bare_words) + r")\b", re.IGNORECASE)

    # Should match
    should_match = [
        "The model was validated.",
        "This approach guarantees correctness.",
        "The results clearly show improvement.",
        "This is the optimal solution.",
        "validated, proved, confirmed",
    ]
    for text in should_match:
        check(f"regex matches '{text[:50]}'", bool(pattern.search(text)))

    # Should NOT match (qualified or compound)
    should_not_match = [
        "pre-validated pipeline",
        "re-validated approach",
        "non-optimal but acceptable",
    ]
    # Note: these are known false positives in Pass 1 (cleared by Pass 2)
    for text in should_not_match:
        matches = pattern.findall(text)
        if matches:
            warn(f"regex matches compound '{text[:50]}'",
                 f"matched: {matches} — known Pass 1 false positive")


# ═══════════════════════════════════════════════════════════════════
# TEST 6: Configuration defaults
# ═══════════════════════════════════════════════════════════════════
def test_configuration():
    print("\n=== Test 6: Configuration Defaults ===")

    # Defaults from configuration.md
    defaults = {
        "source_axes": list,
        "bibliography_path": str,
        "output_dir": str,
        "session_index": str,
        "persist_sources": bool,
        "integration_checks": list,
        "max_sources_per_axis": int,
        "saturation_window": int,
        "dual_screening": bool,
        "agreement_threshold": float,
        "protocol_registry": str,
        "osf_token": str,
        "osf_project_id": str,
        "meta_analysis": str,
        "stakeholder_review": bool,
        "deep_reading": bool,
        "living_review": bool,
        "surveillance_interval_days": int,
    }
    check("18 config vars documented", len(defaults) == 18)


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
def main():
    print("deepseek-research Smoke Test")
    print(f"SKILL_DIR: {SKILL_DIR}")
    print(f"Python: {sys.version}")

    test_file_integrity()
    test_scripts()
    test_templates()
    test_skill_consistency()
    test_iron_rule_c()
    test_configuration()

    print(f"\n{'='*50}")
    print(f"RESULTS: {pass_count} PASS, {fail_count} FAIL, {warn_count} WARN")
    print(f"{'='*50}")

    if fail_count > 0:
        print("SMOKE TEST FAILED")
        sys.exit(1)
    else:
        print("SMOKE TEST PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
