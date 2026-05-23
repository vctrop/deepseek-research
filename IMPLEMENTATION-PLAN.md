# Plano de Correções e Melhorias — deepseek-research v1.7.0 → v1.7.1

**Base:** ANALYSIS-REPORT-001.md + TEST-REPORT.md
**Data:** 2026-05-23
**Total de alterações:** 12 (6 correções + 6 melhorias)

---

## Resumo

| ID | Tipo | Severidade | Origem | Arquivo(s) afetado(s) |
|----|------|-----------|--------|----------------------|
| FIX-1 | Correção | 🟡 BUG | B1 — Stage 2.1 skip logic | `SKILL.md`, `references/pipeline-detail.md` |
| FIX-2 | Correção | 🟡 BUG | B2 — Stage 2.2 skip logic | `SKILL.md`, `references/pipeline-detail.md` |
| FIX-3 | Correção | 🟡 BUG | B3 — MANIFEST × GATE-8 contradição | `references/pipeline-detail.md` |
| FIX-4 | Correção | 🟠 CRASH | C1 — Session state ausente após Stage 3.5 | `references/pipeline-detail.md` |
| FIX-5 | Correção | 🟠 CRASH | C2 — Rate-limiting em negative searches | `references/pipeline-detail.md` |
| FIX-6 | Correção | 🔵 OBS | O1 — Config override não documentado | `references/pipeline-detail.md` |
| IMP-1 | Melhoria | — | Smoke test: _build_per_topic_queries | `scripts/smoke_test.py` |
| IMP-2 | Melhoria | — | Smoke test: todos os 10 builders | `scripts/smoke_test.py` |
| IMP-3 | Melhoria | — | Crash recovery: flag `resumed_from_crash` | `references/pipeline-detail.md` |
| IMP-4 | Melhoria | — | Deep read: limpeza de artefatos (S*_raw.html) | `references/pipeline-detail.md` |
| IMP-5 | Melhoria | — | MANIFEST: registrar Stage 1.7 override | `references/pipeline-detail.md` |
| IMP-6 | Melhoria | — | Documentar dois modos de negative search | `references/subagent-prompts.md` |

---

## Correções (FIX-1 a FIX-6)

### FIX-1: Stage 2.1 skip logic — contar eixos que retornaram fontes, não eixos do config

**Raiz:** B1 — `SKILL.md` linha 215: `Run ONLY if source_axes has ≥2 axes that returned sources.` O orchestrator interpretou `source_axes` como a variável de config (`["web", "grey"]`), mas após Stage 1.7 adicionar `opensource`, a condição deveria avaliar os eixos que efetivamente produziram fontes no Source Inventory (3 eixos).

**Alteração em `SKILL.md` linha 215:**

```
DE:
**Condition:** Run ONLY if `source_axes` has ≥2 axes that returned sources.

PARA:
**Condition:** Run ONLY if ≥2 axes returned at least 1 source in `02-source-inventory.md`.
Count axes from the Discovery Summary table, not from config — Stage 1.7 may have
added opensource dynamically.
```

**Alteração em `references/pipeline-detail.md` — adicionar após Stage 2 (Source Discovery), antes de Stage 2.1:**

Inserir nova subseção "Stage 2.1 — Condition Evaluation":
```markdown
### Stage 2.1 Condition Check

Before deciding to skip Stage 2.1, count axes from the **Discovery Summary** table
in `02-source-inventory.md`, NOT from the config variable `source_axes`:

```
grep_files(pattern="^\| (web|grey|bibliography|codebase|opensource) \|",
           path="{session_dir}/02-source-inventory.md")
```

Count the number of unique axis names matched. If ≥2, execute reconciliation.
If <2, skip with reason "single-axis discovery" and advance to Stage 2.2.

**Rationale:** Stage 1.7 may dynamically add `opensource` to the active axes.
Counting from the inventory table reflects what actually ran, not what was configured.
```

---

