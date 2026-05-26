# Sub-agent Prompts

Carregado pelo orquestrador durante Stage 2. Prompts são gerados via
`helpers.build_subagent_prompt()` — sem JSON manual, sem interpolação frágil.

---

## dsr-bibliography (Bibliography axis)

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-bibliography', rq_text='{RQ_TEXT}', bibliography_path='{bibliography_path}', main_topic='{main_topic}', topics='{topics}'))")
```

```
agent_open(name="dsr-bibliography", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","web_search","fetch_url","write_file"],
  prompt=<output do code_execution>)
```

**Output file:** `/tmp/dsr-bibliography-results.md` — lido pelo orquestrador
após `agent_eval`. Sub-agent DEVE escrever resultados completos antes de responder.

**Busca:** Local (`grep_files` + `read_file` em `{bibliography_path}`) e web
(`web_search` + `fetch_url`). Inclui queries de limitações/críticas.

---

## dsr-code (Codebase axis)

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-code', rq_text='{RQ_TEXT}'))")
```

```
agent_open(name="dsr-code", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","file_search","write_file"],
  prompt=<output do code_execution>)
```

**Output file:** `/tmp/dsr-code-results.md`.

**Busca:** `grep_files` com padrões derivados da RQ (nomes de função, constantes,
algoritmos) + `read_file` dos arquivos com matches.

---

---

## dsr-verify-titles (Batch Title Verification)

```
code_execution(code="import sys, json; sys.path.insert(0, '{SKILL_DIR}/scripts'); from verify_title_match import _extract_sources_with_url; from pathlib import Path; sources = _extract_sources_with_url(Path('{session_dir}/02-source-inventory.md')); source_list = [{'source_id': k, 'reported_title': v.get('reported_title', ''), 'url': v.get('url', '')} for k, v in sources.items()]; print(json.dumps(source_list))")

code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-verify-titles', source_list_json='<JSON da etapa anterior>'))")
```

```
agent_open(name="dsr-verify-titles", model="deepseek-v4-flash",
  allowed_tools=["fetch_url", "write_file"],
  prompt=<output do code_execution>)
agent_eval(agent_id="...", block=true, timeout_ms=900000)
```

**Output file:** `/tmp/dsr-verify-results.json` — copiar para `{session_dir}/03-gate0-results.json`.

**Busca:** Para cada `{source_id, reported_title, url}`, faz `fetch_url(url)`, extrai
page title, compara com o título reportado usando match de keywords (≥50% de palavras
com 5+ caracteres, ignorando stopwords).

**Timeout:** 900s (15 min) para 40 fontes × 15s cada.

---

## Tipos aceitos por `build_subagent_prompt()`

`"dsr-bibliography"`, `"dsr-code"`, `"dsr-verify-titles"`
