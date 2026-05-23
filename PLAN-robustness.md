# Plano de Robustez — Correções de Confiabilidade do Pipeline

**Branch:** `analysis/bibliography-pdf-collection`
**Data:** 2026-05-23
**Status:** Plano de implementação

---

## Diagnóstico Consolidado

Três classes de falha encontradas nos relatórios existentes:

| # | Classe | Evidência | Impacto |
|---|--------|----------|---------|
| C1 | **URLs/IDs fabricados** | S6: arXiv 2407.14476 (paper de matemática) em vez de 2407.14482 (ChatQA 2) | Fonte inexistente entra na síntese |
| C2 | **Verificação pulada** | 19/25 fontes "ACCESSIBLE (inferred)" — zero `fetch_url` | Conteúdo real nunca confirmado |
| C3 | **Deep reads superficiais** | W2/W3/W4: 3 claims cada, boilerplate idêntico, ~26 linhas | Claims STRONG baseados em abstracts |

Causa-raiz comum: **o pipeline confia cegamente na saída de sub-agentes Flash**, delegando verificação para um orquestrador que também é LLM e também alucina.

---

## Correções (6 frentes, ordenadas por impacto)

### FRENTE 1 — GATE-0: Title Match Verification

**Arquivos:** `SKILL.md` (Stage 3), `references/pipeline-detail.md` (Stage 3)

**Regra:** Toda fonte com URL deve ter seu título verificado antes de ser considerada ACCESSIBLE.

**Protocolo:**
```
Para cada fonte com URL:
  1. fetch_url(url) → extrair título da página
  2. Comparar com título reportado pelo sub-agente
  3. Se mismatch → flag HALLUCINATED, remover da tabela, registrar
  4. Se 404/403/timeout → UNVERIFIABLE
  5. Se OK + título bate → ACCESSIBLE
```

**Mudança no SKILL.md Stage 3, após o item 1 atual:**
```markdown
### 3.1 Title Match Gate (GATE-0)

Para cada fonte com URL:
1. `fetch_url("{url}")` — verificar HTTP status.
2. Extrair `<title>` ou primeiro `h1`.
3. Comparar com título reportado no `02-source-inventory.md`:
   - **Match:** ACCESSIBLE
   - **Mismatch:** HALLUCINATED — remover fonte, registrar no Title Mismatch log
   - **404/403/Timeout:** UNVERIFIABLE
4. Fontes sem URL (local files, bibliography): `read_file` em vez de `fetch_url`.
5. **Nenhuma fonte pode ser "ACCESSIBLE (inferred)".** Categoria abolida.
```

**Mudança no template `source-verification.md`:**
- Coluna `Status` perde o valor `ACCESSIBLE (inferred)`. Valores válidos: `ACCESSIBLE`, `UNVERIFIABLE`, `HALLUCINATED`, `EXCLUDED`.
- Nova seção: `## Title Mismatch Detection` (já existe parcialmente no relatório RAG — formalizar).

---

### FRENTE 2 — Coverage → Confidence Binding

**Arquivos:** `references/deep-reading.md`, `templates/source-deep-read.md`, `SKILL.md` (Stage 5)

**Regra:** A cobertura do documento processado limita a confiança máxima dos claims extraídos.

**Tabela de binding:**
```
| Cobertura           | Confidence máximo | Justificativa                                    |
|---------------------|-------------------|--------------------------------------------------|
| ≥ 80%               | HIGH              | Documento quase completo processado              |
| 50–79%              | MODERATE          | Mais da metade; seções-chave cobertas            |
| 25–49%              | LOW               | Abaixo da metade; possível viés de seção         |
| < 25%               | SPECULATIVE       | Apenas abstract/intro — não é deep read real     |
| Desconhecida        | LOW (cap)         | Sem métrica de chunking → assumir pior caso      |
```

