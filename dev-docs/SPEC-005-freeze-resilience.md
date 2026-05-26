# SPEC-005: Freeze Resilience — Runtime Anti-Hang Fixes

**Data:** 2026-05-26
**Motivação:** Investigação de congelamento da sessão `2026-05-26-physical-dynamics-as-computation` (Stage 4, após 7 deep reads + 1 blocker)
**Princípio:** Intervenções cirúrgicas. Nenhuma reescrita de arquitetura. Cada fix é uma adição ou modificação pontual no pipeline, nos scripts, ou nos templates.
**Relação com plano v3.2:** Complementar. O plano `26-05-2026-skill-improvement-plan.md` (I-1 a I-10) cobre integridade de verificação; esta SPEC cobre resiliência de runtime. Nenhum overlap.

---

## 1. Root Cause Summary

Três vetores de congelamento foram identificados na sessão investigada:

| Vetor | Evidência | Bloqueia |
|-------|-----------|----------|
| **RLM `sub_query_batch` sem timeout** | `rlm_configure` atual só define `output_feedback`. `sub_query_timeout_secs` nunca é configurado. Se 1 query filha de N travar, `rlm_eval` bloqueia o orquestrador indefinidamente. | Orquestrador inteiro |
| **Loop de resolução de paywall** | B02 (Nature Electronics) lista 8 rotas de acesso tentadas, todas falharam, e termina pedindo "PDF via institutional subscription" — ação humana não-automatizável. O orquestrador pode ter tentado resolver isso em runtime. | Progresso do Stage 4 |
| **Sessão RLM órfã** | `B10_test.md` (0 bytes, criado junto com `B10.md`) indica uma sessão RLM que foi aberta (write_file do destino) mas nunca produziu output. Se o `rlm_eval` travou, o `rlm_close` nunca foi chamado. | Sessões RLM subsequentes |

Fatores contribuintes:
- `max_sources_per_axis=20` não enforced no Stage 2 (68 fontes descobertas vs cap declarado)
- Nenhum checkpoint de saturação salvo em disco (sem `_saturation_check.md`)
- `error-recovery.md` lista "RLM session hang → rlm_close e reabrir com timeout menor" mas isso depende do orquestrador detectar o hang — impossível se o `rlm_eval` bloqueia o próprio orquestrador

### 1.1 Architectural Constraint (fundamental)

**O orquestrador é síncrono.** Toda tool call (`rlm_eval`, `agent_eval`, `exec_shell`) bloqueia o loop de raciocínio do modelo até retornar ou expirar. Se uma tool call congela (não retorna, não falha, não expira), o orquestrador inteiro congela — irreversivelmente, sem possibilidade de auto-detecção.

Isso significa que **nenhum fix que dependa de o orquestrador "detectar" um hang durante uma tool call bloqueante pode funcionar**. O orquestrador só pode agir _entre_ tool calls. Portanto, a defesa deve ser preventiva (timeout configurado _antes_ da chamada) ou arquitetural (isolar operações bloqueantes em sub-agents com timeout próprio).

**Implicações para os fixes:**
- F-1 (`sub_query_timeout_secs`) é preventivo — correto, mas só cobre queries filhas, não o `rlm_eval` pai.
- F-3 (cleanup) depende de F-1 funcionar — se F-1 não converte hang em erro, F-3 nunca executa.
- F-6 (per-source budget) é aspiracional — o orquestrador não tem cronômetro interno.

---

## 2. Priority Matrix

| # | Fix | Prioridade | Esforço | Impacto | Bloqueia |
|---|-----|-----------|---------|---------|----------|
| F-0 | Sub-agent wrapper para `rlm_eval` (timeout isolation) | 🔴 Crítica | 1h, 2 arquivos | Isola hangs do RLM do orquestrador; permite `rlm_close` mesmo se `rlm_eval` travar | Vetor principal (arquitetural) |
| F-1 | `sub_query_timeout_secs` no RLM contract | 🔴 Crítica | 0.5h, 2 arquivos | Impede hang de queries filhas dentro do RLM | Complementa F-0 |
| F-2 | Paywall circuit breaker (max 3 tentativas) | 🔴 Crítica | 0.5h, 2 arquivos | Impede loop em paywall não-resolvível | B02, futuros |
| F-3 | Cleanup RLM em todos os paths de erro | 🔴 Crítica | 0.5h, 1 arquivo | Previne sessões RLM órfãs | B10_test |
| F-4 | Enforce `max_sources_per_axis` deterministicamente | 🟡 Alta | 0.5h, 1 script | Reduz volume de Stage 3-4 ao contratado | Exaustão de contexto |
| F-5 | Checkpoint de saturação em disco | 🟡 Alta | 0.5h, 3 arquivos | Permite retomada e auditoria | Resume from interruption |
| F-6 | Per-source budget guideline (documentação) | 🟢 Média | 0.5h, 1 arquivo | Guia o orquestrador com limites explícitos por tier | Progresso parcial |
| F-7 | RLM metrics no `pipeline_metrics.py` | 🟢 Média | 0.5h, 1 arquivo | Visibilidade de falhas RLM cross-session | Debug |