### FIX-2: Stage 2.2 skip logic — verificar eixo web nos resultados, não no config

**Raiz:** B2 — `SKILL.md` linha 227: `Run ONLY if "web" is in source_axes.` O orchestrator pulou com razão "web not primary axis", sugerindo que interpretou a condição como algo além de "web está presente" (possivelmente "web é o único eixo" ou "web é o eixo primário").

**Alteração em `SKILL.md` linha 227:**

```
DE:
**Condition:** Run ONLY if `"web"` is in `source_axes`.

PARA:
**Condition:** Run ONLY if web axis returned at least 1 source in `02-source-inventory.md`.
Check the Discovery Summary table — row `web` must have `Sources found ≥ 1`.
```

**Alteração em `references/pipeline-detail.md` — adicionar após Stage 2.1, antes de Stage 2.2:**

```markdown
### Stage 2.2 Condition Check

Do NOT check the config variable `source_axes`. Instead, verify from the inventory:

```
grep_files(pattern="^\| web \| [1-9]", path="{session_dir}/02-source-inventory.md")
```

If the web axis row shows ≥1 source found, execute PRESS review.
If 0 sources or web axis absent from inventory, skip with reason "web axis returned 0 sources."
```

---

### FIX-3: GATE-8 — alinhar verificação com a skip logic corrigida

**Raiz:** B3 — MANIFEST reportou GATE-8 como N/A "thresholds not computed" enquanto Stage 2.2 estava marcado como skip "web not primary axis". Com FIX-2 aplicado, Stage 2.2 executará corretamente quando web tiver fontes.

**Alteração em `references/pipeline-detail.md` §GATE-8 (linha ~954):**

```
DE:
**GATE-8 — PRISMA + PRESS compliance.**

PARA:
**GATE-8 — PRISMA + PRESS compliance.**
**Condition:** Run ONLY if Stage 2.2 (PRESS Review) executed.
If Stage 2.2 was skipped (web axis returned 0 sources): SKIP with note "no web sources to review."
```

Adicionar verificação explícita no comando do gate:
```
# Pre-check: did Stage 2.2 execute?
grep_files(pattern="PRESS Review", path="{session_dir}/02-source-inventory.md")
# If no match: SKIP (Stage 2.2 was skipped).
# If match: proceed with PRISMA/PRESS checks below.
```

---

### FIX-4: Session state checkpoint após Stage 3.5

**Raiz:** C1 — Nenhum `.session-state.json` foi encontrado após o crash na Sessão 1. O último estado escrito apontava para Stage 3.5, mas sem o arquivo, a Sessão 2 teve que inferir o estado a partir dos arquivos existentes.

**Alteração em `references/pipeline-detail.md` §Stage 3.5:**

Adicionar ao final da seção Stage 3.5 (após o último passo de deep reading), antes de avançar para Stage 4:

```markdown
N. **Checkpoint — session state after deep reading:**
   After all Level A deep reads complete and `_consolidation.md` is written,
   write session state BEFORE advancing to Stage 4:

   ```
   code_execution → helpers.write_session_state("{session_dir}",
     current_stage="4",
     last_completed_stage="3.5",
     current_checklist_item=10,
     deep_read_level_a_count={N},
     deep_read_level_b_pending={M})
   ```

   This is a critical checkpoint — Stage 3.5 is the most expensive stage and
   the most likely to be interrupted. If the pipeline crashes after this point,
   Stage 4 (Synthesis) can resume directly without re-running deep reads.

   **Crash recovery at this checkpoint:**
   - Check `MANIFEST.txt` for `## Gate Results`. If absent, Close is still pending.
   - Count `S*.md` files in `deep-reads/`. If ≥1 exist, deep reading is complete.
   - Resume from Stage 4 (Synthesis), not Stage 3.5.
