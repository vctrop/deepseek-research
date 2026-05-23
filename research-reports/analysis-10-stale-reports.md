# Análise Cross-Relatório: 10 Data Points da Skill deepseek-research v3.0

**Data:** 2026-05-23
**Fonte:** `/home/vctrop/Victor/Ponto-Azul/nux/research-reports/stale_2026-05-23-*`
**Skill version:** `6f4d6a4` (maioria dos relatórios)
**Método:** Análise estrutural de 10 relatórios completos (01 a 05 + deep-reads + MANIFEST + protocol-freeze)

---

## Sumário Executivo

Dos 10 relatórios, **todos** reportam 5/5 GATEs PASS nos MANIFESTs. Isso não reflete qualidade — reflete que os GATEs atuais só verificam estrutura, não verdade. Os 3 problemas identificados na análise da própria skill (URLs fabricadas, verificação pulada, deep reads superficiais) manifestam-se aqui de forma diferente — o pipeline do nux tem mitigadores parciais (usa código local como fonte primária), mas falha consistentemente em fontes bibliográficas externas.

---

## Tabela de Severidade

| Relatório | Fontes | Deep reads | PDFs | Abstract-only | Severidade | Nota |
|-----------|--------|-----------|------|--------------|------------|------|
| v08-planing-waterjet | 17 | 4 (código) | 0 | 0 | MINOR | Sem fontes externas — usa reports internos |
| v09-synthesis | 22 | 4 (bib) | 5 menções | 0 | MINOR | Melhor da classe; busca web rate-limited |
| v1.0-environment | 38 | 4 (2 cód, 2 bib) | 0 | **1 (P6-P9)** | **MODERATE** | RQ2 inteira baseada em abstracts I-grade |
| v1.2-multi-material | 32 | 9 (mix) | 2 menções | 0 | MINOR | Bom equilíbrio código+bib |
| v1.3-compiler-ir | 32 | 8 (mix) | 6 menções | 0 | MINOR | Fontes externas acessadas |
| v1.4-milestone | 29 | 7 (bib) | 1 menção | 0 | MINOR | Tem métricas de chunking |
| v1.5-ground-effect | 18 | 8 (5 PDF, 3 cód) | **9 menções** | 0 | **GOOD** | **Melhor relatório — PDFs reais com read_file** |
| v1.7-credibility | 22 | 6 (mix) | 0 | 0 | MINOR | 0 Iron Rule C violations |
| v1.8-cross-domain | 15 | 4 (mix) | 2 menções | 0 | MINOR | Escopo menor |
| v2.0-lightcompanion | **73** | 6 (6 bib) | 0 | **4 (W-02,W-04,W-07,B-01)** | **SEVERE** | 4/6 deep reads são abstract/snippets; 60 fontes |

---

## Achados por Categoria

### 1. Fontes Externas: O Calcanhar de Aquiles

**Padrão consistente:** Papers acadêmicos externos são sistematicamente sub-processados. Em contraste, código-fonte local e research reports internos são bem processados.

| Relatório | Fontes externas com texto completo | Fontes externas apenas abstract/snippet |
|-----------|-----------------------------------|---------------------------------------|
| v1.0 | 0 | 8 (P6-P9 + W13-W17 como UNVERIFIABLE) |
| v1.5 | 5 (PDFs locais via read_file) | 0 |
| v2.0 | 2 (W-07-web parcial) | 4 (W-02, W-04, W-07-web, B-01) |

**v1.5 é a exceção que prova a regra:** quando PDFs existem localmente, o pipeline os processa com `read_file`. A falha não está no processamento — está na **ausência de aquisição**. A SPEC-003 (Unpaywall + arXiv PDF + Sci-Hub) fecha exatamente este gap.

### 2. v1.0: O Caso da RQ2 Baseada em Abstracts

O deep read `P6-P9-precipitation.md` (59 linhas) declara explicitamente:

> "Status: Rapid evidence assessment via abstracts and snippets. Full papers blocked by Cloudflare/JS challenges. Evidence grade: I (inference from abstracts and search snippets)."

Todas as 7 claims são I-grade. O 05-report.md (linha 84) honestamente reporta:

> "Sources: P6 (Emerald 2022, credibility MEDIUM, evidence: I-grade from abstract)..."

O MANIFEST reporta GATE-3 (Textual Evidence) PASS, mas as claims de precipitation são I-grade — **GATE-3 não valida que claims STRONG tenham evidência V-grade; ele só verifica que claims STRONG em 04-synthesis.md têm citação**. Como o 04-synthesis.md classificou precipitation como MODERATE (não STRONG), o gate passou. Mas o problema real é que **uma RQ inteira é respondida com evidência de qualidade mínima**.

### 3. v2.0: O Caso dos "V-grade" de Snippets

W-04 deep read: "status: PARTIAL — abstract/snippets only; full text not accessed (rate limited)". Claims extraídos de "ScienceDirect snippet", "PMC/NIH snippet", "dsr-bibliography summary". Classificados como V-grade e P-grade.

**Isto é uma classificação incorreta:** Um snippet de busca web não é V-grade (verbatim do paper). É I-grade (inferência de fonte intermediária). O sub-agente dsr-bibliography sumarizou o snippet; o deep read reporta o sumário como V-grade. **Há duas camadas de paráfrase entre o texto real do paper e a claim.**

O MANIFEST lista 10 claims STRONG com "V (verbatim)" — mas W-04-C1 é "ScienceDirect snippet", não o paper. Isso infla artificialmente a confiança do relatório.

### 4. v1.5: O Melhor Relatório — e o Que Ele Prova

