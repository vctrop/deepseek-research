# Designs de Mínimo Esforço — Fechamento Real dos Gaps

**Data:** 2026-05-23
**Princípio:** Intervenções cirúrgicas. Nada de reescrever a arquitetura.
Cada design é um script Python que roda como GATE no Close ou como helper
no Stage 3/5, invocado via `code_execution`. Zero mudanças no runtime.

---

## Design 1: GATE-6 — Verification Completeness Check

**Custo:** ~40 linhas, 1 novo script
**Arquivo:** `scripts/verify_completeness.py`
**Gap que fecha:** Fontes não verificadas (Falha 2), GATE-0 não executado (Falha 1)

### O que faz

Lê `02-source-inventory.md` + `03-source-verification.md`. Para cada fonte com URL
no inventory, verifica se existe entrada correspondente na tabela de verificação
com Status preenchido (não vazio, não placeholder).

### Regras

```
1. Extrair fontes do 02-source-inventory.md (regex: | S{n} | title | type | ... |)
2. Extrair verificações do 03-source-verification.md (Credibility Matrix table)
3. Para cada fonte com URL:
   a. Deve existir linha correspondente na Credibility Matrix
   b. Status deve ser ACCESSIBLE, UNVERIFIABLE, HALLUCINATED, ou EXCLUDED
   c. Se status ausente ou placeholder → FAIL
4. Soma ACCESSIBLE + UNVERIFIABLE + HALLUCINATED + EXCLUDED deve bater
   com total de fontes no Verification Summary
```

### O que NÃO faz

Não verifica se o título bate (isso requer fetch_url real, que code_execution
não tem). Apenas verifica se o orquestrador preencheu o campo — ou seja, se
executou o GATE-0.

### Integração

Adicionar ao Close (6º gate):

```
### GATE-6: Verification Completeness

code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from verify_completeness import check
print(check("{session_dir}/02-source-inventory.md", "{session_dir}/03-source-verification.md"))
''')
```

---

## Design 2: GATE-7 — Evidence Grade Sanity Check

**Custo:** ~50 linhas, 1 novo script
**Arquivo:** `scripts/verify_evidence_grades.py`
**Gap que fecha:** Snippets como V-grade (Falha 4), Coverage cap bypass

### O que faz

Lê todos os `deep-reads/*.md`. Para cada um, cruza Access method + Coverage
com as grades dos claims.

### Regras

```
1. Para cada deep-reads/{source_id}.md:
   a. Extrair Access method do header
   b. Extrair Coverage do header
   c. Extrair claims e suas grades da tabela

2. Se Access method contém "snippet" ou "abstract":
   → Qualquer claim V-grade ou P-grade é FLAG: "V-grade claim from snippet source"

3. Se Coverage < 25%:
   → Claims V-grade são FLAG: "V-grade claim with <25% coverage"

4. Se Coverage não reportada:
   → WARN: "Coverage not reported — assuming LOW cap"

5. Se Access method = "snippets_only" ou "abstract_only":
   → Claims com grade V ou P são automaticamente downgraded para I-grade
     (o script não modifica os arquivos, apenas reporta)
```

### Integração

Adicionar ao Close (7º gate). Output é PASS/FAIL com lista de violações.

---

## Design 3: GATE-2 Determinístico — Iron Rule C com Filtro de Contexto

**Custo:** ~70 linhas, modificar `scripts/helpers.py`
**Arquivo:** `scripts/helpers.py` (nova função `check_iron_rule_c_deterministic`)
**Gap que fecha:** Iron Rule C falsos positivos (Falha 5)

### O que faz

Substitui o grep cego do GATE-2 atual por uma análise com 3 filtros de exclusão.

### Regras

