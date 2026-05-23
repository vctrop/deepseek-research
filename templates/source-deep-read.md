---
session: {date}-{slug}
stage: 3.5
source_id: {source_id}
skill_version: {skill_git_hash}
model: {model_id}
timestamp_utc: {iso8601_utc}
---

# Deep Read: {source_id}

**Source:** {source_title}
**Location:** {source_path_or_url}
**Document tier:** T1 / T2 / T3 / T4 / T5
**Chunking strategy:** {direct_read / paginated / RLM_chunking / codebase_grep}
**Commit analyzed:** {commit_hash — T5 only; "N/A" for non-T5}
**Chunks processed:** {n_chunks} of {total_chunks} ({coverage_pct}% coverage)
**Sections skipped:** {skipped_sections — "None" or list with rationale}

---

## Overall Assessment

**COMPREHENSIVE / PARTIAL / MINIMAL**

{One-sentence assessment of coverage quality. Example: "COMPREHENSIVE — all relevant sections processed; 14 claims extracted across 8 sections."}

---

## Extracted Claims

Claims relevant to RQ: `{RQ_TEXT}`

| ID | Claim (verbatim) | Evidence grade | Section ref | Page/line | Notes |
|----|-----------------|---------------|-------------|-----------|-------|
| C1 | "{exact quote from source}" | V / P / I / M / E | §{section} | p. {page}, l. {line} / {file}:{line} | {any caveats about context} |
| C2 | "{exact quote from source}" | V / P / I / M | §{section} | p. {page}, l. {line} | |
| ... | | | | | |

**Evidence grades:**
- **V (Verbatim):** Exact text from source — directly citable in synthesis as STRONG evidence.
- **P (Paraphrase with context):** Restated with surrounding context — MODERATE evidence.
- **I (Inference):** Derived from data/figures/tables — WEAK evidence, requires cross-validation.
- **M (Mathematical):** Contains theorem/proof/equation — ⚠ requires human verification; capped at LOW confidence.
- **E (Empirical — implementation):** Evidence from real executable code (implementation, benchmark, test, hardcoded constant). STRONG if repository RoB Low; MODERATE if Some concerns.

See `references/deep-reading.md` §Textual Evidence Taxonomy for full definitions.

---

## Internal Consistency

**Issues found:** {0} / {N}

{If 0 issues:}
> No internal contradictions detected across the claims extracted above.

{If issues found, for each:}

### IC1: {issue_title}

- **Claim A:** C{n} — "{excerpt}" (§{section})
- **Claim B:** C{m} — "{excerpt}" (§{section})
- **Type:** claim-claim / claim-data / claim-method / abstract-body
- **Severity:** MINOR / SIGNIFICANT / CRITICAL
- **Assessment:** {one-paragraph analysis of the contradiction and its implications for using this source as evidence}

---

## Mathematical Claims

{If no M-grade claims:}
> No mathematical claims (M-grade) extracted. All claims are V, P, or I grade.

{If M-grade claims present, for each:}

### MC1: {claim_id} — {brief description}

- **Claim:** C{n} — "{verbatim mathematical statement}"
- **Type:** theorem / proof / equation / algorithm correctness
- **⚠ MATHEMATICAL — requires human verification.** The LLM cannot verify mathematical proofs. This claim is reported as "the source asserts that..." with confidence capped at LOW.
- **Verification guidance:** {what a human reviewer should check — e.g., "Verify the proof in §3.2 against the stated assumptions A1-A4"}

---

## Sections Skipped (T4 only)

{If no sections skipped:}
> All sections were processed. No sections were skipped.

{If sections skipped:}

| Section | Pages | Reason for skipping |
|---------|-------|---------------------|
| §{section} | {page_range} | {rationale — e.g., "Appendix: derivative proofs — not relevant to RQ about algorithm performance"} |

---

## Failure Notes (if applicable)

{If deep read was INACCESSIBLE, PARTIAL, or FAILED:}

**Status:** INACCESSIBLE / PARTIAL / FAILED
**Reason:** {concrete reason — e.g., "fetch_url returned HTTP 403 (paywall)", "RLM session timed out after 120s", "Document is scanned PDF with no extractable text"}
**Impact on synthesis:** {what this means for downstream stages — e.g., "This source cannot contribute V-grade evidence to synthesis"}