**Total estimado:** ~3.5h (vs 12h do plano v3.2). Todos os fixes são independentes e podem ser implementados em paralelo.

---

## 3. Dependency Map

```
F-0 (sub-agent wrapper) ← Fundação arquitetural. Sem F-0, F-1 e F-3 são frágeis.
 ├── F-1 (RLM timeout) — F-1 opera dentro do wrapper de F-0
 ├── F-3 (cleanup) — F-3 pode executar via agent_close do F-0
 └── F-7 (metrics) — métricas de timeout no contexto de F-0

F-1 (RLM timeout interno)
 └── complementa F-0 (timeout de queries filhas + timeout de rlm_eval)

F-2 (paywall breaker) — independente; integra com pdfs/mapping.json do Stage 3.1
F-4 (max_sources enforcement) — independente
F-5 (saturation checkpoint) — independente; requer update em stage_status.py
F-6 (per-source budget) — documentação, sem dependências de código

Relação com plano v3.2:
F-5 (saturation checkpoint) requer modificação em stage_status.py (I-9)
F-7 (RLM metrics) estende I-10 (pipeline_metrics.py)
```

---

## 4. Designs

### F-0: Sub-agent Wrapper para `rlm_eval` (Timeout Isolation)

**Arquivos modificados:**
- `references/pipeline-detail.md` — Stage 4 §4.2, novo fluxo RLM com wrapper
- `references/deep-reading.md` — §RLM Lifecycle Contract, versão com wrapper

**O que muda:**

O problema fundamental: `rlm_eval` bloqueia o orquestrador. Se o runtime RLM não tem timeout próprio no nível da tool call (e não tem — `rlm_eval` não expõe `timeout_ms`), a única defesa é isolar a operação em um sub-agent. Sub-agents (`agent_open`) aceitam timeout no `agent_eval`. Se o sub-agent expira, o orquestrador recebe controle de volta e pode executar `agent_close` (que por sua vez chama `rlm_close`).

**Wrapper pattern para cada deep read T3/T4:**

```
# Em vez de chamar rlm_eval diretamente (bloqueante):
#   rlm_eval(name="dr-S1", code="...")

# Usar sub-agent wrapper:
agent_open(
    name="deepread-S1",
    model="deepseek-v4-flash",
    allowed_tools=["rlm_open", "rlm_configure", "rlm_eval", "rlm_close", "handle_read", "write_file"],
    prompt="""
    Execute deep read para source S1.
    
    1. rlm_open(name="dr-S1", file_path="{source_path}")
    2. rlm_configure(name="dr-S1", output_feedback="metadata", sub_query_timeout_secs=120)
    3. Chunk e processar claims via sub_query_batch
    4. Extrair claims table e escrever em deep-reads/S1.md
    5. rlm_close(name="dr-S1")
    """
)

# Aguardar com timeout:
agent_eval(agent_id="...", block=true, timeout_ms=600000)  # 10 min max por fonte

# Se agent_eval retornar timeout ou erro:
#   → agent_close(agent_id="...")
#   → rlm_close(name="dr-{source_id}")  # ⚠ O orquestrador DEVE chamar explicitamente!
#     O sub-agent pode não ter tido chance de fazer rlm_close antes do timeout.
#   → Marcar fonte como FAILED
#   → Prosseguir
```

**Trade-off:** O sub-agent Flash processa uma fonte por vez (não batch). Isso significa que o orquestrador pode processar múltiplas fontes _em paralelo_ (vários sub-agents simultâneos com seus próprios timeouts), compensando a perda do batch processing. O throughput final pode ser maior porque fontes rápidas não esperam fontes lentas.

**⚠ Limitação de tool availability:** O sub-agent Flash precisa de acesso às tools RLM. Se o runtime não permitir que sub-agents usem `rlm_open`/`rlm_eval`/`rlm_close`, o wrapper não funciona no modo completo. Dois fallbacks:

1. **Fallback A (preferencial):** O orquestrador faz `rlm_open` antes de disparar o sub-agent, e o sub-agent só executa `rlm_eval`/`rlm_close`. Neste caso, `rlm_open` ainda é feito pelo orquestrador (com risco de hang residual), mas `rlm_eval` fica isolado no sub-agent com timeout.

