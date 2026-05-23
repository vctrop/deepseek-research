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
| `allow_scihub` | `false` | Habilitar fallback Sci-Hub para papers sem OA copy (⚠ use por sua conta e risco) |
| `scihub_domain` | `""` | Domínio Sci-Hub específico (auto-detecta se vazio) |

Opcional: `.deepseek/deepseek-research.toml` com estas mesmas 10 variáveis.
Placeholders `{output_dir}`, `{date}-{slug}`, `{RQ}`, `{SKILL_DIR}`,
`{bibliography_path}`, `{session_dir}`, `{oss_clone_dir}`, `{iso8601_utc}`,
`{skill_git_hash}`, `{model_id}`, `{date}`, `{slug}`, `{unpaywall_email}`,
`{allow_scihub}`, `{scihub_domain}` são interpolados pelo
orquestrador. `{SKILL_DIR}` → diretório de instalação da skill.
`{allow_scihub}` é interpolado como `True` ou `False` (Python literal).

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
Stage 1: RQ Formulation     → 01-rq-brief.md, protocol-freeze.json
Stage 2: Source Discovery    → 02-source-inventory.md
Stage 3: Source Verification → 03-source-verification.md
Stage 4: Deep Reading        → deep-reads/*.md
Stage 5: Synthesis + Report  → 04-synthesis.md, 05-report.md
Close:   Verification        → MANIFEST.txt (5 gates)
```

**Resume from interruption:** retome do último estágio com output file completo.

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

## Stage 2: Source Discovery

**Output:** `02-source-inventory.md`
**Template:** `{SKILL_DIR}/templates/source-inventory.md`

### 2.1 Bibliografia (sub-agent Flash)

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-bibliography', rq_text='{RQ_TEXT}', bibliography_path='{bibliography_path}', main_topic='{main_topic}', topics='{topics}'))")
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

### 3.1 Full-Text PDF Acquisition

Para fontes bibliográficas (papers), tentar obter o PDF completo via cadeia de
fallback SPEC-003:

```
code_execution(code='''
import sys, json; sys.path.insert(0, "{SKILL_DIR}/scripts")
from helpers import resolve_fulltext

# O orquestrador interpola {allow_scihub} como True ou False.
# Safe default False se placeholder não resolvido.
_allow_scihub_raw = "{allow_scihub}"
try:
    allow_scihub = {"true": True, "false": False}[_allow_scihub_raw.strip().lower()]
except (KeyError, AttributeError):
    allow_scihub = False

result = resolve_fulltext(
    doi="{doi}",            # se disponível
    arxiv_id="{arxiv_id}",  # se disponível
    source_id="{source_id}",
    output_dir="{session_dir}/pdfs/",
    unpaywall_email="{unpaywall_email}",
    allow_scihub=allow_scihub,
)
print(json.dumps(result))
''')
```

Cadeia: arXiv PDF → Unpaywall API (requer `unpaywall_email` config) → Sci-Hub
(requer `allow_scihub=true`). Se `pdf_path` retornado, usar `read_file` para
extrair texto. Ver `references/pipeline-detail.md` §3.1 para detalhes.

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

## Close: Verification (5 gates)

**Output:** `MANIFEST.txt`

| Gate | Descrição |
|------|-----------|
| GATE-1 | File integrity — outputs esperados existem e não estão vazios |
| GATE-2 | IRON RULE C — sem claims nus em report/synthesis |
| GATE-3 | Textual evidence — STRONG claims têm V-grade ou E-grade corroborado |
| GATE-4 | RoB completeness — toda fonte tem rating |
| GATE-5 | Placeholder resolution — sem `{placeholder}` não resolvido |

**GATE-2 exec:**
```
grep_files(pattern="\\b(validated|proved|confirmed|demonstrated|ensures|guarantees|always|never|optimal|definitive|conclusive|certainly|undoubtedly|obviously|clearly)\\b", path="{session_dir}/")
```
Para cada match, verificar qualificação (source + method + conditions).

---

## Session output structure

```
{output_dir}/{date}-{slug}/
├── MANIFEST.txt
├── protocol-freeze.json
├── 01-rq-brief.md
├── 02-source-inventory.md
├── 03-source-verification.md
├── deep-reads/
│   └── {source_id}.md
├── 04-synthesis.md
└── 05-report.md
```
