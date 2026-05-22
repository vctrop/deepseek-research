# Sub-agent Prompts

Loaded by the orchestrator during Stage 2 and Stage 4.5 dispatch.
Do NOT inline these in SKILL.md — they are bulky and change rarely.

---

## Stage 2: dsr-bibliography (Bibliography axis)

```
agent_open(name="dsr-bibliography", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","file_search","web_search","fetch_url","rlm_open","rlm_eval","rlm_close","write_file"],
  prompt="Search project bibliography at {bibliography_path} for sources relevant to RQ: {RQ_TEXT}

  {LOCAL_SOURCES_BLOCK}

  ## Mandatory: Negative search
  For the main topic of this RQ, you MUST run at least these queries:
  - \"limitations of {main_topic}\"
  - \"criticism of {main_topic}\"
  - \"failure cases of {main_topic}\"
  Report findings in the persistence_manifest under 'negative_search'.

  ## Output contract
  1. Markdown table: | Source ID | Title/Path | Type | Relevance (1-5) | Why relevant |
  2. persistence_manifest JSON block — LAST element of response, in dedicated ```json fence.

  ## persistence_manifest format
  ```json
  {
    \"persistence_manifest\": {
      \"new_sources\": [
        {
          \"save_as\": \"papers/author-year-slug.pdf\",
          \"source_id\": \"author-year-slug\",
          \"type\": \"paper\",
          \"title\": \"Full title\",
          \"authors\": [\"Author, A.\"],
          \"year\": 2024,
          \"doi\": \"10.xxxx/xxxxx\",
          \"keywords\": [\"kw1\", \"kw2\"],
          \"summary\": \"2-3 sentence summary of key contributions.\",
          \"quality_level\": \"II\",
          \"source_type\": \"journal\"
        }
      ],
      \"reused_local\": [{\"source_id\": \"existing-id\"}],
      \"negative_search\": {
        \"queries_attempted\": [\"limitations of X\", \"X fails when\"],
        \"results_found\": 2,
        \"results_summary\": \"Instability with >5 fidelity levels (Le Gratiet 2014)\"
      }
    }
  }
  ```

  Rules:
  - new_sources: every source obtained online. save_as = {type}s/{first-author}-{year}-{short-title-kebab}.{ext}
  - reused_local: every source read from local corpus. Only source_id.
  - negative_search: REQUIRED — report all negative queries and their findings.
  - If empty: emit [] (never omit the block).
  - The block MUST be the last element of the response.")
```

LOCAL_SOURCES_BLOCK format (if non-empty, from Stage 1.5):
```
## Local Corpus (pre-indexed sources — do NOT fetch online)

The following sources are already on disk. Read each from {bibliography_path}/{path},
re-annotate for the current RQ, and mark as Access: ✓ Local corpus.

{local_sources_json}

Focus online search effort on topics, authors, and time periods NOT covered by these sources.
```

---

## Stage 2: dsr-web (Web axis)

```
agent_open(name="dsr-web", model="deepseek-v4-flash",
  allowed_tools=["web_search","fetch_url","write_file"],
  prompt="Web search for RQ: {RQ_TEXT}

  ## Mandatory: Negative search
  You MUST run these queries IN ADDITION to the primary topic queries:
  - \"limitations of {main_topic}\"
  - \"criticism of {main_topic}\"
  - \"alternatives to {main_topic}\"
  Report all queries and their results in a 'negative_search' section.

  ## Output REQUIRED format
  ### Source Table
  | Source ID | URL | Type (academic/industry/blog) | Relevance (1-5) | Why relevant |

  ### Search Audit
  | Query | Results returned | Results used |

  ### Negative Search
  | Query | Results found | Key findings |")
```

---

## Stage 2: dsr-code (Codebase axis)

```
agent_open(name="dsr-code", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","file_search","write_file"],
  prompt="Search project codebase for implementations, patterns, docs relevant to: {RQ_TEXT}

  ## Output REQUIRED format
  | Source ID | File:Line | Type (impl/doc/test/config) | Relevance (1-5) | Why relevant |")
```

---

## Stage 4.5: dsr-da (Devil's Advocate)

```
agent_open(name="dsr-da", model="deepseek-v4-pro",
  allowed_tools=["read_file","write_file"],
  prompt="Read {session_dir}/04-synthesis.md.
  Also read {SKILL_DIR}/references/iron-rule-c.md for the full bare claims list.
  Review against the Devil's Advocate checklist below.
  Write findings to {session_dir}/04a-devils-advocate.md using the template at {SKILL_DIR}/templates/devils-advocate.md.

  ## Checklist

  ### Cherry-picking
  - Contradictory sources excluded or downweighted?
  - If DIVERGENT consensus, minority view given fair space?
  - Negative evidence found but not reported?
  - Negative search results from Stage 2 acknowledged?

  ### Overconfidence
  - Bare claims (validated, proved, confirmed, demonstrated, ensures, guarantees, always, never, optimal, definitive, conclusive, certainly, undoubtedly, obviously, clearly) without qualifiers?
  - Evidence strength propagated into claim language?
  - Source credibility tier conflated with evidence strength?
  - Would hostile reviewer find confidence disproportionate to evidence?

  ### Gap honesty
  - Gaps with severity + concrete next steps?
  - Absence of evidence distinguished from evidence of absence?
  - 'Open questions' genuinely open, or rhetorical?

  ### Bias
  - Synthesis favors project-internal sources over external?
  - Reference frameworks evaluated by same standard as project?
  - Confirmation bias toward pre-existing architectural decisions?
  - All agreeing sources share same author group/institution/funding?

  ## Verdict
  PASS / MINOR (cosmetic fixes) / REVISE (substantive — list required revisions with line references).
  Write verdict as a single line: **Verdict: {PASS/MINOR/REVISE}**")
```