```

---

### FIX-5: Retry para negative searches com rate-limiting

**Raiz:** C2 — 4 queries de negative search em Stage 2.6 foram bloqueadas por rate-limiting. O sub-agente derivou evidência contrária das fontes primárias (comportamento correto), mas a pipeline não tentou re-executar as queries.

**Alteração em `references/pipeline-detail.md` §Stage 2.6 (Adversarial Search):**

Adicionar após o passo de sub-agent dispatch:

```markdown
3a. **Rate-limit recovery (if needed):**
    After sub-agent returns, check the Search Audit table for blocked queries:
    ```
    grep_files(pattern="blocked|rate.limit", path="{session_dir}/01c-adversarial-results.md")
    ```
    If ≥2 queries were blocked AND no adversarial sources were found:
    - Wait 30 seconds (backoff).
    - Re-dispatch the sub-agent with the blocked queries only.
    - If still blocked after 2 retries, proceed with note "adversarial search incomplete
      due to rate-limiting — contrary evidence derived from primary sources only."
    - Record the retry count in `01c-adversarial-results.md`.
```

---

### FIX-6: Documentar Stage 1.7 override no MANIFEST

**Raiz:** O1 — MANIFEST não registra que `opensource` foi adicionado dinamicamente pelo Stage 1.7, causando inconsistência entre o config reportado e os eixos que executaram.

**Alteração em `references/pipeline-detail.md` §Stage 1.7:**

Adicionar após o passo 4 (auto-add opensource):

```markdown
4a. **Record override in MANIFEST:**
    ```
    write_file(path="{session_dir}/MANIFEST.txt", content="...",
      append="\n## Config Overrides\n- Stage 1.7: Auto-added `opensource` to source_axes (score {score} ≥ 6)\n")
    ```
    This ensures the MANIFEST documents that active axes differ from the config file.
```

E em SKILL.md §Stage 1.7, adicionar ao header:

```
DE:
**Condition:** Run ALWAYS. Determines whether `opensource` axis should be active.

PARA:
**Condition:** Run ALWAYS. Determines whether `opensource` axis should be active.
If opensource is added, record the override in MANIFEST.txt under `## Config Overrides`.
```

---

## Melhorias (IMP-1 a IMP-6)

### IMP-1: Smoke test — adicionar _build_per_topic_queries

**Raiz:** TEST-REPORT.md — Próximo passo #4: esta função não tem cobertura no smoke test atual.

**Alteração em `scripts/smoke_test.py` — adicionar após Test 2 (linha ~140, após `_build_adversarial_prompt`):**

```python
    # _build_per_topic_queries
    from prompts import _build_per_topic_queries
    
    result = _build_per_topic_queries("TBT,CBH,FEP", '"limitations of {topic}"')
    check("_build_per_topic_queries 3 topics → 3 lines",
          len([l for l in result.strip().split('\n') if l.strip()]) == 3)
    
    result_empty = _build_per_topic_queries("", "pattern {topic}")
    check("_build_per_topic_queries empty → empty string",
          result_empty.strip() == "")
    
    result_single = _build_per_topic_queries("single", "query {topic}")
    check("_build_per_topic_queries single → 1 line",
          len([l for l in result_single.strip().split('\n') if l.strip()]) == 1)
    
    result_trim = _build_per_topic_queries("a, b , c", "topic:{topic}")
    check("_build_per_topic_queries trim whitespace",
          len([l for l in result_trim.strip().split('\n') if l.strip()]) == 3)
