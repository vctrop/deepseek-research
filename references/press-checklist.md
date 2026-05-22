# PRESS 2015 Checklist — Search Strategy Peer Review

Loaded by the orchestrator at Stage 2.2. Applied to each search query per active axis.
Based on: McGowan et al. (2016) "PRESS Peer Review of Electronic Search Strategies:
2015 Guideline Statement." _Journal of Clinical Epidemiology_, 75:40-46.

---

## Checklist Elements

For each search query, rate each element: ADEQUATE / INADEQUATE / NOT APPLICABLE.

| # | Element | Question | Check |
|---|---------|----------|-------|
| 1 | **Translation of RQ** | Are all PICO/SPICE elements of the RQ represented in the search strategy? Are the correct concepts targeted? | |
| 2 | **Boolean & proximity operators** | Are AND/OR/NOT used correctly? Are proximity operators (NEAR, ADJ) used where appropriate? Are nested Boolean expressions correctly parenthesized? | |
| 3 | **Subject headings** | Are controlled vocabulary terms used where the database supports them (MeSH, Emtree, etc.)? Are they exploded/expanded appropriately? | |
| 4 | **Text word searching** | Are synonyms, acronyms, spelling variants (US/UK), and truncation covered adequately? Are free-text terms comprehensive? | |
| 5 | **Spelling & syntax** | Are there any typos, missing quotes, or syntax errors that would cause the search to fail or return zero results? | |
| 6 | **Limits & filters** | Are date, language, publication type, or other filters justified and applied correctly? Are exclusion filters documented with rationale? | |

---

## Application Procedure (Stage 2.2)

1. After Stage 2 sub-agents return their search audit tables and before consolidation:
   a. For each unique search query in the Search Audit table, apply the 6-element checklist.
   b. The orchestrator reads the query string and evaluates each element inline.
   c. Thinking: moderate — each element requires judgment about query quality.

2. Rating scale:
   - **ADEQUATE** — The element is correctly implemented.
   - **INADEQUATE** — The element has a specific issue. Document the issue and proposed correction.
   - **NOT APPLICABLE** — The element does not apply to this search context (e.g., subject headings for web search).

3. For any element rated INADEQUATE:
   a. Document the specific issue.
   b. Propose a corrected query.
   c. If ≥2 elements are INADEQUATE: re-run the search with the corrected query before proceeding to consolidation.
   d. If 1 element is INADEQUATE: note it but proceed; flag in GATE-8.

4. Write results to `02-source-inventory.md` under "## PRESS Review".

---

## Template Output

```markdown
## PRESS Review

### Query: "{query_string}" (Axis: {axis})

| # | Element | Rating | Notes |
|---|---------|--------|-------|
| 1 | Translation of RQ | ADEQUATE / INADEQUATE / N/A | {notes} |
| 2 | Boolean operators | ADEQUATE / INADEQUATE / N/A | {notes} |
| 3 | Subject headings | ADEQUATE / INADEQUATE / N/A | {notes} |
| 4 | Text word searching | ADEQUATE / INADEQUATE / N/A | {notes} |
| 5 | Spelling & syntax | ADEQUATE / INADEQUATE / N/A | {notes} |
| 6 | Limits & filters | ADEQUATE / INADEQUATE / N/A | {notes} |

**Overall:** {PASS: all elements ADEQUATE or N/A / REVISE: ≥1 INADEQUATE}

### Revised queries (if applicable)
{Corrected query strings for any re-run searches}
```
