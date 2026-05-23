# Pipeline Detail Reference

Carregado pelo orquestrador em cada estágio quando o SKILL.md enxuto diz
"Ver `references/pipeline-detail.md` §Stage N para instruções detalhadas."

## Estágios (5 + Close)

```
Stage 1: RQ Formulation
Stage 2: Source Discovery (bibliography + codebase)
Stage 3: Source Verification
Stage 4: Deep Reading
Stage 5: Synthesis + Report
Close:   Verification (5 gates)
```

---

## Stage 1: RQ Formulation

**Quem:** Orquestrador (Pro)
**Output:** `01-rq-brief.md`, `protocol-freeze.json`

1. Obter RQ via `request_user_input` ou do prompt do usuário.
2. Extrair tópicos:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from topic_extractor import extract_topics, topics_to_csv; topics = extract_topics('{RQ_TEXT}'); print(topics_to_csv(topics))")
   ```
   Armazenar como `{topics}` para Stage 2.
3. Extrair `main_topic` do primeiro tópico ou da RQ.
4. Classificar escopo:
   - Se a RQ menciona código-fonte, repositórios ou implementações → ativar codebase.
   - Se menciona papers, literatura ou teoria → ativar bibliography.
   - Default: ambos (`["bibliography", "codebase"]`).
5. Derivar 3-5 sub-questions da RQ.
6. Definir critérios de inclusão/exclusão:
   - Inclusão: peer-reviewed, código aberto, data recente, relevante.
   - Exclusão: paywall, língua inacessível, fora do escopo.
7. Ler template `{SKILL_DIR}/templates/rq-brief.md` via `read_file`.
8. Preencher e escrever `01-rq-brief.md` via `write_file`.
9. Calcular SHA256:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_sha256; print(compute_sha256('{session_dir}/01-rq-brief.md'))")
   ```
10. Gerar `protocol-freeze.json`:
    ```json
    {
      "protocol_version": "3.0",
      "rq_sha256": "{rq_sha256}",
      "rq_text": "{RQ_TEXT}",
      "timestamp_utc": "{iso8601_utc}",
      "source_axes": {source_axes},
      "sub_questions": ["{SQ1}", "{SQ2}", "..."],
      "inclusion_criteria": "..." ,
      "exclusion_criteria": "..."
    }
    ```

---

## Stage 2: Source Discovery

**Quem:** 2 sub-agents Flash (bibliography + codebase) + Orquestrador
**Output:** `02-source-inventory.md`

### 2.1 Bibliografia

Gerar prompt via helpers.py:
```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-bibliography', rq_text='{RQ_TEXT}', bibliography_path='{bibliography_path}', main_topic='{main_topic}', topics='{topics}'))")
```

Dispatch:
```
agent_open(name="dsr-bibliography", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","web_search","fetch_url","write_file"],
  prompt=<output>)
agent_eval(agent_id="...", block=true, timeout_ms=180000)
read_file("/tmp/dsr-bibliography-results.md")
```

O sub-agent:
- Busca em `{bibliography_path}` via `grep_files` + `read_file`.
- Busca web via `web_search` + `fetch_url`.
- Executa queries de limitações: "limitations of {T}", "criticism of {T}",
  "failure cases of {T}" para cada tópico.
- Escreve output COMPLETO em `/tmp/dsr-bibliography-results.md`.

### 2.2 Codebase

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-code', rq_text='{RQ_TEXT}'))")
agent_open(name="dsr-code", model="deepseek-v4-flash",
  allowed_tools=["grep_files","read_file","file_search","write_file"],
  prompt=<output>)
agent_eval(agent_id="...", block=true, timeout_ms=180000)
read_file("/tmp/dsr-code-results.md")
```

O sub-agent faz `grep_files` com padrões derivados da RQ e `read_file` dos
arquivos com matches.

### 2.3 Consolidação

1. Parsear ambos os outputs.
2. Merge → deduplicação (por URL/path).
3. Atribuir IDs: S1, S2, S3, ...
4. Tabela de fluxo PRISMA-style:
   ```
   Identified: {TOTAL} → After dedup: {DEDUPED} → Selected for verification: {P}
   ```
5. Preencher template `source-inventory.md` e escrever.

**Tabela de fontes:** ID | Título | Tipo (paper/código/doc) | Relevância (1-5) | Why

---

## Stage 3: Source Verification

**Quem:** Orquestrador (Pro)
**Output:** `03-source-verification.md`

1. Para cada fonte em `02-source-inventory.md`:
   a. Verificar acessibilidade: URL → `fetch_url`, arquivo → `read_file`.
      Se 404/403/timeout → "UNVERIFIABLE".
   b. Classificar tipo: paper / código / documentação / repositório.
   c. Classificar como primary / secondary / tertiary.

2. Risk of bias (ver `{SKILL_DIR}/references/risk-of-bias.md`):
   - **Papers:** 4 perguntas.
   - **Código:** 3 perguntas.
   - Rating: Low / Medium / High. Pior domínio define overall.

3. Preencher template `source-verification.md`:
   - Verification Summary table.
   - Credibility Matrix (source-level).
   - RoB Summary Table.
   - Detailed RoB por fonte (se Some concerns ou High).
   - Unverifiable Sources.
   - Excluded Sources.

---

## Stage 4: Deep Reading

**Quem:** Orquestrador (Pro)
**Output:** `deep-reads/{source_id}.md`

### 4.1 Priorização

Ordenar fontes verificadas por relevância (desc). Selecionar top `max_deep_reads`.

### 4.2 Processamento sequencial

Para cada fonte (da maior relevância para menor):

**Papers (T1-T4):**

| Tier | Tamanho | Método |
|------|---------|--------|
| T1 | < 5KB | `read_file` direto |
| T2 | 5-50KB | `read_file` paginado (2-3 leituras) |
| T3 | 50-200KB | `rlm_open` → chunk(8K, overlap=1K) → batch → `rlm_close` |
| T4 | > 200KB | Leitura seletiva: ToC → intro/conclusion → seções relevantes |

**RLM contract para T3/T4:**
```
rlm_open(name="dr-{source_id}", file_path="{source_path}")
rlm_configure(name="dr-{source_id}", output_feedback="metadata")
rlm_eval(name="dr-{source_id}", code="chunks = chunk(chunk_size=8000, overlap=1000); finalize({'n_chunks': len(chunks), 'chunks': chunks})")

