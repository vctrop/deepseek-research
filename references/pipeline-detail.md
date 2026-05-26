# Pipeline Detail Reference

Carregado pelo orquestrador em cada estágio quando o SKILL.md enxuto diz
"Ver `references/pipeline-detail.md` §Stage N para instruções detalhadas."

## Estágios (5 + Close + Indexing)

```
Phase 0:  Index Bootstrap
Stage 1:  RQ Formulation
Phase 1.5: Local Corpus Triage
Stage 2:  Source Discovery (bibliography + codebase)
Stage 3:  Source Verification
Stage 4:  Deep Reading
Stage 5:  Synthesis + Report
Close:    Persistence + Verification
```

---

## Phase 0: Index Bootstrap + Config Check

**Quem:** Orquestrador (Pro)
**Output:** `bibliography/index/sources.json`, `.deepseek/deepseek-research.toml`

1. `config_ensure()` — verifica se `.deepseek/deepseek-research.toml` existe
   e contém todas as 10 chaves. Cria o arquivo se ausente; adiciona chaves
   faltantes com defaults se incompleto. Nunca sobrescreve valores existentes.
2. `init_sources()` — idempotente, cria `bibliography/` e `bibliography/index/`
   com `sources.json` vazio (`[]`) se não existirem.
3. `scan_unindexed()` — varre `bibliography/` por arquivos não indexados.
4. Se encontrados: notificar usuário com contagem.
5. Prosseguir silenciosamente se tudo ok.

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

## Phase 1.5: Local Corpus Triage

**Quem:** Orquestrador (Pro)
**Output:** `local_sources_json` (passado para o sub-agent dsr-bibliography em Stage 2)

1. Rodar `query_sources()` com keywords extraídos dos tópicos da RQ:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from index_sources import query_sources; from pathlib import Path; import json; result = query_sources(Path('{bibliography_path}'), '{topics}'.split(','), top_n=10); print(json.dumps(result, indent=2))")
   ```
2. O JSON output é `{local_sources_json}` — array de entries com `id`, `title`,
   `path`, `keywords`, `summary`, `year`, `doi`.
3. Se vazio (`[]`): pular, sub-agent dsr-bibliography roda sem contexto local.
4. Se houver matches: injetar no prompt do `dsr-bibliography` via
   `local_sources_json={local_sources_json}`.

---

## Stage 2: Source Discovery

**Quem:** 2 sub-agents Flash (bibliography + codebase) + Orquestrador
**Output:** `02-source-inventory.md`

### 2.1 Bibliografia

Gerar prompt via helpers.py (com `local_sources_json` se disponível):
```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-bibliography', rq_text='{RQ_TEXT}', bibliography_path='{bibliography_path}', main_topic='{main_topic}', topics='{topics}', local_sources_json='{local_sources_json}'))")
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
5. Preencher template `source-inventory.md` como draft (`02-source-inventory-draft.md`).

6. **Enforce source caps (antes de escrever o inventory final):**
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from enforce_source_caps import enforce_caps; import json; result = enforce_caps('{session_dir}/02-source-inventory-draft.md', max_per_axis={max_sources_per_axis}); print(json.dumps(result, indent=2))")
   ```
   Se fontes foram removidas:
   - Truncar a tabela ativa no inventory final às fontes kept.
   - Registrar fontes removidas em seção `## Cap Enforcement`.
   - Remover o draft: `exec_shell("rm {session_dir}/02-source-inventory-draft.md")`.
   Se nenhuma fonte removida: renomear draft → final.

**Tabela de fontes:** ID | Título | Tipo (paper/código/doc) | DOI | Relevância (1-5) | Why

**Captura de DOI (obrigatório para papers):** o sub-agent dsr-bibliography DEVE
extrair o DOI de cada paper (meta tags, página arXiv, ou texto visível) e
preenchê-lo na coluna dedicada. Usar `N/A` quando genuinamente indisponível.
Nunca fabricar DOIs. Esta coluna é consumida pelo `resolve_all_fulltext()` no
Stage 3.1 para habilitar shadow libraries e Unpaywall.

