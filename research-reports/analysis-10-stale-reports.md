# Segunda Análise Crítica: Os Erros Ainda Aconteceriam?

**Data:** 2026-05-23
**Contexto:** As 6 frentes de correção foram implementadas nos commits `be79a49` + `47b8a0a`.
**Pergunta:** A versão corrigida da skill ainda cometeria os mesmos erros dos 10 relatórios stale?

---

## Resposta Curta

**Sim, vários deles.** As correções são majoritariamente constrangimentos estruturais
(templates, regras documentadas, campos obrigatórios nos headers) que dependem de
um orquestrador LLM disciplinado para executá-las. Nenhuma correção é um
*enforcement automático* — código determinístico que bloqueia o pipeline se
violado. A skill melhorou significativamente, mas o problema fundamental persiste:
**o executor do pipeline é uma LLM, e LLMs podem pular etapas, interpretar regras
de forma frouxa, ou reportar métricas falsas.**

---

## Mapeamento Falha → Correção → Persistência

### Falha 1: URLs fabricadas (sub-agente Flash gera arXiv ID errado)

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Prevenção na origem | Nenhuma — sub-agente podia reportar qualquer URL | Prompt exige `fetch_url` de verificação + anti-hallucination rule |
| Detecção | Nenhuma — GATE-0 não existia | GATE-0: fetch_url + title match em toda fonte com URL |
| **Persiste?** | — | **Sim, se o orquestrador pular o GATE-0** |

**Por que:** O GATE-0 é uma instrução no SKILL.md, não um script executado
automaticamente. Se o orquestrador (LLM Pro) estiver com pressa, contexto cheio,
ou simplesmente confiar que "o arXiv é confiável", ele pode pular a verificação
— exatamente como fez com "ACCESSIBLE (inferred)" antes.

**Cenário de falha:** Orquestrador processa 30 fontes, vê que a maioria é arXiv,
decide "vou verificar só as não-arxiv". Uma URL fabricada de arXiv passa.

**Mitigação real:** O prompt hardening (sub-agente verifica antes de reportar)
é a defesa mais forte, porque atua na origem. Mas se o sub-agente Flash alucinar
um ID e depois `fetch_url` nele retornar 404, ele deve excluí-lo. Se ele alucinar
um ID que por acaso existe (paper diferente), só o GATE-0 pega.

---

### Falha 2: Fontes não verificadas (19/25 "ACCESSIBLE inferred")

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Categoria "inferred" | Existia e era usada livremente | Abolida dos templates |
| **Persiste?** | — | **Sim, por omissão** |

**Por que:** O template agora força o orquestrador a escolher ACCESSIBLE,
UNVERIFIABLE, HALLUCINATED, ou EXCLUDED. Mas se ele não fizer `fetch_url`, a
escolha é arbitrária. Ele pode:
- Marcar como ACCESSIBLE sem verificar (confia na URL) → mesmo efeito do "inferred"
- Marcar como UNVERIFIABLE sem tentar → perde fontes válidas

**Cenário de falha:** Orquestrador tem 40 fontes, `fetch_url` é lento (1.5-4s
delay por request = 2-3 minutos). Decide verificar só as 10 primeiras. As outras
30 ficam sem status ou são marcadas como UNVERIFIABLE por timeout implícito.

**Mitigação real:** Nenhuma. O template constrange, mas não força. A única
solução seria um script Python que itera sobre `02-source-inventory.md`, faz
`fetch_url` em cada URL, e escreve `03-source-verification.md` — mas isso
exigiria acesso programático ao `fetch_url`, que é um tool do modelo, não uma
função Python.

---

### Falha 3: Deep reads superficiais (W2: 3 claims, 26 linhas)

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Coverage reportada | Opcional, raramente presente | Obrigatória no header do deep read |
| Consequência de coverage baixa | Nenhuma — claims superficiais podiam ser STRONG | Coverage cap: <25% → SPECULATIVE, <50% → cap MODERATE |
| **Persiste?** | — | **Parcialmente** |

**Por que:** Se o orquestrador fizer um deep read superficial (só abstract +
introdução) e reportar coverage honesta (ex: 25%), o cap limita o dano —
SPECULATIVE não gera findings STRONG. OK, funciona.