# Processar claims:
rlm_eval(name="dr-{source_id}", code="""
results = sub_query_batch(
    queries=[f"Extract all claims relevant to RQ '{rq_text}' from this text. For each claim, provide: (a) verbatim quote, (b) evidence grade (V/P/I/M), (c) section reference. Text: {chunk}" for chunk in chunks],
    dependency_mode="independent",
    safety_note="Each chunk is from the same document but processed independently — no cross-chunk dependencies."
)
finalize(results)
""")

rlm_close(name="dr-{source_id}")
```

**Código (T5):**
1. Clone: `exec_shell("git clone --depth 1 --single-branch {repo_url} {oss_clone_dir}/{org}_{repo}/")`. Se já existe: `git pull --ff-only`. Timeout 120s.
2. `grep_files` com padrões da RQ.
3. `read_file` dos arquivos com matches.
4. Extrair claims E-grade com file:line reference.
5. Executar `exec_shell("cd {oss_clone_dir}/{org}_{repo} && git rev-parse HEAD")` → commit hash.
6. Adicionar `oss/` ao `.gitignore` se ausente.

### 4.3 Saturação

Após cada 3 deep reads concluídas:
```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_saturation; print(compute_saturation('{session_dir}/deep-reads/', '{RQ_TEXT}', last_n=2))")
```
Se retornar `True` (últimas 2 fontes sem claims V/E novos) → interromper.

### 4.4 Output

Cada fonte gera `deep-reads/{source_id}.md` com:
- Metadata (source_id, tier, chunking, commit hash se T5).
- Extracted Claims table (verbatim quote + grade + section ref).
- Internal Consistency (0 ou N issues).
- Mathematical Claims (se houver M-grade).
- Sections Skipped (T4 only).
- Overall Assessment: COMPREHENSIVE / PARTIAL / MINIMAL.

### 4.5 Context budget

- Processar T3/T4 em batches de 3 fontes.
- Após cada batch, se > 70% do budget → `/compact` e continuar.

---

## Stage 5: Synthesis + Report

**Quem:** Orquestrador (Pro)
**Output:** `04-synthesis.md`, `05-report.md`

### 5.1 Synthesis

1. Listar e ler todos os `deep-reads/{source_id}.md`.
2. Extrair todas as claims tables.
3. Cross-reference:
   - Mesma claim em múltiplas fontes → convergente.
   - Claims contraditórios → registrar conflito.
   - Claim único → anotar "single-source".
4. **Adversarial thinking pass:**
   - Para cada finding: existe evidência contrária? (procurar nos claims de
     fontes com baixa relevância ou nas queries negativas do Stage 2).
   - O claim é corroborado por ≥2 fontes independentes?
   - Há viés de seleção? (todas as fontes do mesmo grupo/lab/ano?)
5. Classificar: STRONG / MODERATE / WEAK.
6. Cada finding cita ≥1 quote verbatim com source_id + section.
7. Escrever `04-synthesis.md` via template.

### 5.2 Report

1. Ler `04-synthesis.md`.
2. Carregar `{SKILL_DIR}/templates/report.md`.
3. Escrever Executive Summary (4-6 parágrafos no topo).
4. Preencher Key Findings com qualified language (Iron Rule C).
5. Structured Data: tabela de constantes numéricas + algoritmos.
6. Methodological Note: 3-4 parágrafos honestos sobre:
   - Escopo: rapid evidence assessment, não revisão sistemática.
   - Viés: single-reviewer, LLM-based judgment, possible selection bias.
   - Limitações: cobertura temporal, idioma, acessibilidade.
   - Confiança: confidence labels são orientações, não medidas estatísticas.
7. Escrever `05-report.md`.

---

## Close: Verification

**Output:** `MANIFEST.txt`

### Procedimento

1. Criar `MANIFEST.txt` com header.
2. Executar cada gate:

**GATE-1 (File integrity):** `list_dir("{session_dir}")` → verificar 8 arquivos.

**GATE-2 (IRON RULE C):**
```
grep_files(pattern="\\b(validated|proved|confirmed|demonstrated|ensures|guarantees|always|never|optimal|definitive|conclusive|certainly|undoubtedly|obviously|clearly)\\b", path="{session_dir}/")
```
Para cada match, verificar qualificação. Reportar violações.

**GATE-3 (Textual evidence):** Verificar se claims STRONG em `04-synthesis.md` e
`05-report.md` têm citação V-grade ou E-grade.

**GATE-4 (RoB completeness):** Verificar `03-source-verification.md` — toda fonte
acessível tem RoB rating.

**GATE-5 (Placeholder resolution):**
```
grep_files(pattern="\\{[A-Za-z_]+\\}", path="{session_dir}/")
```
Zero matches esperados.

3. Registrar resultados em `MANIFEST.txt` sob `## Gate Results`.
4. Pipeline completo.