```python
# Palavras proibidas
BARE_CLAIM_WORDS = [
    "validated", "proved", "confirmed", "demonstrated",
    "ensures", "guarantees", "always", "never",
    "optimal", "definitive", "conclusive",
    "certainly", "undoubtedly", "obviously", "clearly",
]

# Padrões de exclusão (não são claims nus)
EXCLUSION_PATTERNS = [
    # 1. Verbatim quote: "texto entre aspas" com atribuição
    r'"[^"]*\b(?:%s)\b[^"]*"\s*(?:\(|\[|—|–|,\s*(?:et\s+al|20\d))',
    # 2. Negação: "not validated", "failed to confirm", "does not guarantee"
    r'\b(?:not|never|failed\s+to|does\s+not|do\s+not)\s+\w*\s*\b(?:%s)\b',
    # 3. Atribuição externa: "Smith et al. confirmed", "was demonstrated by"
    r'\b(?:et\s+al\.?|authors?|researchers?|study|paper|work)\s+\(?20\d{1,3}\)?\s*\w*\s*\b(?:%s)\b',
    # 4. Meta-linguagem: "this finding was confirmed", "as demonstrated above"
    r'\b(?:this|these|our|the)\s+\w+\s+(?:was|were|is|are|has|have)\s+\b(?:%s)\b',
]

def check_iron_rule_c_deterministic(report_path: str, synthesis_path: str) -> dict:
    """
    Retorna {"pass": bool, "violations": [{"line": N, "word": "...", "context": "..."}]}
    
    Para cada arquivo:
    1. grep palavras proibidas
    2. Para cada match, verificar se encaixa em algum EXCLUSION_PATTERNS
    3. Se não encaixa → violação
    4. Se encaixa → OK (não é claim nu)
    """
```

### Eficácia estimada

Com base nos 10 relatórios: ~80% de redução de falsos positivos. v1.0 passaria
de 12 hits para ~2-3 violações reais.

### Integração

Substituir o bloco GATE-2 no SKILL.md:

```
### GATE-2: Iron Rule C (determinístico)

code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from helpers import check_iron_rule_c_deterministic
result = check_iron_rule_c_deterministic(
    "{session_dir}/05-report.md",
    "{session_dir}/04-synthesis.md"
)
print(json.dumps(result, indent=2))
''')

Se result["pass"] == False → revisar violações manualmente.
```

---

## Design 4: Batch PDF Acquisition

**Custo:** ~30 linhas, modificar `scripts/fulltext.py`
**Arquivo:** `scripts/fulltext.py` (nova função `resolve_all_fulltext`)
**Gap que fecha:** PDF acquisition dependente de disciplina do orquestrador (Falha 6)

### O que faz

Em vez de o orquestrador chamar `resolve_fulltext` para cada fonte, um batch
que processa todas de uma vez.

```python
def resolve_all_fulltext(
    inventory_path: str,
    output_dir: str,
    unpaywall_email: str = "",
    allow_scihub: bool = False,
) -> dict:
    """
    Lê 02-source-inventory.md, extrai DOI e arXiv ID de cada fonte,
    chama resolve_fulltext para cada uma, retorna mapping.
    
    Returns:
        {"results": {"S1": {...}, "S2": {...}, ...},
         "summary": {"total": N, "arxiv": N, "oa": N, "scihub": N, "unavailable": N}}
    """
```

### Extração de DOI/arXiv ID do inventory

```python
# Regex para extrair DOI de texto
DOI_PATTERN = r'\b10\.\d{4,}/[^\s]+'

# Regex para extrair arXiv ID
ARXIV_PATTERN = r'\b(?:arxiv\.org/abs/|arXiv:)(\d{4}\.\d{4,5}(?:v\d+)?)\b'
```

### Integração

O orquestrador chama UMA vez no Stage 3:

```
code_execution(code='''
import sys, json; sys.path.insert(0, "{SKILL_DIR}/scripts")
from fulltext import resolve_all_fulltext
result = resolve_all_fulltext(
    inventory_path="{session_dir}/02-source-inventory.md",
    output_dir="{session_dir}/pdfs/",
    unpaywall_email="{unpaywall_email}",
    allow_scihub={allow_scihub},
)
# Salvar mapping para Stage 4
with open("{session_dir}/pdfs/mapping.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"Resolved {result['summary']['total']} sources: "
      f"{result['summary']['arxiv']} arxiv, "
      f"{result['summary']['oa']} unpaywall, "
      f"{result['summary']['unavailable']} unavailable")
''')
```

