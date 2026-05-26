---
target: deepseek-research skill v3.0
status: draft
created: 2026-05-23
updated: 2026-05-23 (post-review corrections)
author: deepseek-tui (DeepSeek V4 Pro)
supersedes: SPEC-001 (professional-research-parity)
skill_version_target: 3.0.0
---

# SPEC-002: Simplificação para Pesquisa Bibliográfica + Análise de Código

## 1. Sumário Executivo

A skill `deepseek-research` cresceu de um pipeline de "rapid evidence assessment"
para um motor de ~7.800 linhas (40+ arquivos) que tenta replicar o workflow de uma
equipe de revisão sistemática profissional (Cochrane/Campbell). O resultado é uma
skill que sofre de crise de identidade, sobrecarga metodológica importada da
medicina clínica, e fragilidade por acoplamento excessivo.

**Esta spec propõe reduzir a skill para ~1.600 linhas, focando em seu diferencial
real: pesquisa bibliográfica com deep reading (RLM) e análise sistemática de
código-fonte (T5).**

O escopo passa de "rapid evidence assessment com pretensões de revisão sistemática"
para "pesquisa bibliográfica + análise de código sistemática, com extração de
evidência textual e empírica".

---

## 2. Diagnóstico

### 2.1 Métricas atuais

| Métrica | Valor |
|----------|-------|
| Total de linhas (todos os arquivos) | ~7.800 |
| Arquivos | 40+ |
| Estágios do pipeline | 15 + Close (23 gates) |
| Scripts Python | 11 |
| Templates | 13 |
| Arquivos de referência | 15 |
| Variáveis de configuração | 24 |
| Eixos de descoberta | 5 (web, bibliography, codebase, opensource, grey) |
| Tipos de sub-agent | 10 |
| Cenários de error recovery | 34 |

### 2.2 Problemas identificados

1. **Crise de identidade**: o frontmatter diz "multi-source research pipeline",
   o corpo diz "rapid evidence assessment", mas a implementação é um híbrido que
   não é nem rápido nem sistemático.

2. **Importação acrítica de metodologia clínica**: meta-análise (DerSimonian-Laird,
   forest plots, I², τ², fail-safe N), GRADE (BMJ/WHO/Cochrane), PRISMA, PRESS,
   Egger's test — todos importados de revisão sistemática clínica sem validação
   para engenharia/CS. O próprio `epistemic-limitations.md` admite que a skill
   não é um revisor sistemático.

3. **Fragilidade por acoplamento**: checklist IDs posicionais que quebram com
   reordenação, `id=15` com duplo uso (Stage 1.7 e Close), crash recovery que
   depende de `.session-state.json`, 11 scripts interdependentes.

4. **Falácia de precisão**: a skill produz ratings numéricos (κ, I², GRADE ⊕⊕⊕⊝)
   que parecem precisos mas são extraídos por LLM de fontes heterogêneas. O
   resultado é uma falsa sensação de rigor quantitativo.

5. **Feature creep do SPEC-001**: o SPEC-001 definiu 13 gaps para atingir
   "paridade com equipe de pesquisa profissional", resultando em um pipeline
   que tenta fazer tudo e entrega pouco valor incremental por complexidade
   adicionada.

6. **Context budget sob pressão constante**: o pipeline tem warning threshold
   (120K tokens) e halt threshold (180K tokens) porque acumula referências,
   templates e stage outputs. A complexidade é autofágica.

---

## 3. Arquitetura Alvo

### 3.1 Estrutura de diretórios

```
deepseek-research/
├── SKILL.md                        (~220 linhas)
├── references/
│   ├── pipeline-detail.md          (~330 linhas)
│   ├── deep-reading.md             (~200 linhas, simplificado)
│   ├── iron-rule-c.md              (mantido)
│   ├── risk-of-bias.md             (~60 linhas, simplificado)
│   ├── error-recovery.md           (~40 linhas, simplificado)
│   └── subagent-prompts.md         (~80 linhas, simplificado)
├── templates/
│   ├── rq-brief.md
│   ├── source-inventory.md
│   ├── source-verification.md
│   ├── synthesis.md
│   ├── report.md
│   └── source-deep-read.md
└── scripts/
    ├── helpers.py                  (simplificado)
    ├── prompts.py                  (sub-agent builders)
    └── topic_extractor.py          (mantido)
```