---

## Stage 3: Source Verification

**Quem:** Orquestrador (Pro)
**Output:** `03-source-verification.md`

### 3.0 Title Match Gate (GATE-0)

**Objetivo:** Detectar fontes cuja URL foi fabricada pelo sub-agente (ex: arXiv
ID que não corresponde ao paper alegado). Toda fonte com URL DEVE ser verificada
antes de ser considerada ACCESSIBLE.

**Caminho preferencial: Sub-agent Flash (dsr-verify-titles)**
Para 5+ fontes com URL, descarregue a verificação em lote para um sub-agent Flash:

```
# 1. Extrair fontes com URL do inventory
code_execution(code="import sys, json; sys.path.insert(0, '{SKILL_DIR}/scripts'); from verify_title_match import _extract_sources_with_url; from pathlib import Path; sources = _extract_sources_with_url(Path('{session_dir}/02-source-inventory.md')); print(json.dumps([{{'source_id': k, 'reported_title': v.get('reported_title', ''), 'url': v.get('url', '')}} for k, v in sources.items()], indent=2))")

# 2. Gerar prompt e disparar sub-agent
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import build_subagent_prompt; print(build_subagent_prompt('dsr-verify-titles', source_list_json='<JSON da etapa 1>'))")
agent_open(name="dsr-verify-titles", model="deepseek-v4-flash", allowed_tools=["fetch_url", "write_file"], prompt=<output>)
agent_eval(agent_id="...", block=true, timeout_ms=900000)

# 3. Copiar resultados para a sessão
read_file("/tmp/dsr-verify-results.md")  # ou fetch do JSON
write_file("{session_dir}/03-gate0-results.json", content=<JSON copiado>)
```

**Caminho manual (fallback para ≤4 fontes ou se Flash indisponível):**
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

### 3.0.1 Checkpoint JSON (OBRIGATÓRIO)

Após completar GATE-0 (por qualquer caminho), o orquestrador DEVE escrever
`{session_dir}/03-gate0-results.json` com o schema de checkpoint:

```json
{
  "gate": "GATE-0",
  "timestamp_utc": "{iso8601_utc}",
  "verifications": [
    {
      "source_id": "S1",
      "reported_title": "ChatQA 2: Bridging the Gap to GPT-4",
      "fetched_url": "https://arxiv.org/abs/2407.16833",
      "page_title": "ChatQA 2: Bridging the Rag to GPT-4V",
      "match_keywords_reported": ["chatqa", "bridging", "gap"],
      "match_keywords_found": ["chatqa", "bridging"],
      "match_pct": 66.7,
      "verdict": "MATCH",
      "notes": "Minor title variation (Rag vs Gap)"
    }
  ],
  "summary": {
    "total_with_url": 6,
    "match": 4,
    "mismatch": 1,
    "unverifiable": 1
  }
}
```

Este checkpoint é verificado deterministicamente por GATE-0b no Close phase.

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
print(f"Total: {result['summary']['total']} | "
      f"arxiv: {result['summary'].get('arxiv', 0)} | "
      f"oa: {result['summary'].get('oa', 0)} | "
      f"unavailable: {result['summary'].get('unavailable', 0)}")

# Salvar mapping para Stage 4
with open("{session_dir}/pdfs/mapping.json", "w") as f:
    json.dump(result, f, indent=2)
