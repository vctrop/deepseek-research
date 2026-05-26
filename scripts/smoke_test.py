#!/usr/bin/env python3
"""smoke_test.py — Teste estrutural automatizado para deepseek-research v3.0.

Rode após qualquer alteração em SKILL.md, references/, scripts/, ou templates/.
Exit code 0 = todos os testes passam. Non-zero = falhas encontradas.

Usage:
    python3 scripts/smoke_test.py
    python3 scripts/smoke_test.py --verbose
    python3 scripts/smoke_test.py --skip-scripts
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
# TEST 1: File integrity — expected files exist (v3.0 set)
# ═══════════════════════════════════════════════════════════════════
def test_file_integrity():
    print("\n=== Test 1: File Integrity ===")

    expected_refs = [
        "iron-rule-c", "error-recovery", "subagent-prompts",
        "risk-of-bias", "deep-reading", "pipeline-detail",
    ]
    expected_scripts = [
        "helpers", "prompts", "topic_extractor",
        "index_sources", "fulltext", "verify_title_match",
        "stage_status", "pipeline_metrics",
    ]
    expected_templates = [
        "rq-brief", "source-inventory", "source-verification", "synthesis",
        "report", "source-deep-read",
    ]
    expected_root = ["SKILL.md", "README.md", "LICENSE.txt", "AGENTS.md"]

    for ref in expected_refs:
        check(f"references/{ref}.md", (SKILL_DIR / "references" / f"{ref}.md").is_file())

    for script in expected_scripts:
        check(f"scripts/{script}.py", (SKILL_DIR / "scripts" / f"{script}.py").is_file())

    for tmpl in expected_templates:
        check(f"templates/{tmpl}.md", (SKILL_DIR / "templates" / f"{tmpl}.md").is_file())

    for root_file in expected_root:
        check(root_file, (SKILL_DIR / root_file).is_file())


# ═══════════════════════════════════════════════════════════════════
# TEST 2: Script importability + functional checks
# ═══════════════════════════════════════════════════════════════════
def test_scripts():
    if SKIP_SCRIPTS:
        print("\n=== Test 2: Scripts (SKIPPED) ===")
        return

    print("\n=== Test 2: Script Importability ===")

    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    sys.path.insert(0, str(SKILL_DIR / "tests"))

    # helpers.py
    try:
        from helpers import (
            compute_sha256, resolve_placeholders,
            build_subagent_prompt, compute_saturation,
            config_ensure, check_coverage_grade_consistency,
        )
        check("helpers.py import", True)

        sha = compute_sha256(str(SKILL_DIR / "SKILL.md"))
        check("compute_sha256 returns 64-char hex", len(sha) == 64, f"got len={len(sha)}")

        sha_empty = compute_sha256("/nonexistent/path.txt")
        check("compute_sha256 returns empty on missing file", sha_empty == "")

        # Test placeholder resolution
        resolved = resolve_placeholders("{date}", str(SKILL_DIR))
        check("resolve_placeholders replaces {date}", resolved != "{date}", f"got '{resolved}'")

        # Test build_subagent_prompt
        prompt = build_subagent_prompt("dsr-bibliography", rq_text="test RQ",
                                        bibliography_path="bib/", main_topic="test topic")
        check("build_subagent_prompt(dsr-bibliography) returns string",
              isinstance(prompt, str) and len(prompt) > 0)

        prompt2 = build_subagent_prompt("dsr-code", rq_text="test RQ")
        check("build_subagent_prompt(dsr-code) returns string",
              isinstance(prompt2, str) and len(prompt2) > 0)

        # Verify unknown template raises
        try:
            build_subagent_prompt("dsr-nonexistent", rq_text="x")
            check("build_subagent_prompt rejects unknown template", False)
        except ValueError:
            check("build_subagent_prompt rejects unknown template", True)

        # compute_saturation with empty dir
        sat = compute_saturation("/nonexistent/deep-reads/", "test RQ")
        check("compute_saturation returns False for nonexistent dir", not sat)

        # check_coverage_grade_consistency
        cov_result = check_coverage_grade_consistency(
            "/nonexistent/deep-reads/", "/nonexistent/synthesis.md"
        )
        import json
        cov_parsed = json.loads(cov_result)
        check("check_coverage_grade_consistency returns valid JSON",
              isinstance(cov_parsed, dict))
        # GATE-9 key is only present when synthesis file exists (not early-return).
        # When synthesis is missing, the function returns {"pass": True, "note": ..., "violations": []}
        check("check_coverage_grade_consistency has pass key",
              "pass" in cov_parsed)
        check("check_coverage_grade_consistency has violations key",
              "violations" in cov_parsed)

        # config_ensure
        import tempfile, tomllib
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: creates config when absent
            result = config_ensure(tmpdir)
            check("config_ensure creates when absent", result == "created")
            config_path = Path(tmpdir) / ".deepseek" / "deepseek-research.toml"
            check("config_ensure writes file", config_path.exists())
            parsed = tomllib.loads(config_path.read_text())
            check("config_ensure has all 10 keys", len(parsed) == 10,
                  f"got {len(parsed)} keys: {list(parsed.keys())}")

            # Test 2: ok when complete
            result = config_ensure(tmpdir)
            check("config_ensure returns ok when complete", result == "ok")

            # Test 3: adds missing keys (simulate by removing lines)
            content = config_path.read_text()
            stripped = "\n".join(
                line for line in content.splitlines()
                if "unpaywall_email" not in line and "allow_scihub" not in line
            )
            config_path.write_text(stripped)
            result = config_ensure(tmpdir)
            check("config_ensure adds missing keys",
                  result.startswith("added ") and "unpaywall_email" in result)
            reparsed = tomllib.loads(config_path.read_text())
            check("config_ensure restored 10 keys", len(reparsed) == 10)

    except Exception as e:
        check("helpers.py import", False, str(e))

    # prompts.py
    try:
        from prompts import _build_bibliography_prompt, _build_code_prompt, _build_per_topic_queries, _build_verify_titles_prompt
        check("prompts.py import", True)

        per_topic = _build_per_topic_queries("TBT,CBH", '"limitations of {topic}"')
        check("_build_per_topic_queries returns bullet list",
              len(per_topic) > 0 and "- " in per_topic)

        bib_prompt = _build_bibliography_prompt("test RQ", "bib/", "main", "TBT,CBH")
        check("_build_bibliography_prompt with topics", "TBT" in bib_prompt)

        code_prompt = _build_code_prompt("test RQ")
        check("_build_code_prompt returns string", len(code_prompt) > 0)

        # Test dsr-verify-titles prompt builder
        import json
        test_sources = json.dumps([
            {"source_id": "S1", "reported_title": "Test Paper", "url": "https://example.com/paper"}
        ])
        verify_prompt = _build_verify_titles_prompt(test_sources)
        check("_build_verify_titles_prompt returns string", len(verify_prompt) > 0)
        check("_build_verify_titles_prompt includes source_id",
              "S1" in verify_prompt)
        check("_build_verify_titles_prompt includes URL",
              "https://example.com/paper" in verify_prompt)
        check("_build_verify_titles_prompt includes match heuristic",
              "match_pct" in verify_prompt)
        check("_build_verify_titles_prompt includes output path",
              "/tmp/dsr-verify-results.json" in verify_prompt)

    except Exception as e:
        check("prompts.py import", False, str(e))

    # topic_extractor.py
    try:
        from topic_extractor import extract_topics, topics_to_csv
        check("topic_extractor.py import", True)

        topics = extract_topics(
            "comparison of Thousand Brain Theory, Critical Brain Hypothesis, "
            "and Free Energy Principle in computational neuroscience"
        )
        check("extract_topics finds topics", len(topics) >= 2, f"got {len(topics)}: {topics}")
        csv = topics_to_csv(topics)
        check("topics_to_csv returns comma-separated", "," in csv, f"got '{csv}'")

    except Exception as e:
        check("topic_extractor.py import", False, str(e))

    # index_sources.py
    try:
        import tempfile
        from index_sources import (
            init_sources, scan_unindexed, query_sources,
            add_source, update_sessions,
        )
        check("index_sources.py import", True)

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "bib"

            # init
            init_sources(base)
            check("init_sources creates base dir", base.is_dir())
            check("init_sources creates index/", (base / "index").is_dir())
            idx_path = base / "index" / "sources.json"
            check("init_sources creates sources.json", idx_path.exists())

            # Idempotent
            init_sources(base)
            check("init_sources is idempotent", idx_path.exists())

            # scan_unindexed (empty)
            result = scan_unindexed(base)
            check("scan_unindexed empty returns []", result == [], f"got {result}")

            # add_source
            pdf = base / "test.pdf"
            pdf.write_text("fake pdf content")
            entry = {
                "id": "smith-2020", "title": "Test Paper",
                "authors": ["Smith, J."], "year": 2020,
                "doi": "10.1234/test", "keywords": ["test"],
                "summary": "A test paper.", "quality_level": "II",
                "source_type": "paper",
            }
            result = add_source(base, pdf, entry)
            check("add_source returns entry with path", result.get("path") == "smith-2020.pdf")
            check("add_source copies file to bibliography",
                  (base / "smith-2020.pdf").exists())
            check("add_source sets indexed_at", "indexed_at" in result)

            # Duplicate ID
            try:
                add_source(base, pdf, {"id": "smith-2020", "title": "Dup"})
                check("add_source rejects duplicate ID", False)
            except ValueError:
                check("add_source rejects duplicate ID", True)

            # query_sources
            # Reinit with fresh data
            import json
            idx_path.write_text(json.dumps([entry]))
            results = query_sources(base, ["test", "paper"], top_n=5)
            check("query_sources returns results", len(results) >= 1)
            check("query_sources returns correct entry",
                  results[0].get("id") == "smith-2020")

            # No-match query
            results = query_sources(base, ["xyzzy", "nonexistent"], top_n=5)
            check("query_sources no-match returns []", results == [])

            # update_sessions
            update_sessions(base, "smith-2020", "2026-05-24-test")
            entries = json.loads(idx_path.read_text())
            sessions = entries[0].get("sessions_used", [])
            check("update_sessions appends slug", "2026-05-24-test" in sessions)

            # update_sessions bad ID
            try:
                update_sessions(base, "nonexistent", "slug")
                check("update_sessions raises on bad ID", False)
            except KeyError:
                check("update_sessions raises on bad ID", True)

    except Exception as e:
        check("index_sources.py functional tests", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# TEST 3: Template validity — all templates parse clean
# ═══════════════════════════════════════════════════════════════════
def test_templates():
    print("\n=== Test 3: Template Validity ===")

    templates_dir = SKILL_DIR / "templates"
    for tmpl in sorted(templates_dir.glob("*.md")):
        content = tmpl.read_text(encoding="utf-8")
        check(f"{tmpl.name} non-empty", len(content) > 50)
        check(f"{tmpl.name} starts with ---", content.strip().startswith("---"))


# ═══════════════════════════════════════════════════════════════════
# TEST 4: SKILL.md consistency
# ═══════════════════════════════════════════════════════════════════
def test_skill_consistency():
    print("\n=== Test 4: SKILL.md Consistency ===")

    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    # 5 stages + 2 indexing phases
    for s in ["Phase 0", "Phase 1.5", "Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"]:
        check(f"SKILL.md mentions {s}", s in skill_text)

    # 10 gates (v3.0) + GATE-0b (v3.2)
    gates = [f"GATE-{i}" for i in range(1, 11)]
    for g in gates:
        check(f"SKILL.md mentions {g}", g in skill_text)
    check("SKILL.md mentions GATE-0b", "GATE-0b" in skill_text)

    # Pipeline overview
    for token in ["RQ Formulation", "Source Discovery", "Source Verification",
                   "Deep Reading", "Synthesis + Report", "Close"]:
        check(f"SKILL.md pipeline mentions {token}", token in skill_text)

    # Key references
    for ref_file in ["pipeline-detail.md", "deep-reading.md", "risk-of-bias.md",
                      "error-recovery.md", "subagent-prompts.md", "iron-rule-c.md"]:
        check(f"SKILL.md references {ref_file}", ref_file in skill_text)

    # Key templates
    for tmpl in ["rq-brief.md", "source-inventory.md", "source-verification.md",
                  "synthesis.md", "report.md", "source-deep-read.md"]:
        check(f"SKILL.md references templates/{tmpl}", tmpl in skill_text)

    # Config vars
    for var in ["source_axes", "bibliography_path", "output_dir",
                 "max_sources_per_axis", "max_deep_reads", "deep_reading", "oss_clone_dir"]:
        check(f"SKILL.md config var {var}", var in skill_text)

    # Sub-agents
    check("dsr-bibliography referenced", "dsr-bibliography" in skill_text)
    check("dsr-code referenced", "dsr-code" in skill_text)

    # No stale references
    stale_refs = ["epistemology.md", "grade-framework.md", "press-checklist.md",
                   "epistemic-limitations.md", ".session-state.json",
                   "devils-advocate", "meta-analysis", "GRADE", "PRISMA 2020",
                   "Cohen's κ", "dual_screening", "living_review", "OSF/Zenodo"]
    for stale in stale_refs:
        if stale in skill_text:
            warn(f"SKILL.md contains stale reference: {stale}")

    # pipeline-detail consistency (only documents GATE 1-5 procedurally)
    pd_text = (SKILL_DIR / "references" / "pipeline-detail.md").read_text(encoding="utf-8")
    pd_gates = [f"GATE-{i}" for i in range(1, 6)]
    for g in pd_gates:
        check(f"pipeline-detail.md mentions {g}", g in pd_text)
    for s in ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"]:
        check(f"pipeline-detail.md mentions {s}", s in pd_text)

    # 5-stage pipeline not 15+
    check("pipeline does not reference Stage 1.5", "Stage 1.5" not in pd_text)
    check("pipeline does not reference Stage 2.1", "Stage 2.1" not in pd_text)
    check("pipeline does not reference Stage 3.5", "Stage 3.5" not in pd_text)


# ═══════════════════════════════════════════════════════════════════
# TEST 5: Iron Rule C patterns present
# ═══════════════════════════════════════════════════════════════════
def test_iron_rule_c():
    print("\n=== Test 5: Iron Rule C ===")

    ruled = (SKILL_DIR / "references" / "iron-rule-c.md").read_text(encoding="utf-8")

    for word in ["validated", "proved", "confirmed", "demonstrated", "ensures",
                  "guarantees", "always", "never", "optimal", "definitive",
                  "conclusive", "certainly", "undoubtedly", "obviously", "clearly"]:
        check(f"Iron Rule C mentions '{word}'", word in ruled.lower())


# ═══════════════════════════════════════════════════════════════════
# TEST 6: Evidence taxonomy preserved
# ═══════════════════════════════════════════════════════════════════
def test_taxonomy():
    print("\n=== Test 6: Evidence Taxonomy ===")

    dr_text = (SKILL_DIR / "references" / "deep-reading.md").read_text(encoding="utf-8")
    for grade in ["V — Verbatim", "P — Paraphrase", "I — Inference",
                   "M — Mathematical", "E — Empirical"]:
        check(f"deep-reading.md mentions {grade}", grade in dr_text)


# ═══════════════════════════════════════════════════════════════════
# TEST 7: Templates reference only valid companion files
# ═══════════════════════════════════════════════════════════════════
def test_template_refs():
    print("\n=== Test 7: Template Ref Integrity ===")

    templates_dir = SKILL_DIR / "templates"
    for tmpl in sorted(templates_dir.glob("*.md")):
        content = tmpl.read_text(encoding="utf-8")
        # Check for old references we know should be removed
        for stale in ["epistemology.md", "epistemic-limitations.md",
                       "grade-framework.md", "press-checklist.md"]:
            if stale in content:
                warn(f"{tmpl.name} references stale file: {stale}")


# ═══════════════════════════════════════════════════════════════════
# TEST 8: Verification gate fixtures
# ═══════════════════════════════════════════════════════════════════
def test_verification_gates():
    print("\n=== Test 8: Verification Gate Fixtures ===")

    fixtures_dir = SKILL_DIR / "tests" / "fixtures"
    if not fixtures_dir.exists():
        print("  [SKIP] tests/fixtures/ directory not found")
        return

    import json

    # GATE-6: verify_completeness
    try:
        from verify_completeness import check as gate6

        # complete-pass should PASS
        result = json.loads(gate6(
            str(fixtures_dir / "complete-pass" / "02-source-inventory.md"),
            str(fixtures_dir / "complete-pass" / "03-source-verification.md"),
        ))
        check("GATE-6: complete-pass fixture passes",
              result["pass"] is True,
              f"violations: {result.get('violations', [])}")

        # missing-status should FAIL
        result = json.loads(gate6(
            str(fixtures_dir / "missing-status" / "02-source-inventory.md"),
            str(fixtures_dir / "missing-status" / "03-source-verification.md"),
        ))
        check("GATE-6: missing-status fixture fails",
              result["pass"] is False)
        check("GATE-6: missing-status detects S2",
              any("S2" in v for v in result.get("violations", [])),
              f"violations: {result.get('violations', [])}")
    except Exception as e:
        check("GATE-6 fixture tests", False, str(e))

    # GATE-7: verify_evidence_grades
    try:
        from verify_evidence_grades import check as gate7

        # complete-pass should PASS
        result = json.loads(gate7(
            str(fixtures_dir / "complete-pass" / "deep-reads")
        ))
        check("GATE-7: complete-pass fixture passes",
              result["pass"] is True,
              f"violations: {result.get('violations', [])}")

        # snippet-v-grade should FAIL
        result = json.loads(gate7(
            str(fixtures_dir / "snippet-v-grade" / "deep-reads")
        ))
        check("GATE-7: snippet-v-grade fixture fails",
              result["pass"] is False)
        check("GATE-7: snippet-v-grade detects V-grade from snippet",
              any("V-grade" in v or "snippet" in v.lower() for v in result.get("violations", [])),
              f"violations: {result.get('violations', [])}")
    except Exception as e:
        check("GATE-7 fixture tests", False, str(e))

    # GATE-8: verify_source_refs
    try:
        from verify_source_refs import check as gate8

        # complete-pass should PASS
        result = json.loads(gate8(
            str(fixtures_dir / "complete-pass" / "02-source-inventory.md"),
            str(fixtures_dir / "complete-pass" / "04-synthesis.md"),
            str(fixtures_dir / "complete-pass" / "05-report.md"),
        ))
        check("GATE-8: complete-pass fixture passes",
              result["pass"] is True,
              f"violations: {result.get('violations', [])}")

        # ghost-source should FAIL
        result = json.loads(gate8(
            str(fixtures_dir / "ghost-source" / "02-source-inventory.md"),
            str(fixtures_dir / "ghost-source" / "04-synthesis.md"),
            str(fixtures_dir / "ghost-source" / "05-report.md"),
        ))
        check("GATE-8: ghost-source fixture fails",
              result["pass"] is False)
        check("GATE-8: ghost-source detects S99",
              any("S99" in v for v in result.get("violations", [])),
              f"violations: {result.get('violations', [])}")
    except Exception as e:
        check("GATE-8 fixture tests", False, str(e))

    # GATE-2: check_iron_rule_c_deterministic (bare-claim fixture)
    try:
        from helpers import check_iron_rule_c_deterministic

        # bare-claim should FAIL (has "guarantees", "conclusively", "validated")
        result = json.loads(check_iron_rule_c_deterministic(
            str(fixtures_dir / "bare-claim" / "05-report.md"),
            str(fixtures_dir / "bare-claim" / "04-synthesis.md"),
        ))
        check("GATE-2: bare-claim fixture fails",
              result["pass"] is False,
              f"result: {result}")
        check("GATE-2: bare-claim detects bare words",
              len(result.get("violations", [])) > 0,
              f"got {len(result.get('violations', []))} violations")

        # complete-pass should PASS (has qualified language)
        result = json.loads(check_iron_rule_c_deterministic(
            str(fixtures_dir / "complete-pass" / "05-report.md"),
            str(fixtures_dir / "complete-pass" / "04-synthesis.md"),
        ))
        check("GATE-2: complete-pass fixture passes",
              result["pass"] is True,
              f"violations: {result.get('violations', [])}")
    except Exception as e:
        check("GATE-2 fixture tests", False, str(e))

    # GATE-9: check_coverage_grade_consistency (low-coverage-strong fixture)
    try:
        from helpers import check_coverage_grade_consistency

        # low-coverage-strong should FAIL (STRONG from 10% coverage)
        result = json.loads(check_coverage_grade_consistency(
            str(fixtures_dir / "low-coverage-strong" / "deep-reads"),
            str(fixtures_dir / "low-coverage-strong" / "04-synthesis.md"),
        ))
        check("GATE-9: low-coverage-strong fixture fails",
              result["pass"] is False,
              f"result: {result}")
        check("GATE-9: low-coverage-strong detects coverage issue",
              any("coverage" in v.lower() or "10" in v for v in result.get("violations", [])),
              f"violations: {result.get('violations', [])}")

        # complete-pass should PASS
        result = json.loads(check_coverage_grade_consistency(
            str(fixtures_dir / "complete-pass" / "deep-reads"),
            str(fixtures_dir / "complete-pass" / "04-synthesis.md"),
        ))
        check("GATE-9: complete-pass fixture passes",
              result["pass"] is True,
              f"violations: {result.get('violations', [])}")
    except Exception as e:
        check("GATE-9 fixture tests", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# TEST 9: Topic extractor validation
# ═══════════════════════════════════════════════════════════════════
def test_topic_extractor_validation():
    print("\n=== Test 9: Topic Extractor Validation ===")
    try:
        from test_topic_extractor import run_all as run_topic_tests
        pass_count, fail_count, results = run_topic_tests()
        for r in results:
            check(
                f"topic_extractor: {r['rq_preview'][:60]}",
                r["passed"],
                f"recall={r['recall']:.0%}, found={r['found']}",
            )
        # Overall passing threshold: ≥80% average recall
        avg_recall = sum(r["recall"] for r in results) / len(results) if results else 0
        check(
            f"topic_extractor average recall ≥ 80%",
            avg_recall >= 0.80,
            f"got {avg_recall:.0%}",
        )
    except Exception as e:
        check("topic_extractor validation", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
def main():
    print("deepseek-research Smoke Test (v3.0)")
    print(f"SKILL_DIR: {SKILL_DIR}")
    print(f"Python: {sys.version}")

    test_file_integrity()
    test_scripts()
    test_templates()
    test_skill_consistency()
    test_iron_rule_c()
    test_taxonomy()
    test_template_refs()
    test_verification_gates()
    test_topic_extractor_validation()

    total = pass_count + fail_count
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
