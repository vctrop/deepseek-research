---
name: deepseek-research
description: Pesquisa bibliográfica + análise de código sistemática com deep reading (RLM). Pipeline de 5 estágios: formulação da RQ → descoberta de fontes → verificação → deep reading → síntese + relatório. Acionado por "deep research X", "/deep-research Z", "investigue profundamente Y", "pesquisa fundamental sobre W".
---

# deepseek-research v3.0

Pesquisa bibliográfica e análise de código-fonte com extração de evidência
textual (verbatim) e empírica (código). 5 estágios + deep reading via RLM +
adversarial thinking integrado. **Rapid evidence assessment** — não é revisão
sistemática. Todo julgamento é feito por sub-agents LLM. Gates verificam
completude estrutural, não verdade. Report final DEVE incluir Methodological Note.

## Allowed tools

**Orquestrador:** `request_user_input`, `agent_open`, `agent_eval`, `handle_read`, `rlm_open`, `rlm_eval`, `rlm_configure`, `rlm_close`, `grep_files`, `read_file`, `write_file`, `exec_shell`, `web_search`, `fetch_url`, `checklist_write`, `checklist_update`, `validate_data`, `code_execution`

**dsr-bibliography (Flash):** `grep_files`, `read_file`, `web_search`, `fetch_url`, `write_file`

**dsr-code (Flash):** `grep_files`, `read_file`, `file_search`, `write_file`

