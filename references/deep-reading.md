# Deep Source Reading

Loaded by the orchestrator at Stage 3.5 and referenced by sub-agents during
deep reading of individual sources. Do NOT inline this content in SKILL.md.

---

## Rationale

The pipeline's epistemic bottleneck is the gap between *discovering* a source
and *understanding* it. Discovery stages (Stage 2) return titles, abstracts, and
relevance scores. Verification (Stage 3) checks accessibility and performs
risk-of-bias assessment from metadata. Neither reads the source body in depth.

**Deep reading closes this gap.** For each included source, a sub-agent processes
the full document via RLM (Recursive Language Model) chunking, extracts claims
with exact textual evidence, verifies internal consistency, and flags
mathematical or methodological claims that require human review.

The output of deep reading is not a summary — it is a structured extraction of
claims anchored to verbatim text, enabling downstream synthesis (Stage 4) and
human verification (GATE-18).

---

## When Deep Reading Applies

| Condition | Action |
|-----------|--------|
| `deep_reading = false` | Skip Stage 3.5 entirely. Stages 3-4 behave as v1.5 (no textual evidence requirement). |
| 0 sources after Stage 2 | Skip Stage 3.5. "Insufficient evidence" report path. |
| Source is UNVERIFIABLE (Stage 3) | Skip deep reading for that source. Mark as "not deep-read — unverifiable." |
| Source is bibliography (local file) | Deep read via RLM chunking of the local file. |
| Source is web (URL) | Deep read via `fetch_url` → RLM chunking. If fetch fails or returns paywall, mark "not deep-read — inaccessible." |
| Source is codebase (file) | Lightweight deep read: read the file directly (no RLM needed for code < 50KB). |

---

## Document Size Tiers

RLM chunking strategy depends on document size. The orchestrator estimates size
before dispatch and selects the tier:

| Tier | Size | Strategy | Chunk size | Overlap |
|------|------|----------|-----------|---------|
| **T1 — Short** | < 5KB | Direct `read_file` — no RLM needed | N/A | N/A |
| **T2 — Medium** | 5–50KB | `read_file` paginated (2-3 reads) | N/A | N/A |
| **T3 — Long** | 50–200KB | `rlm_open` → `chunk()` → `sub_query_batch` | 8K chars | 1K chars |
| **T4 — Book** | > 200KB | `rlm_open` → `chunk()` with selective reading: first process ToC/abstract/intro/conclusion, then deep-read only sections relevant to RQ | 8K chars | 1K chars |

**T4 selective reading procedure:**
1. Chunk the table of contents (first 10% of document) → identify relevant sections.
2. Chunk introduction and conclusion → extract thesis and key findings.
3. For each relevant section identified in step 1, chunk and deep-read.
4. Skip clearly irrelevant sections (e.g., appendix A of a textbook when RQ is about algorithm X).
5. Record which sections were skipped and why in the deep read output.

---

## Textual Evidence Taxonomy

Every claim extracted during deep reading must be classified by its evidential
basis within the source:

| Evidence grade | Definition | Example | Use in synthesis |
|---------------|-----------|---------|-----------------|
| **V — Verbatim** | Exact text copied from source, with line/chapter reference | "The algorithm achieves O(n log n) worst-case complexity (p. 47, §3.2)" | STRONG — directly citable |
| **P — Paraphrase with context** | Claim restated in own words, with surrounding context cited | "The authors argue that co-kriging fails above 5 fidelity levels, citing instability in the covariance matrix (p. 12, §4.1)" | MODERATE — faithful to source but interpretation involved |
| **I — Inference** | Claim derived from source data/figures/tables but not explicitly stated | "Figure 3 shows error increases with dimensionality; we infer the method is unsuitable for d > 20 (p. 8, Fig. 3)" | WEAK — requires cross-validation with other sources |
| **M — Mathematical** | Claim that includes a mathematical statement (theorem, equation, proof) | "Theorem 3.1: convergence rate is O(1/√n) under assumptions A1-A4 (p. 15)" | Flagged for human review — LLM cannot verify proofs |

