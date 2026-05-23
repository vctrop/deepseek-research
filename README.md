# DeepSeek Research Skill v3.0

Pesquisa bibliográfica e análise de código-fonte sistemática com deep reading
via RLM. Pipeline de 5 estágios com adversarial thinking integrado.

## What it does

Produz uma structured rapid evidence assessment com:

- **2 eixos de descoberta:** bibliografia (local + web) e codebase (grep + análise)
- **Deep reading:** processamento de documentos completos via RLM chunking com extração de claims verbatim (taxonomia V/P/I/M/E)
- **Adversarial thinking:** pass integrado no Stage 5 que avalia evidência contrária, independência de fontes e viés de seleção
- **5 verification gates:** checagens de integridade estrutural ao final do pipeline

## Quick Start

```
deep research How does in-context learning work in large language models?
```

A skill irá:
1. Formular a research question e gerar `protocol-freeze.json`
2. Descobrir fontes nos eixos de bibliografia e codebase
3. Verificar acessibilidade e avaliar risk of bias
4. Deep-read das fontes com extração de evidência verbatim
5. Sintetizar findings com adversarial thinking pass
6. Produzir relatório final com Executive Summary e Methodological Note

**Output:** `research-reports/YYYY-MM-DD-slug/` contendo 8 arquivos.

## Configuration

Crie `.deepseek/deepseek-research.toml` no root do projeto:

```toml
# Eixos de descoberta
source_axes = ["bibliography", "codebase"]

# Output directory
output_dir = "research-reports/"

# Deep reading
deep_reading = true

# Máximo de fontes para deep reading (sujeito a saturação)
max_deep_reads = 10

# Máximo de fontes por eixo
max_sources_per_axis = 20

# Caminho do índice bibliográfico
bibliography_path = "bibliography/"

# Clone de repositórios (T5)
oss_clone_dir = "oss/"
```

Todas as variáveis têm defaults sensíveis (7 variáveis no total).

## Pipeline Stages

| # | Stage | Output |
|---|-------|--------|
| 1 | RQ Formulation | `01-rq-brief.md`, `protocol-freeze.json` |
| 2 | Source Discovery | `02-source-inventory.md` |
| 3 | Source Verification | `03-source-verification.md` |
| 4 | Deep Reading | `deep-reads/*.md` |
| 5 | Synthesis + Report | `04-synthesis.md`, `05-report.md` |
| Close | Verification | `MANIFEST.txt` (5 gates) |

## Output Structure

```
research-reports/YYYY-MM-DD-slug/
├── MANIFEST.txt
├── protocol-freeze.json
├── 01-rq-brief.md
├── 02-source-inventory.md
├── 03-source-verification.md
├── deep-reads/
│   └── S{id}.md
├── 04-synthesis.md
└── 05-report.md
```

## Migration from v2.x

A v3.0 remove features que não eram validadas para CS/engenharia:

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
julgamentos são realizados por sub-agents LLM. Os 5 gates verificam completude
estrutural, não verdade. Todo relatório inclui uma Methodological Note.

## Development

Ver `AGENTS.md` para o guia de desenvolvimento.

```bash
python3 scripts/smoke_test.py
```

## License

MIT — ver `LICENSE.txt`.
