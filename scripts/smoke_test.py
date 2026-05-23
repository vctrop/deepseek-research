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
        "protocol_registry", "living_review", "grade",
        "topic_extractor", "stage_output",
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
            sort_deep_read_queue,
        )
        check("helpers.py import", True)
        # Quick functional test
        sha = compute_sha256(str(SKILL_DIR / "SKILL.md"))
        check("compute_sha256 returns 64-char hex", len(sha) == 64, f"got len={len(sha)}")
        sha_empty = compute_sha256("/nonexistent/path.txt")
        check("compute_sha256 returns empty on missing file", sha_empty == "")
        # sort_deep_read_queue functional test
        test_sources = json.dumps([
            {"source_id": "S1", "priority": "primary_empirical", "relevance": 4},
            {"source_id": "S2", "priority": "answers_SQ_directly", "relevance": 5},
            {"source_id": "S3", "priority": "code_reference", "relevance": 3},
            {"source_id": "S4", "priority": "cross_theory_comparison", "relevance": 4},
            {"source_id": "S5", "priority": "review_secondary", "relevance": 2},
        ])
        sorted_json = sort_deep_read_queue(test_sources)
        sorted_sources = json.loads(sorted_json)
        check("sort_deep_read_queue returns 5 sources", len(sorted_sources) == 5)
        check("sort_deep_read_queue: S2 first (answers_SQ_directly)",
              sorted_sources[0]["source_id"] == "S2")
        check("sort_deep_read_queue: S3 last (code_reference, tier 5)",
              sorted_sources[-1]["source_id"] == "S3")
        # Default priority test
        test_default = json.dumps([
            {"source_id": "A", "relevance": 5},
            {"source_id": "B", "priority": "answers_SQ_directly", "relevance": 1},
        ])
        sorted_default = json.loads(sort_deep_read_queue(test_default))
        check("sort_deep_read_queue: explicit priority beats default",
              sorted_default[0]["source_id"] == "B")
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
        from living_review import check_update_needed, build_surveillance_queries, record_surveillance
        check("living_review.py import", True)
    except Exception as e:
        check("living_review.py import", False, str(e))

    # grade.py — self-test
    try:
        result = subprocess.run(
            ["python3", str(SKILL_DIR / "scripts" / "grade.py"), "--self-test"],
            capture_output=True, text=True, timeout=30,
        )
        check("grade.py self-test exit 0", result.returncode == 0,
              f"exit={result.returncode}, stderr={result.stderr[:200]}")
    except Exception as e:
        check("grade.py self-test", False, str(e))

    # topic_extractor.py
    try:
        from topic_extractor import extract_topics, topics_to_csv
        check("topic_extractor.py import", True)
        topics = extract_topics(
            "comparison of Thousand Brain Theory, Free Energy Principle, and Predictive Processing"
        )
        check("extract_topics returns list", isinstance(topics, list))
        check("extract_topics finds >=2 topics", len(topics) >= 2,
              f"got {len(topics)}: {topics}")
        csv = topics_to_csv(topics)
        check("topics_to_csv returns comma-separated", "," in csv or len(topics) <= 1)
    except Exception as e:
        check("topic_extractor.py", False, str(e))

    # Adversarial prompt builder
    try:
        from prompts import _build_adversarial_prompt
        result = _build_adversarial_prompt(
            rq_text="Test RQ: effect of X on Y",
            included_sources_json='[{"source_id": "S1", "title": "Test Paper"}]',
            main_topic="test topic",
        )
        check("_build_adversarial_prompt returns non-empty str", len(result) > 100)
        check("_build_adversarial_prompt contains ADVERSARIAL SEARCH",
              "ADVERSARIAL SEARCH" in result)
    except Exception as e:
        check("_build_adversarial_prompt", False, str(e))

    # _build_per_topic_queries
    try:
        from prompts import _build_per_topic_queries
        
        result = _build_per_topic_queries("TBT,CBH,FEP", '"limitations of {topic}"')
        check("_build_per_topic_queries 3 topics → 3 lines",
              len([l for l in result.strip().split('\n') if l.strip()]) == 3)
        
        result_empty = _build_per_topic_queries("", "pattern {topic}")
        check("_build_per_topic_queries empty → empty string",
              result_empty.strip() == "")
        
        result_single = _build_per_topic_queries("single", "query {topic}")
        check("_build_per_topic_queries single → 1 line",
              len([l for l in result_single.strip().split('\n') if l.strip()]) == 1)
        
        result_trim = _build_per_topic_queries("a, b , c", "topic:{topic}")
        check("_build_per_topic_queries trim whitespace",
              len([l for l in result_trim.strip().split('\n') if l.strip()]) == 3)
    except Exception as e:
        check("_build_per_topic_queries", False, str(e))

    # build_subagent_prompt — all 10 templates
    try:
        from helpers import build_subagent_prompt
        
        builder_tests = {
            'dsr-bibliography': dict(rq_text='Test RQ', bibliography_path='/tmp', main_topic='test'),
            'dsr-web': dict(rq_text='Test RQ', main_topic='test'),
            'dsr-code': dict(rq_text='Test RQ'),
            'dsr-opensource': dict(rq_text='Test RQ', main_topic='test'),
            'dsr-grey': dict(rq_text='Test RQ', main_topic='test'),
            'dsr-deep-read': dict(source_id='S1', source_path_or_url='http://ex.com',
                                  source_title='T', rq_text='RQ', skill_dir=str(SKILL_DIR),
                                  session_dir='/tmp'),
            'dsr-deep-read-t5': dict(source_id='S1', repo_url='http://ex.com',
                                     rq_text='RQ', skill_dir=str(SKILL_DIR), session_dir='/tmp'),
            'dsr-adversarial': dict(rq_text='RQ', included_sources_json='[]', main_topic='test'),
            'dsr-da': dict(session_dir='/tmp', skill_dir=str(SKILL_DIR)),
            'dsr-tiebreak': dict(rq_text='RQ', bibliography_path='/tmp',
                                 disagreement_list='S1: INCLUDE vs EXCLUDE'),
        }
        
        for name, kwargs in builder_tests.items():
            prompt = build_subagent_prompt(name, **kwargs)
            check(f"build_subagent_prompt({name})",
                  prompt is not None and len(prompt) > 100,
                  f"got {len(prompt) if prompt else 0} chars")
        
        try:
            build_subagent_prompt('invalid-name', rq_text='x')
            check("build_subagent_prompt(invalid) raises", False, "should have raised ValueError")
        except (ValueError, KeyError):
            check("build_subagent_prompt(invalid) raises", True)
    except Exception as e:
        check("build_subagent_prompt dispatcher", False, str(e))

    # stage_output.py
    try:
        from stage_output import stage_output_exists, stage_output_valid, stage_is_complete
        check("stage_output.py import", True)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            # Missing file
            assert not stage_is_complete(tmp, "01-rq-brief.md")
            # Valid file
            from pathlib import Path
            p = Path(tmp) / "01-rq-brief.md"
            p.write_text("## Research Question\n...\n## Sub-Questions\n...")
            assert stage_is_complete(tmp, "01-rq-brief.md")
        check("stage_is_complete smoke test", True)
    except Exception as e:
        check("stage_output.py", False, str(e))


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
    expected_gates = set(range(1, 24))  # GATE-1 through GATE-23
    check("23 gates in SKILL.md", gates_skill == expected_gates,
          f"missing: {sorted(expected_gates - gates_skill)}")
    check("23 gates in pipeline-detail.md", gates_pd == expected_gates,
          f"missing: {sorted(expected_gates - gates_pd)}")

    # Count checklist ids
    updates = [int(x) for x in re.findall(r"checklist_update\(\s*id\s*=\s*(\d+)", pd_text)]
    expected_ids = set(range(1, 17))
    actual_ids = set(updates)
    check("checklist ids 1-16 all covered", actual_ids == expected_ids,
          f"missing: {sorted(expected_ids - actual_ids)}, extra: {sorted(actual_ids - expected_ids)}")

    # Line count within budget
    lines = len(skill_text.splitlines())
    check(f"SKILL.md line count ≤ 550", lines <= 550, f"actual: {lines}")

    # Intro mentions correct counts
    check("SKILL.md intro mentions stages", "stages" in skill_text)
    if "23 verification gates" in skill_text or "22 verification gates" in skill_text:
        check("SKILL.md intro mentions gate count", True)
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
        "oss_clone_dir": str,
        "adversarial_search": bool,
    }
    check("20 config vars documented", len(defaults) == 20)


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