**Total estimado: ~1.600 linhas (redução de ~80%).**

### 3.2 Pipeline (5 estágios + Close)

```
Stage 1: RQ Formulation     → 01-rq-brief.md
Stage 2: Source Discovery    → 02-source-inventory.md
Stage 3: Source Verification → 03-source-verification.md
Stage 4: Deep Reading        → deep-reads/*.md
Stage 5: Synthesis + Report  → 04-synthesis.md, 05-report.md
Close:   Verification        → MANIFEST.txt (5 gates)
```

---

## 4. Pipeline Detalhado

### Stage 1: RQ Formulation

**Objetivo:** Estruturar a pergunta de pesquisa, extrair palavras-chave, definir
escopo e eixos de descoberta.

**Output:** `01-rq-brief.md`

**Procedimento:**
1. Receber RQ do usuário.
2. Extrair tópicos/palavras-chave via `topic_extractor.py`.
3. Classificar escopo: bibliografia, código, ou ambos.
4. Definir sub-questions (máximo 3-5).
5. Definir critérios de inclusão/exclusão simples.
6. Gerar `01-rq-brief.md` com template `rq-brief.md`.
7. Calcular SHA256 do brief como protocol freeze.
8. Gerar `protocol-freeze.json` com timestamp ISO 8601, SHA256, RQ original,
   e metadata de escopo. Este arquivo serve como registro local de protocolo
   que o usuário pode opcionalmente depositar em repositório público (OSF,
   Zenodo, Figshare) para credibilidade acadêmica.

**Removido do Stage 1 atual:**
- FINER scoring
- Knowledge type taxonomy (declarative/procedural/causal/predictive)
- Operational definitions template
- Review type declaration (systematic/rapid/scoping/narrative)
- Pre-registration automática (OSF/Zenodo) — substituída por protocol-freeze.json local
- Open-source applicability decision (6 critérios)
- Local corpus triage

### Stage 2: Source Discovery

**Objetivo:** Descobrir fontes relevantes via busca bibliográfica e análise de
codebase.

**Output:** `02-source-inventory.md`

**Procedimento:**
1. **Eixo bibliografia** (sub-agent Flash):
   - Busca local: `grep_files` + `read_file` no `bibliography_path`.
   - Busca web: `web_search` + `fetch_url` com queries derivadas da RQ.
   - Inclui queries de limitações/críticas: "limitations of {T}",
     "criticism of {T}", "failure cases of {T}".
   - Output: `/tmp/dsr-bibliography-results.md`.

2. **Eixo codebase** (sub-agent Flash):
   - `grep_files` com padrões derivados da RQ (nomes de função, constantes,
     algoritmos).
   - `read_file` dos arquivos com matches.
   - Output: `/tmp/dsr-code-results.md`.

3. **Consolidação** (orquestrador):
   - Merge dos resultados dos sub-agents.
   - Deduplicação.
   - Tabela de fontes com: ID, título, tipo (paper/código/doc), relevância (1-5).
   - Incluir tabela de fluxo simplificada (PRISMA-style):
     "Identified: N → After dedup: M → Selected for verification: P".
   - Template: `source-inventory.md`.

**Removido do Stage 2 atual:**
- Dual screening + tiebreak + Cohen's κ
- PRISMA flow diagram completo — substituído por tabela simplificada de 1 linha
- PRESS checklist
- Saturation criterion (saturation window) — substituído por heurística inline no Stage 4
- Grey literature axis
- Open-source discovery axis separado
- Adversarial search sub-agent (Stage 2.6) — adversarial thinking incorporado no Stage 5
- Persistence / corpus index

**Mantido do Stage 2 atual:**
- Queries de busca negativa (limitações, críticas) — incorporadas nas queries
  normais, não em estágio separado
- Sub-agents Flash para descoberta
- Output via `/tmp/dsr-*-results.md`

### Stage 3: Source Verification

**Objetivo:** Verificar acessibilidade e classificar fontes por tipo e risco de viés.

**Output:** `03-source-verification.md`

**Procedimento:**
1. Para cada fonte:
   - Verificar acessibilidade (URL reachable, file exists).
   - Classificar tipo: paper, código, documentação.
   - Classificar como primary/secondary/tertiary.