## Configuração (defaults inline)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `source_axes` | `["bibliography", "codebase"]` | Eixos de descoberta |
| `bibliography_path` | `"bibliography/"` | Índice bibliográfico local |
| `output_dir` | `"research-reports/"` | Diretório de output |
| `max_sources_per_axis` | `20` | Teto de fontes por eixo |
| `max_deep_reads` | `10` | Máx. fontes para deep reading (sujeito a saturação) |
| `deep_reading` | `true` | Habilitar deep reading |
| `oss_clone_dir` | `"oss/"` | Clone de repositórios (T5) |
| `unpaywall_email` | `""` | Email para Unpaywall API (requerido para OA lookup; vazio = desabilitado) |
| `shadow_libraries` | `[]` | Shadow libraries habilitadas em ordem de fallback. Opções: `"scihub"` (Sci-Hub + SciDB), `"libgen"` (Library Genesis SciMag), `"annas_archive"` (Anna's Archive). Ex: `["scihub", "libgen"]`. ⚠ use por sua conta e risco — ver políticas da sua instituição |
| `scihub_domain` | `""` | Domínio Sci-Hub específico (auto-detecta se vazio) |

Opcional: `.deepseek/deepseek-research.toml` com estas mesmas 10 variáveis.
Placeholders `{output_dir}`, `{date}-{slug}`, `{RQ}`, `{SKILL_DIR}`,
`{bibliography_path}`, `{session_dir}`, `{oss_clone_dir}`, `{iso8601_utc}`,
`{skill_git_hash}`, `{model_id}`, `{date}`, `{slug}` são interpolados pelo
orquestrador. `{SKILL_DIR}` → diretório de instalação da skill.
Configurações de PDF acquisition (`unpaywall_email`, `allow_scihub`,
`scihub_domain`) são lidas diretamente do `.toml` via `config_read()`
no Stage 3.1 — não são placeholders.

## Quick Reference

| Recurso | Path |
|---------|------|
| Pipeline detalhado | `{SKILL_DIR}/references/pipeline-detail.md` |
| Deep reading | `{SKILL_DIR}/references/deep-reading.md` |
| Risk of bias | `{SKILL_DIR}/references/risk-of-bias.md` |
| Error recovery | `{SKILL_DIR}/references/error-recovery.md` |
| Sub-agent prompts | `{SKILL_DIR}/references/subagent-prompts.md` |
| Iron Rule C | `{SKILL_DIR}/references/iron-rule-c.md` |

## Pipeline Overview

```
Phase 0:  Index Bootstrap      → bibliography/index/sources.json
Stage 1:  RQ Formulation       → 01-rq-brief.md, protocol-freeze.json
Phase 1.5: Local Corpus Triage → local_sources list (query index)
Stage 2:  Source Discovery     → 02-source-inventory.md
Stage 3:  Source Verification  → 03-source-verification.md
Stage 4:  Deep Reading         → deep-reads/*.md
Stage 5:  Synthesis + Report   → 04-synthesis.md, 05-report.md
Close:    Persistence + Gates  → MANIFEST.txt, SESSION-INDEX.md
```

**Resume from interruption:** retome do último estágio com output file completo.
Se `03-source-verification.md` existe, retome do Stage 4.

---

## Phase 0: Index Bootstrap + Config Check

**Output:** `bibliography/index/sources.json` (criado se não existir), `.deepseek/deepseek-research.toml` (criado/corrigido se necessário)

1. Verificar/corrigir config:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import config_ensure; print(config_ensure('.'))")
   ```
   - `"created"` → config criado com defaults
   - `"added N keys: ..."` → chaves faltantes adicionadas
   - `"ok"` → nada a fazer

2. Verificar se `{bibliography_path}/index/` existe:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import init_sources; from pathlib import Path; init_sources(Path('{bibliography_path}')); print('Index bootstrap OK')")
   ```
3. Escanear por arquivos não-indexados:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import scan_unindexed; from pathlib import Path; import json; result = scan_unindexed(Path('{bibliography_path}')); print(json.dumps(result, indent=2))")
   ```
4. Se houver arquivos não-indexados (>0 no JSON array): emitir nota
   `"Note: {N} unindexed files in bibliography/. Run /index-sources to incorporate them."`
   Caso contrário: silencioso, prosseguir.

---

## Stage 1: RQ Formulation

**Output:** `01-rq-brief.md`, `protocol-freeze.json`

1. Receber RQ do usuário.
2. Extrair tópicos via `topic_extractor.py`:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from topic_extractor import extract_topics, topics_to_csv; topics = extract_topics('{RQ_TEXT}'); print(topics_to_csv(topics))")
   ```
3. Classificar escopo: bibliografia, código, ou ambos.
4. Definir sub-questions (3-5).
5. Critérios de inclusão/exclusão.
6. Gerar `01-rq-brief.md` (template `{SKILL_DIR}/templates/rq-brief.md`).
7. SHA256 do brief → `protocol-freeze.json` (timestamp ISO 8601, SHA256, RQ).
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_sha256; print(compute_sha256('{session_dir}/01-rq-brief.md'))")
   ```

---

## Phase 1.5: Local Corpus Triage

**Output:** `local_sources` list (passado para Stage 2)

1. Extrair keywords dos tópicos da RQ (já disponíveis de Stage 1 como `{topics}`).
2. Consultar o índice local:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import query_sources; from pathlib import Path; import json; result = query_sources(Path('{bibliography_path}'), '{topics}'.split(','), top_n=10); print(json.dumps(result, indent=2))")
   ```
3. Armazenar o JSON output como `{local_sources_json}`.
4. Se o array estiver vazio (`[]`) → prosseguir para Stage 2 sem fontes locais.
5. Se houver matches: passar `local_sources_json={local_sources_json}` para
   `build_subagent_prompt` no Stage 2.1. O sub-agent `dsr-bibliography` receberá
   a lista de fontes locais no prompt e as lerá via `read_file` antes de buscar
   na web. Fontes locais incluídas devem ser marcadas com "(local corpus)" na
   coluna Why da tabela de fontes.

---

## Stage 2: Source Discovery

**Output:** `02-source-inventory.md`
**Template:** `{SKILL_DIR}/templates/source-inventory.md`

### 2.1 Bibliografia (sub-agent Flash)

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-bibliography', rq_text='{RQ_TEXT}', bibliography_path='{bibliography_path}', main_topic='{main_topic}', topics='{topics}', local_sources_json='{local_sources_json}'))")
agent_open(name="dsr-bibliography", model="deepseek-v4-flash", allowed_tools=["grep_files","read_file","web_search","fetch_url","write_file"], prompt=<output>)
```
Output: `/tmp/dsr-bibliography-results.md`. Inclui queries negativas
("limitations of {T}", "criticism of {T}", "failure cases of {T}").

### 2.2 Codebase (sub-agent Flash)

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-code', rq_text='{RQ_TEXT}'))")
agent_open(name="dsr-code", model="deepseek-v4-flash", allowed_tools=["grep_files","read_file","file_search","write_file"], prompt=<output>)
```
Output: `/tmp/dsr-code-results.md`.

### 2.3 Consolidação (Orquestrador)

Merge → dedup → tabela (ID, título, tipo, relevância 1-5) → tabela de fluxo
PRISMA-style: "Identified: N → After dedup: M → Selected: P".

---

## Stage 3: Source Verification

**Output:** `03-source-verification.md`
**Template:** `{SKILL_DIR}/templates/source-verification.md`

### 3.0 Title Match Gate (GATE-0)

Para cada fonte com URL no `02-source-inventory.md`:
1. `fetch_url("{url}")` para verificar HTTP status.
2. Extrair o título da página (primeiro `<h1>` ou `<title>`).
3. Comparar com o título reportado pelo sub-agente:
   - **Match:** fonte marcada como ACCESSIBLE.
   - **Mismatch:** fonte marcada como HALLUCINATED — o sub-agente fabricou
     uma URL que não corresponde ao conteúdo alegado. Remover da tabela de
     fontes ativas e registrar no Title Mismatch log.
   - **404/403/Timeout:** fonte marcada como UNVERIFIABLE.
4. Fontes sem URL (arquivos locais, bibliography): usar `read_file` para
   verificar existência e extrair título quando aplicável.
5. **A categoria "ACCESSIBLE (inferred)" está abolida.** Toda fonte deve ser
   verificada ativamente ou marcada como UNVERIFIABLE.

### 3.1 Full-Text PDF Acquisition (Batch)

Para fontes bibliográficas (papers), resolver PDFs em lote. **Uma única chamada**
processa todas as fontes do inventory via `resolve_all_fulltext()`:

```
code_execution(code='''
import sys, json; sys.path.insert(0, "{SKILL_DIR}/scripts")

# Ler config do projeto (sem dependência de interpolação do LLM)
from helpers import config_read
cfg = config_read(".")
unpaywall_email = cfg.get("unpaywall_email", "")
shadow_libraries = cfg.get("shadow_libraries", [])
scihub_domain = cfg.get("scihub_domain", "")

from fulltext import resolve_all_fulltext
result_json = resolve_all_fulltext(
    inventory_path="{session_dir}/02-source-inventory.md",
    output_dir="{session_dir}/pdfs/",
    unpaywall_email=unpaywall_email,
    shadow_libraries=shadow_libraries,
    scihub_domain=scihub_domain,
)
result = json.loads(result_json)
print(f"Total: {result['summary']['total']} | arxiv: {result['summary'].get('arxiv', 0)} | oa: {result['summary'].get('oa', 0)} | unavailable: {result['summary'].get('unavailable', 0)}")

# Salvar mapping para Stage 4
with open("{session_dir}/pdfs/mapping.json", "w") as f:
    json.dump(result, f, indent=2)
''')
```

Cadeia por fonte: arXiv PDF → Unpaywall API (requer `unpaywall_email` config) →
Sci-Hub (requer `allow_scihub=true`). O Stage 4 lê `pdfs/mapping.json` para saber
quais PDFs estão disponíveis. Ver `references/pipeline-detail.md` §3.1.

### 3.2 Credibility + Risk of Bias

1. Classificar tipo (paper/código/doc) e primary/secondary/tertiary.
2. Risk of bias (3 níveis: Low/Medium/High):
   - **Papers (4 perguntas):** acessibilidade, metodologia documentada, conflito
     de interesse, peer review do venue.
   - **Código (3 perguntas):** CI/tests passam, múltiplos contribuidores,
     usado/dependenciado por outros projetos.
   - Propagação worst-case.
3. Ver `{SKILL_DIR}/references/risk-of-bias.md`.

---

## Stage 4: Deep Reading

**Output:** `deep-reads/{source_id}.md`
**Template:** `{SKILL_DIR}/templates/source-deep-read.md`

1. Priorizar top `max_deep_reads` fontes por relevância.
2. **Saturação:** após cada 3 deep reads, verificar se últimas 2 adicionaram
   claims novos (V ou E). Se não → interromper.
3. **Papers:** T1 (<5KB) `read_file`, T2 (5-50KB) paginado, T3 (50-200KB) RLM
   chunk+batch, T4 (>200KB) ToC→intro/conclusion→seções relevantes.
4. **RLM lifecycle:** `rlm_open` → `rlm_eval` → `rlm_close`. Máximo 1 ativa.
5. **Código (T5):** clone `--depth 1 --single-branch` (120s timeout), grep,
   read_file, extrair claims E-grade, registrar commit hash.
6. **Context budget:** batch de 3 fontes T3/T4, compactar se >70%.
7. Output: tabela de claims (V/P/I/M/E) + internal consistency + assessment.
8. Ver `{SKILL_DIR}/references/deep-reading.md`.

---

## Stage 5: Synthesis + Report

**Output:** `04-synthesis.md`, `05-report.md`
**Templates:** `{SKILL_DIR}/templates/synthesis.md`, `{SKILL_DIR}/templates/report.md`

### 5.1 Synthesis

1. Carregar todos os `deep-reads/{source_id}.md`.
2. **Coverage cap:** para cada fonte, extrair `coverage_pct` do header do deep read.
   Aplicar o cap de confidence conforme tabela em `references/deep-reading.md` §Coverage → Confidence Binding:
   - coverage ≥ 80% → permite HIGH
   - 50–79% → cap MODERATE
   - 25–49% → cap LOW
   - < 25% → cap SPECULATIVE; claims só podem ser usados como corroboração
   - coverage não reportada → cap LOW
3. Cross-reference: dedup, convergência, contradição.
4. **Adversarial thinking pass:** para cada finding, avaliar evidência contrária,
   independência de fontes, viés de seleção/publicação.
5. Classificar: STRONG / MODERATE / WEAK (respeitando o coverage cap).
6. Cada finding cita ≥1 quote verbatim. Gerar `04-synthesis.md`.

### 5.2 Report

1. Executive Summary (4-6 parágrafos).
2. Key Findings com qualified language (Iron Rule C).
3. Structured Data: constantes numéricas e algoritmos.
4. Methodological Note: limitações epistêmicas.
5. Confidence: HIGH / MEDIUM / LOW / SPECULATIVE.
6. Gerar `05-report.md`.

**Iron Rule C:** Claims nus proibidos. Ver `{SKILL_DIR}/references/iron-rule-c.md`.

---

## Close: Persistence + Verification

**Output:** `MANIFEST.txt`, `SESSION-INDEX.md`, `bibliography/index/sources.json`

### Persistence (executar antes dos gates)

Para fontes usadas no relatório que sobreviveram ao Stage 3 (ACCESSIBLE):

1. **Fontes novas (web-discovered):** para cada fonte nova usada no `05-report.md`
   que não estava no índice local, persistir via `add_source`:
   ```
   code_execution(code='''
   import sys, json; sys.path.insert(0, "{SKILL_DIR}/scripts")
   from index_sources import add_source
   from pathlib import Path

   # Para cada fonte nova: copiar PDF/markdown do session_dir/pdfs/ para bibliography/
   # e adicionar entrada ao índice.
   entry = {{
       "id": "{source_id}",
       "title": "{title}",
       "authors": [{authors}],
       "year": {year},
       "doi": "{doi}",
       "keywords": [{keywords}],
       "summary": "{summary}",
       "quality_level": "{quality_level}",
       "source_type": "{source_type}",
       "sessions_used": ["{session_slug}"],
   }}
   file_path = Path("{session_dir}/pdfs/{source_id}.pdf")
   if file_path.exists():
       result = add_source(Path("{bibliography_path}"), file_path, entry)
       print(f"Indexed: {{result['path']}}")
   else:
       print(f"Skip (no file): {{source_id}}")
   ''')
   ```

2. **Fontes locais reutilizadas:** atualizar `sessions_used`:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import update_sessions; from pathlib import Path; update_sessions(Path('{bibliography_path}'), '{source_id}', '{session_slug}'); print('Session updated')")
   ```

3. **SESSION-INDEX.md:** append uma linha à tabela em `{output_dir}/SESSION-INDEX.md`:
   ```
   | {date} | {slug} | {research_target} | rapid | {key_findings_summary_≤280_chars} |
   ```
   Se o arquivo não existir, criar com header row primeiro.

4. Emitir resumo: "Corpus updated: {X} new sources indexed, {Y} local sources reused."

### Verification Gates (10 gates)

| Gate | Tipo | Descrição |
|------|------|-----------|
| GATE-1 | Manual | File integrity — outputs esperados existem e não estão vazios |
| GATE-2 | **Automático** | IRON RULE C — `check_iron_rule_c_deterministic()` com filtros de contexto |
| GATE-3 | Manual | Textual evidence — STRONG claims têm V-grade ou E-grade corroborado |
| GATE-4 | Manual | RoB completeness — toda fonte tem rating |
| GATE-5 | Manual | Placeholder resolution — sem `{placeholder}` não resolvido |
| GATE-6 | **Automático** | Verification Completeness — `verify_completeness.py` |
| GATE-7 | **Automático** | Evidence Grade Sanity — `verify_evidence_grades.py` |
| GATE-8 | **Automático** | Source Ref Cross-Check — `verify_source_refs.py` |
| GATE-9 | Manual | Coverage-Grade Consistency — `check_coverage_grade_consistency()` |
| GATE-10 | Manual | Batch PDF Acquisition — `resolve_all_fulltext()` executado no Stage 3 |

### Gates Automáticos (code_execution)

**GATE-2 (Iron Rule C determinístico):**
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from helpers import check_iron_rule_c_deterministic
print(check_iron_rule_c_deterministic(
    "{session_dir}/05-report.md",
    "{session_dir}/04-synthesis.md"
))
''')
```

**GATE-6 (Verification Completeness):**
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_completeness import check
print(check("{session_dir}/02-source-inventory.md", "{session_dir}/03-source-verification.md"))
''')
```

**GATE-7 (Evidence Grade Sanity):**
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_evidence_grades import check
print(check("{session_dir}/deep-reads/"))
''')
```

**GATE-8 (Source Ref Cross-Check):**
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_source_refs import check
print(check(
    "{session_dir}/02-source-inventory.md",
    "{session_dir}/04-synthesis.md",
    "{session_dir}/05-report.md"
))
''')
```

**GATE-9 (Coverage-Grade Consistency):**
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from helpers import check_coverage_grade_consistency
print(check_coverage_grade_consistency(
    "{session_dir}/deep-reads/",
    "{session_dir}/04-synthesis.md"
))
''')
```

---

## Session output structure

```
{output_dir}/
├── SESSION-INDEX.md          ← append-only session log
├── {date}-{slug}/
│   ├── MANIFEST.txt
│   ├── protocol-freeze.json
│   ├── 01-rq-brief.md
│   ├── 02-source-inventory.md
│   ├── 03-source-verification.md
│   ├── pdfs/
│   │   └── mapping.json
│   ├── deep-reads/
│   │   └── {source_id}.md
│   ├── 04-synthesis.md
│   └── 05-report.md
└── bibliography/
    ├── index/
    │   └── sources.json      ← cross-session corpus index
    └── {source_id}.pdf        ← persisted source files
```
