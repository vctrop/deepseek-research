#!/usr/bin/env python3
"""topic_extractor.py — Extract short topic names from RQ text for negative queries.

Each topic must be 1-5 words, lowercase, domain-specific.
Quality gate: every topic must have ≤5 words and ≥2 characters.

Called via code_execution from SKILL.md Stage 2.
"""

from __future__ import annotations

import re

# Stopwords to exclude from topic boundaries
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "to", "for", "and",
    "with", "using", "via", "from", "is", "at", "by", "or",
    "as", "be", "it", "not", "but", "are", "was", "were",
    "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those",
    "how", "what", "why", "when", "where", "which", "who",
    "does", "comparison", "accurate", "effective", "current",
    "state", "art", "work", "handle", "operate", "function",
    "manage", "improve", "affect", "impact", "compare", "perform",
    "achieve", "compared", "experimental", "modern", "methods",
    "like",
}


def _clean_topic(t: str) -> str:
    """Clean a candidate topic string — remove stopwords from edges."""
    t = t.strip().rstrip('.,;:?)\'"!')
    words = t.split()
    while words and words[0].lower() in STOPWORDS:
        words.pop(0)
    while words and words[-1].lower() in STOPWORDS:
        words.pop()
    return " ".join(words).lower()


def _split_into_segments(text: str) -> list[str]:
    """Split text into candidate topic segments at common connectors.

    For segments longer than 5 words, also extract sub-phrases of 2-5 words.
    """
    # Split on: "in", "for", "against", "with", "using", "via", "between", "compared to", "and", ","
    segments = re.split(
        r'\s+(?:in|for|against|compared\s+to|with|using|via|between|to|and|or)\s+',
        text.strip(),
    )
    result = []
    for seg in segments:
        cleaned = _clean_topic(seg)
        if not cleaned or len(cleaned) < 2:
            continue
        result.append(cleaned)
        # For segments with 4+ words, also add sub-phrases
        words_in_seg = cleaned.split()
        if len(words_in_seg) >= 4:
            for ws in (5, 4, 3, 2):
                for i in range(len(words_in_seg) - ws + 1):
                    sub = _clean_topic(" ".join(words_in_seg[i:i + ws]))
                    pw = sub.split()
                    non_sw = [w for w in pw if w not in STOPWORDS]
                    if len(non_sw) >= 2 and len(pw) >= 2:
                        result.append(sub)
    return result


def _extract_noun_phrases(text: str) -> list[str]:
    """Extract meaningful noun phrases from text.

    Chunks the text into sliding windows of 2-5 words and keeps those
    that look like noun phrases (contain at least 2 non-stopword words).
    """
    phrases = []
    words = text.split()
    for window_size in (5, 4, 3, 2):
        for i in range(len(words) - window_size + 1):
            phrase = _clean_topic(" ".join(words[i:i + window_size]))
            pw = phrase.split()
            non_sw = [w for w in pw if w not in STOPWORDS]
            if len(non_sw) >= 2 and len(pw) >= 2:
                phrases.append(phrase)
    return phrases