2. Risk of bias simplificado (3 níveis, 4 perguntas para papers, 3 para código):
   - **Papers:**
     - A fonte é acessível e completa?
     - A metodologia é documentada?
     - Há conflito de interesse evidente?
     - O venue de publicação tem peer review?
   - **Código:**
     - O repositório tem CI e os testes passam?
     - Há múltiplos contribuidores ou é single-maintainer?
     - O código é usado/dependenciado por outros projetos (proxy de maturidade)?
   - Rating: Low / Medium / High.
   - RoB rating é propagado via worst-case quando uma fonte tem múltiplos critérios.
3. Template: `source-verification.md`.

**Removido do Stage 3 atual:**
- 6 study types × 4-7 domains cada
- D6 (algorithmic fidelity) — movido para deep reading T5
- Overall RoB com worst-case propagation — simplificado para 3 níveis

### Stage 4: Deep Reading

**Objetivo:** Processar o corpo completo das fontes, extrair claims com evidência
textual, verificar consistência.

**Output:** `deep-reads/{source_id}.md`

**Procedimento:**
1. Priorizar fontes: top N por relevância (N configurável, default 10).
2. Aplicar heurística de saturação: após cada 3 deep reads concluídas, avaliar
   se as últimas 2 fontes adicionaram claims com grade V (verbatim) ou E
   (empírico) que não estavam presentes nas fontes anteriores. Se não,
   interromper deep reading (saturação atingida). Isso evita processar fontes
   redundantes e economiza context budget.
3. Para papers (T1-T4):
   - T1 (< 5KB): `read_file` direto.
   - T2 (5-50KB): `read_file` paginado.
   - T3 (50-200KB): `rlm_open` → chunk → `sub_query_batch`.
   - T4 (> 200KB): leitura seletiva (ToC → intro/conclusion → seções relevantes).
   - Extrair claims com taxonomia V/P/I/M (verbatim/paráfrase/inferência/matemático).
4. **RLM session lifecycle contract:**
   - Sessions são abertas, avaliadas e fechadas sequencialmente (máximo 1 ativa).
   - Cada source T3/T4 segue o padrão: `rlm_open` → `rlm_eval` (batch) → `rlm_close`.
   - Em caso de erro, `rlm_close` é invocado no cleanup para evitar resource leak.
5. Para código (T5):
   - Se repositório remoto: verificar se `oss/{org}_{repo}/` já existe.
     Se existir, usar `git pull --ff-only`; senão, `git clone --depth 1 --single-branch`.
   - Timeout de clone: 120s. Em caso de timeout, registrar como PARTIAL com nota.
   - `grep_files` com padrões derivados da RQ.
   - `read_file` dos arquivos com matches.
   - Extrair claims com grade E (empírico — implementação).
   - Registrar commit hash para reprodutibilidade.
   - Nota: adicionar `oss/` ao `.gitignore` do workspace se ainda não estiver presente.
6. **Context budget management no Stage 4:**
   - Processar T3/T4 em batches de no máximo 3 fontes.
   - Após cada batch, avaliar context usage. Se > 70% do limite estimado,
     compactar outputs acumulados em `deep-reads/_batch_N_compact.md` antes
     de prosseguir.
   - O `_consolidation.md` final referencia os batches compactados.
7. Cada fonte gera `deep-reads/{source_id}.md` com:
   - Tabela de claims extraídos (verbatim quote + grade + referência).
   - Overall assessment: COMPREHENSIVE / PARTIAL / MINIMAL.
8. Consolidar em `deep-reads/_consolidation.md`.

**Removido do Stage 4 atual:**
- Internal consistency checks (claim-claim, claim-data, claim-method,
  abstract-body) — a síntese cross-reference cobre isso
- Mathematical flagging automático — substituído por grade M com nota de
  "requer verificação humana"

**Mantido do Stage 3.5 atual:**
- Taxonomia V/P/I/M/E — integralmente
- Tiers T1-T5 e chunking strategy
- RLM chunking contract
- Output contract (source-deep-read.md)
- T5 source code reading procedure
- Commit hash para reprodutibilidade

### Stage 5: Synthesis + Report

**Objetivo:** Sintetizar claims extraídos, avaliar convergência/divergência,
produzir relatório final.

**Output:** `04-synthesis.md`, `05-report.md`

