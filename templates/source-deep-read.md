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
**Chunking strategy:** {direct_read / paginated / RLM_chunking / codebase_grep / selective_pages / snippets_only}
**Commit analyzed:** {commit_hash — T5 only; "N/A" for non-T5}
**Chunks processed:** {n_chunks} of {total_chunks}
**Coverage:** {coverage_pct}%  ⚠ REQUIRED — see Coverage table in references/deep-reading.md
**Sections skipped:** {skipped_sections — "None" or list with rationale}
**Access method:** {direct_fulltext / arxiv_html / arxiv_pdf / unpaywall_oa / scihub / local_pdf / abstract_only / snippets}

---

## Overall Assessment

**COMPREHENSIVE / PARTIAL / MINIMAL / SNIPPET_ONLY**

{One-sentence assessment of coverage quality. If SNIPPET_ONLY: "SNIPPET_ONLY — claims extracted from search snippets and abstracts only; full text was not accessed. All claims are I-grade."}

---

## Extracted Claims

Claims relevant to RQ: `{RQ_TEXT}`

| ID | Claim (verbatim) | Evidence grade | Section ref | Page/line | Notes |
|----|-----------------|---------------|-------------|-----------|-------|
| C1 | "{exact quote from source}" | V / P / I / M / E | §{section} | p. {page}, l. {line} / {file}:{line} | {source medium: e.g., "from direct full-text", "from ScienceDirect snippet — I-grade"} |
| C2 | "{exact quote from source}" | V / P / I / M | §{section} | p. {page}, l. {line} | |
| ... | | | | | |

**Evidence grades:**
- **V (Verbatim):** Exact text from source — directly citable in synthesis as STRONG evidence. Only from direct full-text access (`read_file`, `rlm_open`), NOT from search snippets or abstracts.
- **P (Paraphrase with context):** Restated with surrounding context — MODERATE evidence.
- **I (Inference):** Derived from data/figures/tables, OR from search snippets, abstracts, or sub-agent summaries. WEAK evidence, requires cross-validation.
- **M (Mathematical):** Contains theorem/proof/equation — ⚠ requires human verification; capped at LOW confidence.
- **E (Empirical — implementation):** Evidence from real executable code (implementation, benchmark, test, hardcoded constant). STRONG if repository RoB Low; MODERATE if Some concerns.

**⚠ Snippets and abstracts are I-grade, not V-grade.** See `references/deep-reading.md` §Snippets e sumários não são V-grade.

---

## Internal Consistency

{If coverage ≥ 80% and no issues:}
> No internal contradictions detected across the claims extracted above.

{If coverage ≥ 80% and issues found, for each:}

### IC1: {issue_title}

- **Claim A:** C{n} — "{excerpt}" (§{section})
- **Claim B:** C{m} — "{excerpt}" (§{section})
- **Type:** claim-claim / claim-data / claim-method / abstract-body
- **Severity:** MINOR / SIGNIFICANT / CRITICAL
- **Assessment:** {one-paragraph analysis}

{If coverage < 80%:}
> **Not fully verified:** The deep read processed {coverage_pct}% of the document. Cross-checking claims against tables/figures in unprocessed sections was not performed. Claims should be treated as unverified extractions.
>
> Specific checks:
> - Claim-claim: {if checked, report result; otherwise "Not verified — partial coverage"}
> - Claim-data: {if checked, report result; otherwise "Not verified — tables/figures in unprocessed sections"}
> - Claim-method: {if checked, report result; otherwise "Not verified — method section partially processed"}
> - Abstract-body: {if body was processed, report result; otherwise "Not verified — body not fully processed"}

---

## Mathematical Claims

{If no M-grade claims:}
> No mathematical claims (M-grade) extracted.

{If M-grade claims present, for each:}

### MC1: {claim_id} — {brief description}

- **Claim:** C{n} — "{verbatim mathematical statement}"
- **Type:** theorem / proof / equation / algorithm correctness
- **⚠ MATHEMATICAL — requires human verification.**
- **Verification guidance:** {what a human reviewer should check}

---

## Sections Skipped (T4 only)

{If no sections skipped:}
> All sections were processed. No sections were skipped.

{If sections skipped:}

| Section | Pages | Reason for skipping |
|---------|-------|---------------------|
| §{section} | {page_range} | {rationale} |

---

## Failure Notes (if applicable)

{If deep read was INACCESSIBLE, PARTIAL, FAILED, or SNIPPET_ONLY:}

**Status:** INACCESSIBLE / PARTIAL / FAILED / SNIPPET_ONLY
**Reason:** {concrete reason — e.g., "fetch_url returned HTTP 403 (paywall)", "RLM session timed out after 120s", "Document is scanned PDF with no extractable text", "Full text not accessed; claims from search snippets only"}
**Impact on synthesis:** {what this means for downstream stages — e.g., "This source cannot contribute V-grade evidence to synthesis", "All claims are I-grade and capped at WEAK confidence"}
