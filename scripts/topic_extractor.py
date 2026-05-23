#!/usr/bin/env python3
"""topic_extractor.py — Extract short topic names from RQ text for negative queries.

Each topic must be 1-5 words, lowercase, domain-specific.
Quality gate: every topic must have ≤5 words and ≥2 characters.

Called via code_execution from SKILL.md Stage 2.
"""

from __future__ import annotations

import re


def extract_topics(rq_text: str, max_topics: int = 6) -> list[str]:
    """Extract short topic names from a research question for negative queries.

    Heuristics used (in order):
      1. Explicit lists after "such as", "including", "like", "e.g.", "i.e."
      2. Capitalized noun phrases (proper names of theories/methods/algorithms)
      3. Quoted phrases inside double quotes

    Args:
        rq_text: Full research question text.
        max_topics: Maximum number of topics to return (default 6).

    Returns:
        List of lowercase topic strings, each 1-5 words, 2-50 characters.
        Empty list if RQ is too short or no topics found.
    """
    if len(rq_text) < 20:
        return []

    candidates: list[str] = []

    # Pattern 1: "X, Y, and Z" or "X, Y, Z" (explicit lists after prepositions)
    list_pattern = re.findall(
        r'(?:such as|including|like|e\.g\.|i\.e\.)\s+(.+?)(?:\.|;|\n|$)',
        rq_text, re.IGNORECASE,
    )
    for match in list_pattern:
        items = re.split(r',|\sand\s', match)
        for item in items:
            cleaned = item.strip().lower()
            if 2 < len(cleaned) < 60:
                candidates.append(cleaned)

    # Pattern 2: Capitalized noun phrases (proper names)
    proper_pattern = re.findall(
        r'\b([A-Z][a-z]+(?:\s(?:[A-Z][a-z]+|of|in|for|to|and|the)){1,4})',
        rq_text,
    )
    for p in proper_pattern:
        cleaned = p.strip().lower()
        if 2 < len(cleaned) < 60:
            candidates.append(cleaned)

    # Pattern 3: Quoted phrases
    quoted = re.findall(r'"([^"]{3,60})"', rq_text)
    for q in quoted:
        cleaned = q.strip().lower()
        candidates.append(cleaned)

    # Deduplicate, filter, truncate
    seen: set[str] = set()
    result: list[str] = []
    for c in candidates:
        c = c.strip().rstrip('.,;:')
        word_count = len(c.split())
        if c not in seen and 2 <= len(c) <= 50 and 1 <= word_count <= 5:
            seen.add(c)
            result.append(c)

    return result[:max_topics]


def topics_to_csv(topics: list[str]) -> str:
    """Convert topic list to comma-separated string for build_subagent_prompt."""
    return ",".join(topics)


# Self-test
if __name__ == "__main__":
    test_rq = (
        "comparison of computational theories of brain function: "
        "Thousand Brain Theory, Critical Brain Hypothesis, "
        "Free Energy Principle, Neural Manifolds, and Predictive Processing"
    )
    topics = extract_topics(test_rq)
    print(f"Topics extracted: {topics}")
    csv = topics_to_csv(topics)
    print(f"CSV: {csv}")
    assert len(topics) >= 3, f"Expected >=3 topics, got {len(topics)}"
    for t in topics:
        word_count = len(t.split())
        assert 1 <= word_count <= 5, f"Topic '{t}' has {word_count} words"
    # Test empty/short input
    assert extract_topics("short") == [], "Short RQ should return empty"
    assert extract_topics("") == [], "Empty RQ should return empty"
    # Test quoted phrases
    topics2 = extract_topics('We study "latent diffusion models" and "mixture of experts" in detail')
    assert len(topics2) >= 2, f"Expected >=2 quoted topics, got {len(topics2)}"
    print("Self-test PASSED")
