---
name: deepseek-research
description: Pesquisa bibliográfica + análise de código sistemática com deep reading (RLM). Pipeline de 5 estágios: formulação da RQ → descoberta de fontes → verificação → deep reading → síntese + relatório. Acionado por "deep research X", "/deep-research Z", "investigue profundamente Y", "pesquisa fundamental sobre W".
---

# deepseek-research v3.0

Rapid evidence assessment com 5 estágios + deep reading via RLM +
adversarial thinking integrado. Todo julgamento é feito por sub-agents LLM.
Gates verificam completude estrutural, não verdade.

## Allowed tools

**Orquestrador:** `request_user_input`, `agent_open`, `agent_eval`, `handle_read`,
`rlm_open`, `rlm_eval`, `rlm_configure`, `rlm_close`, `grep_files`,
`read_file`, `write_file`, `exec_shell`, `web_search`, `fetch_url`,
`checklist_write`, `checklist_update`, `validate_data`, `code_execution`

Ferramentas de sub-agents: ver `{SKILL_DIR}/references/subagent-prompts.md`.

## Configuração

| Variável | Default | Descrição |
|----------|---------|-----------|
| `source_axes` | `["bibliography", "codebase"]` | Eixos de descoberta |
| `output_dir` | `"research-reports/"` | Diretório de output |
| `max_sources_per_axis` | `20` | Teto de fontes por eixo |
| `max_deep_reads` | `10` | Máx. fontes para deep reading |
| `deep_reading` | `true` | Habilitar deep reading |

Demais variáveis (`bibliography_path`, `oss_clone_dir`, `unpaywall_email`,
`shadow_libraries`, `scihub_domain`) e placeholders: ver
`{SKILL_DIR}/references/pipeline-detail.md` §Config.

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

**Resume from interruption:** `stage_status.py` detecta o próximo stage.
Se `03-source-verification.md` existe, retome do Stage 4 (fallback manual).
Ver `{SKILL_DIR}/references/pipeline-detail.md` §Resume.

---

## Phase 0: Index Bootstrap + Config Check

**Output:** `bibliography/index/sources.json`, `.deepseek/deepseek-research.toml`

1. `config_ensure()` — cria/corrige `.deepseek/deepseek-research.toml`.
2. `init_sources()` — idempotente, cria `bibliography/index/sources.json`.
3. `scan_unindexed()` — detecta PDFs não-indexados.
4. Se encontrados: notificar usuário. Senão, silencioso.

Ver `{SKILL_DIR}/references/pipeline-detail.md` §Phase 0 para code blocks.

---

## Stage 1: RQ Formulation

**Output:** `01-rq-brief.md`, `protocol-freeze.json`
**Template:** `{SKILL_DIR}/templates/rq-brief.md`

1. Receber RQ. Extrair tópicos via `topic_extractor.py`.
2. Classificar escopo (bibliografia, código, ou ambos). Derivar 3-5 sub-questions.
3. Definir critérios de inclusão/exclusão.
4. Gerar `01-rq-brief.md` e `protocol-freeze.json` (SHA256 do brief).

Ver `{SKILL_DIR}/references/pipeline-detail.md` §Stage 1.

---

## Phase 1.5: Local Corpus Triage

**Output:** `local_sources_json` (passado para Stage 2)

1. `query_sources()` com keywords dos tópicos da RQ.
2. Se matches: injetar no prompt do `dsr-bibliography` (Stage 2).
3. Fontes locais marcadas como "(local corpus)" na coluna Why.

Ver `{SKILL_DIR}/references/pipeline-detail.md` §Phase 1.5.

---

## Stage 2: Source Discovery

**Output:** `02-source-inventory.md`
**Template:** `{SKILL_DIR}/templates/source-inventory.md`

### 2.1 Bibliografia (sub-agent Flash)
`dsr-bibliography` busca web + local corpus. Output: `/tmp/dsr-bibliography-results.md`.
Inclui queries negativas ("limitations of {T}", "criticism of {T}").

### 2.2 Codebase (sub-agent Flash)
`dsr-code` faz grep + read_file no workspace. Output: `/tmp/dsr-code-results.md`.

### 2.3 Consolidação (Orquestrador)
Merge → dedup → `enforce_source_caps.py` → inventory final com PRISMA flow.
Fontes excedentes truncadas por relevância; registradas em `## Cap Enforcement`.

Ver `{SKILL_DIR}/references/pipeline-detail.md` §Stage 2.

---

## Stage 3: Source Verification

**Output:** `03-source-verification.md`
**Template:** `{SKILL_DIR}/templates/source-verification.md`

### 3.0 Title Match Gate (GATE-0)
Cada fonte com URL: `fetch_url` → extrair título → comparar com o reportado.
Match → ACCESSIBLE. Mismatch → HALLUCINATED. 404/403 → UNVERIFIABLE.
Checkpoint: `03-gate0-results.json`. Categoria "ACCESSIBLE (inferred)" abolida.

