# Deep Source Reading

Carregado pelo orquestrador no Stage 4.

## Taxonomia de Evidência Textual

| Grade | Definição | Uso em síntese |
|-------|-----------|----------------|
| **V — Verbatim** | Texto exato da fonte, com ref §/linha | STRONG — diretamente citável |
| **P — Paraphrase** | Claim reescrito com contexto | MODERATE — fiel mas com interpretação |
| **I — Inference** | Derivado de dados/figuras/tabelas | WEAK — requer cross-validation |
| **M — Mathematical** | Teorema/prova/equação | ⚠ Flagged — requer verificação humana, capped LOW |
| **E — Empirical** | Código executável: implementação, benchmark, teste, constante | STRONG se RoB Low E cross-source corroborado; senão MODERATE |

**Regra de síntese:** STRONG requer ≥1 V-grade (textual) ou E-grade com
RoB Low + corroboração cross-source. MODERATE aceita V, P, ou E sem corroboração.
WEAK aceita I-grade. E-grade sem corroboração → cap MODERATE.

## Tiers de Documento

| Tier | Tamanho | Estratégia | Chunk | Overlap |
|------|---------|-----------|-------|---------|
| T1 — Short | < 5KB | `read_file` direto | — | — |
| T2 — Medium | 5–50KB | `read_file` paginado (2-3 reads) | — | — |
| T3 — Long | 50–200KB | `rlm_open` → chunk → `sub_query_batch` | 8K chars | 1K chars |
| T4 — Book | > 200KB | Seletiva: ToC → intro/conclusion → seções relevantes | 8K chars | 1K chars |
| T5 — Source code | Qualquer | `grep_files` + `read_file` | — | — |

**T4 seletiva:** Chunk do ToC (10% inicial) → identificar seções relevantes →
chunk intro + conclusion → deep-read apenas seções relevantes. Registrar seções
puladas com justificativa.

**T5 source code:**
1. Clone: `git clone --depth 1 --single-branch {repo_url} {oss_clone_dir}/{org}_{repo}/`
   (timeout 120s). Se existe: `git pull --ff-only`.
2. Gravar commit hash: `git rev-parse HEAD`.
3. Survey: README, package manifest, dir listing.
4. `grep_files` com padrões da RQ.
5. `read_file` dos arquivos com matches.
6. Extrair claims E-grade (o que o código realmente faz, não o que alega fazer).
7. Consistency check: implementação vs algoritmo documentado, testes passam?

## Heurística de Saturação

Após cada 3 deep reads concluídas, avaliar se as últimas 2 fontes adicionaram
claims V ou E novos. Se nenhum claim novo → saturação atingida, interromper.

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_saturation; print(compute_saturation('{session_dir}/deep-reads/', '{RQ_TEXT}', last_n=2))")
```

## RLM Lifecycle Contract

```
rlm_open(name="dr-{source_id}", file_path="{source_path}")
rlm_configure(name="dr-{source_id}", output_feedback="metadata")
rlm_eval(name="dr-{source_id}", code="chunks = chunk(chunk_size=8000, overlap=1000); finalize({'n_chunks': len(chunks), 'chunks': chunks})")
rlm_eval(name="dr-{source_id}", code="""
results = sub_query_batch(
    queries=[...],
    dependency_mode="independent",
    safety_note="Each chunk is from the same document, processed independently."
)
finalize(results)
""")
rlm_close(name="dr-{source_id}")
```

- Máximo 1 RLM session ativa por vez.
- Sempre fechar no cleanup em caso de erro.
- T1/T2: `read_file` direto, sem RLM.

## Internal Consistency Checks

1. Claim-claim: dois claims se contradizem?
2. Claim-data: números reportados batem com tabelas/figuras?
3. Claim-method: conclusão segue do método descrito?
4. Abstract-body: abstract representa o corpo com precisão?

## Output Contract

Cada deep read → `{session_dir}/deep-reads/{source_id}.md` com:
- Metadata header (source_id, tier, chunking, commit hash se T5).
- Extracted Claims table (verbatim quote + grade + ref).
- Internal Consistency (0 ou N issues).
- Mathematical Claims (se houver).
- Sections Skipped (T4).
- Overall Assessment: COMPREHENSIVE / PARTIAL / MINIMAL.

**Failure modes:**
- INACCESSIBLE → documento não acessível (paywall, 404).
- PARTIAL → T4 com >50% seções puladas.
- FAILED → RLM timeout ou erro irrecuperável.