Mas se o orquestrador reportar coverage falsa (ex: 90% quando só leu 25%), o
sistema é bypassado. Um orquestrador LLM pode fazer isso sem intenção maliciosa
— basta interpretar "coverage" como "coverage das seções que eu li" em vez de
"coverage do documento inteiro".

**Cenário de falha:** Paper de 200KB, orquestrador lê introdução (10KB) +
conclusão (5KB). Reporta: "Coverage: 100% (li introdução e conclusão, que contêm
todos os claims relevantes)". Isso é 7.5% de coverage real, mas o orquestrador
racionalizou como 100%.

**Mitigação real:** O campo `Chunks processed: N of M` força o orquestrador a
declarar quantos chunks processou. Se ele usou RLM chunking, o número de chunks
é determinístico. Mas se ele usou T4 (seletiva) ou T2 (paginado), não há
verificação externa. E mesmo com RLM, o orquestrador pode mentir sobre `M`.

---

### Falha 4: Snippets classificados como V-grade (v2.0 W-04)

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Regra | Inexistente | "Snippets e sumários não são V-grade" documentada |
| Template | Sem indicação da fonte dos claims | Campo `Access method` obrigatório |
| **Persiste?** | — | **Parcialmente** |

**Por que:** A classificação V/P/I/M ainda é feita por LLM. Se o orquestrador
classificar um snippet como V-grade, há uma inconsistência detectável:
`Access method: snippets_only` + `Grade: V` → contradição. Mas não há um gate
automático que cruza esses dois campos.

**Cenário de falha:** O orquestrador faz deep read de um paper via snippets.
No campo Access method escreve "snippets_only" (correto). Mas na tabela de
claims, classifica C1 como "V" porque o snippet continha uma frase entre aspas
que *parecia* verbatim. O orquestrador não percebe que há 2 hops de paráfrase
entre o texto real do paper e o snippet.

**Mitigação real:** A regra documentada + campo Access method são fortes. Mas
a única garantia real seria um verificador pós-Stage-4 que lê o Access method
de cada deep read e força todos os claims para I-grade se method for
"snippets_only" ou "abstract_only".

---

### Falha 5: Iron Rule C falsos positivos (GATE-2 frágil)

| Aspecto | Antes | Depois |
|---------|-------|--------|
| GATE-2 | grep cego + inspeção LLM | **Idêntico — sem mudança** |
| **Persiste?** | — | **Sim, integralmente** |

**Por que:** Nenhuma correção foi aplicada ao GATE-2. Ele ainda faz grep de
palavras proibidas e depende de inspeção manual por LLM. Verbatin quotes de
papers ("The results confirm...") ainda disparam falsos positivos. Negações
("not validated") ainda disparam falsos positivos.

**Cenário de falha:** Relatório cita um paper: "Smith et al. (2024) demonstrated
that..." — GATE-2 flag. Orquestrador inspeciona, vê que é citação legítima,
marca PASS. Isso funciona, mas o falso positivo consome atenção e contexto.

**Mitigação real:** Nenhuma. Esta frente ficou de fora do plano de implementação
por ser a mais complexa (requer análise sintática, não regex).

---

### Falha 6: Sem PDF real (v1.0/v2.0: abstract-only)

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Aquisição de PDF | Inexistente | SPEC-003: arXiv PDF → Unpaywall → Sci-Hub |
| **Persiste?** | — | **Sim, por falha de configuração ou omissão** |

**Por que:** O código existe e funciona (smoke test passou). Mas:
1. Requer `unpaywall_email` configurado. Se vazio → Unpaywall pulado → só arXiv PDF.
2. Requer `allow_scihub=true` para Sci-Hub. Default false → só arXiv PDF + Unpaywall.
3. Requer que o orquestrador extraia DOI/arXiv ID do `02-source-inventory.md`.
4. Requer que o orquestrador execute o `code_execution` do Stage 3.1.
5. Se a fonte não tem DOI nem arXiv ID → sem fallback possível.