**Mudança no Stage 5 (Synthesis):**
Após carregar `deep-reads/*.md`, para cada fonte:
1. Extrair `coverage_pct` do header.
2. Aplicar cap de confidence.
3. Se coverage < 25%, claims dessa fonte só podem ser usados como corroboração, nunca como evidência primária de um finding STRONG.

**Mudança no template `source-deep-read.md`:**
- Campo `Chunks processed` passa de opcional para **obrigatório**.
- Adicionar campo `Coverage: {pct}%` no header.
- Se T1/T2 (sem chunking), coverage = 100% (lido integralmente).
- Se T4 com seções puladas, coverage = (chars processados / chars totais estimados) * 100.

---

### FRENTE 3 — SPEC-003: PDF Full-Text Acquisition

**Arquivos:** `scripts/fulltext.py` (criar), `scripts/helpers.py` (modificar), `SKILL.md` (Stage 3), `references/pipeline-detail.md` (Stage 3)

**Cadeia de fallback:**
```
DOI disponível?
 ├─ SIM → Unpaywall API (GET /v2/{DOI}?email={email})
 │        ├─ url_for_pdf existe → download → salvar PDF
 │        └─ null → próximo
 └─ arXiv ID?
    ├─ SIM → GET arxiv.org/pdf/{id}.pdf → salvar PDF
    └─ DOI disponível + allow_scihub=true?
       └─ Sci-Hub → GET sci-hub.{domain}/{DOI} → parse → download PDF

Se PDF obtido → read_file → texto extraído → disponível para Stage 4
Se tudo falhar → UNVERIFIABLE
```

**Novo script `scripts/fulltext.py`:**
```python
def resolve_fulltext(
    doi: str | None,
    arxiv_id: str | None,
    source_id: str,
    output_dir: str,
    unpaywall_email: str,
    allow_scihub: bool = False,
    scihub_domain: str = "",
) -> dict:
    """
    Returns: {"status": "oa"|"arxiv"|"scihub"|"unavailable",
              "pdf_path": str|None, "pdf_url": str|None,
              "oa_status": str|None, "method": str}
    """
```

**Novas config:**
```toml
unpaywall_email = ""     # obrigatório para Unpaywall
allow_scihub = false     # default off
scihub_domain = ""       # auto-detect if empty
```

---

### FRENTE 4 — Sub-agent Prompt Hardening

**Arquivos:** `scripts/prompts.py`

**Problema:** O sub-agente `dsr-bibliography` (Flash) recebe `web_search` + `fetch_url`, mas o prompt atual não exige que ele **verifique** o que encontrou. Ele pode reportar uma URL de search result sem nunca abri-la.

**Mudanças no prompt `_build_bibliography_prompt()`:**

1. Adicionar restrição de verificação:
```
## MANDATORY: Verify every source before including it
For each source you plan to include, you MUST:
1. fetch_url on the source URL to confirm it exists (HTTP 200)
2. Read enough content to confirm the title matches what you're reporting
3. If fetch_url fails (404/403/timeout), do NOT include the source
4. Never fabricate or guess URLs — only include URLs you have successfully fetched
```

2. Exigir evidência verificável:
```
## Output contract
For each source, include:
- The EXACT URL you successfully fetched (copy-paste from fetch_url result)
- The EXACT title as it appears on the page (copy-paste, not paraphrase)
- The first 200 characters of the page content as evidence of successful fetch
```

3. Adicionar aviso anti-alucinação:
```
## CRITICAL: Anti-hallucination rule
- arXiv IDs are 7-digit numbers (e.g., 2407.16833). If you're unsure of an ID,
  fetch the URL to verify it returns the expected paper.
- Never generate an arXiv ID from memory — only use IDs you have seen in
  web_search results or successfully fetched URLs.
- If web_search returns a snippet with a title but no clear URL, run a
  follow-up search to find the URL. Do not guess.
```

---

### FRENTE 5 — Evasão de Detecção por Editoras

**Arquivos:** `scripts/fulltext.py`, `references/pipeline-detail.md` (Stage 3)