2. **Fallback B (degradado):** Se nem `rlm_eval` está disponível para sub-agents, o wrapper não é viável. O orquestrador processa fontes sequencialmente com `rlm_eval` direto + F-1 (`sub_query_timeout_secs`). A proteção é reduzida (só cobre queries filhas, não o `rlm_eval` pai), mas ainda é melhor que o status quo.

**Acceptance criteria:**
- `agent_eval` com `timeout_ms=600000` garante que nenhuma fonte bloqueie o orquestrador por >10 min
- Sub-agent que expira → `agent_close` → `rlm_close` → fonte marcada FAILED
- Orquestrador retoma controle após timeout e processa próxima fonte
- Fontes podem ser processadas em paralelo (até `max_deep_reads` sub-agents simultâneos)

**Rollback:** Remover o fluxo wrapper do pipeline-detail.md. Voltar ao rlm_eval direto pelo orquestrador.

---

### F-1: `sub_query_timeout_secs` no RLM Contract

**Arquivos modificados:**
- `references/pipeline-detail.md` — Stage 4 §RLM contract
- `references/deep-reading.md` — §RLM Lifecycle Contract

**O que muda:**

No `pipeline-detail.md`, o bloco RLM contract atual:

```
rlm_configure(name="dr-{source_id}", output_feedback="metadata")
```

Passa a ser:

```
rlm_configure(name="dr-{source_id}", output_feedback="metadata", sub_query_timeout_secs=120)
```

No `deep-reading.md`, mesmo contrato. Adicionar nota:

> **Timeout:** `sub_query_timeout_secs=120` garante que, se qualquer query filha
> do `sub_query_batch` não responder em 2 minutos, o batch falha com erro.
> O orquestrador deve capturar o erro via `try/except` implícito (se `rlm_eval`
> retornar erro ou output vazio, marcar fonte como FAILED e prosseguir).

**Acceptance criteria:**
- `rlm_configure` em todos os templates RLM inclui `sub_query_timeout_secs=120`
- Documentos T3 (~100KB) com 13 chunks completam batch em <120s em condições normais
- Timeout acionado → fonte marcada como FAILED, não TRAVA o orquestrador

**Rollback:** Remover `sub_query_timeout_secs=120` das 2 linhas. RLM volta ao comportamento anterior (sem timeout explícito).

---

### F-2: Paywall Circuit Breaker

**Arquivos modificados:**
- `references/pipeline-detail.md` — Stage 4 §4.0, antes de "Papers (T1-T4)"
- `references/error-recovery.md` — adicionar linha na tabela de cenários

**O que muda:**

Adicionar ao `pipeline-detail.md` Stage 4, antes da tabela de tiers:

```
### 4.0 Paywall Circuit Breaker

Antes de tentar deep-read de qualquer fonte paper:

1. PRIMEIRO: consultar `pdfs/mapping.json` (gerado pelo Stage 3.1).
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

3. Circuit breaker global: se ≥5 fontes consecutivas resultarem INACCESSIBLE,
   interromper Stage 4 — as fontes restantes provavelmente também são inacessíveis.
   Prosseguir para Stage 5 com as fontes processadas até agora.

4. Fontes INACCESSIBLE NÃO contam contra `max_deep_reads`. O cap se aplica a
   fontes efetivamente processadas (COMPREHENSIVE / PARTIAL / MINIMAL).
   INACCESSIBLE e FAILED são registradas mas não consomem vaga.
   Ex: max_deep_reads=10, 3 INACCESSIBLE, 10 processadas → total de 13 fontes
   visitadas, 10 efetivas.
```

No `error-recovery.md`, adicionar à tabela:

```
| Paywall irresolvível (3+ tentativas) | Marcar INACCESSIBLE; escrever deep-read blocker; prosseguir |
| 5+ INACCESSIBLE consecutivos | Interromper Stage 4; circuito aberto; prosseguir para Stage 5 |
```

**Acceptance criteria:**
- Fonte com `pdfs/mapping.json` status `unavailable` → INACCESSIBLE sem re-tentativa
- Fontes sem mapping.json: máximo 3 fetch_url antes de INACCESSIBLE
- Circuit breaker global acionado após 5 INACCESSIBLE consecutivos
- Deep-read de fonte INACCESSIBLE tem header "BLOCKED — Paywall" e claims table vazia
- Fontes INACCESSIBLE não consomem vaga de `max_deep_reads`
- Tempo total gasto em paywall ≤ 90s por fonte (3 tentativas × 30s timeout cada)

**Rollback:** Remover §4.0 do pipeline-detail.md. Remover linhas da tabela em error-recovery.md.

---