**Procedimento:**
1. Carregar todos os `deep-reads/*.md`.
2. Cross-reference de claims entre fontes.
3. Para cada finding:
   - Classificar convergência: CONSENSUS (≥2 fontes independentes STRONG),
     DIVERGENT (fontes conflitantes), INSUFFICIENT (< 2 fontes).
   - Atribuir força de evidência:
     - **STRONG**: ≥2 fontes independentes com V-grade ou E-grade corroborado.
     - **MODERATE**: 1 fonte forte ou 2+ fontes MODERATE.
     - **WEAK**: fonte única, sem verificação cruzada.
4. **Adversarial thinking pass:** após gerar findings, o orquestrador faz uma
   passada de pensamento adversarial sobre cada finding STRONG ou MODERATE:
   "What would a skeptical reviewer say about this finding? What alternative
   explanation exists? What evidence would refute it?". As respostas são
   incorporadas como qualificações nos findings (ex: "Caveat: ...").
5. Iron Rule C enforcement: nenhum claim sem qualificação.
6. Template: `synthesis.md`.
7. Gerar `05-report.md` com:
   - **Executive Summary** (1-2 páginas no topo, autossuficiente para tomada de decisão).
   - Findings com força de evidência e citações.
   - **Structured Data**: tabela de claims extraídos em formato tabular
     (derivada do `04-synthesis.md`) para interoperabilidade.
   - **Methodological Note**: "Source selection was performed by a single AI
     reviewer. Readers should consider this a rapid evidence assessment, not a
     systematic review. Inter-rater reliability was not assessed. A protocol
     freeze file (`protocol-freeze.json`) is available for audit."
   - Limitações epistêmicas (3-4 parágrafos honestos).
   - Referências.
8. Template: `report.md`.

