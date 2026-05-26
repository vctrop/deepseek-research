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
| Paywall irresolvível (3+ tentativas) | Marcar INACCESSIBLE; escrever deep-read blocker; prosseguir |
| 5+ INACCESSIBLE consecutivos | Interromper Stage 4; circuito aberto; prosseguir para Stage 5 |
| RLM sub_query_batch timeout | `rlm_close` imediatamente; marcar fonte FAILED; próximo batch |
| Context budget atingido | `/compact` + "continue deep research {slug}" |
| `bibliography_path` não encontrado | Remover "bibliography" dos axes; continuar com codebase |
| Offline (sem internet) | Remover busca web; anotar "offline" no report |
| Config TOML malformado | Usar defaults; warn user |

## Resume from interruption

Se o pipeline for interrompido:

1. **Método preferencial:** usar `stage_status.py` para detectar o estado exato:
   ```
   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from stage_status import check; print(check('{session_dir}'))")
   ```
   O script verifica a presença do marcador `<!-- STAGE_COMPLETE -->` no final
   de cada arquivo de output, detectando arquivos truncados (crash durante
   `write_file`).
2. **Fallback manual:** verificar `{session_dir}` — outputs de cada stage são
   arquivos `.md`.
3. Retomar do primeiro stage sem output file completo.
4. Ex: se `03-source-verification.md` existe → começar no Stage 4.
5. Ex: se `02-source-inventory.md` existe mas não `03-source-verification.md` →
   começar no Stage 3.
6. Não há `.session-state.json` — os outputs do stage são o estado.