### F-3: RLM Cleanup em Todos os Paths de Erro

**Arquivos modificados:**
- `references/pipeline-detail.md` — Stage 4 §4.2, expandir RLM contract
- `SKILL.md` — Stage 4, adicionar RLM sweep na retomada (se budget de linhas permitir)

**O que muda:**

O bloco RLM contract atual é linear (happy path). Adicionar tratamento de erro explícito com critérios de detecção:

```
# RLM contract com cleanup:
rlm_open(name="dr-{source_id}", file_path="{source_path}")

# Se rlm_open retornar erro → fonte INACCESSIBLE, próximo.

rlm_configure(name="dr-{source_id}", output_feedback="metadata", sub_query_timeout_secs=120)

# --- Chunking ---
rlm_eval(name="dr-{source_id}", code="...chunk...")
# Detecção de falha:
# - Se retorno de rlm_eval contém "error" no status → falha
# - Se handle_read retorna None para o resultado → falha
# - Se n_chunks == 0 → falha (documento vazio ou ilegível)

# --- Processamento de claims ---
rlm_eval(name="dr-{source_id}", code="""
results = sub_query_batch(
    queries=[...],
    dependency_mode="independent",
    safety_note="..."
)
finalize(results)
""")
# Detecção de falha:
# - rlm_eval retorna erro → falha
# - handle_read retorna None → falha (timeout ou crash do RLM)
# - results é lista vazia → warning (documento sem claims relevantes; não é falha)

# Em QUALQUER path de saída (sucesso, falha, timeout):
rlm_close(name="dr-{source_id}")

# REGRA: rlm_close DEVE ser chamado em todo fim de processamento.
# Máximo 1 sessão RLM ativa POR sub-agent/POR orquestrador (se modo direto).
# No modo F-0 (sub-agents paralelos), cada sub-agent tem sua própria sessão RLM.
```

Adicionar nota explícita:

> ⚠ **Detecção de falha do RLM:**
> - `rlm_eval` retorna status de erro → `rlm_close` IMEDIATAMENTE.
> - `handle_read` do resultado retorna `None` → `rlm_close` IMEDIATAMENTE
>   (indica que o RLM não produziu output — timeout ou crash interno).
> - Nunca tente reabrir a mesma sessão. Crie uma nova (`dr-{source_id}-retry`)
>   se necessário.

**RLM Sweep na retomada (Stage 4 resume):**

Ao iniciar o Stage 4 (seja primeiro processamento ou retomada), executar sweep para fechar sessões RLM órfãs de execuções anteriores:

```
# Sweep de RLM sessions órfãs (antes de abrir qualquer nova sessão):
# Para cada fonte no inventory que ainda não tem deep-read completo:
#   1. Tentar rlm_close(name="dr-{source_id}") — idempotente se já fechada.
#   2. Ignorar erro (sessão pode já ter sido fechada ou nunca ter existido).
#   3. Registrar no log: "RLM sweep: dr-{source_id} closed (was orphaned)" ou "already closed".
```

Isso resolve o cenário em que o orquestrador foi interrompido (crash, `/compact`, timeout externo) e sessões RLM ficaram abertas. O sweep é seguro porque `rlm_close` em uma sessão já fechada é no-op ou erro inócuo.

**Acceptance criteria:**
- Após qualquer `rlm_eval` que falhe, `rlm_close` é chamado no mesmo turno
- Critérios de detecção de falha são explícitos e testáveis:
  - `rlm_eval` com status de erro → falha
  - `handle_read` retorna None → falha
  - `n_chunks == 0` → falha
- RLM sweep no início do Stage 4 fecha sessões órfãs
- Sessões RLM órfãs = 0 ao final do Stage 4
- `B10_test.md`-style 0-byte files não ocorrem mais (write_file só após output confirmado)

**Rollback:** Reverter o bloco RLM contract para a versão linear (sem branches de erro). Remover RLM sweep da retomada.

---

### F-4: Enforce `max_sources_per_axis` Deterministicamente

**Arquivo novo:** `scripts/enforce_source_caps.py`
**Arquivos modificados:** `references/pipeline-detail.md` — final do Stage 2 (§2.3)

**O que faz:**

Script Python que lê `02-source-inventory.md`, conta fontes por eixo (bibliography / codebase), e se algum eixo exceder `max_sources_per_axis`, trunca ao top-N por relevância.

```python
def enforce_caps(inventory_path: str, max_per_axis: int = 20) -> dict:
    """
    Lê 02-source-inventory.md, trunca fontes excedentes por eixo.
    
    Returns:
        {"bibliography": {"before": 24, "after": 20, "removed": ["B21","B22","B23","B24"]},
         "codebase":    {"before": 44, "after": 20, "removed": ["C21",...]}}
    """
```

