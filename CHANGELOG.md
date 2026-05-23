# Changelog

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