```

---

### IMP-2: Smoke test — testar todos os 10 builders via dispatcher

**Raiz:** Smoke test atual só testa `_build_adversarial_prompt` diretamente. Os outros 9 builders não são testados no smoke test (apenas na execução manual G4).

**Alteração em `scripts/smoke_test.py` — adicionar após IMP-1:**

```python
    # build_subagent_prompt dispatcher — all 10 templates
    from helpers import build_subagent_prompt
    
    builder_tests = {
        'dsr-bibliography': dict(rq_text='Test RQ', bibliography_path='/tmp', main_topic='test'),
        'dsr-web': dict(rq_text='Test RQ', main_topic='test'),
        'dsr-code': dict(rq_text='Test RQ'),
        'dsr-opensource': dict(rq_text='Test RQ', main_topic='test'),
        'dsr-grey': dict(rq_text='Test RQ', main_topic='test'),
        'dsr-deep-read': dict(source_id='S1', source_path_or_url='http://ex.com',
                              source_title='T', rq_text='RQ', skill_dir=str(SKILL_DIR),
                              session_dir='/tmp'),
        'dsr-deep-read-t5': dict(source_id='S1', repo_url='http://ex.com',
                                 rq_text='RQ', skill_dir=str(SKILL_DIR), session_dir='/tmp'),
        'dsr-adversarial': dict(rq_text='RQ', included_sources_json='[]', main_topic='test'),
        'dsr-da': dict(session_dir='/tmp', skill_dir=str(SKILL_DIR)),
        'dsr-tiebreak': dict(rq_text='RQ', bibliography_path='/tmp',
                             disagreement_list='S1: INCLUDE vs EXCLUDE'),
    }
    
    for name, kwargs in builder_tests.items():
        try:
            prompt = build_subagent_prompt(name, **kwargs)
            check(f"build_subagent_prompt({name})",
                  prompt is not None and len(prompt) > 100,
                  f"got {len(prompt) if prompt else 0} chars")
        except Exception as e:
            check(f"build_subagent_prompt({name})", False, str(e))
    
    # Invalid name must raise
    try:
        build_subagent_prompt('invalid-name', rq_text='x')
        check("build_subagent_prompt(invalid) raises", False, "should have raised ValueError")
    except (ValueError, KeyError):
        check("build_subagent_prompt(invalid) raises", True)
```

---

### IMP-3: MANIFEST — adicionar flag `resumed_from_crash`

**Raiz:** Sessão 2 retomou de um crash mas não há registro no MANIFEST. Isso é essencial para rastreabilidade.

**Alteração em `references/pipeline-detail.md` §Close — adicionar ao início:**

```markdown
### Pre-flight: Crash Recovery Detection

Before executing Close, check whether this session was resumed from a crash:

1. Count `S*.md` files with timestamps separated by >1 hour from other stage outputs:
   ```
   exec_shell(command="ls -lt --time-style=full-iso {session_dir}/deep-reads/S*.md 2>/dev/null | head -5")
   ```
2. If deep read files have timestamps >1 hour before synthesis/MANIFEST files,
   this session was resumed. Record in MANIFEST:
   ```
   ## Recovery
   resumed_from_crash: true
   sessions_used: 2
   session_1_completed_through: Stage 3.5 (deep reading)
   session_2_resumed_from: Stage 4 (synthesis)
   ```
```

---

### IMP-4: Limpeza de artefatos no Close

**Raiz:** `deep-reads/S3_raw.html` ficou como artefato residual no diretório da sessão.

**Alteração em `references/pipeline-detail.md` §Close — adicionar ao Auto-Run Procedure, antes dos gates:**

```markdown
0. **Cleanup artifacts from deep reading:**
   Remove raw HTML dumps and temporary files created during Stage 3.5:
   ```
   exec_shell(command="rm -f {session_dir}/deep-reads/*_raw.html {session_dir}/deep-reads/*.tmp 2>/dev/null")
   ```
   These are intermediate artifacts, not final outputs.
```

---

### IMP-5: MANIFEST — seção `## Config Overrides`

**Raiz:** Além do FIX-6 (registrar override pontual), o MANIFEST deve ter uma seção estruturada para todos os overrides.

**Alteração em `references/pipeline-detail.md` §Stage 1.7 — complementar FIX-6:**

```markdown
## Config Overrides section in MANIFEST

The MANIFEST.txt template should include a `## Config Overrides` section.
Populate it at Close with all deviations from the config file:

```
## Config Overrides
| Override | Stage | Reason |
|----------|-------|--------|
| opensource added to source_axes | 1.7 | Score 8/12 ≥ 6 (auto-enabled) |
```