**Integração no pipeline-detail.md §2.3 (após "Merge → dedup → tabela"):**

```
3.5 Enforce source caps (antes de escrever 02-source-inventory.md final):

   # IMPORTANTE: O inventory draft precisa existir ANTES da chamada ao script.
   # Fluxo correto:
   #   a. Escrever draft do inventory: 02-source-inventory-draft.md
   #   b. Rodar enforce_source_caps.py sobre o draft
   #   c. Escrever inventory final com a tabela truncada + seção Cap Enforcement
   #   d. Remover o draft: exec_shell("rm {session_dir}/02-source-inventory-draft.md")

   code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from enforce_source_caps import enforce_caps; import json; result = enforce_caps('{session_dir}/02-source-inventory-draft.md', max_per_axis={max_sources_per_axis}); print(json.dumps(result, indent=2))")
   
   Se fontes foram removidas: registrar no inventory final em "## Cap Enforcement".
   Fontes removidas são listadas mas não entram na tabela ativa.
```

**Acceptance criteria:**
- Sessão com 24 bib + 44 code → inventory final tem ≤20 por eixo
- Fontes removidas são listadas em seção "Cap Enforcement" para transparência
- Script é determinístico (ordena por relevance desc, desempata por source_id)
- `max_sources_per_axis=0` desabilita o cap (útil para debug)
- ⚠ Guarda explícita no script: `if max_per_axis > 0 and count > max_per_axis:` — valor 0 significa "sem limite", não "remover todas as fontes"

**Rollback:** Remover a chamada ao script do pipeline-detail.md. Inventories antigos com >20 fontes continuam funcionando (sem breaking change).

---

### F-5: Checkpoint de Saturação em Disco

**Arquivos modificados:**
- `references/pipeline-detail.md` — Stage 4 §4.3
- `SKILL.md` — Stage 4 §Saturação (se couber no budget de 250 linhas; senão só pipeline-detail)

**O que muda:**

Após cada verificação de saturação (a cada 3 deep reads), escrever checkpoint:

```
code_execution(code="import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from helpers import compute_saturation; result = compute_saturation('{session_dir}/deep-reads/', '{RQ_TEXT}', last_n=2); print(result)")

# Sempre escrever checkpoint, independente do resultado:
write_file("{session_dir}/deep-reads/_saturation_check.md", content=f"""# Saturation Check

**Timestamp:** {iso8601_utc}
**Deep reads completed:** {n_completed}
**Saturation reached:** {result}
**Action:** {"STOP — proceed to Stage 5" if result else "CONTINUE — process next batch"}
""")
```

Se saturação atingida → interromper Stage 4 e prosseguir para Stage 5.
Se não → continuar para próximo batch de 3 fontes.

**Checkpoint final:** Ao término do Stage 4 (seja por saturação, `max_deep_reads` atingido, ou circuit breaker global), escrever checkpoint final com todas as fontes processadas. Isso garante que `stage_status.py` detecta conclusão mesmo se o último batch teve <3 fontes e portanto não disparou a verificação periódica.

**Acceptance criteria:**
- `_saturation_check.md` existe após cada verificação de saturação
- Arquivo registra timestamp, N de deep reads concluídas, e resultado booleano
- Na retomada de sessão interrompida, `stage_status.py` lê este arquivo para saber se Stage 4 foi concluído ou interrompido
- **`stage_status.py` modificado:** adicionar detecção de `_saturation_check.md` no método `check()`. Se o arquivo existe e contém "STOP", Stage 4 é considerado concluído (mesmo sem `<!-- STAGE_COMPLETE -->` em `04-synthesis.md`). Se contém "CONTINUE", Stage 4 está em progresso.

**Rollback:** Remover o bloco `write_file` do pipeline-detail.md e a detecção em `stage_status.py`. Verificação de saturação continua funcionando (só não deixa checkpoint).

---

### F-6: Per-source Budget Guidelines (Documentação)

**Arquivos modificados:**
- `references/pipeline-detail.md` — Stage 4 §4.2, adicionar guideline de budget

**O que muda:**

Adicionar ao início do loop de processamento do Stage 4:

```
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
```

**Acceptance criteria:**
- Documentado como guideline no pipeline-detail.md (não é gate automático)
- Orquestrador tem limites claros para cada tier de fonte, implementados via F-0/F-1
- "NUNCA tentar reprocessar a mesma fonte" é regra explícita
- Timeouts do F-0 e F-1 estão alinhados com os budgets documentados

**Rollback:** Remover §4.2.0. Nenhum código dependente.

---

### F-7: RLM Metrics no `pipeline_metrics.py`