**Headers de browser realista:**
```python
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
```

**Rate limiting:**
```python
import time, random

def interrequest_delay():
    time.sleep(random.uniform(1.5, 4.0))
```

**Cookie/sessão para publishers:**
```python
def fetch_with_session(url: str) -> tuple[int, str]:
    """
    1. GET landing page → extrair cookies
    2. GET target URL com cookies
    """
```

**Protocolo de falha:**
- HTTP 403 + Cloudflare/DataDome no corpo → `UNVERIFIABLE (bot protection)`, não retentar
- HTTP 429 → aguardar 30s, retentar 1x com headers de browser
- HTTP 406 → adicionar `Accept: */*`, retentar 1x

**Mudança no pipeline-detail.md Stage 3:**
Adicionar § "Bot Detection Avoidance" com o protocolo acima.

---

### FRENTE 6 — Internal Consistency Real (não boilerplate)

**Arquivos:** `references/deep-reading.md`, `templates/source-deep-read.md`

**Problema:** W2, W3, W4 têm checks de internal consistency idênticos ("Numbers verified against tables"), que são impossíveis de serem verdadeiros para papers diferentes.

**Mudança no template `source-deep-read.md`:**
Substituir o bloco boilerplate:

```markdown
## Internal Consistency

{Se 0 issues:}
> No internal contradictions detected across the claims extracted above.

{Se issues, enumerar. Se NÃO foi possível verificar, dizer explicitamente:}
> **Not verified:** The deep read processed {coverage_pct}% of the document.
> Cross-checking claims against tables/figures was not performed. Claims
> should be treated as unverified extractions.
```

**Regra:** se `coverage < 80%`, o campo "Internal Consistency" deve sempre conter a ressalva de verificação parcial. Claims "verified against tables" só são permitidos se o chunking cobriu as tabelas relevantes.

---

## Ordem de Implementação

| Ordem | Frente | Arquivos | Estimativa | Dependências |
|-------|--------|----------|------------|--------------|
| 1 | **GATE-0** | `SKILL.md`, `pipeline-detail.md`, `source-verification.md` | 3 arquivos, ~40 linhas | Nenhuma |
| 2 | **Coverage→Confidence** | `deep-reading.md`, `source-deep-read.md`, `SKILL.md` | 3 arquivos, ~30 linhas | Nenhuma |
| 3 | **Prompt hardening** | `prompts.py` | 1 arquivo, ~25 linhas | Nenhuma |
| 4 | **SPEC-003: fulltext.py** | `fulltext.py` (novo), `helpers.py`, `SKILL.md` | 3 arquivos, ~120 linhas | Nenhuma |
| 5 | **Evasão de detecção** | `fulltext.py`, `pipeline-detail.md` | 2 arquivos, ~50 linhas | Depende de fulltext.py existir |
| 6 | **Internal consistency real** | `deep-reading.md`, `source-deep-read.md` | 2 arquivos, ~15 linhas | Nenhuma |

**Total:** ~10 arquivos modificados/criados, ~280 linhas.

As frentes 1-3 podem ser implementadas em paralelo (sem dependências entre si).
A frente 4 é independente. A frente 5 depende da 4 apenas porque o código de
download vive em `fulltext.py`. A frente 6 é independente.

---

## Verificação Pós-Implementação

Após implementar todas as frentes, re-executar o pipeline em uma RQ conhecida e verificar:

1. **GATE-0:** Nenhuma fonte com status "ACCESSIBLE (inferred)" no output.
2. **GATE-0:** Se sub-agente fabricar URL, o Title Mismatch log captura.
3. **Coverage:** Nenhum finding STRONG baseado em fonte com coverage < 50%.
4. **PDF:** Pelo menos 1 fonte com PDF baixado e processado (se houver DOI).
5. **Evasão:** Nenhum 403 por User-Agent em publishers que aceitam browser normal.
6. **Internal consistency:** Nenhum bloco de boilerplate idêntico entre deep reads diferentes.
