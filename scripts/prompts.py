#!/usr/bin/env python3
"""prompts.py — Sub-agent prompt builders para deepseek-research v3.0.

2 builders: dsr-bibliography e dsr-code.
Chamados via `build_subagent_prompt()` em helpers.py.
"""

from __future__ import annotations

import json


def _build_per_topic_queries(topics_str: str, query_template: str) -> str:
    """Gera queries por tópico a partir de uma string CSV de tópicos.

    Args:
        topics_str: Tópicos separados por vírgula (ex: "THT,CBH,FEP").
        query_template: Template com placeholder {topic} (ex: '"limitations of {topic}"').

    Returns:
        Lista em bullet separada por newlines, uma query por tópico.
        String vazia se topics_str vazio.
    """
    if not topics_str or not topics_str.strip():
        return ""
    topics = [t.strip() for t in topics_str.split(",") if t.strip()]
    if not topics:
        return ""
    return "\n".join(f'- {query_template.format(topic=t)}' for t in topics)


def _build_bibliography_prompt(
    rq_text: str,
    bibliography_path: str,
    main_topic: str,
    topics: str = "",
    local_sources_json: str = "",
) -> str:
    """Prompt para sub-agent dsr-bibliography.

    Args:
        local_sources_json: JSON string de entradas do corpus local
            (output de index_sources.py query). Vazio se não houver matches.
    """
    if topics:
        per_topic = _build_per_topic_queries(topics, '"limitations of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"criticism of {topic}"')
        per_topic += "\n" + _build_per_topic_queries(topics, '"failure cases of {topic}"')
        negative_block = f"""## Mandatory: Negative search (per-topic)
For each topic below, you MUST run ALL of these queries:
{per_topic}"""
    else:
        negative_block = f"""## Mandatory: Negative search
For the main topic of this RQ, run at least:
- "limitations of {main_topic}"
- "criticism of {main_topic}"
- "failure cases of {main_topic}\""""

    # Build local corpus block if sources are available
    local_block = ""
    if local_sources_json and local_sources_json.strip() and local_sources_json.strip() != "[]":
        local_block = f"""## Local Corpus (already indexed — read these files first)

The following sources are in your local bibliography at {bibliography_path}
and matched the RQ keywords. Read them via `read_file` and include relevant
ones in your output table. Mark them as **local** in a Source ID comment.

```json
{local_sources_json}
```

For each local source you include:
- Use `read_file("{bibliography_path}/{{filename}}")` to verify the file exists
- Include it in your main source table with the note "(local corpus)" in the Why column
- Do NOT re-search the web for these — they are already in the corpus
"""

    return f"""Search project bibliography at {bibliography_path} for sources relevant to RQ: {rq_text}

{local_block}

{negative_block}

## MANDATORY: Verify every source before including it
For each source you plan to include in your results, you MUST:
1. `fetch_url` on the source URL to confirm it exists and returns HTTP 200.
2. Read enough content to confirm the title matches what you are reporting.
3. If `fetch_url` fails (404, 403, timeout, or any non-200 status), do NOT include the source in your table. Report it in a separate "Attempted but inaccessible" section instead.
4. Never fabricate, guess, or approximate URLs. Only include URLs you have successfully fetched and whose content you have read.

## CRITICAL: DOI Capture (mandatory for papers)
For every paper source you include, you MUST capture its DOI:
1. **arXiv papers:** the DOI is often listed on the arXiv abstract page under "DOI:" or in the "Bibliographic data" sidebar. Fetch the abstract page (`https://arxiv.org/abs/{id}`) and extract the DOI.
2. **Publisher pages:** check the page source for meta tags:
   - `<meta name="citation_doi" content="10.XXXX/...">`
   - `<meta name="dc.identifier.doi" content="10.XXXX/...">`
   - `<meta name="dc.identifier" content="doi:10.XXXX/...">`
3. **Visible text:** look for "DOI:" or "doi:" followed by a `10.XXXX/...` pattern anywhere on the page.
4. **Always verify:** a valid DOI starts with `10.` followed by a slash, e.g., `10.1038/nature12373`.
5. **If no DOI is found:** fill the DOI column with `N/A`. Never fabricate, guess, or approximate a DOI.
6. **For code repositories and non-paper sources:** fill with `N/A`.

The DOI column is MANDATORY in the output table — every row must have either a valid DOI or "N/A".

## CRITICAL: Anti-hallucination rule
- arXiv IDs are 7-digit numbers (e.g., 2407.16833). If you are unsure of an ID, fetch the URL to verify it returns the expected paper. arXiv abstract pages are at `https://arxiv.org/abs/{id}`.
- Never generate an arXiv ID from memory or by analogy — only use IDs you have seen in `web_search` results or successfully fetched URLs.
- If `web_search` returns a snippet with a title but no clear URL, run a follow-up search to find the URL. Do not guess.
- If you cannot verify a source, do not include it. Prefer fewer verified sources over more unverified ones.

## Output contract
1. Markdown table: | Source ID | Title/Path | Type | DOI | Relevance (1-5) | Why relevant |
   - The Title column MUST contain the EXACT title as it appears on the fetched page (copy-paste, do not paraphrase).
   - The Path column MUST contain the EXACT URL you successfully fetched (copy-paste from the `fetch_url` result).
   - The DOI column MUST contain either a valid DOI (`10.XXXX/...`) or `N/A`. See "DOI Capture" section above for extraction instructions.
2. Negative search results section with queries attempted and key findings.
3. "Attempted but inaccessible" section for sources you tried to fetch but could not access (with the URL, HTTP status, and reason).

## MANDATORY: Write complete results to file
Before responding, write your COMPLETE source table, negative search results, and inaccessible-sources section to `/tmp/dsr-bibliography-results.md` using write_file. Inline response can be a summary."""


def _build_code_prompt(rq_text: str) -> str:
    """Prompt para sub-agent dsr-code."""
    return f"""Search project codebase for implementations, patterns, docs relevant to: {rq_text}

## Procedure
1. grep_files with RQ-derived patterns (function names, algorithm names,
   constants, class names).
2. read_file of files with matches.
3. Focus on: core algorithm implementations, benchmark harnesses, test files,
   configuration constants, docstrings.

## Output REQUIRED format
| Source ID | File:Line | Type (impl/doc/test/config) | Relevance (1-5) | Why relevant |

## MANDATORY: Write complete results to file
Write your COMPLETE source table to `/tmp/dsr-code-results.md` using write_file.
Inline response can be a summary."""