**Arquivo modificado:** `scripts/pipeline_metrics.py` (extensão do I-10)

**O que muda:**

Adicionar ao bloco de métricas — apenas o que é deterministicamente computável
a partir dos arquivos de output (sem depender de logs de runtime):

```
- Deep reads: {completed} completed / {failed} failed / {inaccessible} inaccessible
- RLM orphan indicators: {orphan_count} zero-byte files detected
- Evidence grades from deep reads: V={n}, P={n}, I={n}, M={n}, E={n}
```

**Extração:** O script lê `deep-reads/*.md` e classifica cada arquivo:

| Condição | Classificação |
|----------|---------------|
| Arquivo não existe para source_id no inventory | skipped |
| Arquivo existe, 0 bytes | **orphan** (RLM session aberta mas nunca produziu output) |
| Header contém `**Status:** FAILED` | failed |
| Header contém `**Status:** INACCESSIBLE` ou `BLOCKED` | inaccessible |
| Header contém `**Overall Assessment:** COMPREHENSIVE` ou `PARTIAL` ou `MINIMAL` | completed |
| Claims table populada (≥1 claim) sem header de status | completed |
| Nenhuma das anteriores | unclassified (reportar como warning) |

**O que NÃO é computável (e portanto NÃO incluído):**
- "RLM sessions opened/closed" — não há registro de chamadas `rlm_open`/`rlm_close`
  nos arquivos de output. Só sabemos o resultado final (arquivo .md).
- "RLM total wall time" — não há timestamps de início/fim por fonte nos outputs.
- "RLM timeouts" — um timeout de F-0 ou F-1 resulta em FAILED ou orphan,
  mas não podemos distinguir a causa raiz apenas do output.

**Acceptance criteria:**
- `pipeline_metrics.py` reporta classificação de deep reads (completed/failed/inaccessible/orphan)
- Arquivos 0-byte são detectados e reportados como "orphan indicators"
- Métricas aparecem no `MANIFEST.txt` sob `## Pipeline Metrics`
- Nenhuma métrica de runtime (opened/closed/timeouts) que dependa de logs inexistentes

**Rollback:** Remover as linhas de RLM do `pipeline_metrics.py`. Bloco de métricas continua funcionando sem elas.

---

### 4.1 Integrated Stage 4 Flow (cross-fix)

O fluxo abaixo integra F-0 a F-7 em uma sequência coesa de Stage 4. Este bloco
substitui o §4.2 atual do `pipeline-detail.md`.

```
### 4.0 Pre-flight: Accessibility pre-filter

1. Carregar pdfs/mapping.json (se existir).
2. Para cada fonte no inventory (ordenada por relevance desc):
   a. Se status em mapping.json == "unavailable" ou "paywall" → pré-marcar INACCESSIBLE.
   b. Se status == "abstract_only" → pré-marcar ABSTRACT_ONLY (todos claims serão I-grade).
   c. Caso contrário → ACCESSIBLE candidata.
3. Selecionar top max_deep_reads fontes ACCESSIBLE + ABSTRACT_ONLY.
   - INACCESSIBLE pré-marcadas são puladas (não consomem vaga).
   - Se ACCESSIBLE + ABSTRACT_ONLY < max_deep_reads, processar todas as disponíveis.
   - Ex: max_deep_reads=10, 3 INACCESSIBLE pré-marcadas, 12 restantes → processar top 10.
   - Ex: max_deep_reads=10, 8 INACCESSIBLE, 5 restantes → processar as 5.

### 4.1 RLM Sweep (F-3 resume)

Antes de abrir qualquer sessão RLM:
- Para cada fonte no inventory, tentar rlm_close(name="dr-{source_id}").
- Ignorar erros (idempotente). Registrar "RLM sweep: N sessions closed".

### 4.2 Parallel Deep Read Dispatch (F-0)

Para batch de até 3 fontes simultâneas (limite de paralelismo para
context budget):

1. Disparar sub-agents em paralelo:
   ```
   Para fonte em batch:
     agent_open(
       name="deepread-{source_id}",
       model="deepseek-v4-flash",
       allowed_tools=["rlm_open","rlm_configure","rlm_eval","rlm_close",
                      "handle_read","write_file","read_file","grep_files",
                      "fetch_url","exec_shell"],
       prompt=<deep read instructions>,
       max_depth=0  # sem sub-agents filhos
     )
   ```

2. Aguardar todos com timeout individual:
   ```
   Para cada sub-agent no batch:
     agent_eval(agent_id="...", block=true, timeout_ms=600000)
   ```

3. Para cada sub-agent:
   a. Se retornou sucesso → coletar deep-read/{source_id}.md.
   b. Se timeout → agent_close → rlm_close → marcar FAILED.
   c. Se erro → agent_close → rlm_close → marcar FAILED.
   d. ⚠ IMPORTANTE: após agent_close, executar rlm_close(name="dr-{source_id}")
      explicitamente. O sub-agent pode não ter tido chance de fazê-lo.

### 4.3 Paywall Circuit Breaker (F-2)

Para fontes sem entrada em mapping.json (inventários antigos):
1. Tentar até 3 rotas de acesso.
2. Se falhar → INACCESSIBLE (não re-tentar).
3. Se ≥5 fontes consecutivas resultarem INACCESSIBLE → interromper Stage 4.

### 4.4 Saturation Checkpoint (F-5)

Após cada batch de 3 fontes:
1. compute_saturation(last_n=2).
2. Escrever _saturation_check.md.
3. Se saturation==True OU max_deep_reads atingido OU circuit breaker global
   acionado → STOP, prosseguir para Stage 5.

⚠ Check também ao final do processamento (último batch pode ter <3 fontes).
Se a última fonte processada foi a N-ésima e saturation foi atingida no batch
anterior, a decisão já foi tomada.

### 4.5 Context Budget

Após cada batch, verificar context pressure. Se >70% → /compact + continuar.
No modo F-0 (paralelo), o contexto do orquestrador cresce mais devagar porque
os sub-agents isolam o processamento pesado.
```

