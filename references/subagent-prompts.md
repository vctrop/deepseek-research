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

## Tipos aceitos por `build_subagent_prompt()`

`"dsr-bibliography"`, `"dsr-code"`
