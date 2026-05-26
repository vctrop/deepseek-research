# Changelog

## v3.1.0 (2026-05-26)

### Added

- **SPEC-005: Freeze Resilience** — 8 fixes para congelamento de runtime no Stage 4:
  - F-0: Sub-agent wrapper para `rlm_eval` com timeout isolation
  - F-1: `sub_query_timeout_secs=120` no contrato RLM
  - F-2: Paywall circuit breaker com integração `pdfs/mapping.json`
  - F-3: RLM cleanup em todos os paths de erro + sweep na retomada
  - F-4: `enforce_source_caps.py` — enforcement determinístico de `max_sources_per_axis`
  - F-5: Checkpoint de saturação em disco (`_saturation_check.md`)
  - F-6: Per-source budget guidelines documentados
  - F-7: Métricas RLM no `pipeline_metrics.py`
- Restrição arquitetural documentada: orquestrador síncrono não pode auto-detectar hangs
- Fluxo integrado de Stage 4 com paralelismo (até 3 sub-agents simultâneos)

### Changed

- `pipeline-detail.md`: Stage 4 redesign pendente (fluxo wrapper + pre-flight filter)
- `deep-reading.md`: contrato RLM atualizado com timeout + wrapper pattern
- `error-recovery.md`: novos cenários (paywall irresolvível, 5+ INACCESSIBLE consecutivos)
- `stage_status.py`: modificação pendente para detectar `_saturation_check.md`
- `pipeline_metrics.py`: extensão pendente com classificação de deep reads

## v3.0.0 (2026-05-23)

### Breaking Changes

- Pipeline reduzido de 15 estágios + 23 gates para 5 estágios + 5 gates
- Foco em pesquisa bibliográfica + análise de código (2 eixos)
- Removidos: meta-análise, GRADE, PRISMA completo, PRESS, grey literature,
  opensource discovery, Devil's Advocate sub-agent separado, living review,
  dual screening + Cohen's κ, pre-registration automática (OSF/Zenodo),
  persistência de corpus, crash recovery stateful
- 7 variáveis de configuração (redução de 24)
- 2 tipos de sub-agent (redução de 10)
- ~1.600 linhas totais (redução de ~80%)

### Added

- `protocol-freeze.json` local (substitui pre-registration automática)
- Adversarial thinking pass inline no Stage 5
- Heurística de saturação para deep reading
- Resume from last stage via output files (sem `.session-state.json`)
- Executive Summary + Methodological Note no report template

### Changed

- SKILL.md: 406 → 211 linhas
- pipeline-detail.md: 1164 → 286 linhas
- deep-reading.md: simplificado, adicionada heurística de saturação
- risk-of-bias.md: 3 níveis (Low/Medium/High), 4+3 perguntas
- error-recovery.md: 10 cenários (redução de 34)
- subagent-prompts.md: apenas dsr-bibliography e dsr-code
- helpers.py: removidos kappa, session state, persistence, protocol, living review
- prompts.py: 2 builders (redução de 9)
- Templates simplificados: FINER, knowledge types, operational definitions,
  PRISMA completo, PRESS, meta-analysis section removidos

### Removed Files

- scripts: meta_analysis.py, grade.py, living_review.py, protocol_registry.py,
  index_sources.py, stage_output.py, bootstrap_config.py
- references: epistemology.md, grade-framework.md, press-checklist.md,
  epistemic-limitations.md, anti-patterns.md, context-budget.md,
  model-matrix.md, placeholders.md, configuration.md
- templates: local-corpus-triage.md, opensource-decision.md, devils-advocate.md,
  stakeholder-review.md, plain-summary.md, decision-brief.md, data-supplement.json
- REVIEW-PHASE-1.md, IMPLEMENTATION-PLAN.md

## v2.x

See git history for v2.x changelog. v2.x-last tag available for users who
need features removed in v3.0.