---

## 5. File Inventory

### Arquivos modificados

| Arquivo | Touch por | Tipo de mudança |
|---------|-----------|-----------------|
| `references/pipeline-detail.md` | F-0, F-1, F-2, F-3, F-4, F-5, F-6 | Adicionar fluxo wrapper F-0; adicionar timeout ao RLM contract; adicionar §4.0 (paywall breaker + integração com mapping.json); expandir RLM contract com cleanup e detecção de falha; adicionar chamada ao `enforce_source_caps.py` com fluxo draft-final; adicionar checkpoint de saturação; adicionar §4.2.0 (per-source budget guidelines) |
| `references/deep-reading.md` | F-0, F-1 | Adicionar `sub_query_timeout_secs=120` e padrão wrapper ao RLM contract |
| `references/error-recovery.md` | F-2 | Adicionar linhas "Paywall irresolvível" e "5+ INACCESSIBLE consecutivos" à tabela |
| `SKILL.md` | F-3, F-5 | (Opcional, se budget de linhas permitir) Adicionar RLM sweep na retomada; nota sobre checkpoint de saturação |
| `scripts/stage_status.py` | F-5 | Adicionar detecção de `_saturation_check.md` para Stage 4 resume |
| `scripts/pipeline_metrics.py` | F-7 | Adicionar classificação de deep reads (completed/failed/inaccessible/orphan) |

### Arquivos novos

| Arquivo | De | Propósito |
|---------|-----|-----------|
| `scripts/enforce_source_caps.py` | F-4 | Truncar fontes excedentes por eixo após Stage 2 |
| `dev-docs/SPEC-005-freeze-resilience.md` | — | Esta SPEC |

---

## 6. Risk Triggers

| Risco | Probabilidade | Impacto | Indicador | Mitigação |
|-------|--------------|---------|-----------|-----------|
| F-0: Sub-agent Flash não tem acesso às tools RLM (`rlm_open`/`rlm_eval`/`rlm_close`) | M | F-0 não implementável; fallback para orquestrador direto | Erro "tool not allowed" ao abrir sub-agent | Usar fallback: orquestrador faz `rlm_open`, sub-agent só faz `rlm_eval`/`rlm_close` |
| F-0: Sub-agents paralelos consomem contexto excessivo do orquestrador | M | Context budget do orquestrador esgotado mais rápido | Context pressure > 70% durante Stage 4 | Limitar paralelismo a 3 sub-agents simultâneos; usar `/compact` entre batches |
| `sub_query_timeout_secs=120` muito curto para documentos grandes (>200KB, 25+ chunks) | M | Fonte marcada FAILED falsamente | Documentos T4 são seletivos (não batch completo); T3 ≤ 200KB → ≤ 25 chunks | Ajustar para 180s se falsos positivos >10% |
| Timeout do `rlm_eval` não é respeitado pelo runtime RLM | L | Comportamento igual ao atual (hang) | Testar com documento T3 grande | F-0 isola o hang em sub-agent; `agent_close` força `rlm_close` |
| `enforce_source_caps.py` remove fonte crítica que o dsr-bibliography priorizou | L | Perda de source relevante | Ordenação por relevance desc; desempate por source_id | Fontes removidas são listadas no inventory para auditoria |
| Paywall circuit breaker global (5 consecutivos) interrompe Stage 4 prematuramente | L | Fontes acessíveis após as 5 paywalled são perdidas | Fontes ordenadas por relevância; paywalled tendem a ser high-relevance | Ajustar threshold para 7 se falso positivo |
| `stage_status.py` modificado interpreta `_saturation_check.md` incorretamente em retomada | L | Stage 4 considerado completo quando não está | Arquivo contém "STOP" mas nem todas as fontes planejadas foram processadas | Verificar também contagem de deep reads vs `max_deep_reads` |