**Removido do Stage 4-5 atual:**
- Meta-análise quantitativa (DerSimonian-Laird, forest plots, I², τ², fail-safe N)
- GRADE certainty framework (⊕⊕⊕⊕ ratings)
- Sensitivity analysis (leave-one-out, subgroup)
- Publication bias detection (Egger's test, funnel plots, trim-and-fill)
- Devil's Advocate checkpoint (Stage 4.5) — adversarial thinking é incorporado
  como passo inline no Stage 5
- Stakeholder review (Stage 4.6)
- Múltiplos formatos de output (plain-summary, decision-brief,
  data-supplement) — consolidados em um único report.md com Executive Summary
  + Structured Data section

### Close: Verification

**Objetivo:** Verificar integridade estrutural dos outputs.

**Procedimento (5 gates):**

| Gate | Descrição | Comando |
|------|-----------|---------|
| GATE-1 | Outputs existem e não são vazios | `find {session_dir} -name "*.md" -empty` → deve retornar vazio |
| GATE-2 | Iron Rule C — sem claims não qualificados | `grep_files` com padrão de termos absolutos, excluindo matches dentro de blockquotes (`> ...`), após negações (`not`, `does not`, `fails to`, `cannot`), e com verificação de ±1 sentença de contexto. Padrão base: `\b(validated|proved|confirmed|demonstrated|ensures|guarantees|always|never|optimal|definitive|conclusive|certainly|undoubtedly|obviously|clearly)\b`. Output: lista de matches com contexto para revisão manual. |
| GATE-3 | Placeholders resolvidos — sem `{`, `PLACEHOLDER`, `T00:00:00Z` | `grep_files(pattern="\\{|PLACEHOLDER|T00:00:00Z", path="{session_dir}/")` → deve retornar vazio |
| GATE-4 | MANIFEST íntegro — SHA256 + stage log | `validate_data(path="{session_dir}/MANIFEST.txt")` |
| GATE-5 | Deep reading enforcement — `_consolidation.md` existe e não é vazio | `test -s {session_dir}/deep-reads/_consolidation.md` |

**Removido dos 23 gates atuais:**
- GATE-5 (persistence manifest), GATE-6 (corpus index), GATE-7 (unindexed files)
- GATE-8 (PRISMA + PRESS compliance)
- GATE-9 (RoB completeness), GATE-10 (inter-rater reliability κ)
- GATE-11 (protocol registration)
- GATE-12 (meta-analysis self-test), GATE-14 (sensitivity flagging)
- GATE-13 (GRADE completeness)
- GATE-15 (output format completeness — 4 output files)
- GATE-16 (stakeholder review)
- GATE-17 (living review cadence)
- GATE-19 (session MANIFEST SHA256 — consolidado no GATE-4)
- GATE-21 (minimum file count — 7 core files)
- GATE-23 (publication bias)

---

## 5. Inventário de Alterações

### 5.1 Arquivos a REMOVER

| Arquivo | Motivo |
|---------|--------|
| `scripts/meta_analysis.py` | Meta-análise clínica; irrelevante para biblio+código |
| `scripts/grade.py` | GRADE framework; adaptação não validada de medicina |
| `scripts/living_review.py` | Vigilância automatizada; YAGNI |
| `scripts/protocol_registry.py` | Registro OSF/Zenodo automático; substituído por protocol-freeze.json local |
| `scripts/index_sources.py` | Corpus persistente; acumula viés |
| `scripts/stage_output.py` | Crash recovery stateful (.session-state.json); substituído por resume-from-last-stage |
| `scripts/bootstrap_config.py` | Config via TOML externo; substituído por inline |
| `references/epistemology.md` | 245 linhas de taxonomia; substituído por 10 linhas no SKILL.md |
| `references/grade-framework.md` | GRADE adaptation; removido com grade.py |
| `references/press-checklist.md` | PRESS 2015; irrelevante para web search |
| `references/epistemic-limitations.md` | 8 limitações catalogadas; substituído por 3-4 parágrafos inline + Methodological Note |
| `references/anti-patterns.md` | 20 anti-patterns; 5 mais críticos absorvidos em error-recovery.md |
| `references/context-budget.md` | Monitoramento de contexto; substituído por heurística inline no Stage 4 |
| `references/model-matrix.md` | Matriz de custo; informativo mas não essencial |
| `references/placeholders.md` | Resolução de placeholders; documentado inline |
| `templates/local-corpus-triage.md` | Triage de corpus local; feature removida |
| `templates/opensource-decision.md` | Decisão de opensource; feature removida |
| `templates/devils-advocate.md` | Devil's Advocate checkpoint; incorporado no Stage 5 |
| `templates/stakeholder-review.md` | Stakeholder review; feature enterprise removida |
| `templates/plain-summary.md` | Plain summary; consolidado como Executive Summary no report.md |
| `templates/decision-brief.md` | Decision brief; consolidado como Executive Summary no report.md |
| `templates/data-supplement.json` | Data supplement; consolidado como Structured Data table no report.md |

### 5.2 Arquivos a SIMPLIFICAR

| Arquivo | Linhas atuais | Linhas alvo | Alterações |
|---------|--------------|-------------|------------|
| `SKILL.md` | 406 | ~220 | Pipeline de 5 estágios; remover 15 estágios + 23 gates; remover todas as references a arquivos deletados; adicionar protocol-freeze, resume-from-last-stage, adversarial pass |
| `references/pipeline-detail.md` | 1,164 | ~330 | 5 estágios em vez de 15; adicionar RLM lifecycle, clone safety, context budget heuristics, saturation heuristic, adversarial thinking pass; remover batch mode, crash recovery, context monitoring, skip logic table, idempotency checks |
| `references/deep-reading.md` | ~250 | ~200 | Remover internal consistency checks, mathematical flagging (grade M cobre); manter taxonomia e tiers; adicionar saturation heuristic |
| `references/risk-of-bias.md` | 131 | ~60 | 3 níveis (Low/Medium/High), 4 perguntas papers + 3 perguntas código; remover 6 study types × múltiplos domains |
| `references/error-recovery.md` | ~60 | ~40 | 10 cenários em vez de 34; adicionar resume-from-last-stage; absorver 5 anti-patterns críticos do anti-patterns.md removido |
| `references/subagent-prompts.md` | 287 | ~80 | Apenas dsr-bibliography e dsr-code; remover dsr-web, dsr-opensource, dsr-grey, dsr-da, dsr-tiebreak, dsr-deep-read-t5 |
| `scripts/helpers.py` | 367 | ~150 | Remover kappa, session state, persistence, protocol, living review; manter build_subagent_prompt, resolve_placeholders, compute_saturation |
| `scripts/prompts.py` | 502 | ~200 | Apenas 2 builders (bibliography, code) em vez de 9 |

### 5.3 Arquivos a MANTER (sem alterações)

| Arquivo | Motivo |
|---------|--------|
| `references/iron-rule-c.md` | Essencial; sem alterações necessárias |
| `scripts/topic_extractor.py` | Extração de tópicos; sem alterações necessárias |
| `templates/source-deep-read.md` | Template de deep read; mantido como está |
| `templates/rq-brief.md` | Simplificado mas estrutura base mantida |
| `templates/source-inventory.md` | Simplificado mas estrutura base mantida; adicionar tabela de fluxo PRISMA-style |
| `templates/source-verification.md` | Simplificado mas estrutura base mantida; adicionar perguntas RoB para código |
| `templates/synthesis.md` | Simplificado mas estrutura base mantida; adicionar adversarial thinking pass |
| `templates/report.md` | Simplificado mas estrutura base mantida; adicionar Executive Summary + Structured Data + Methodological Note |

### 5.4 Arquivos a ATUALIZAR

| Arquivo | Alterações |
|---------|------------|
| `AGENTS.md` | Atualizar arquitetura; remover referências a scripts deletados |
| `README.md` | Atualizar descrição; quick start; pipeline stages; nota sobre migração v2→v3 |
| `CHANGELOG.md` | Adicionar entrada v3.0.0 |
| `IMPLEMENTATION-PLAN.md` | Atualizar ou remover |
| `REVIEW-PHASE-1.md` | Remover (obsoleto) |
| `SPEC-001-professional-research-parity.md` | Marcar como superseded |

---

## 6. Configuração

### 6.1 Variáveis (inline no SKILL.md, com defaults)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `source_axes` | `["bibliography", "codebase"]` | Eixos de descoberta ativos |
| `bibliography_path` | `"bibliography/"` | Caminho para índice bibliográfico |
| `output_dir` | `"research-reports/"` | Diretório de output |
| `max_sources_per_axis` | `20` | Teto de fontes por eixo |
| `max_deep_reads` | `10` | Máximo de fontes para deep reading (sujeito a saturação) |
| `deep_reading` | `true` | Habilitar deep reading |
| `oss_clone_dir` | `"oss/"` | Diretório para clone de repositórios |

Total: 7 variáveis (redução de 24).

Removidas: `session_index`, `persist_sources`, `integration_checks`,
`saturation_window`, `dual_screening`, `agreement_threshold`, `protocol_registry`,
`osf_token`, `osf_project_id`, `meta_analysis`, `stakeholder_review`,
`living_review`, `surveillance_interval_days`, e 4 outras.

### 6.2 Configuração opcional via TOML

O arquivo `.deepseek/deepseek-research.toml` continua suportado, mas apenas
com as 7 variáveis acima. Se ausente, defaults são usados. Sem bootstrap.

---

## 7. Sub-agents

### 7.1 Tipos (reduzido de 10 para 2)

| Nome | Estágio | Modelo | Ferramentas |
|------|---------|--------|-------------|
| `dsr-bibliography` | Stage 2 | Flash | `grep_files`, `read_file`, `web_search`, `fetch_url`, `write_file` |
| `dsr-code` | Stage 2 | Flash | `grep_files`, `read_file`, `file_search`, `write_file` |

### 7.2 Deep reading

Deep reading (Stage 4) é executado pelo orquestrador (Pro), não por sub-agents
dedicados. Para fontes T3/T4, usa RLM sessions (`rlm_open`/`rlm_eval`/`rlm_close`).
Para código T5, usa `exec_shell` (clone) + `grep_files` + `read_file`.

**RLM lifecycle contract:**
- Sessions são sequenciais (máximo 1 ativa por vez).
- Cada source segue: `try: rlm_open → rlm_eval → finally: rlm_close`.
- `rlm_close` é garantido via cleanup mesmo em caso de erro.
- Outputs são coletados e escritos em `deep-reads/{source_id}.md` após `rlm_close`.

**Removidos:** `dsr-web`, `dsr-opensource`, `dsr-grey`, `dsr-da`, `dsr-tiebreak`,
`dsr-deep-read`, `dsr-deep-read-t5`.

---

## 8. Output da Sessão

```
{output_dir}/{date}-{slug}/
├── MANIFEST.txt
├── protocol-freeze.json
├── 01-rq-brief.md
├── 02-source-inventory.md
├── 03-source-verification.md
├── deep-reads/
│   ├── _consolidation.md
│   ├── S1.md
│   ├── S2.md
│   └── ...
├── 04-synthesis.md
└── 05-report.md
```

**Adicionado em relação à estrutura atual:**
- `protocol-freeze.json`: registro local de protocolo com timestamp, SHA256, RQ original, metadata de escopo. Substitui a integração OSF/Zenodo removida.

**Removidos da estrutura atual:**
- `01a-local-corpus-triage.md`
- `01b-opensource-decision.md`
- `01c-adversarial-results.md`
- `protocol-registration.json` — substituído por `protocol-freeze.json`
- `04a-devils-advocate.md`
- `04b-stakeholder-review.md`
- `05-plain-summary.md`
- `05-decision-brief.md`
- `05-data-supplement.json`
- `.session-state.json`

---

## 9. Plano de Implementação

### 9.1 Estratégia de Rollback

**Branching:** Toda a implementação ocorre em branch `feature/spec-002-v3-simplification`.
A branch `main` mantém a versão 2.x estável até validação completa.

**Tags:** Antes de iniciar, criar tag `v2.x-last` em main. Após validação, merge
com `--no-ff` e tag `v3.0.0`. Se a validação falhar, a branch é descartada e
main permanece inalterada.

**Rollback rápido:** `git checkout main && git branch -D feature/spec-002-v3-simplification`.

### 9.2 Estimativa de Esforço

| Fase | Passos | Esforço estimado |
|------|--------|-----------------|
| Fase 1: Remoção | 4 | 1-2 dias |
| Fase 2: Simplificação | 8 | 3-5 dias |
| Fase 3: Atualização | 4 | 1-2 dias |
| Fase 4: Validação | 4 | 2-3 dias |
| **Total** | **20** | **7-12 dias (1.5-2.5 semanas)** |

### Fase 1: Remoção (arquivos obsoletos)

1. Deletar scripts: `meta_analysis.py`, `grade.py`, `living_review.py`,
   `protocol_registry.py`, `index_sources.py`, `stage_output.py`,
   `bootstrap_config.py`.
2. Deletar references: `epistemology.md`, `grade-framework.md`,
   `press-checklist.md`, `epistemic-limitations.md`, `anti-patterns.md`,
   `context-budget.md`, `model-matrix.md`, `placeholders.md`.
3. Deletar templates: `local-corpus-triage.md`, `opensource-decision.md`,
   `devils-advocate.md`, `stakeholder-review.md`, `plain-summary.md`,
   `decision-brief.md`, `data-supplement.json`.
4. Rodar `smoke_test.py` e ajustar para refletir nova estrutura.

### Fase 2: Simplificação (arquivos mantidos)

5. Reescrever `SKILL.md` (~220 linhas, 5 estágios).
6. Reescrever `references/pipeline-detail.md` (~330 linhas).
7. Simplificar `references/deep-reading.md` (~200 linhas).
8. Simplificar `references/risk-of-bias.md` (~60 linhas).
9. Simplificar `references/error-recovery.md` (~40 linhas, absorver 5 anti-patterns).
10. Reescrever `references/subagent-prompts.md` (~80 linhas, 2 sub-agents).
11. Simplificar `scripts/helpers.py` (~150 linhas).
12. Reescrever `scripts/prompts.py` (~200 linhas, 2 builders).

### Fase 3: Atualização (documentação)

13. Atualizar templates mantidos (6 templates).
14. Atualizar `AGENTS.md`, `README.md`, `CHANGELOG.md`.
15. Remover `REVIEW-PHASE-1.md`, marcar `SPEC-001` como superseded.
16. Atualizar `IMPLEMENTATION-PLAN.md`.

### Fase 4: Validação

17. Rodar smoke test.
18. Executar pipeline completo com **3 RQs de natureza diferente**:
    - **RQ-A (bibliográfica pura):** "What is the state of the art in
      retrieval-augmented generation for code generation?"
    - **RQ-B (código puro):** "How is attention implemented in llama.cpp?"
    - **RQ-C (mista):** "How do different LLM serving frameworks handle
      KV cache eviction?"
19. Verificar todos os 5 gates no Close para cada RQ.
20. Revisar outputs finais para qualidade, comparando com baseline v2.x:
    - Número de claims V/E-grade extraídos por RQ.
    - Cobertura de subtópicos (avaliação qualitativa).
    - Tempo total de execução.

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Pipeline simplificado produz sínteses menos rigorosas | Média | A skill atual já admite que não é sistemática (L8). O rigor real vem da taxonomia V/P/I/M/E e T5, que são mantidos integralmente. Adversarial thinking pass no Stage 5 adiciona rigor sem complexidade. |
| Usuários sentem falta de meta-análise/GRADE | Baixa | Features podem ser readicionadas como skills separadas se houver demanda real. Migração: usuários de v2.x que dependem destas features devem permanecer na tag `v2.x-last` até que plugins equivalentes existam. |
| Remoção de crash recovery causa perda de trabalho em sessões longas | Média | O pipeline de 5 estágios salva outputs após cada stage (arquivos `.md`). Se interrompido, o orquestrador retoma do último stage com output completo. Instrução explícita no SKILL.md: "If interrupted, resume from the last completed stage output file." |
| Sub-agents simplificados perdem cobertura | Baixa | Bibliografia + codebase cobrem o caso de uso alvo. Web, opensource e grey literature eram overkill. |
| Context budget estoura no Stage 4 com 10 deep reads | Média | Mitigação em duas camadas: (a) saturation heuristic interrompe early se fontes forem redundantes, (b) batch compaction após cada 3 fontes T3/T4. |
| Clone de repositórios arbitrários é operação de risco | Baixa | Verificação de existência prévia, `--depth 1 --single-branch`, timeout 120s, nota sobre `.gitignore`. |

---

## 11. Critérios de Aceitação

- [ ] SKILL.md ≤ 250 linhas
- [ ] Total de arquivos ≤ 20 (vs. 40+ atuais)
- [ ] Pipeline executa em ≤ 5 estágios + Close
- [ ] Todos os 5 gates passam em uma execução completa para cada RQ de validação
- [ ] Taxonomia V/P/I/M/E preservada integralmente
- [ ] T5 source code reading preservado integralmente
- [ ] Iron Rule C enforcement mantido (com regex de contexto ±1 sentença)
- [ ] Nenhum arquivo de referência ou script referenciado no SKILL.md está ausente
- [ ] Smoke test passa
- [ ] Métricas de qualidade comparáveis com baseline v2.x:
  - Claims V/E-grade ≥ 80% do baseline para mesma RQ
  - Cobertura de subtópicos equivalente ou superior (qualitativo)
  - Tempo total de execução ≤ 60% da versão atual
- [ ] `protocol-freeze.json` é gerado e contém SHA256 verificável do `01-rq-brief.md`
- [ ] Deep reading respeita RLM lifecycle contract (abre ≤ 1 session, fecha em cleanup)
- [ ] Clone de repositórios não sobrescreve diretórios existentes sem `--ff-only`

---

## 12. Migração para Usuários da v2.x

Usuários que dependem de features removidas na v3.0 têm as seguintes opções:

| Feature removida | Alternativa na v3.0 | Plano futuro |
|------------------|---------------------|-------------|
| Meta-análise (DerSimonian-Laird, forest plots) | Não disponível | Skill separada `deepseek-meta-analysis` se houver ≥3 usuários solicitando |
| GRADE certainty framework | Substituído por STRONG/MODERATE/WEAK | Não planejado; GRADE não é validado para CS |
| PRISMA flow diagram completo | Tabela simplificada de 1 linha no source-inventory | Template PRISMA como skill separada se demandado |
| Dual screening + Cohen's κ | Methodological Note em report.md | Não planejado; single-reviewer é admissível para rapid evidence assessment |
| OSF/Zenodo pre-registration automática | `protocol-freeze.json` local (registro manual pelo usuário) | Reintegração futura se API de registro simplificar |
| Living review (surveillance) | Re-execução manual do pipeline | Skill separada `deepseek-living-review` se houver demanda |
| Decision brief standalone | Executive Summary no topo do report.md | Suficiente para 90% dos casos |
| Data supplement JSON | Structured Data table no report.md | Re-extração programática se necessário |

Usuários que precisam manter acesso às features removidas devem permanecer na tag
`v2.x-last` (criada antes do merge da v3.0). A branch `main` continuará acessível
para consulta e patches de segurança na v2.x por 6 meses após o release da v3.0.