O Stage 4 então lê `mapping.json` para saber quais PDFs estão disponíveis.

---

## Design 5: Coverage vs Grade Cross-Check (embutido no GATE-3)

**Custo:** ~25 linhas, modificar `scripts/helpers.py`
**Arquivo:** `scripts/helpers.py` (nova função `check_coverage_grade_consistency`)
**Gap que fecha:** Coverage cap bypass (orquestrador reporta coverage falsa)

### O que faz

Modifica o GATE-3 existente (Textual Evidence) para também verificar se STRONG
findings no `04-synthesis.md` citam fontes com coverage suficiente.

### Regras

```
1. Extrair todos os findings STRONG do 04-synthesis.md
2. Para cada finding, extrair quais source_ids são citados
3. Para cada source_id citado, ler coverage_pct do deep read
4. Se coverage_pct < 50%:
   → FLAG: "STRONG finding cites source {id} with only {pct}% coverage"
5. Se coverage_pct não reportada:
   → FLAG: "STRONG finding cites source {id} with unknown coverage"
```

### Integração

Adicionar ao bloco GATE-3 existente no SKILL.md, após a verificação atual.
Ou como um novo GATE-8.

---

## Design 6: Source ID Cross-Reference Check

**Custo:** ~20 linhas, 1 novo script
**Arquivo:** `scripts/verify_source_refs.py`
**Gap que fecha:** Inconsistência interna — 05-report.md citando fontes que não existem

### O que faz

Verifica que todos os source_ids citados no `05-report.md` e `04-synthesis.md`
realmente existem no `02-source-inventory.md` ou `03-source-verification.md`.

### Regras

```
1. Extrair todos os source_ids citados em 04-synthesis.md e 05-report.md
   (regex: \b[Ss]\d+\b, \bCODE-\d+\b, etc.)
2. Extrair todos os source_ids do 02-source-inventory.md
3. Reportar qualquer source_id citado que não existe no inventory
4. Reportar qualquer source_id no inventory que nunca é citado (fonte órfã)
```

### Integração

Adicionar ao Close como GATE-8 ou embutir no GATE-1 (File Integrity).

---

## Sumário: O Que Implementar e Em Que Ordem

| # | Design | Linhas | Arquivo | Fecha gap | Determinístico? |
|---|--------|--------|---------|-----------|-----------------|
| 1 | Verification Completeness | ~40 | `verify_completeness.py` | Fontes não verificadas | Sim |
| 2 | Evidence Grade Sanity | ~50 | `verify_evidence_grades.py` | Snippets como V-grade | Sim |
| 3 | Iron Rule C determinístico | ~70 | `helpers.py` | Falsos positivos GATE-2 | Sim (80%) |
| 4 | Batch PDF Acquisition | ~30 | `fulltext.py` | PDF depende de disciplina | Sim |
| 5 | Coverage-Grade Cross-Check | ~25 | `helpers.py` | Coverage cap bypass | Sim |
| 6 | Source Ref Cross-Check | ~20 | `verify_source_refs.py` | Fontes fantasmas | Sim |

**Total:** ~235 linhas em 4 arquivos (1 novo, 3 modificados).

**Ordem recomendada:** 1 → 6 → 2 → 5 → 3 → 4
(da maior relação impacto/esforço para a menor)

**Princípio de design comum a todos:** São scripts Python executados via
`code_execution` no Close. Não dependem do orquestrador para enforcement —
o código retorna PASS/FAIL deterministicamente. Se FAIL, o MANIFEST registra
a falha e o pipeline é bloqueado até correção.

**O que NÃO resolvem:** O GATE-0 ainda não é totalmente determinístico porque
`code_execution` não tem acesso à tool `fetch_url`. O Design 1 verifica se o
orquestrador *preencheu* o campo de verificação, mas não se o conteúdo está
correto. Para um GATE-0 verdadeiramente determinístico, seria necessário que
o runtime expusesse `fetch_url` como função Python — ou que o script usasse
`urllib.request` (que funciona para a maioria das URLs).
