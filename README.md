# DeepSeek Research Skill v3.1

Pesquisa bibliográfica e análise de código-fonte sistemática com deep reading
via RLM. Pipeline de 5 estágios + 2 fases de indexação + adversarial thinking
integrado + persistência cross-session de corpus bibliográfico.

## What it does

Produz uma structured rapid evidence assessment com:

- **2 eixos de descoberta:** bibliografia (local + web) e codebase (grep + análise)
- **Cross-session corpus indexing:** fontes descobertas na web são persistidas em `bibliography/`
  com índice JSON consultável por keywords; pesquisas futuras reutilizam o corpus local
  antes de buscar na web
- **Deep reading:** processamento de documentos completos via RLM chunking com extração de claims verbatim (taxonomia V/P/I/M/E)
- **Adversarial thinking:** pass integrado no Stage 5 que avalia evidência contrária, independência de fontes e viés de seleção
- **10 verification gates:** checagens de integridade estrutural ao final do pipeline

## Quick Start

```
deep research How does in-context learning work in large language models?
```

A skill irá:
1. Verificar/criar `.deepseek/deepseek-research.toml` e bootstrap do índice bibliográfico
2. Formular a research question e gerar `protocol-freeze.json`
3. Consultar o corpus local por fontes já indexadas relevantes (local triage)
4. Descobrir fontes nos eixos de bibliografia e codebase (web + local)
5. Verificar acessibilidade e avaliar risk of bias
6. Deep-read das fontes com extração de evidência verbatim
7. Sintetizar findings com adversarial thinking pass
8. Produzir relatório final com Executive Summary e Methodological Note
9. Persistir novas fontes no corpus local para reúso futuro

**Output:** `research-reports/YYYY-MM-DD-slug/` + `bibliography/index/sources.json` + `SESSION-INDEX.md`

## Configuration

O arquivo `.deepseek/deepseek-research.toml` é criado e mantido automaticamente
pela skill (Phase 0 — `config_ensure`). Na primeira execução, ele é gerado com
todos os defaults. Em execuções subsequentes, chaves faltantes são adicionadas
sem sobrescrever valores existentes.

```toml
# deepseek-research v3.1 — Configuração auto-gerada
source_axes = ["bibliography", "codebase"]
output_dir = "research-reports/"
deep_reading = true
max_deep_reads = 10
max_sources_per_axis = 20
bibliography_path = "bibliography/"
oss_clone_dir = "oss/"
unpaywall_email = ""
allow_scihub = false
scihub_domain = ""
```

Todas as 10 variáveis têm defaults sensíveis. Para habilitar acesso a PDFs de
papers com Open Access, preencha `unpaywall_email` com seu email institucional
(a API Unpaywall é gratuita).

## Pipeline Stages

| # | Stage | Output |
|---|-------|--------|
| 0 | Index Bootstrap + Config Check | `bibliography/index/sources.json`, `.deepseek/deepseek-research.toml` |
| 1 | RQ Formulation | `01-rq-brief.md`, `protocol-freeze.json` |
| 1.5 | Local Corpus Triage | `local_sources` (query index → Stage 2) |
| 2 | Source Discovery | `02-source-inventory.md` |
| 3 | Source Verification | `03-source-verification.md` |
| 4 | Deep Reading | `deep-reads/*.md` |
| 5 | Synthesis + Report | `04-synthesis.md`, `05-report.md` |
| Close | Persistence + Verification | `MANIFEST.txt`, `SESSION-INDEX.md` |

## Output Structure

```
research-reports/
├── SESSION-INDEX.md          ← append-only session log
└── YYYY-MM-DD-slug/
    ├── MANIFEST.txt
    ├── protocol-freeze.json
    ├── 01-rq-brief.md
    ├── 02-source-inventory.md
    ├── 03-source-verification.md
    ├── pdfs/
    │   └── mapping.json
    ├── deep-reads/
    │   └── S{id}.md
    ├── 04-synthesis.md
    └── 05-report.md

bibliography/
├── index/
│   └── sources.json          ← cross-session corpus index
└── {source_id}.pdf           ← persisted source files
```

