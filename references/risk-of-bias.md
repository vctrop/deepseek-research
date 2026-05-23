# Risk of Bias Assessment

Carregado pelo orquestrador no Stage 3.

## Rating (3 níveis)

| Rating | Significado |
|--------|-------------|
| **Low** | Sem concerns — estudo bem conduzido neste domínio |
| **Medium** | Issues potenciais que podem afetar confiança |
| **High** | Issues sérias que enfraquecem substancialmente a confiança |

## Papers (4 perguntas)

| # | Pergunta | Evidência esperada |
|---|----------|--------------------|
| 1 | A fonte é acessível e completa? | Full-text disponível, não é abstract-only |
| 2 | A metodologia é documentada? | Método, dados, e análise descritos com clareza |
| 3 | Há conflito de interesse evidente? | Funding source, affiliation, competing interests |
| 4 | O venue tem peer review? | Journal/conferência com revisão por pares |

## Código (3 perguntas)

| # | Pergunta | Evidência esperada |
|---|----------|--------------------|
| 1 | CI configurada e testes passam? | CI badge verde, `cargo test`/`pytest`/`npm test` OK |
| 2 | Múltiplos contribuidores? | >1 committer, organizações no GitHub, histórico de PRs |
| 3 | Usado/dependenciado por outros? | Stars, dependents, citações, uso por projetos conhecidos |

## Overall Risk of Bias

O overall RoB é o pior rating entre todos os domínios (worst-case propagation).

| Overall | Ação em síntese |
|---------|----------------|
| **Low** | Usar sem reservas |
| **Medium** | Usar com nota de limitação |
| **High** | Usar com cautela; preferir corroboração de outra fonte |

## Template Output

```markdown
## RoB Summary

| Source ID | Type | Overall RoB | Key concern |
|-----------|------|------------|-------------|
| S{n} | paper/code | Low/Medium/High | {one-line summary} |
```

Para fontes Medium ou High, incluir tabela detalhada:

```markdown
### S{n}: {title}

| Domain | Rating | Evidence |
|--------|--------|----------|
| {domain} | Low/Medium/High | {specific evidence} |
```