---

## 7. Acceptance Criteria (Cross-fix)

Após implementação de F-0 a F-7:

1. **F-0: Isolamento de hang:** Sessão de teste com documento T3 (100KB) onde `rlm_eval` força timeout → `agent_eval` retorna timeout em ≤600s. Orquestrador chama `agent_close` → `rlm_close`. Pipeline processa próxima fonte. Sem congelamento do orquestrador.
2. **F-0: Paralelismo:** 3 sub-agents de deep read disparam simultaneamente. Cada um processa uma fonte T3. Orquestrador consolida resultados conforme cada um completa.
3. **F-1: Timeout de queries filhas:** Dentro de um sub-agent F-0, `sub_query_batch` com `sub_query_timeout_secs=120` conclui ou falha em ≤120s.
4. **F-2: Paywall sem re-tentativa:** Fonte com `pdfs/mapping.json` status `unavailable` → INACCESSIBLE sem fetch_url. Pipeline não bloqueia.
5. **F-2: Circuit breaker global:** 5 fontes consecutivas INACCESSIBLE → Stage 4 interrompido. Orquestrador prossegue para Stage 5.
6. **F-3: Cleanup após falha:** `rlm_eval` retorna erro → `rlm_close` no mesmo turno. `handle_read` retorna None → `rlm_close` no mesmo turno.
7. **F-3: RLM sweep na retomada:** Sessão interrompida durante Stage 4 → ao retomar, RLM sweep fecha sessões órfãs antes de abrir novas.
8. **F-4: Cap enforcement:** Sessão com 30+ fontes por eixo → `enforce_source_caps.py` trunca a 20. Inventory final tem ≤20 por eixo. `max_sources_per_axis=0` desabilita o cap.
9. **F-5: Checkpoint + resume:** `_saturation_check.md` escrito após cada verificação. `stage_status.py` detecta "STOP" no checkpoint e considera Stage 4 concluído na retomada.
10. **F-6: Budget guidelines:** Documentado no pipeline-detail.md. Timeouts do F-0/F-1 alinhados com budgets por tier.
11. **F-7: Métricas de output:** `pipeline_metrics.py` reporta classificação completed/failed/inaccessible/orphan. Arquivos 0-byte → orphan indicators.

---

## 8. Sign-off

Esta SPEC endereça os 3 vetores de congelamento identificados na sessão `2026-05-26-physical-dynamics-as-computation` mais a restrição arquitetural fundamental (orquestrador síncrono). 

**F-0 (`sub-agent wrapper`) é o fix de maior impacto:** em vez de tentar adicionar timeouts onde a arquitetura não permite, isola a operação bloqueante em um sub-agent com timeout próprio. Transforma "orquestrador congelado" em "sub-agent expirado → `agent_close` → próximo".

**F-1 (`sub_query_timeout_secs`) agora complementa F-0:** opera dentro do wrapper para evitar que queries filhas bloqueiem o sub-agent.

**Mudanças em relação à versão original da SPEC:**
- Adicionado F-0 (wrapper) como fundação arquitetural
- F-2 agora integra com `pdfs/mapping.json` do Stage 3.1 e inclui circuit breaker global
- F-3 adiciona critérios explícitos de detecção de falha e RLM sweep na retomada
- F-4 corrige o fluxo chicken-and-egg (draft → enforce → final) e adiciona guarda `max_per_axis > 0`
- F-5 requer modificação em `stage_status.py`
- F-6 renomeado para "guidelines" — honesto sobre ser documentação, não mecanismo
- F-7 limitado a métricas computáveis de output files (sem dependência de logs de runtime)

**Esforço total revisado:** ~4.5h (3.5h originais + 1h para F-0; estimativas dos demais fixes mantidas).

**Implementação recomendada:** F-0 primeiro (é a fundação). F-1, F-2, F-3 em paralelo após F-0. F-4, F-5, F-7 em paralelo. F-6 é documentação e pode ser feito a qualquer momento. Coordenar F-5 com I-9 (`stage_status.py`) e F-7 com I-10 (`pipeline_metrics.py`) do plano v3.2 para evitar conflitos de merge.