## Bibliography Indexing

A skill mantém um corpus bibliográfico cross-session em `bibliography/`. Ao final
de cada pesquisa, fontes web descobertas e verificadas são automaticamente
persistidas no índice local para reúso em pesquisas futuras.

### Como funciona

1. **Phase 0 — Bootstrap:** o config (`deepseek-research.toml`) e o índice
   (`bibliography/index/sources.json`) são criados automaticamente na primeira
   execução. Arquivos soltos em `bibliography/` são detectados e reportados
   para indexação manual.

2. **Phase 1.5 — Local Triage:** antes de buscar na web, a skill consulta o índice
   local com as keywords extraídas da research question. Fontes já indexadas que
   casam com os termos são enviadas ao sub-agent `dsr-bibliography` como contexto,
   evitando buscas duplicadas.

3. **Close — Persistence:** fontes novas usadas no relatório são copiadas para
   `bibliography/` e indexadas com metadados (título, autores, ano, DOI, keywords,
   resumo). Fontes locais reutilizadas têm seu registro de sessão atualizado.

### Schema do índice

Cada entrada em `sources.json` segue este formato:

```json
{
  "id": "smith-2020",
  "title": "In-Context Learning in Large Language Models",
  "authors": ["Smith, J.", "Doe, A."],
  "year": 2020,
  "doi": "10.1234/example",
  "keywords": ["in-context learning", "llms", "few-shot"],
  "summary": "Investigates ICL mechanisms across model scales.",
  "quality_level": "II",
  "source_type": "paper",
  "sessions_used": ["2026-05-24-in-context-learning-llms"],
  "path": "smith-2020.pdf",
  "indexed_at": "2026-05-24",
  "indexed_by": "auto"
}
```

### Comandos manuais

O script `index_sources.py` expõe 4 subcomandos para operações manuais:

```bash
# Inicializar o índice (idempotente)
python3 scripts/index_sources.py init --base-dir bibliography/

# Encontrar arquivos não-indexados
python3 scripts/index_sources.py scan-unindexed --base-dir bibliography/

# Buscar por keywords (scoring: keywords 3×, title 2×, summary 1×)
python3 scripts/index_sources.py query --base-dir bibliography/ \
  --keywords "in-context learning,transformers" --top 10

# Atualizar registro de sessão de uma entrada
python3 scripts/index_sources.py update-sessions --base-dir bibliography/ \
  --id smith-2020 --session 2026-05-24-in-context-learning-llms
```

### SESSION-INDEX.md

O arquivo `research-reports/SESSION-INDEX.md` mantém um log append-only de
todas as pesquisas realizadas:

```
| Date | Slug | Target | Mode | Key Findings (≤280 chars) |
|------|------|--------|------|---------------------------|
```

Cada nova pesquisa adiciona uma linha ao final da tabela.

## Migration from v2.x

A v3.0/v3.1 remove features que não eram validadas para CS/engenharia:

| Feature removida | Alternativa |
|------------------|-------------|
| Meta-análise (DerSimonian-Laird) | Não disponível — possível skill separada futura |
| GRADE certainty framework | Substituído por STRONG/MODERATE/WEAK |
| PRISMA flow diagram completo | Tabela simplificada de 1 linha |
| Pre-registration automática (OSF/Zenodo) | `protocol-freeze.json` local |
| Devil's Advocate sub-agent separado | Adversarial thinking pass inline no Stage 5 |
| Living review (surveillance) | Re-execução manual do pipeline |

Usuários que precisam manter acesso às features removidas devem permanecer na
tag `v2.x-last`.

## Epistemic Scope

Esta é uma **rapid evidence assessment**, não uma revisão sistemática. Todos os
julgamentos são realizados por sub-agents LLM. Os 10 gates verificam completude
estrutural, não verdade. Todo relatório inclui uma Methodological Note.

## Development

Ver `AGENTS.md` para o guia de desenvolvimento.

```bash
python3 scripts/smoke_test.py
```

## License

MIT — ver `LICENSE.txt`.