### 3.1 Full-Text PDF Acquisition
`resolve_all_fulltext()` em lote: arXiv PDF → Unpaywall → Sci-Hub → LibGen →
Anna's Archive → Abstract via DOI. Output: `pdfs/mapping.json`.
Stage 4 consome este mapping para o paywall circuit breaker.

### 3.2 Credibility + Risk of Bias
Classificar tipo (paper/código/doc), primary/secondary/tertiary.
RoB: 4 perguntas para papers, 3 para código. Rating: Low/Medium/High.

Ver `{SKILL_DIR}/references/pipeline-detail.md` §Stage 3.

---

## Stage 4: Deep Reading

**Output:** `deep-reads/{source_id}.md`
**Template:** `{SKILL_DIR}/templates/source-deep-read.md`

1. **RLM Sweep:** fechar sessões órfãs antes de abrir novas (`rlm_close` idempotente).
2. **Paywall breaker:** consultar `pdfs/mapping.json`; max 3 rotas por fonte;
   circuit breaker global após 5 INACCESSIBLE consecutivas.
3. Priorizar top `max_deep_reads` fontes ACCESSIBLE. INACCESSIBLE não consomem vaga.
4. **T3/T4 (preferencial):** sub-agent wrapper com `timeout_ms=600000`.
   Fallback: modo direto com `sub_query_timeout_secs=120` no RLM contract.
5. **Saturação:** a cada 3 deep reads, verificar claims novos (V/E).
   Escrever `_saturation_check.md` em disco.
6. **Código (T5):** clone `--depth 1` (120s timeout), grep, claims E-grade.
7. **Context budget:** batch de 3 fontes T3/T4; `/compact` se >70%.

Ver `{SKILL_DIR}/references/pipeline-detail.md` §Stage 4 e
`{SKILL_DIR}/references/deep-reading.md`.

---

## Stage 5: Synthesis + Report

**Output:** `04-synthesis.md`, `05-report.md`
**Templates:** `{SKILL_DIR}/templates/synthesis.md`, `{SKILL_DIR}/templates/report.md`

### 5.1 Synthesis
Cross-reference de claims com coverage cap. Adversarial thinking pass:
evidência contrária, independência de fontes, viés de seleção.
Classificar STRONG / MODERATE / WEAK. Cada finding cita ≥1 quote verbatim.

### 5.2 Report
Executive Summary (4-6 ¶), Key Findings (Iron Rule C), Structured Data,
Methodological Note com limitações session-specific. Confidence labels.

**Iron Rule C:** Claims nus proibidos. Ver `{SKILL_DIR}/references/iron-rule-c.md`.
Ver `{SKILL_DIR}/references/pipeline-detail.md` §Stage 5.

---

## Close: Persistence + Verification

**Output:** `MANIFEST.txt`, `SESSION-INDEX.md`, `bibliography/index/sources.json`

### Persistence
1. Fontes novas: `add_source()` → índice local + cópia para `bibliography/`.
2. Fontes reutilizadas: `update_sessions()`.
3. `SESSION-INDEX.md`: append de linha com date, slug, findings (≤280 chars).
4. `pipeline_metrics.py` → anexar ao MANIFEST.txt.

### Verification Gates

| Gate | Descrição |
|------|-----------|
| GATE-1 | File integrity — outputs existem e não estão vazios |
| GATE-2 | IRON RULE C — `check_iron_rule_c_deterministic()` |
| GATE-3 | Textual evidence — STRONG claims têm V-grade ou E-grade |
| GATE-4 | RoB completeness — toda fonte tem rating |
| GATE-5 | Placeholder resolution — sem `{placeholder}` não resolvido |
| GATE-6 | Verification Completeness — `verify_completeness.py` |
| GATE-7 | Evidence Grade Sanity — `verify_evidence_grades.py` |
| GATE-8 | Source Ref Cross-Check — `verify_source_refs.py` |
| GATE-9 | Coverage-Grade Consistency — `check_coverage_grade_consistency()` |
| GATE-10 | Batch PDF Acquisition — `resolve_all_fulltext()` executado |
| GATE-0b | Title Match Checkpoint — `verify_title_match.py` |

Comandos dos gates automáticos: ver `{SKILL_DIR}/references/pipeline-detail.md` §Close.

---

## Session output structure

```
{output_dir}/
├── SESSION-INDEX.md
└── {date}-{slug}/
    ├── MANIFEST.txt
    ├── protocol-freeze.json
    ├── 01-rq-brief.md
    ├── 02-source-inventory.md
    ├── 03-source-verification.md
    ├── pdfs/
    │   └── mapping.json
    ├── deep-reads/
    │   └── {source_id}.md
    ├── 04-synthesis.md
    └── 05-report.md
```
