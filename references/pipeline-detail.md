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

### 3.0 Title Match Gate (GATE-0)

**Objetivo:** Detectar fontes cuja URL foi fabricada pelo sub-agente (ex: arXiv
ID que não corresponde ao paper alegado). Toda fonte com URL DEVE ser verificada
antes de ser considerada ACCESSIBLE.

**Procedimento por fonte:**
```
Para cada fonte com URL:
  1. fetch_url("{url}") — verificar HTTP status.
  2. Extrair o título da página:
     - HTML: primeiro <h1> ou <title>
     - PDF (se arxiv.org/pdf/...): título da primeira página extraído
  3. Comparar com o título reportado no 02-source-inventory.md.
     Critério de match: ≥50% das palavras com 5+ caracteres do título
     reportado aparecem no título da página (case-insensitive, ignorando
     stopwords: "a", "an", "the", "of", "in", "on", "to", "for", "and",
     "with", "using", "via", "from"). Exemplo:
       - Reportado: "ChatQA 2: Bridging the Gap to GPT-4"
       - Página: "ChatQA 2: Bridging the Rag to GPT-4V"
       - Palavras-chave do reportado: chatqa, bridging, gap (3 palavras)
       - Match: "chatqa", "bridging" vs "chatqa", "bridging", "rag" → 2/3 = 67% → MATCH
     a. Match: ACCESSIBLE.
     b. Mismatch: HALLUCINATED — remover fonte da tabela ativa e registrar
        em "## Title Mismatch Detection" com:
        | Source ID | Reported URL | Actual content | Resolution |
     c. 404/403/Timeout: UNVERIFIABLE
  4. Fontes sem URL (arquivos locais, código): verificar via read_file.
```

**⚠ A categoria "ACCESSIBLE (inferred)" está abolida.** Se uma fonte não pôde
ser verificada (ex: busca web rate-limited), ela é UNVERIFIABLE, não "inferred
accessible". O orquestrador NÃO DEVE inferir acessibilidade com base em
confiança no repositório (ex: "arxiv é confiável").

### 3.1 Full-Text PDF Acquisition — Batch (SPEC-003)

**Uma única chamada** processa todas as fontes paper do inventory.
DOI e arXiv ID são extraídos automaticamente via regex do texto das linhas.

```
code_execution(code='''
import sys, json; sys.path.insert(0, "{SKILL_DIR}/scripts")

_allow_scihub_raw = "{allow_scihub}"
try:
    allow_scihub = {"true": True, "false": False}[_allow_scihub_raw.strip().lower()]
except (KeyError, AttributeError):
    allow_scihub = False

from fulltext import resolve_all_fulltext
result_json = resolve_all_fulltext(
    inventory_path="{session_dir}/02-source-inventory.md",
    output_dir="{session_dir}/pdfs/",
    unpaywall_email="{unpaywall_email}",
    allow_scihub=allow_scihub,
)
result = json.loads(result_json)
print(f"Total: {result['summary']['total']} | "
      f"arxiv: {result['summary'].get('arxiv', 0)} | "
      f"oa: {result['summary'].get('oa', 0)} | "
      f"unavailable: {result['summary'].get('unavailable', 0)}")

# Salvar mapping para Stage 4
with open("{session_dir}/pdfs/mapping.json", "w") as f:
    json.dump(result, f, indent=2)
''')
```

**Extração automática:** `resolve_all_fulltext()` usa regex para encontrar
DOI (`10.XXXX/...`) e arXiv ID (`arXiv:YYMM.NNNNN`) no texto de cada linha
do inventory. Fontes com type != "paper" são puladas.

**Cadeia de fallback por fonte:**
1. **arXiv PDF:** `GET https://arxiv.org/pdf/{id}.pdf` → salvar → `read_file`
2. **Unpaywall API:** `GET https://api.unpaywall.org/v2/{doi}?email={email}`
   → extrair `best_oa_location.url_for_pdf` → baixar PDF
3. **Sci-Hub (opt-in):** `GET https://sci-hub.{domain}/{doi}` → extrair URL

**Config necessária:**
```toml
# .deepseek/deepseek-research.toml
unpaywall_email = "researcher@example.com"  # requerido para Unpaywall
allow_scihub = false                         # default: off
scihub_domain = ""                           # auto-detect if empty
```

**Tratamento de bordas:** 403/Cloudflare → UNVERIFIABLE; PDF > 50MB → skip;
PDF scaneado → FAILED; Captcha Sci-Hub → próximo domínio → UNVERIFIABLE.

**Resultado:** `pdfs/mapping.json` mapeia source_id → {pdf_path, status, method}.
O Stage 4 lê este arquivo para decidir entre `read_file(pdf_path)` e fallback.

**Evasão de detecção (bot):** `fulltext.py` usa headers Chrome 132 Linux,
delay 1.5-4.0s entre requests, timeout 30s.

### 3.2 Credibility + Risk of Bias

1. Para cada fonte verificada:
   a. Classificar tipo: paper / código / documentação / repositório.
   b. Classificar como primary / secondary / tertiary.

2. Risk of bias (ver `{SKILL_DIR}/references/risk-of-bias.md`):
   - **Papers:** 4 perguntas.
   - **Código:** 3 perguntas.
   - Rating: Low / Medium / High. Pior domínio define overall.

3. Preencher template `source-verification.md`:
   - Verification Summary table.
   - Credibility Matrix (source-level) — coluna Status: ACCESSIBLE | UNVERIFIABLE | HALLUCINATED | EXCLUDED.
   - RoB Summary Table.
   - **Title Mismatch Detection** (fontes HALLUCINATED).
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