**Cenário de falha:** Paper da Springer com DOI. `unpaywall_email` configurado.
Unpaywall retorna `is_oa: false` (paper fechado). `allow_scihub=false` (default).
Resultado: `status: "unavailable"`. O orquestrador marca como UNVERIFIABLE para
full-text e o deep read é feito sobre o abstract — exatamente como antes.

**Mitigação real:** Para papers do arXiv, a cobertura melhorou (arXiv PDF é
sempre tentado). Para papers com OA copy, melhorou (Unpaywall). Para papers
fechados sem Sci-Hub, nada mudou.

---

## Novos Riscos Introduzidos pelas Correções

### Risco A: Falsos positivos no GATE-0

O critério de title match (≥50% palavras-chave) pode falhar quando:
- O título na página HTML do arXiv usa formatação diferente (ex: lowercase forcado)
- O título no `02-source-inventory.md` foi truncado pelo sub-agente
- A página HTML retorna um título genérico ("arXiv.org e-Print archive") em vez do título do paper

Uma fonte legítima marcada como HALLUCINATED é removida permanentemente.

### Risco B: Coverage cap pune papers densos

Um paper pode ter 80% de seu conteúdo relevante concentrado em 30% do texto
(ex: a metodologia e resultados estão em 3 seções de 10 páginas cada, enquanto
o paper tem 30 páginas). O orquestrador pode fazer deep reading seletivo dessas
3 seções e reportar coverage 30% → cap MODERATE, mesmo tendo processado todo o
conteúdo relevante.

### Risco C: Complexidade acumulada

Cada correção adiciona passos que o orquestrador deve executar. O Stage 3 agora tem:
1. GATE-0 (fetch_url + title match para cada fonte)
2. PDF acquisition (code_execution para cada fonte com DOI/arXiv)
3. Credibility + RoB
4. Preencher template com 5 colunas de status

Para 30 fontes, isso é potencialmente 30 fetch_url + 15 code_execution +
preenchimento de tabela. O orquestrador pode começar a pular etapas por
fadiga de contexto.

---

## O Que Realmente Fecharia Cada Gap

| Falha | Correção atual (constrangimento) | Correção real (enforcement) |
|-------|----------------------------------|----------------------------|
| URLs fabricadas | GATE-0 como instrução no SKILL.md | Script Python que lê 02-source-inventory.md, faz fetch_url em cada URL, compara títulos, e escreve 03-source-verification.md com coluna Title Match |
| Fontes não verificadas | Categoria "inferred" abolida | Pré-GATE determinístico que bloqueia o Stage 4 se alguma fonte não tiver fetch_url registrado |
| Deep reads superficiais | Coverage obrigatória no header | Pós-GATE que lê coverage_pct de cada deep read e força reclassificação dos claims se coverage < threshold |
| Snippets como V-grade | Regra documentada + Access method | Pós-GATE que cruza Access method com Evidence grade: se method contém "snippet" ou "abstract", todos os claims são downgraded para I-grade |
| Iron Rule C | grep + LLM (inalterado) | Pós-GATE com análise sintática: detectar se a palavra proibida está em verbatim quote (entre aspas + citação), negação, ou contexto de citação |
| Sem PDF | SPEC-003 (code_execution manual) | Pré-GATE que, para cada fonte bibliography, tenta resolve_fulltext automaticamente e popula o campo pdf_path |

**Todos os "corrections reais" compartilham uma propriedade:** são scripts
Python determinísticos executados como gate, não instruções para o orquestrador.
Isso exigiria que o executor do pipeline (DeepSeek TUI) permitisse hooks
automáticos entre estágios — ou que a skill fosse reestruturada como um
programa Python com o LLM como componente, em vez de um prompt com o LLM
como executor.

---

## Veredito

A versão corrigida é **significativamente melhor** que a original. Três das seis
falhas têm mitigação real (não apenas documental): sub-agente agora verifica
fontes, coverage cap limita dano de deep reads superficiais, SPEC-003 provê
aquisição de PDF quando configurada.

Mas a skill **ainda cometeria** versões atenuadas de todos os erros se executada
por um orquestrador LLM descuidado, apressado, ou com contexto cheio. O problema
arquitetural de fundo — um pipeline cujo executor é uma LLM não-determinística —
não foi resolvido. Foi apenas cercado com mais instruções.