5 PDFs processados com `read_file pages 1-5`, `pages 1-3`, etc. Tamanhos reais: 756KB, 1.38MB, 6.78MB, 4.01MB, 1.24MB. O `read_file` extraiu texto de PDFs binários com sucesso.

**O que isso prova:** O mecanismo de extração de PDF já funciona. O problema nunca foi técnico — foi de **aquisição**: os PDFs estavam no `bibliography/` local. A SPEC-003 simplesmente estende isso para PDFs remotos.

Limitação: mesmo em v1.5, a leitura foi seletiva (páginas 1-3, 1-5) — não chunking completo. Coverage real é ~15-30%.

### 5. Iron Rule C: Falsos Positivos em Massa

| Relatório | Hits do grep | Prováveis falsos positivos |
|-----------|-------------|--------------------------|
| v1.0 | 12 | ~8 (verbatim quotes de papers: "The presented results confirm...") |
| v1.5 | 6 | ~4 |
| v2.0 | 3 | ~2 |

O GATE-2 atual faz grep cego de palavras proibidas, sem verificar se são:
- Verbatim quotes de fontes (legítimo)
- Negações ("not validated")
- Contexto de citação ("confirmed in peer-reviewed literature...")

Isso gera falso sentimento de segurança — o gate reporta "PASS" após inspeção manual, mas a inspeção é ela mesma uma LLM. Um gate verdadeiramente deterministico precisa de análise sintática, não regex.

### 6. GATE-0: O Gate que Não Existe

**Zero** relatórios contêm "HALLUCINATED", "Title Mismatch", "fabricated", ou "does not correspond" em seus `03-source-verification.md`. Isso pode significar:

- **(A)** Nenhum sub-agente fabricou URLs (improvável — a taxa de alucinação do Flash é conhecida)
- **(B)** O GATE-0 nunca foi executado (mais provável — não existe no pipeline atual)
- **(C)** Foi executado mas não encontrou problemas (possível para fontes de código local)

A ausência de detecção não é evidência de ausência de fabricação. É evidência de ausência de verificação.

### 7. Coverage: A Métrica Fantasma

Apenas **v1.4** reporta métricas de chunking nos deep reads:
- "Chunks processed: 1 of 1 (100% coverage)"
- "Chunks processed: 1 of 1 (~30% coverage of relevant sections)"

Nenhum outro relatório reporta coverage. Deep reads de código (v08, v1.0, v1.5, v1.7) processam arquivos inteiros — coverage efetivamente 100%, mas não documentada. Deep reads de papers são seletivos (páginas 1-5) com coverage implícita de 15-30%, mas não declarada.

---

## Padrões de Qualidade por Tipo de Fonte

| Tipo de fonte | Processamento típico | Qualidade | Viés |
|--------------|---------------------|-----------|------|
| Código nux local | `read_file` ou `grep_files` completo | **Alta** — V-grade real, linha exata | Viés de confirmação (código próprio) |
| Research reports internos | `read_file` do sumário | **Alta** — V-grade de documento interno | Cita a si mesmo |
| Código OSS clonado | `grep_files` + `read_file` | **Alta** — E-grade com commit hash | — |
| PDFs no bibliography/ | `read_file` seletivo (páginas 1-5) | **Média** — parcial, sem chunking | Só cobre introdução |
| Papers arXiv com HTML | `rlm_open(url=...)` chunking | **Média** — cobertura variável | — |
| Papers com paywall | Apenas abstract/snippet | **Baixa** — I-grade, 2 hops de paráfrase | Viés de acessibilidade |

---

## Recomendações Priorizadas (do plano para a skill)

Com base nos 10 data points, a prioridade de correção é:

| # | Correção | Evidência dos relatórios | Impacto |
|---|----------|------------------------|---------|
| 1 | **SPEC-003 (PDF acquisition)** | v1.5 prova que PDF local funciona; v1.0/v2.0 mostram falha sem PDFs | Fecha o gap entre "abstract-only" e "full-text" |
| 2 | **GATE-0 (Title Match)** | Zero detecções de alucinação — o gate não existe | Previne S6-like fabrications |
| 3 | **Coverage→Confidence binding** | v2.0 W-04: snippets classificados como V-grade | Impede que snippets sejam tratados como evidência STRONG |
| 4 | **Grade reclassification** | Snippet de busca ≠ V-grade; é I-grade com 2 hops | Corrige a taxonomia de evidência para fontes intermediárias |
| 5 | **Iron Rule C sintático** | 12 hits no v1.0, maioria falsos positivos | Substituir grep cego por análise de contexto |
| 6 | **Chunking obrigatório para T3/T4** | Só v1.4 reporta chunking; v1.5 lê só p.1-5 sem chunk | Garantir que "deep read" não significa "li a introdução" |

---

## Nota sobre o Pipeline do Nux vs Pipeline da Skill

Os relatórios do nux foram gerados com a skill, mas em um ambiente diferente:
- Têm `bibliography/` populado com PDFs locais (ex: v1.5)
- Têm `oss/` com clones de JSBSim, ArduPilot, code-house
- Usam código local como fonte primária (reduz dependência de busca web)
- Tiveram busca web rate-limited/blocked (DuckDuckGo + Bing)

Isso criou um viés interessante: os relatórios são **melhores** para claims de código (E-grade com linha exata) e **piores** para claims de literatura (I-grade de snippets). A skill foi originalmente desenhada para pesquisa bibliográfica — mas o ambiente do nux a empurrou para ser uma ferramenta de análise de código. Isso funcionou razoavelmente bem, mas não é o caso de uso para o qual a skill foi otimizada.