''')
```

**Extração automática:** `resolve_all_fulltext()` primeiro lê a coluna DOI
dedicada (formato novo: 6 colunas). Se a coluna contém um DOI válido ou `N/A`,
usa diretamente; caso contrário, faz fallback para regex no texto da linha
(busca por `10.XXXX/...` e `arXiv:YYMM.NNNNN`). Isso garante retrocompatibilidade
com inventories antigos (5 colunas, sem coluna DOI). Fontes com type != "paper"
são puladas. A captura de DOIs pelo sub-agent no Stage 2 é crítica: sem DOI,
shadow libraries e Unpaywall não podem ser acionados para fontes paywalled.

**Cadeia de fallback por fonte:**
1. **arXiv PDF:** `GET https://arxiv.org/pdf/{id}.pdf` → salvar
2. **Unpaywall API:** `GET https://api.unpaywall.org/v2/{doi}?email={email}`
   → extrair `best_oa_location.url_for_pdf` → baixar PDF
3. **Sci-Hub (opt-in):** `GET https://sci-hub.{domain}/{doi}` → extrair URL do PDF
4. **Library Genesis (opt-in):** `GET https://{domain}/scimag/json.php?doi={doi}`
   → extrair `download_url` ou construir via MD5 → baixar PDF
5. **Anna's Archive (opt-in):** HTML scraping em `annas-archive.org/search?q={doi}`
   → extrair link de download ou IPFS → baixar PDF
6. **Abstract via DOI:** `GET https://doi.org/{doi}` → extrair abstract de meta tags
   ou container estrutural (fallback mínimo, sempre ativo)

**Config necessária:**
```toml
# .deepseek/deepseek-research.toml
unpaywall_email = "researcher@example.com"  # requerido para Unpaywall
shadow_libraries = ["scihub", "libgen"]      # shadow libraries em ordem de fallback
scihub_domain = ""                           # auto-detect if empty
```

**Tratamento de bordas:** 403/Cloudflare → UNVERIFIABLE; PDF > 50MB → skip;
PDF scaneado → FAILED; página de login/paywall → abstract descartado;
Cloudflare JS challenge → shadow library retorna None e tenta próxima.

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

### 4.0 Paywall Circuit Breaker

Antes de tentar deep-read de qualquer fonte paper:

1. **PRIMEIRO:** consultar `pdfs/mapping.json` (gerado pelo Stage 3.1).
   - Se `status == "success"` e `pdf_path` existe → usar PDF para deep read.
   - Se `status == "unavailable"` ou `"paywall"` → fonte já foi considerada
     inacessível no Stage 3.1. NÃO re-tentar acesso. Marcar INACCESSIBLE.
   - Se `status == "abstract_only"` → deep read do abstract apenas; todos os
     claims serão I-grade (não V-grade). Marcar PARTIAL no header.

2. Se `pdfs/mapping.json` não existe ou não tem entrada para a fonte
   (fallback para inventários antigos):
   a. Verificar `03-source-verification.md` → status da fonte.
   b. Se UNVERIFIABLE por paywall → marcar INACCESSIBLE, pular.
   c. Se ACCESSIBLE mas requer autenticação (Nature, Elsevier, Springer):
      - Tentar até 3 rotas de acesso (fetch_url, Unpaywall, shadow library).
      - Se 3 falharem → marcar INACCESSIBLE, escrever deep-read com header
        "BLOCKED — Paywall" e prosseguir.
      - NUNCA delegar ao orquestrador "obter PDF via subscrição institucional".

3. **Circuit breaker global:** se ≥5 fontes consecutivas resultarem INACCESSIBLE,
   interromper Stage 4 — as fontes restantes provavelmente também são inacessíveis.
   Prosseguir para Stage 5 com as fontes processadas até agora.

4. Fontes INACCESSIBLE NÃO contam contra `max_deep_reads`. O cap se aplica a
   fontes efetivamente processadas (COMPREHENSIVE / PARTIAL / MINIMAL).
   INACCESSIBLE e FAILED são registradas mas não consomem vaga.
   Ex: max_deep_reads=10, 3 INACCESSIBLE, 10 processadas → total de 13 fontes
   visitadas, 10 efetivas.

### 4.1 RLM Sweep (Resume Safety)

Antes de abrir qualquer sessão RLM, executar sweep para fechar sessões órfãs
de execuções anteriores (crash, `/compact`, timeout externo):

```
# Para cada fonte no inventory que ainda não tem deep-read completo:
#   1. Tentar rlm_close(name="dr-{source_id}") — idempotente se já fechada.
#   2. Ignorar erro (sessão pode já ter sido fechada ou nunca ter existido).
#   3. Registrar no log: "RLM sweep: dr-{source_id} closed (was orphaned)"
#      ou "already closed".
```

Este sweep é seguro porque `rlm_close` em uma sessão já fechada é no-op ou
erro inócuo. Resolve o cenário de sessões RLM órfãs que bloqueiam a abertura
de novas sessões (máximo 1 sessão RLM ativa por vez).

### 4.2 Priorização

Ordenar fontes verificadas por relevância (desc). Selecionar top `max_deep_reads`.

### 4.2.0 Per-source Budget Guidelines

⚠ ESTA SEÇÃO É DOCUMENTAÇÃO, NÃO MECANISMO. O orquestrador (LLM) não tem
cronômetro interno e não pode medir wall-clock time. Os limites abaixo são
implementados indiretamente via timeouts de ferramentas (F-0, F-1) e devem
ser usados como referência para dimensionamento de timeouts, não como
gatilhos de interrupção.

Cada fonte tem um budget máximo de tempo, implementado via:
- T1/T2 (sem RLM): 3 minutos — via `read_file` sem timeout explícito
  (documentos pequenos não justificam wrapper)
- T3/T4 (com RLM): 10 minutos — via F-0 (`agent_eval` timeout_ms=600000)
  + F-1 (`sub_query_timeout_secs=120`)
- T5 (código, clone): 5 minutos — via `exec_shell` timeout 120s +
  `grep_files` + `read_file`

Regras comportamentais (enforced via design, não cronômetro):
1. NUNCA tentar reprocessar a mesma fonte na mesma sessão (sem retry loop).
2. Se F-0 retornar timeout → marcar FAILED, prosseguir.
3. Se F-1 retornar timeout → marcar FAILED, prosseguir.
4. Salvar output parcial antes de marcar FAILED (o que foi extraído até o timeout).

Os timeouts efetivos são:
- F-0: `agent_eval` com `timeout_ms=600000` (10 min) → teto por fonte T3/T4
- F-1: `sub_query_timeout_secs=120` (2 min) → teto por batch de queries
- `fetch_url` timeout 30s → 3 tentativas = 90s max (F-2)
- `exec_shell` clone timeout 120s

### 4.4 Processamento de fontes (modo preferencial: sub-agent wrapper)

**⚠ Arquitetura de isolamento de timeout:** O orquestrador é síncrono —
se uma tool call (`rlm_eval`, `agent_eval`) congela, o orquestrador inteiro
congela irreversivelmente. Para evitar isso, T3/T4 devem ser processadas via
sub-agents com timeout, isolando o RLM do loop principal.

**Modo preferencial — Sub-agent wrapper para T3/T4:**

```
Para cada fonte T3/T4:
  1. Orquestrador faz rlm_open no documento → obtém file_path/content
  2. Dispara sub-agent com timeout:
     agent_open(name="deep-read-{source_id}", model="deepseek-v4-pro",
       allowed_tools=["rlm_open","rlm_eval","rlm_configure","rlm_close",
                      "read_file","write_file","handle_read"],
       prompt="<instruções completas de deep read>")
     agent_eval(agent_id="...", block=true, timeout_ms=600000)
  3. Sub-agent executa: rlm_configure → chunk → sub_query_batch → write deep read
  4. Sub-agent que expira (timeout_ms=600000) → agent_close → fonte FAILED
  5. Orquestrador retoma controle após timeout e processa próxima fonte
  6. Fontes podem ser processadas em paralelo (até max_deep_reads sub-agents simultâneos)
```

**Benefícios:**
- Timeout de 10min por fonte — se travar, não bloqueia o orquestrador
- Fontes são processadas em isolamento — crash de uma não afeta outras
- `agent_close` + `rlm_close` são garantidos mesmo em timeout

**Fallback (modo direto, se rlm_eval indisponível para sub-agents):**

Para cada fonte (da maior relevância para menor):

**Papers (T1-T4):**

| Tier | Tamanho | Método |
|------|---------|--------|
| T1 | < 5KB | `read_file` direto |
| T2 | 5-50KB | `read_file` paginado (2-3 leituras) |
| T3 | 50-200KB | `rlm_open` → chunk(8K, overlap=1K) → batch → `rlm_close` |
| T4 | > 200KB | Leitura seletiva: ToC → intro/conclusion → seções relevantes |

No modo direto, o timeout depende exclusivamente de F-1 (`sub_query_timeout_secs=120`)
e o orquestrador está vulnerável a hangs do `rlm_eval` pai. Use o modo preferencial
sempre que possível.

**RLM contract para T3/T4 (com cleanup em todos os paths):**
```
# 1. Abrir sessão RLM
rlm_open(name="dr-{source_id}", file_path="{source_path}")
# Se rlm_open retornar erro → fonte INACCESSIBLE, próximo.

# 2. Configurar timeout
rlm_configure(name="dr-{source_id}", output_feedback="metadata", sub_query_timeout_secs=120)

# 3. Chunking
rlm_eval(name="dr-{source_id}", code="chunks = chunk(chunk_size=8000, overlap=1000); finalize({'n_chunks': len(chunks), 'chunks': chunks})")
# Detecção de falha:
# - Se rlm_eval retornar erro → rlm_close IMEDIATAMENTE, fonte FAILED
# - Se handle_read retornar None → rlm_close IMEDIATAMENTE, fonte FAILED
# - Se n_chunks == 0 → rlm_close, fonte FAILED (documento vazio/ilegível)

# 4. Processar claims via sub_query_batch
rlm_eval(name="dr-{source_id}", code="""
results = sub_query_batch(
    queries=[f"Extract all claims relevant to RQ '{rq_text}' from this text. For each claim, provide: (a) verbatim quote, (b) evidence grade (V/P/I/M), (c) section reference. Text: {chunk}" for chunk in chunks],
    dependency_mode="independent",
    safety_note="Each chunk is from the same document but processed independently — no cross-chunk dependencies."
)
finalize(results)
""")
# Detecção de falha:
# - rlm_eval retorna erro → rlm_close IMEDIATAMENTE, fonte FAILED
# - handle_read retorna None → rlm_close IMEDIATAMENTE (timeout ou crash do RLM)
# - results é lista vazia → warning (documento sem claims relevantes; não é falha)

# 5. EM QUALQUER PATH (sucesso, falha, timeout): FECHAR A SESSÃO
rlm_close(name="dr-{source_id}")
```

**⚠ Detecção de falha do RLM:**
- `rlm_eval` retorna status de erro → `rlm_close` IMEDIATAMENTE.
- `handle_read` do resultado retorna `None` → `rlm_close` IMEDIATAMENTE
  (indica que o RLM não produziu output — timeout ou crash interno).
- Nunca tente reabrir a mesma sessão. Crie uma nova (`dr-{source_id}-retry`)
  se necessário.
- Máximo 1 sessão RLM ativa por vez. Sempre fechar no cleanup em caso de erro.

**Código (T5):**
1. Clone: `exec_shell("git clone --depth 1 --single-branch {repo_url} {oss_clone_dir}/{org}_{repo}/")`. Se já existe: `git pull --ff-only`. Timeout 120s.
2. `grep_files` com padrões da RQ.
3. `read_file` dos arquivos com matches.
4. Extrair claims E-grade com file:line reference.
5. Executar `exec_shell("cd {oss_clone_dir}/{org}_{repo} && git rev-parse HEAD")` → commit hash.
6. Adicionar `oss/` ao `.gitignore` se ausente.

### 4.5 Saturação

Após cada 3 deep reads concluídas:
```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_saturation; print(compute_saturation('{session_dir}/deep-reads/', '{RQ_TEXT}', last_n=2))")
```

**Checkpoint de saturação em disco (sempre escrever, independente do resultado):**
```
write_file("{session_dir}/deep-reads/_saturation_check.md", content=f"""# Saturation Check

**Timestamp:** {iso8601_utc}
**Deep reads completed:** {n_completed}
**Saturation reached:** {result}
**Action:** {"STOP — proceed to Stage 5" if result else "CONTINUE — process next batch"}
""")
```

Se saturação atingida → interromper Stage 4 e prosseguir para Stage 5.
Se não → continuar para próximo batch de 3 fontes.

**Checkpoint final:** Ao término do Stage 4 (seja por saturação, `max_deep_reads`
atingido, ou circuit breaker global), escrever checkpoint final com todas as
fontes processadas. Isso garante que `stage_status.py` detecta conclusão mesmo
se o último batch teve <3 fontes.

### 4.6 Output

Cada fonte gera `deep-reads/{source_id}.md` com:
- Metadata (source_id, tier, chunking, commit hash se T5).
- Extracted Claims table (verbatim quote + grade + section ref).
- Internal Consistency (0 ou N issues).
- Mathematical Claims (se houver M-grade).
- Sections Skipped (T4 only).
- Overall Assessment: COMPREHENSIVE / PARTIAL / MINIMAL.

### 4.7 Context budget

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
7. **5b. Write 2-3 paragraphs of session-specific limitations** for the
   `{session_specific_limitations}` placeholder in the Methodological Note:
   - How many sources were paywalled/inaccessible?
   - Which axes failed or underperformed?
   - Any sub-agent failures or timeouts?
   - Any sources downgraded due to coverage or access method?
   - Any mathematical claims requiring human verification?
   Be concrete. Do not reuse generic language from the template.

   Example of good session-specific limitations:
   > **This session:** 3 of 12 bibliography sources were paywalled
   > (Springer, Elsevier) and only abstracts were available. The Sci-Hub
   > fallback was disabled. The codebase axis failed because the primary
   > repository was private. Source S4 was downgraded from V-grade to
   > I-grade because only 23% of the document was processed (T4 selective
   > reading). Finding K3 contains mathematical claims (M-grade) that
   > require human verification.

8. Escrever `05-report.md`.

---

## Close: Persistence + Verification

**Output:** `MANIFEST.txt`, `SESSION-INDEX.md`, `bibliography/index/sources.json`

### Persistência de Corpus

Após Stage 5, persistir fontes usadas no relatório que passaram no Stage 3:

1. **Fontes novas (web-discovered):** para cada fonte nova usada no `05-report.md`,
   chamar `add_source()` com o arquivo PDF/markdown e os metadados (id, title,
   authors, year, doi, keywords, summary, quality_level, source_type).
2. **Fontes locais reutilizadas:** chamar `update_sessions()` para cada fonte
   local usada, registrando `{session_slug}` em `sessions_used`.
3. **SESSION-INDEX.md:** append de uma linha com date, slug, target, mode, e
   key findings (≤280 chars). Criar o arquivo com header row se não existir.
4. Emitir resumo: "Corpus updated: X new, Y reused."
5. **Pipeline Metrics:** anexar ao MANIFEST.txt:
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from pipeline_metrics import compute
print(compute("{session_dir}"))
''')
```

### Verification Gates

1. Criar `MANIFEST.txt` com header.
2. Executar cada gate:

**GATE-1 (File integrity):** `list_dir("{session_dir}")` → verificar 8 arquivos.

**GATE-2 (IRON RULE C — determinístico):**
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

**GATE-3 (Textual evidence):** Verificar se claims STRONG em `04-synthesis.md` e
`05-report.md` têm citação V-grade ou E-grade.

**GATE-4 (RoB completeness):** Verificar `03-source-verification.md` — toda fonte
acessível tem RoB rating.

**GATE-5 (Placeholder resolution):**
```
grep_files(pattern="\\{[A-Za-z_]+\\}", path="{session_dir}/")
```
Zero matches esperados.

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

**GATE-0b (Title Match Checkpoint):**
```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_title_match import check
print(check("{session_dir}"))
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

3. Registrar resultados em `MANIFEST.txt` sob `## Gate Results`.
4. Pipeline completo.