**Rule for synthesis:** STRONG findings must be supported by at least one V-grade
claim. MODERATE findings require V or P. WEAK findings accept I-grade.

**Mathematical claims (M-grade):** These are automatically flagged with
`⚠ MATHEMATICAL — requires human verification`. The orchestrator must NOT
present an M-grade claim as verified evidence. It may report the claim as
"the source asserts that..." but confidence is capped at LOW.

---

## Internal Consistency Checks

The deep reader must check the source for internal contradictions:

1. **Claim-claim consistency:** Do any two claims in the source contradict each other?
   - Example: §3 says "method requires labeled data" but §5 says "method was tested on unlabeled data."
2. **Claim-data consistency:** Do the reported numbers match the tables/figures?
   - The LLM cannot verify this fully, but can flag: "Table 2 reports N=100 but text says N=150 — discrepancy."
3. **Claim-method consistency:** Does the conclusion follow from the described method?
   - Example: "Observational study claims causation" → flag as "causal language without experimental design."
4. **Abstract-body consistency:** Does the abstract accurately represent the body?
   - Common failure mode: abstract claims "we prove X" but body only demonstrates X empirically.

Any inconsistency found must be recorded in the deep read output under
`## Internal Consistency`.

---

## RLM Chunking Contract

When using RLM for T3/T4 documents, the deep reader sub-agent must:

1. **Open RLM session:** `rlm_open(name="dr-{source_id}", file_path="{source_path}")`
2. **Configure for metadata-only feedback:** `rlm_configure(name="dr-{source_id}", output_feedback="metadata")`
3. **Chunk the document:** `rlm_eval(name="dr-{source_id}", code="chunks = chunk(chunk_size=8000, overlap=1000); finalize({'n_chunks': len(chunks), 'chunks': chunks})")`
4. **Process chunks in independent batches:**
   ```
   rlm_eval(name="dr-{source_id}", code="""
   results = sub_query_batch(
       queries=[f"Extract all claims relevant to RQ '{rq_text}' from this text. For each claim, provide: (a) verbatim quote, (b) evidence grade (V/P/I/M), (c) section/chapter reference. Text: {chunk}" for chunk in chunks],
       dependency_mode="independent",
       safety_note="Each chunk is from the same document but processed independently — no cross-chunk dependencies."
   )
   finalize(results)
   """)
   ```
5. **Close RLM session:** `rlm_close(name="dr-{source_id}")`

When RLM is unavailable or the document is T1/T2, use direct `read_file` +
manual claim extraction in the sub-agent context.

---

## Output Contract

Every deep read sub-agent must write a Markdown file to
`{session_dir}/deep-reads/{source_id}.md` using the template at
`{SKILL_DIR}/templates/source-deep-read.md`.

The file must contain:
- Metadata header (source_id, document path, tier, chunking strategy used)
- Extracted claims table with verbatim quotes and evidence grades
- Internal consistency section (any contradictions found)
- Mathematical claims flag section
- Sections skipped (T4 only) with rationale
- Overall assessment: COMPREHENSIVE / PARTIAL / MINIMAL

**Failure modes:**
- Document inaccessible → write "## Deep Read: INACCESSIBLE" with reason
- Document too large (T4 with >50% relevant) → write "## Deep Read: PARTIAL — {N} sections processed of {M} total; {pct}% coverage"
- RLM failed → write "## Deep Read: FAILED — RLM error: {error}"

---

## Integration with Stage 4

Stage 4 (Synthesis) loads deep read outputs as its primary evidence base:

1. Orchestrator reads `{session_dir}/deep-reads/` directory listing.
2. For each `{source_id}.md`, loads the extracted claims table.
3. Cross-references claims across sources (deduplication, convergence, contradiction).
4. Each K-finding in `04-synthesis.md` cites at least one verbatim quote with source
   and section reference.

**No claim may be classified as STRONG without a V-grade citation from a deep-read source.**
This is enforced by GATE-18.
