#!/usr/bin/env python3
"""test_topic_extractor.py — Validation suite for topic_extractor.py.

10 RQ → expected_topics pairs covering diverse domains:
  - AI/ML (in-context learning, RAG, speculative decoding)
  - Neuroscience (computational theories)
  - Systems (distributed systems)
  - Math (proof verification)
  - Biology (protein folding)
  - Chemistry (catalysis)
  - Physics (quantum computing)
  - Security (side-channel attacks)
  - NLP (multilingual translation)
  - Ethics (AI alignment)

Run as: python3 tests/test_topic_extractor.py
Or integrated via: python3 scripts/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from project root or tests/ directory
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from topic_extractor import extract_topics, topics_to_csv


# ── Stopwords for validation ─────────────────────────────────────────
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "to", "for", "and",
    "with", "using", "via", "from", "is", "at", "by", "or",
    "as", "be", "it", "not", "but", "are", "was", "were",
    "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those",
}


# ── Test cases: (rq_text, expected_topics) ──────────────────────────
TEST_CASES: list[tuple[str, list[str]]] = [
    # AI/ML
    (
        "How does in-context learning work in large language models?",
        ["in-context learning", "large language models"],
    ),
    (
        "What are the failure modes of retrieval-augmented generation for "
        "factual question answering?",
        ["retrieval-augmented generation", "factual question answering",
         "failure modes"],
    ),
    (
        "What is the state of the art in speculative decoding for "
        "LLM inference?",
        ["speculative decoding", "llm inference"],
    ),
    # Neuroscience
    (
        "Comparison of Thousand Brain Theory, Critical Brain Hypothesis, and "
        "Free Energy Principle in computational neuroscience",
        ["thousand brain theory", "critical brain hypothesis",
         "free energy principle", "computational neuroscience"],
    ),
    # Systems
    (
        "How do distributed consensus algorithms handle byzantine failures "
        "in permissionless blockchain networks?",
        ["distributed consensus algorithms", "byzantine failures",
         "permissionless blockchain networks"],
    ),
    # Math
    (
        "What are the limitations of automated theorem provers for "
        "formal verification of cryptographic protocols?",
        ["automated theorem provers", "formal verification",
         "cryptographic protocols"],
    ),
    # Biology
    (
        "How accurate are deep learning methods for protein structure "
        "prediction compared to experimental methods like X-ray crystallography?",
        ["deep learning methods", "protein structure prediction",
         "x-ray crystallography"],
    ),
    # Chemistry
    (
        "What catalyst design strategies improve selectivity in "
        "asymmetric hydrogenation reactions?",
        ["catalyst design strategies", "asymmetric hydrogenation reactions"],
    ),
    # Physics
    (
        "What are the current error correction thresholds for "
        "fault-tolerant quantum computing with surface codes?",
        ["error correction thresholds", "fault-tolerant quantum computing",
         "surface codes"],
    ),
    # Security
    (
        "How effective are cache-based side-channel attacks against "
        "modern CPU microarchitectures with hardware mitigations?",
        ["cache-based side-channel attacks", "cpu microarchitectures",
         "hardware mitigations"],
    ),
]


def validate_extraction(rq: str, expected: list[str]) -> dict:
    """Validate topic extraction for a single RQ.

    Returns:
        {"rq_preview": str, "expected": [...], "found": [...],
         "recall": float, "passed": bool, "issues": [...]}
    """
    topics = extract_topics(rq)
    issues: list[str] = []

    # Check each extracted topic
    for t in topics:
        word_count = len(t.split())
        if word_count > 5:
            issues.append(f"Topic '{t}' has {word_count} words (>5)")
        if len(t) < 2:
            issues.append(f"Topic '{t}' is too short (<2 chars)")
        # Check no standalone stopwords
        words = t.split()
        if any(w in STOPWORDS for w in words) and len(words) == 1:
            issues.append(f"Topic '{t}' is a stopword")

    # Recall: what fraction of expected topics were found?
    # Normalize for comparison: lowercase, strip
    found_normalized = {t.lower().strip() for t in topics}
    expected_normalized = {e.lower().strip() for e in expected}
    intersection = found_normalized & expected_normalized
    recall = len(intersection) / len(expected) if expected else 1.0

    passed = recall >= 0.5 and len(issues) == 0

    return {
        "rq_preview": rq[:80] + ("..." if len(rq) > 80 else ""),
        "expected": expected,
        "found": topics,
        "recall": round(recall, 2),
        "passed": passed,
        "issues": issues,
    }


def run_all() -> tuple[int, int, list[dict]]:
    """Run all test cases. Returns (pass_count, fail_count, results)."""
    pass_count = 0
    fail_count = 0
    results = []

    for rq, expected in TEST_CASES:
        result = validate_extraction(rq, expected)
        results.append(result)
        if result["passed"]:
            pass_count += 1
        else:
            fail_count += 1

    return pass_count, fail_count, results


def main():
    pass_count, fail_count, results = run_all()

    print(f"topic_extractor Validation Suite")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        status = "PASS" if r["passed"] else "FAIL"
        print(f"\n[{status}] Case {i}: {r['rq_preview']}")
        print(f"  Expected ({len(r['expected'])}): {r['expected']}")
        print(f"  Found ({len(r['found'])}): {r['found']}")
        print(f"  Recall: {r['recall']:.0%}")
        if r["issues"]:
            for issue in r["issues"]:
                print(f"  Issue: {issue}")

    # Overall metrics
    avg_recall = sum(r["recall"] for r in results) / len(results) if results else 0
    print(f"\n{'='*60}")
    print(f"Results: {pass_count}/{len(results)} cases passed")
    print(f"Average recall: {avg_recall:.0%}")
    print(f"Threshold: ≥50% recall per case")

    if fail_count > 0:
        print("VALIDATION FAILED")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
