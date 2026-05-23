# Error Recovery

Carregado no início do pipeline. Referenciado inline quando ocorre erro.

## Cenários comuns

| Sintoma | Ação |
|----------|------|
| Sub-agent Flash timeout (>120s) | Reduzir escopo; retry 1× |
| Sub-agent Flash falha total | Tentar eixo alternativo; continuar com o que funcionou |
| Web search retorna baixa qualidade | Narrow query; adicionar `site:edu` ou `site:org` |
| Source URL 404/403 | Flag "UNVERIFIABLE"; credibility → Low para 404/403, mantém para timeout |
| 0 fontes em todos os eixos | Skip Stages 3-4; Stage 5 → relatório negativo |
| RLM session hang | `rlm_close` e reabrir com timeout menor |
| Context budget atingido | `/compact` + "continue deep research {slug}" |
| `bibliography_path` não encontrado | Remover "bibliography" dos axes; continuar com codebase |
| Offline (sem internet) | Remover busca web; anotar "offline" no report |
| Config TOML malformado | Usar defaults; warn user |

## Resume from interruption

Se o pipeline for interrompido:

1. Verificar `{session_dir}` — outputs de cada stage são arquivos `.md`.
2. Retomar do primeiro stage sem output file completo.
3. Ex: se `03-source-verification.md` existe → começar no Stage 4.
4. Ex: se `02-source-inventory.md` existe mas não `03-source-verification.md` →
   começar no Stage 3.
5. Não há `.session-state.json` — os outputs do stage são o estado.