If no overrides occurred, write "None — config matched execution."
```

---

### IMP-6: Subagent prompts — documentar fallback para negative search

**Raiz:** C2 — o sub-agente `dsr-web` derivou evidência contrária de fontes primárias quando as queries negativas foram bloqueadas. Isso deve ser documentado como comportamento esperado.

**Alteração em `references/subagent-prompts.md` — adicionar ao final da seção `dsr-web`:**

```markdown
### Negative Search Rate-Limiting Fallback

When negative/contrary search queries are blocked by rate-limiting:

1. Attempt up to 2 retries with 30-second backoff between attempts.
2. If still blocked: extract contrary evidence from primary search results:
   - Look for paragraphs discussing "limitations," "failure cases," "criticism" in
     positive search results.
   - Flag these as "derived from primary sources — not from dedicated contrary search."
3. Record the derivation method in the output's Search Audit table.
4. Do NOT fabricate negative results — only extract from actual sources found.
```

---

## Ordem de Aplicação

| # | ID | Arquivo | Depende de |
|---|-----|---------|------------|
| 1 | FIX-1 | `SKILL.md` + `pipeline-detail.md` | — |
| 2 | FIX-2 | `SKILL.md` + `pipeline-detail.md` | — |
| 3 | FIX-3 | `pipeline-detail.md` | FIX-2 |
| 4 | FIX-4 | `pipeline-detail.md` | — |
| 5 | FIX-5 | `pipeline-detail.md` | — |
| 6 | FIX-6 | `SKILL.md` + `pipeline-detail.md` | — |
| 7 | IMP-1 | `smoke_test.py` | — |
| 8 | IMP-2 | `smoke_test.py` | — |
| 9 | IMP-3 | `pipeline-detail.md` | — |
| 10 | IMP-4 | `pipeline-detail.md` | — |
| 11 | IMP-5 | `pipeline-detail.md` | FIX-6 |
| 12 | IMP-6 | `subagent-prompts.md` | — |

---

## Verificação Pós-Correção

Após aplicar todas as alterações:

```bash
# 1. Smoke test deve passar (novos testes incluídos)
python3 scripts/smoke_test.py --verbose

# 2. Contagem de gates: 23 em SKILL.md e pipeline-detail.md
grep -c "GATE-" SKILL.md
grep -c "GATE-" references/pipeline-detail.md

# 3. Linhas do SKILL.md (deve ficar ≤550 após adições)
wc -l SKILL.md

# 4. Builders: 10/10 compilam
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from helpers import build_subagent_prompt
for name in ['dsr-bibliography','dsr-web','dsr-code','dsr-opensource','dsr-grey',
             'dsr-deep-read','dsr-deep-read-t5','dsr-adversarial','dsr-da','dsr-tiebreak']:
    p = build_subagent_prompt(name, **{
        'dsr-bibliography': dict(rq_text='x', bibliography_path='/tmp', main_topic='t'),
        'dsr-web': dict(rq_text='x', main_topic='t'),
        'dsr-code': dict(rq_text='x'),
        'dsr-opensource': dict(rq_text='x', main_topic='t'),
        'dsr-grey': dict(rq_text='x', main_topic='t'),
        'dsr-deep-read': dict(source_id='S1', source_path_or_url='http://x.com', source_title='T', rq_text='RQ', skill_dir='.', session_dir='/tmp'),
        'dsr-deep-read-t5': dict(source_id='S1', repo_url='http://x.com', rq_text='RQ', skill_dir='.', session_dir='/tmp'),
        'dsr-adversarial': dict(rq_text='RQ', included_sources_json='[]', main_topic='t'),
        'dsr-da': dict(session_dir='/tmp', skill_dir='.'),
        'dsr-tiebreak': dict(rq_text='RQ', bibliography_path='/tmp', disagreement_list='x'),
    }[name])
    assert p and len(p) > 100, f'{name} FAIL'
print('10/10 builders OK')
"
```