def extract_topics(rq_text: str, max_topics: int = 6) -> list[str]:
    """Extract short topic names from a research question for negative queries.

    Heuristics used (in order of priority):
      0. Question structure (subject/object extraction)
      1. Explicit lists after "such as", "including", "like", "e.g."
      2. Hyphenated technical terms (e.g., "retrieval-augmented generation")
      3. Capitalized/proper noun phrases
      4. Quoted phrases
      5. Noun phrase fallback (sliding windows, deprioritized)

    Args:
        rq_text: Full research question text.
        max_topics: Maximum number of topics to return (default 6).

    Returns:
        List of lowercase topic strings, each 1-5 words, 2-50 characters.
    """
    if len(rq_text) < 20:
        return []

    q_lower = rq_text.lower()

    # Candidates collected by priority tier
    tier0: list[str] = []  # question structure
    tier1: list[str] = []  # explicit lists
    tier2: list[str] = []  # hyphenated terms
    tier3: list[str] = []  # proper nouns
    tier4: list[str] = []  # quoted
    tier5: list[str] = []  # fallback n-grams

    # ── Pattern 0: Question structure ────────────────────────────────
    # "How does/do/can X [verb] Y?"
    how_match = re.search(
        r'how\s+(?:does|do|can|might|should|are|is|was|were|effective)\s+(.+?)(?:\s+(?:work|operate|function|handle|manage|improve|affect|impact|compare|perform|achieve)\b|\?)',
        q_lower,
    )
    if how_match:
        subject = how_match.group(1).strip()
        tier0.extend(_split_into_segments(subject))

    # "What are/is/was the X of/for/in Y?"
    what_match = re.search(
        r'what\s+(?:are|is|was|were)\s+(?:the|some|current|key|main|possible|potential)?\s*(.+?)(?:\?|$)',
        q_lower,
    )
    if what_match:
        subject = what_match.group(1).strip()
        tier0.extend(_split_into_segments(subject))

    # "Comparison of X, Y, [and] Z [in W]"
    comp_match = re.search(
        r'comparison\s+(?:of|between)\s+(.+?)(?:\s+in\s+(.+?))?(?:$|\.)',
        q_lower,
    )
    if comp_match:
        for g in comp_match.groups():
            if g:
                items = re.split(r'\s+and\s+|,\s*', g)
                for item in items:
                    cleaned = _clean_topic(item)
                    if len(cleaned) >= 2:
                        tier0.append(cleaned)

    # ── Pattern 1: Explicit lists ────────────────────────────────────
    list_matches = re.findall(
        r'(?:such as|including|like|e\.g\.|i\.e\.)\s+(.+?)(?:\.|;|\n|$)',
        rq_text, re.IGNORECASE,
    )
    for match in list_matches:
        items = re.split(r',|\sand\s', match)
        for item in items:
            cleaned = _clean_topic(item)
            if 2 <= len(cleaned) < 60:
                tier1.append(cleaned)

    # ── Pattern 2: Hyphenated technical terms ────────────────────────
    hyphenated = re.findall(
        r'\b([a-zA-Z]+(?:-[a-zA-Z]+){1,4})\b',
        rq_text,
    )
    for h in hyphenated:
        cleaned = h.lower().strip()
        if 2 <= len(cleaned) < 60 and "-" in cleaned:
            # Also create the expanded version (e.g., "retrieval-augmented generation")
            # by checking if the hyphenated term is followed by more words
            tier2.append(cleaned)

    # Also try to find hyphenated terms followed by 1-2 more words
    # e.g., "retrieval-augmented generation" → full phrase
    expanded_hyphen = re.findall(
        r'\b([a-zA-Z]+(?:-[a-zA-Z]+){1,3}(?:\s+[a-zA-Z]+){1,2})\b',
        rq_text,
    )
    for eh in expanded_hyphen:
        cleaned = _clean_topic(eh)
        if 2 <= len(cleaned) < 60:
            tier2.append(cleaned)

    # ── Pattern 3: Capitalized/proper noun phrases ────────────────────
    proper_matches = re.findall(
        r'\b([A-Z][a-zA-Z]*(?:\s+(?:[A-Z][a-zA-Z]*|[a-z]+)){0,4})',
        rq_text,
    )
    for p in proper_matches:
        cleaned = _clean_topic(p)
        if 2 <= len(cleaned) < 60:
            tier3.append(cleaned)

    # ── Pattern 4: Quoted phrases ────────────────────────────────────
    quoted = re.findall(r'"([^"]{3,60})"', rq_text)
    for q in quoted:
        cleaned = _clean_topic(q)
        tier4.append(cleaned)

    # ── Pattern 5: Noun phrase fallback ──────────────────────────────
    # Only if we don't have enough candidates from higher tiers
    tier5 = _extract_noun_phrases(rq_text)

    # ── Merge with priority ordering ─────────────────────────────────
    # Within each tier, shorter topics come first (more general → better for search)
    all_candidates: list[str] = []
    for tier in (tier0, tier1, tier2, tier3, tier4, tier5):
        # Sort by word count ascending within tier
        tier_sorted = sorted(tier, key=lambda x: len(x.split()))
        all_candidates.extend(tier_sorted)

    # Deduplicate, filter, take top N
    seen: set[str] = set()
    result: list[str] = []
    for c in all_candidates:
        word_count = len(c.split())
        if c not in seen and 2 <= len(c) <= 50 and 1 <= word_count <= 5:
            # No standalone stopwords
            if all(w in STOPWORDS for w in c.split()):
                continue
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
