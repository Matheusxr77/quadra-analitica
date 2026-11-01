# Revisão crítica dos textos de interpretação

Relatório gerado em 01/11/2026 sobre o commit `a914ddb` (branch `feat/tabela-descritiva-boxplot`). **Nada foi reescrito ainda**: este documento só aponta problemas e propõe redações. As correções entram depois da aprovação.

## Como os textos foram extraídos e conferidos

- **Extração do texto final**: a aplicação foi executada (`flask run`) e cada página foi renderizada executando o `static/painel.js` real em Node, com um DOM mínimo e as mesmas chamadas `fetch` do navegador. Assim o relatório mostra exatamente o que aparece na tela, inclusive os textos montados no JavaScript (Comparativo, z-score, dicionário).
- **Cobertura**: `/comparativo` nas 21 combinações (Todos, Dallas Mavericks, Indiana Pacers × 7 variáveis), `/assimetria`, `/cv`, `/iqr`, `/qualidade`, `/sintese` e o bloco de vazamento do `/dicionario`. Os textos de `/assimetria`, `/cv`, `/iqr`, `/qualidade` e `/sintese` não dependem dos seletores (são gerais da página).
- **Números (critério c)**: cada número citado foi extraído (pt-BR, vírgula decimal) e comparado com todos os valores da(s) API(s) que alimentam as tabelas e gráficos da mesma página, em 0 a 4 casas, em módulo e em percentual. Valores derivados citados no texto (média − mediana, CV − piso de Poisson, IQR/Mediana ÷ CV, variação % do DP e do IQR sem outliers, média dos dois times, fator de correção do G1) foram recalculados com as fórmulas correspondentes. Constantes declaradas (1,5; 0,05; 240 etc.) foram separadas dos números calculados.
- **Repetição (g)**: cada frase foi reduzida a um modelo (times → ⟨TIME⟩, variáveis → ⟨VAR⟩, números → #) e contada entre contextos.
- **Consistência entre páginas (d)**: G1, CV, IQR e número de outliers de cada time × variável foram comparados entre Assimetria, CV, IQR, Qualidade, Síntese e a tabela descritiva.

### Resultado das verificações automáticas

| Verificação | Resultado |
|---|---|
| Parágrafos extraídos | 231 (174 distintos; o Comparativo repete os mesmos 3 parágrafos-modelo nas 21 combinações) |
| (c) Números que não batem com a API | **0** — o único não reconhecido automaticamente, 62.664, é 2.238 × 28 (conferido) |
| (d) Valores divergentes entre páginas (G1, CV, IQR, nº de outliers) | **0** |
| (i) Parágrafos sem nenhum número calculado | 92 — 63 são do Comparativo e de textos metodológicos; ver proposta de separação "metodologia × interpretação" |
| (g) Frases-modelo repetidas em ≥ 3 contextos | 13 (detalhe no Anexo A) |

Os números estão certos; os problemas são de **conteúdo**: textos fixos, conclusões fortes demais para n ≈ 75, contradições de leitura entre páginas e falta de leitura de basquete.

## Principais achados (por prioridade)

1. **Comparativo ignora o time selecionado e é quase todo fixo** (detalhe na seção própria). Com "Indiana Pacers" e BLK selecionados, o texto diz "Dallas Mavericks apresenta a maior média de BLK" e "A assimetria é moderada" — a classificação é a dos Mavericks (G1 = 0,75); a dos Pacers é aproximadamente simétrica (G1 = 0,43). O texto é idêntico para Todos, Mavericks e Pacers.
2. **3 dos 4 outliers mais sólidos são jogos com prorrogação, e nenhum texto diz isso.** BLK 15 (Mavericks × DET, 18/12/2025, MIN 265), Rebotes 26 (Mavericks × GSW, 23/03/2026, MIN 265) e PF 37 (Pacers × OKC, 23/10/2025, MIN 290 = duas prorrogações). É a melhor leitura de basquete disponível na base e muda a conclusão: "valores plausíveis" passa a ter explicação concreta (mais minutos ⇒ mais faltas e tocos), e sugere analisar por 48 minutos.
3. **Síntese contradiz a Qualidade**: "o ECOD e o K-NN marcam ≈ 5% dos jogos por construção" — desatualizado; hoje ambos usam a taxa calibrada de 0,70%.
4. **CV e IQR apontam times diferentes como "mais regular" em Rebotes e Assistências** sem explicação. Rebotes: CV diz Mavericks (13,76% × 14,85%), IQR diz Pacers (7,00 × 8,00). Assistências: CV diz Pacers, IQR diz Mavericks. A explicação existe (o CV divide pela média — os Mavericks pegam 2,83 rebotes a mais — e usa o DP, que pesa as caudas; o IQR é absoluto e olha só o miolo), mas precisa estar no texto.
5. **Conclusões fortes demais para n ≈ 75.**
   - O erro-padrão do G1 com n = 75 é ≈ 0,28; STL Mavericks (G1 = 0,51) está a 1,8 EP de zero, ou seja, a "assimetria moderada" não se distingue de simetria a 5%. Só BLK Mavericks (2,7 EP) se sustenta — e ele cai para 0,18 sem o jogo de 15 tocos.
   - Diferenças de CV de 0,6 a 1,1 ponto percentual (Pontos, Rebotes, PF) são tratadas como "mais consistente × mais irregular".
   - IQR de dados inteiros: diferenças de 0,25 a 1 unidade entre times (Assistências, PF, Rebotes) são lidas como "mais concentrado".
6. **Contradições internas na Assimetria e no CV**:
   - Assimetria item 6 diz "onde |G1| < 0,5, média e mediana praticamente coincidem" e, na frase seguinte, aponta BLK Pacers (|G1| = 0,43) como o maior afastamento (0,63 toco, 31% de um DP).
   - Recomenda a mediana para BLK Mavericks com média 5,18 × mediana 5,00 (0,18 toco), mas não para BLK Pacers (0,63 toco).
   - CV item 6: STL Mavericks tem razão IQR/Mediana ÷ CV = 1,37, praticamente o valor esperado numa normal (1,35), e mesmo assim o texto conclui que "a medida robusta é a mais adequada".
   - CV item 3 rotula STL e BLK como "irregular" logo depois de o item 2 dizer que o CV alto "não indica irregularidade do time".
7. **Afirmação sem base**: "10 têm G1 positivo, o padrão esperado em contagens limitadas por zero" — vale para STL e BLK (médias 5–7), não para Pontos (≈ 113) ou Rebotes (≈ 43), em que o zero está a mais de 7 DP.
8. **Juízo de valor como fato**: "como menos faltas é melhor, a vantagem é de Mavericks" — menos faltas pode significar defesa menos agressiva; é uma convenção, deve ser declarada como tal.
9. **Português recorrente (h)**:
   - concordância com nome de time: "Pacers é o mais regular", "Mavericks marcou", "a vantagem é de Mavericks" — usar "os Pacers são…", "os Mavericks marcaram", "dos Mavericks";
   - "caso(s)";
   - "sem 1 o outlier";
   - "imputa-se os ausentes" (→ imputam-se);
   - "A assimetria é aproximadamente simétrica";
   - "×" usado como "versus" e como multiplicação na mesma página;
   - contagens com 2 casas no meio do texto ("2 outliers: 7,00, 37,00" — a vírgula decimal se confunde com a da lista);
   - "2238" sem ponto de milhar ao lado de "62.664".
10. **Repetição e texto genérico**:
    - "Interpretar com cautela" (4×) e "há um padrão predominante, com exceções" (CV e IQR, idênticos);
    - os 5 parágrafos do z-score aparecem duplicados na Síntese;
    - "A mediana ajuda a evitar…", "O CV é adimensional…" e "Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta…" em todas as 21 combinações do Comparativo. Esta última frase também é falsa como raciocínio: o critério de outlier não torna a média robusta.

## Tabela de revisão

Legenda dos critérios: **a** genérico · **b** não responde (explicitamente) ao subitem · **c** número não bate · **d** contradição entre/intra páginas · **e** conclusão forte para n ≈ 75 ou causalidade sem base · **f** sem leitura de basquete · **g** repetição · **h** português.
Códigos de subitem do enunciado (docs/Projeto_1.pdf):
- **Estatística descritiva:** D1 média/mediana/moda · D2 outliers (quantos e quais) · D3 mín./máx./amplitude/DP/variância · D4 quartis · D5 boxplot · D6 gráfico de barras e z-score.
- **Assimetria:** A1 fórmula e justificativa · A2 direção · A3 intensidade e critério · A4 confirmação visual (KDE/boxplot, divergências) · A5 comparação entre variáveis e times · A6 implicação prática.
- **CV:** C1 fórmula · C2 validade · C3 interpretação prática · C4 escalas diferentes · C5 regularidade dos times · C6 CV × DP × assimetria · C7 quadro-resumo.
- **IQR:** I1 método dos quartis · I2 tabela Q1/Q3/IQR · I3 interpretação · I4a amplitude · I4b DP · I5 regra de outliers e conferência · I6 comparação dos times · I7 quadro-resumo.
- **Qualidade:** QE valores especiais · QA ausentes, mecanismos e testes · QO outliers por coluna.
- **Síntese:** S, a seção de síntese/interpretação (exigência mínima iv).

| # | Página | Subitem | Trecho atual | Falhas | Sugestão de nova redação |
|---|---|---|---|---|---|
| 1 | Comparativo (21 combinações) | D1 | "Dallas Mavericks apresenta a maior média de BLK, com 5,18 tocos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura." | a, b, d, f, g | Texto do time selecionado: "Os Pacers bloqueiam 4,63 tocos por jogo em média e 4 na mediana; a distribuição é bimodal (3 e 4 tocos). A média fica 0,63 toco acima da mediana (0,31 DP): poucos jogos com muitos tocos puxam a média, então o jogo típico tem 3 a 4 tocos." |
| 2 | Comparativo | C3/C5 | "Em regularidade relativa, Indiana Pacers tem o menor CV (43,49%). O CV é adimensional e permite comparar dispersões…" | a, d, e, g | Para STL/BLK, avisar o piso de Poisson: "O CV de 43,49% parece alto, mas está abaixo dos 46,49% esperados só pela escala pequena (≈ 4,6 tocos): não indica irregularidade." Para as demais, citar a diferença e se ela é relevante. |
| 3 | Comparativo | A2/A3 | "A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos…" | b, c, d, e, g, h | Usar o G1 do time selecionado e dizer qual é: "Para os Pacers, G1 = 0,43: aproximadamente simétrica (|G1| < 0,5), com leve cauda à direita." Remover a frase sobre o critério de outlier (raciocínio incorreto). |
| 4 | Comparativo | D2/D5 | (não existe texto) | b, f | Novo parágrafo (exemplo para Mavericks + BLK): "O boxplot marca 1 outlier — 15 tocos contra DET em 18/12/2025, jogo com prorrogação (265 min). Os bigodes vão de 0 a 10 e a caixa, de 3 a 7: metade dos jogos tem entre 3 e 7 tocos." |
| 5 | Comparativo | D3/D4 | (não existe texto) | b | Comentar amplitude × IQR × DP do time selecionado e a moda (inclusive quando há duas modas ou é amodal). |
| 6 | Comparativo / Síntese | D6 | Parágrafos do z-score repetidos nas duas páginas | g, f | Manter o texto completo no Comparativo; na Síntese, uma frase com o resultado e um link. Acrescentar leitura: "os Pacers arremessam e convertem mais de três (Δz = 0,66) e fazem mais faltas (0,63); os Mavericks pegam mais rebotes (0,45) — perfis de jogo diferentes com pontuação quase igual." |
| 7 | Assimetria | A1 | "convenção de Bulmer, usual para amostras deste tamanho" | e | "Critério de Bulmer (1979). Como referência de incerteza, o erro-padrão do G1 com n = 75 é ≈ 0,28: valores abaixo de ≈ 0,55 em módulo não se distinguem de zero a 5%." |
| 8 | Assimetria | A2 | "PF: Mavericks G1 = 0,02, à direita (positiva)…" (7 linhas) | e, g, f | Manter a direção pelo sinal (pedido do enunciado), mas marcar "|G1| < 0,2: sinal irrelevante". Agrupar em uma frase com as exceções: "Só STL e BLK dos Mavericks se afastam de zero além do ruído." |
| 9 | Assimetria | A3 | "Aproximadamente simétrica: 12 caso(s)." / "Forte: 0 caso(s)." | h | "12 das 14 distribuições são aproximadamente simétricas, 2 têm assimetria moderada e nenhuma é forte." |
| 10 | Assimetria | A3 | "Moderada: 2 caso(s) — STL (Mavericks, 0,51), BLK (Mavericks, 0,75)." | e, h | "STL dos Mavericks (G1 = 0,51) fica no limite: está a 1,8 erro-padrão de zero e pode ser simétrica. BLK dos Mavericks (0,75, 2,7 EP) é a única assimetria clara — e cai para 0,18 sem o jogo de 15 tocos." |
| 11 | Assimetria | A4 | "BLK (Mavericks): G1 = 0,75, mas sem 1 o outlier (15,00) cai para 0,18." | h, f | "…mas, sem o jogo de 15 tocos contra DET (com prorrogação), cai para 0,18." |
| 12 | Assimetria | A4 | "Os outliers inferiores (26,00, 28,00) alongam essa cauda…" | h, f | "Os jogos de 26 e 28 rebotes (o de 26 contra GSW teve prorrogação) alongam a cauda inferior…" |
| 13 | Assimetria | A5 | "…nesses casos |G1| é pequeno e a diferença é de formato sutil, não de comportamento." / lista sem "e" | h, f | "A direção se repete em Assistências, STL e BLK. Nas outras quatro os sinais se opõem, mas todos os |G1| ficam abaixo de 0,40, dentro do ruído amostral." |
| 14 | Assimetria | A6 | "Onde |G1| < 0,5, média e mediana praticamente coincidem… A maior distância relativa ocorre em BLK (Pacers): … 31,15% de um desvio padrão." | d | "A maior distância entre média e mediana está em BLK dos Pacers (0,63 toco, 0,31 DP), mesmo com G1 = 0,43: em contagens pequenas a mediana anda de 1 em 1 e se afasta da média sem que haja cauda longa." |
| 15 | Assimetria | A6 | "STL (Mavericks): média 7,45 × mediana 7,00 …; a mediana representa melhor o valor típico; métodos robustos são preferíveis." (idem BLK) | d, e, g, h | Basear a recomendação na diferença real: "BLK dos Mavericks: média 5,18 e mediana 5 — diferença de 0,18 toco; qualquer uma descreve o jogo típico. A mediana só é preferível se o jogo de 15 tocos for mantido nas análises seguintes." |
| 16 | CV | C2 | 4 parágrafos terminando em "Interpretar com cautela." | g | Um parágrafo único com uma tabela de piso de Poisson; a cautela dita uma vez. |
| 17 | CV | C3 | "STL: Mavericks 41,66% (irregular); Pacers 36,53% (irregular)." / "BLK…(irregular)" | d | Classificar STL e BLK pelo excesso sobre o piso de Poisson, não pela faixa de 30%: "dispersão compatível com a escala (não é irregularidade)". |
| 18 | CV | C3 | "Na prática, nos Mavericks é comum um jogo ficar ±12,65 pontos por jogo em torno da média de 113,85." (7×) | e, f, g, h | "Cerca de 2 em cada 3 jogos dos Mavericks ficam entre 101 e 126 pontos (média ± 1 DP)." Para FG3M: "Os Mavericks oscilam muito nas bolas de três (CV 35,64%): em noites boas e ruins a diferença passa de 7 cestas, o que pesa no placar." |
| 19 | CV | C5 | "Pontos: Pacers é mais consistente (10,47%) e Mavericks mais irregular (11,11%)." (7×) | e, g, h | Só declarar vencedor quando a diferença for relevante (proposta: intervalo bootstrap do CV, ou razão de CVs > 1,2). "Em Pontos, Rebotes e PF os CVs diferem menos de 1,1 ponto: os times são igualmente regulares. A diferença real está em FG3M (35,64% × 23,22%)." |
| 20 | CV / IQR | C5/I6 | "há um padrão predominante, com exceções." (frase idêntica nas duas páginas) | a, e, g | Substituir pela contagem com relevância: "Fora FG3M, nenhuma diferença de regularidade entre os times é grande o bastante para ser atribuída ao time e não ao acaso." |
| 21 | CV | C6 | "STL (Mavericks): … (razão 1,37). Com assimetria moderada, a medida robusta é a mais adequada…" | d, g | "Razão 1,37, quase a esperada numa normal (1,35): CV e IQR/Mediana contam a mesma história, e o CV é adequado aqui." Para BLK (1,58): explicar que o IQR de valores inteiros (4) é largo perto da mediana (5). |
| 22 | CV | C7 | "Maior diferença entre os times: FG3M, 12,42 pontos percentuais." | f | Acrescentar: "Os Pacers convertem mais de três (13,21) e de forma mais estável; nos Mavericks a bola de três é o recurso mais irregular do ataque." |
| 23 | IQR | I2 | "A tabela abaixo mostra Q1, Q3 e IQR…" | a, b | Mover para a legenda da tabela (é texto de navegação, não interpretação). |
| 24 | IQR | I3 | "O IQR é a largura da faixa que contém os 50% centrais dos jogos: IQR baixo = …" | a | Mover para a seção de metodologia. |
| 25 | IQR | I3 | "50% centrais dos jogos dos Mavericks ficaram entre 105,50 e 121,75 (faixa de 16,25)…" (7×) | f, g, h | "Os 50% centrais…". Uma leitura por variável em vez do modelo fixo: "Em faltas, a metade central dos jogos dos Pacers fica entre 18 e 24, quase 3 faltas acima dos Mavericks (15–21): o deslocamento é de nível, não de dispersão." |
| 26 | IQR | I4a | "para uma distribuição normal com n ≈ 75, amplitude/IQR fica em torno de 3,5–4. Acima de 4 a amplitude está sendo esticada por jogos extremos" | e | Usar uma referência simulada (ex.: percentil 95 de amplitude/IQR em normais com n = 75) em vez de um corte fixo em 4. |
| 27 | IQR | I4a | "PF (Pacers): amplitude 30,00 = 5,00 × IQR (6,00); 2 outliers: 7,00, 37,00." | f, h | "PF dos Pacers: amplitude de 30 faltas, 5 vezes o IQR (6), esticada por dois jogos — 7 faltas contra BOS e 37 contra OKC, este com duas prorrogações." |
| 28 | IQR | I4b | "BLK (Mavericks): DP 2,61 → 2,36 sem 1 outlier (−9,72%), enquanto o IQR vai de 4,00 para 4,00 (+0,00%). DP/σ robusto = 0,88." | b, h | Dar o veredito que o subitem pede: "…o IQR não muda. Mesmo assim DP/σ robusto = 0,88 < 1,10: o DP não está inflado, porque o IQR de 4 tocos já é largo para uma média de 5." Trocar "vai de 4,00 para 4,00 (+0,00%)" por "não muda". |
| 29 | IQR | I4b | "A remoção de poucos jogos muda o DP muito mais do que o IQR…" | e, d | Exceção nos próprios números: em Rebotes dos Mavericks o IQR também cai 9,38% (DP −11,09%). "Em 5 dos 6 casos o IQR não muda; em Rebotes dos Mavericks muda quase tanto quanto o DP, porque um dos outliers fica perto do Q1." |
| 30 | IQR | I5 | "Conferência: os outliers listados foram recontados…coincidem exatamente…" | e | A conferência usa os mesmos limites do boxplot e só poderia divergir em caso de bug. Dizer isso e citar a contagem (10 com k = 1,5). |
| 31 | IQR | I5 | "Uma divergência só apareceria se o boxplot usasse outro método de quartis; por isso o gráfico recebe…" | a | Mover para metodologia (detalhe de implementação). |
| 32 | IQR | I6 | "Rebotes: Pacers mais concentrado (IQR 7,00) e Mavericks mais espalhado (8,00)." (7×) | d, e, g | Explicar a divergência com o CV: "Pelo IQR os Pacers são mais concentrados em Rebotes (7 × 8); pelo CV, os Mavericks (13,76% × 14,85%). Não é contradição: o CV divide pela média, e os Mavericks pegam 2,83 rebotes a mais." Diferenças ≤ 1 em dados inteiros: tratar como empate. |
| 33 | IQR | I7 | "A variável mais assimétrica, BLK (|G1| médio 0,59), é onde a diferença entre CV e IQR/Mediana mais importa…" | a, e | Citar a assimetria só dos Mavericks (a dos Pacers é 0,43) e a razão 1,58. |
| 34 | Qualidade | QA | "O recorte bruto do grupo (149 registros) tem 0 e a base tratada tem 0…" / "2238 registros" ao lado de "62.664" | h | "Nem o recorte bruto (149 registros) nem a base tratada têm ausentes…"; escrever 2.238. |
| 35 | Qualidade | QA | "Na prática, imputa-se os ausentes…" | h | "imputam-se os ausentes". |
| 36 | Qualidade | QA | Parágrafo "Não foi aplicado à base real porque…" idêntico nos 4 testes | g | Manter um parágrafo comum acima dos cartões e, em cada teste, só o motivo específico (LS: base de times, sem séries interrompidas; Fairclough: R sem variação; JJ: um único padrão). |
| 37 | Qualidade | QE | "Mavericks marcou em média 129,33 pontos nos 6 jogos prorrogados contra 112,49…" | h, e | "Os Mavericks marcaram em média 129,33 pontos nos 6 jogos com prorrogação, contra 112,49 no tempo normal (só 6 jogos; diferença coerente com os minutos extras)." |
| 38 | Qualidade | QO | "Os casos em que 4 ou mais métodos concordam … BLK 15 (Mavericks, 18/12/2025 contra DET, 6 de 7 métodos) e PF 37…" | f | Acrescentar: "Três desses quatro jogos tiveram prorrogação (BLK 15 e Rebotes 26 com uma; PF 37 com duas): parte do 'extremo' é tempo de jogo a mais." Propor coluna "por 48 min" na tabela. |
| 39 | Qualidade | QO | "Resumo nas 18 colunas… REB (Mavericks, 3)" | h | Usar o nome da variável ("Rebotes") como nas demais páginas, ou a sigla em todas. |
| 40 | Síntese | S | "o ECOD e o K-NN marcam ≈ 5% dos jogos por construção" | c, d | "ECOD, K-NN, DBSCAN e LOF foram calibrados para marcar 0,70% dos jogos em dados normais; o ECOD univariado depende só do posto." |
| 41 | Síntese | S | "10 têm G1 positivo, o padrão esperado em contagens limitadas por zero e sem teto rígido." | e | "10 têm G1 positivo; em STL e BLK (médias 5 a 7) isso combina com contagens perto de zero. Em Pontos e Rebotes o zero está longe demais para explicar o sinal, que é ruído (|G1| ≤ 0,40)." |
| 42 | Síntese | S | "PF: … como menos faltas é melhor, a vantagem é de Mavericks" | e, h | "Convenção adotada: menos faltas é melhor (menos lances livres cedidos). Com ela, a vantagem é dos Mavericks — ressalvando que mais faltas também podem refletir uma defesa mais agressiva." |
| 43 | Síntese | S | "Mavericks leva vantagem em 3 variáveis (Rebotes, BLK e PF) e Pacers leva vantagem em 2…" | e, h | "Os Mavericks levam vantagem em…". Ressalvar que efeitos pequenos (|Δz| < 0,5) com n ≈ 75 não foram testados. |
| 44 | Síntese | S | "Com k = 3 restam 0 e o teste de Grubbs (α = 0,05) confirma 2: são valores pouco comuns, mas plausíveis em basquete" | f, e | Trocar "plausíveis" pela evidência: "dos dois confirmados pelo Grubbs (BLK 15 e PF 37), ambos ocorreram em jogos com prorrogação". |
| 45 | Síntese | S | Seção 5 repete os 5 parágrafos do z-score | g | Resumo de 1 frase + referência ao Comparativo. |
| 46 | Dicionário | — | (vazamento) | — | Sem falhas: números conferidos (147/147, 149/149) e leitura clara. |

## O texto antigo do Comparativo (`construirInterpretacao`, `static/painel.js`)

**Problema verificado** — a função recebe `dados` de `/api/estatisticas` mas usa sempre `dados.comparativo` (os dois times), ignorando `dados.por_time[time]`:

- o texto é **idêntico** para Todos, Mavericks e Pacers (confirmado nas 21 combinações);
- "lider" e "regular" são sempre escolhidos entre os dois times, mesmo com um time selecionado;
- a assimetria exibida é a do time de maior média, sem dizer qual: com Pacers + BLK aparece "moderada" (dos Mavericks) em vez de "aproximadamente simétrica" (dos Pacers);
- 3 das 5 frases são fixas (critérios a, g) e uma é um raciocínio incorreto ("como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta");
- não comenta moda, amplitude, quartis, outliers nem o boxplot — justamente os subitens D1–D5 que a página exibe.

**Correção proposta**

1. Mover a geração do texto para o domínio: `interpretacao.interpretar_variavel(dados, time, variavel)` em Python, testável, e devolver `interpretacao: [parágrafos]` em `/api/estatisticas`. O `painel.js` só renderiza (como já faz em Assimetria/CV/IQR).
2. Conteúdo, para o **time selecionado** (ou os dois lado a lado em "Todos"), com um parágrafo por subitem:
   - **D1:** média, mediana, moda(s) e a distância média − mediana em DP, com o que isso significa para o jogo típico.
   - **D3/D4:** amplitude, IQR e DP, e qual deles descreve melhor a variável.
   - **D2/D5:** quantos e quais outliers (data, adversário e se houve prorrogação), posição da mediana na caixa e os bigodes.
   - **Assimetria (A2/A3):** classificação do próprio time, com a ressalva do erro-padrão.
   - **Comparação (D6):** diferença para o outro time em unidade e em Δz, com a ressalva de Poisson para STL e BLK.
3. Testes: as 21 combinações devem gerar textos diferentes entre Mavericks e Pacers; todo número citado deve vir de `por_time[time]`.

## Proposta para os testes do item 5

- **Separar metodologia de interpretação na API**: cada parágrafo passa a ter `{"texto", "tipo"}`, com `tipo` ∈ {`"interpretacao"`, `"metodologia"`}. Fórmulas, convenções e definições (ex.: "IQR = Q3 − Q1…", "G1 > 0: cauda à direita") ficam como `metodologia` e aparecem no bloco de fórmula/convenções da página, não na interpretação.
- **Teste (i)**: todo parágrafo `interpretacao` de `/api/assimetria`, `/api/cv`, `/api/iqr`, `/api/qualidade`, `/api/sintese`, `/api/perfil-z` e `/api/estatisticas` (21 combinações) contém ao menos um número que não é constante declarada e que vem dos dados.
- **Teste (ii)**: todo número citado (exceto constantes declaradas numa lista única) coincide com um valor da própria API em 0–4 casas, ou com um derivado calculado por fórmula explícita (a mesma usada pelo verificador deste relatório, movida para `tests/verificador_textos.py`).
- **Testes de regressão** para os achados: o Comparativo muda com o time; a Síntese não cita "≈ 5%"; a frase de vantagem em PF declara a convenção; os outliers de jogos com prorrogação são sinalizados.


## Anexo A — Verificações automáticas

### Frases-modelo repetidas em 3 ou mais contextos

| Contextos | Frase-modelo (⟨TIME⟩, ⟨VAR⟩ e # substituem time, variável e número) |
|---|---|
| 21 | A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura. |
| 21 | Em regularidade relativa, ⟨TIME⟩ tem o menor CV (#%). |
| 21 | O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes. |
| 21 | Como o critério de outlier usa # × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem. |
| 15 | A assimetria é aproximadamente simétrica; |
| 4 | Não foi aplicado à base real porque o recorte dos dois times tem # valores ausentes em todas as colunas: o indicador de ausência R é constante (sempre #), não existem padrões de ausência diferentes para comparar e qualquer estatística do teste ficaria indefinida. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # pontos por jogo. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # rebotes por jogo. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # assistências por jogo. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # roubos de bola por jogo. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # tocos por jogo. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # faltas por jogo. |
| 3 | ⟨TIME⟩ apresenta a maior média de ⟨VAR⟩, com # cestas de # por jogo. |

### Números por parágrafo

Para cada parágrafo: números calculados conferidos com a API (✓) e números não reconhecidos. Constantes declaradas (k = 1,5, α = 0,05, 240 min etc.) não contam como calculadas.

| Página | Contexto | Seção | Calculados conferidos | Não reconhecidos |
|---|---|---|---|---|
| comparativo | Todos · Pontos | Interpretação | 1 ✓ | — |
| comparativo | Todos · Pontos | Interpretação | 1 ✓ | — |
| comparativo | Todos · Pontos | Interpretação | 0 ✓ | — |
| comparativo | geral | Onde o z-score entra | 2 ✓ | — |
| comparativo | geral | Onde o z-score entra | 0 ✓ | — |
| comparativo | geral | Onde o z-score entra | 5 ✓ | — |
| comparativo | geral | Onde o z-score entra | 0 ✓ | — |
| comparativo | geral | Onde o z-score entra | 0 ✓ | — |
| comparativo | Indiana Pacers · BLK | Interpretação | 1 ✓ | — |
| comparativo | Indiana Pacers · BLK | Interpretação | 1 ✓ | — |
| comparativo | Indiana Pacers · BLK | Interpretação | 0 ✓ | — |
| assimetria | geral | 1. Coeficiente e fórmula utilizada | 0 ✓ | — |
| assimetria | geral | 1. Coeficiente e fórmula utilizada | 2 ✓ | — |
| assimetria | geral | 1. Coeficiente e fórmula utilizada | 0 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 0 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 0 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 2. Direção (pelo sinal do coeficiente) | 2 ✓ | — |
| assimetria | geral | 3. Intensidade da assimetria | 2 ✓ | — |
| assimetria | geral | 3. Intensidade da assimetria | 1 ✓ | — |
| assimetria | geral | 3. Intensidade da assimetria | 2 ✓ | — |
| assimetria | geral | 3. Intensidade da assimetria | 0 ✓ | — |
| assimetria | geral | 4. Confirmação visual: histograma com KDE e boxplot | 0 ✓ | — |
| assimetria | geral | 4. Confirmação visual: histograma com KDE e boxplot | 2 ✓ | — |
| assimetria | geral | 4. Confirmação visual: histograma com KDE e boxplot | 5 ✓ | — |
| assimetria | geral | 4. Confirmação visual: histograma com KDE e boxplot | 4 ✓ | — |
| assimetria | geral | 5. Comparação entre variáveis e entre times | 7 ✓ | — |
| assimetria | geral | 5. Comparação entre variáveis e entre times | 0 ✓ | — |
| assimetria | geral | 5. Comparação entre variáveis e entre times | 0 ✓ | — |
| assimetria | geral | 6. Implicação prática: média ou mediana? | 2 ✓ | — |
| assimetria | geral | 6. Implicação prática: média ou mediana? | 2 ✓ | — |
| assimetria | geral | 6. Implicação prática: média ou mediana? | 2 ✓ | — |
| assimetria | geral | 6. Implicação prática: média ou mediana? | 0 ✓ | — |
| cv | geral | 1. Fórmula e convenções | 0 ✓ | — |
| cv | geral | 2. Condição de validade | 0 ✓ | — |
| cv | geral | 2. Condição de validade | 0 ✓ | — |
| cv | geral | 2. Condição de validade | 4 ✓ | — |
| cv | geral | 2. Condição de validade | 3 ✓ | — |
| cv | geral | 2. Condição de validade | 4 ✓ | — |
| cv | geral | 2. Condição de validade | 3 ✓ | — |
| cv | geral | 3. Interpretação prática | 0 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 3. Interpretação prática | 4 ✓ | — |
| cv | geral | 4. Comparação entre variáveis de escalas diferentes | 7 ✓ | — |
| cv | geral | 4. Comparação entre variáveis de escalas diferentes | 0 ✓ | — |
| cv | geral | 4. Comparação entre variáveis de escalas diferentes | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 2 ✓ | — |
| cv | geral | 5. Homogeneidade entre os times | 0 ✓ | — |
| cv | geral | 6. CV × desvio padrão × assimetria | 0 ✓ | — |
| cv | geral | 6. CV × desvio padrão × assimetria | 4 ✓ | — |
| cv | geral | 6. CV × desvio padrão × assimetria | 4 ✓ | — |
| cv | geral | 7. Destaques do quadro-resumo | 2 ✓ | — |
| cv | geral | 7. Destaques do quadro-resumo | 1 ✓ | — |
| iqr | geral | 1. Fórmula e método dos quartis | 0 ✓ | — |
| iqr | geral | 2. Q1, Q3 e IQR lado a lado | 0 ✓ | — |
| iqr | geral | 3. Interpretação prática | 0 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 3. Interpretação prática | 6 ✓ | — |
| iqr | geral | 4. IQR × amplitude | 1 ✓ | — |
| iqr | geral | 4. IQR × amplitude | 4 ✓ | — |
| iqr | geral | 4. IQR × amplitude | 4 ✓ | — |
| iqr | geral | 4. IQR × amplitude | 4 ✓ | — |
| iqr | geral | 4. IQR × amplitude | 4 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 0 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 7 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 7 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 7 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 7 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 7 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 7 ✓ | — |
| iqr | geral | 5. IQR × desvio padrão | 0 ✓ | — |
| iqr | geral | 6. IQR e a regra de outliers | 0 ✓ | — |
| iqr | geral | 6. IQR e a regra de outliers | 0 ✓ | — |
| iqr | geral | 6. IQR e a regra de outliers | 0 ✓ | — |
| iqr | geral | 6. IQR e a regra de outliers | 0 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 2 ✓ | — |
| iqr | geral | 7. Comparação entre os times | 0 ✓ | — |
| iqr | geral | 8. Destaques do quadro-resumo | 7 ✓ | — |
| iqr | geral | 8. Destaques do quadro-resumo | 0 ✓ | — |
| iqr | geral | 8. Destaques do quadro-resumo | 1 ✓ | — |
| qualidade | geral | 1. Ausentes | 1 ✓ | 62.664 (= 2.238 × 28, conferido) |
| qualidade | geral | 1. Ausentes | 0 ✓ | — |
| qualidade | geral | 2. Demonstração dos testes | 4 ✓ | — |
| qualidade | geral | 2. Demonstração dos testes | 6 ✓ | — |
| qualidade | geral | 2. Demonstração dos testes | 1 ✓ | — |
| qualidade | geral | 2. Demonstração dos testes | 0 ✓ | — |
| qualidade | geral | 3. Duplicatas | 2 ✓ | — |
| qualidade | geral | 4. Zeros e negativos | 1 ✓ | — |
| qualidade | geral | 5. Valores fora de domínio e o caso do MIN | 0 ✓ | — |
| qualidade | geral | 5. Valores fora de domínio e o caso do MIN | 0 ✓ | — |
| qualidade | geral | 5. Valores fora de domínio e o caso do MIN | 2 ✓ | — |
| qualidade | geral | 5. Valores fora de domínio e o caso do MIN | 4 ✓ | — |
| qualidade | geral | 6. Outliers por variável: quantos e quais jogos | 1 ✓ | — |
| qualidade | geral | 6. Outliers por variável: quantos e quais jogos | 3 ✓ | — |
| qualidade | geral | 6. Outliers por variável: quantos e quais jogos | 0 ✓ | — |
| qualidade | geral | 6. Outliers por variável: quantos e quais jogos | 0 ✓ | — |
| qualidade | geral | 7. Concordância entre os métodos | 1 ✓ | — |
| qualidade | geral | 7. Concordância entre os métodos | 0 ✓ | — |
| qualidade | geral | 8. Resumo nas 18 colunas de box-score | 0 ✓ | — |
| qualidade | geral | 8. Resumo nas 18 colunas de box-score | 0 ✓ | — |
| qualidade | geral | 9. Por que os métodos discordam | 2 ✓ | — |
| qualidade | geral | 9. Por que os métodos discordam | 1 ✓ | — |
| qualidade | geral | 9. Por que os métodos discordam | 0 ✓ | — |
| qualidade | geral | 10. Outliers multivariados | 0 ✓ | — |
| qualidade | geral | 10. Outliers multivariados | 0 ✓ | — |
| qualidade | geral | 10. Outliers multivariados | 0 ✓ | — |
| qualidade | testes de ausência | Teste de Little (MCAR) | 0 ✓ | — |
| qualidade | testes de ausência | Teste de Little (MCAR) | 0 ✓ | — |
| qualidade | testes de ausência | Teste de Jamshidian-Jalal | 0 ✓ | — |
| qualidade | testes de ausência | Teste de Jamshidian-Jalal | 0 ✓ | — |
| qualidade | testes de ausência | Teste de Listing e Schlittgen (LS) | 0 ✓ | — |
| qualidade | testes de ausência | Teste de Listing e Schlittgen (LS) | 0 ✓ | — |
| qualidade | testes de ausência | Regressão logística de Fairclough | 0 ✓ | — |
| qualidade | testes de ausência | Regressão logística de Fairclough | 0 ✓ | — |
| qualidade | mecanismos | MCAR — Missing Completely At Random · Definição | 0 ✓ | — |
| qualidade | mecanismos | MCAR — Missing Completely At Random · Exemplo na NBA | 0 ✓ | — |
| qualidade | mecanismos | MCAR — Missing Completely At Random · Consequência | 0 ✓ | — |
| qualidade | mecanismos | MAR — Missing At Random · Definição | 0 ✓ | — |
| qualidade | mecanismos | MAR — Missing At Random · Exemplo na NBA | 0 ✓ | — |
| qualidade | mecanismos | MAR — Missing At Random · Consequência | 0 ✓ | — |
| qualidade | mecanismos | MNAR — Missing Not At Random · Definição | 0 ✓ | — |
| qualidade | mecanismos | MNAR — Missing Not At Random · Exemplo na NBA | 0 ✓ | — |
| qualidade | mecanismos | MNAR — Missing Not At Random · Consequência | 0 ✓ | — |
| qualidade | exemplo didático | Nota | 1 ✓ | — |
| sintese | geral | 1. Comparação entre os times | 28 ✓ | — |
| sintese | geral | 1. Comparação entre os times | 0 ✓ | — |
| sintese | geral | 2. Forma das distribuições | 1 ✓ | — |
| sintese | geral | 2. Forma das distribuições | 2 ✓ | — |
| sintese | geral | 2. Forma das distribuições | 0 ✓ | — |
| sintese | geral | 3. Regularidade (CV) | 2 ✓ | — |
| sintese | geral | 3. Regularidade (CV) | 0 ✓ | — |
| sintese | geral | 4. Valores atípicos | 6 ✓ | — |
| sintese | geral | 4. Valores atípicos | 0 ✓ | — |
| sintese | geral | 5. Onde o z-score entra no gráfico de barras | 2 ✓ | — |
| sintese | geral | 5. Onde o z-score entra no gráfico de barras | 0 ✓ | — |
| sintese | geral | 5. Onde o z-score entra no gráfico de barras | 5 ✓ | — |
| sintese | geral | 5. Onde o z-score entra no gráfico de barras | 0 ✓ | — |
| sintese | geral | 5. Onde o z-score entra no gráfico de barras | 0 ✓ | — |
| sintese | geral | 6. Qualidade e preparo da base | 1 ✓ | — |
| sintese | geral | 6. Qualidade e preparo da base | 2 ✓ | — |
| sintese | geral | 7. Limitações | 0 ✓ | — |
| sintese | geral | 7. Limitações | 0 ✓ | — |
| sintese | geral | 7. Limitações | 0 ✓ | — |
| sintese | geral | 8. Conclusão | 1 ✓ | — |
| sintese | geral | 8. Conclusão | 1 ✓ | — |
| dicionario | geral | Vazamento | 4 ✓ | — |
| dicionario | geral | Vazamento | 0 ✓ | — |

O Comparativo foi verificado nas 21 combinações; a tabela mostra duas como amostra porque o texto é o mesmo modelo.

Inconsistências de valores entre páginas: 0.

## Anexo B — Texto final extraído, por página

### /comparativo

**Todos · Pontos — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de Pontos, com 113,85 pontos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (10,47%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Onde o z-score entra** _(origem: sintese.py: textos_zscore)_

> Nas barras em unidades originais, cada variável tem a sua escala: Pontos ficam em torno de 113,03 por jogo e BLK em torno de 4,90. Num mesmo gráfico, a diferença entre os times em BLK desaparece ao lado da escala de Pontos, e a comparação entre variáveis não faz sentido.

> O z-score entra justamente aí: em vez da média bruta, cada barra mostra z = (média do time − média dos jogos dos dois times) ÷ desvio padrão desses jogos. Todas as variáveis passam a ser medidas em desvios padrão, num eixo comum e sem unidade, e as barras ficam comparáveis entre si.

> Lendo o gráfico: a variável que mais separa os times é FG3M (Pacers acima, Δz = 0,66), seguida de PF (Pacers acima, Δz = 0,63) e Rebotes (Mavericks acima, Δz = 0,45); a que menos separa é STL (Mavericks acima, Δz = 0,07). Nenhuma média de time se afasta mais que 0,33 desvio padrão da referência: a diferença entre os times é pequena perto da variação de jogo para jogo.

> Como a referência é formada pelos próprios dois times, a média dos z ponderada pelo número de jogos é zero: as barras dos dois times aparecem quase espelhadas em torno do zero. O que importa é a distância entre elas (Δz), que equivale a uma diferença padronizada de médias.

> O z-score também pode entrar no gráfico por jogo, e não por média: z de cada partida, com |z| > 3 marcando valores extremos — é o critério Z-score usado na página Qualidade dos dados.

**Todos · Rebotes — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de Rebotes, com 44,53 rebotes por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Dallas Mavericks tem o menor CV (13,76%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à esquerda (negativa). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Todos · Assistências — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de Assistências, com 27,20 assistências por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (19,55%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Todos · STL — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de STL, com 7,45 roubos de bola por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (36,53%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Todos · BLK — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de BLK, com 5,18 tocos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (43,49%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Todos · PF — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de PF, com 21,21 faltas por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Dallas Mavericks tem o menor CV (21,86%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à esquerda (negativa). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Todos · FG3M — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de FG3M, com 13,21 cestas de 3 por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (23,22%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · Pontos — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de Pontos, com 113,85 pontos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (10,47%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · Rebotes — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de Rebotes, com 44,53 rebotes por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Dallas Mavericks tem o menor CV (13,76%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à esquerda (negativa). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · Assistências — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de Assistências, com 27,20 assistências por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (19,55%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · STL — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de STL, com 7,45 roubos de bola por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (36,53%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · BLK — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de BLK, com 5,18 tocos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (43,49%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · PF — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de PF, com 21,21 faltas por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Dallas Mavericks tem o menor CV (21,86%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à esquerda (negativa). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Dallas Mavericks · FG3M — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de FG3M, com 13,21 cestas de 3 por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (23,22%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · Pontos — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de Pontos, com 113,85 pontos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (10,47%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · Rebotes — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de Rebotes, com 44,53 rebotes por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Dallas Mavericks tem o menor CV (13,76%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à esquerda (negativa). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · Assistências — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de Assistências, com 27,20 assistências por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (19,55%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · STL — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de STL, com 7,45 roubos de bola por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (36,53%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · BLK — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Dallas Mavericks apresenta a maior média de BLK, com 5,18 tocos por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (43,49%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é moderada; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · PF — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de PF, com 21,21 faltas por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Dallas Mavericks tem o menor CV (21,86%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à esquerda (negativa). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

**Indiana Pacers · FG3M — Interpretação** _(origem: painel.js: construirInterpretacao)_

> Indiana Pacers apresenta a maior média de FG3M, com 13,21 cestas de 3 por jogo. A mediana ajuda a evitar que partidas muito fora do padrão distorçam essa leitura.

> Em regularidade relativa, Indiana Pacers tem o menor CV (23,22%). O CV é adimensional e permite comparar dispersões mesmo quando as métricas possuem escalas diferentes.

> A assimetria é aproximadamente simétrica; distribuição à direita (positiva). Como o critério de outlier usa 1,5 × IQR, a leitura central permanece robusta a extremos e deve ser preferida quando média e mediana se afastarem.

### /assimetria

**1. Coeficiente e fórmula utilizada** _(origem: interpretacao.py: _textos_assimetria)_

> Usamos o coeficiente ajustado de Fisher-Pearson (G1), implementado por pandas.Series.skew — o mesmo valor de scipy.stats.skew(bias=False).

> Justificativa: cada time tem 74 e 75 jogos. O coeficiente de momento de Pearson (g1) é viesado em amostras finitas; o fator √(n(n−1))/(n−2) corrige esse viés (1,0208 para n = 74, 1,0205 para n = 75). Como os jogos são uma amostra do desempenho do time, a versão ajustada é a coerente com o desvio padrão amostral (n − 1) usado no restante do projeto.

> O coeficiente de Bowley, (Q3 + Q1 − 2·Mediana)/IQR, é exibido só como verificação robusta: ele usa apenas os quartis e por isso não é afetado por jogos extremos, mas também ignora as caudas — por isso não substitui o G1.

**2. Direção (pelo sinal do coeficiente)** _(origem: interpretacao.py: _textos_assimetria)_

> G1 > 0: cauda mais longa à direita (positiva); G1 < 0: cauda à esquerda (negativa); G1 = 0: simétrica.

> 10 das 14 combinações variável × time têm assimetria positiva e 4 negativa.

> Pontos: Mavericks G1 = 0,23, à direita (positiva); Pacers G1 = −0,33, à esquerda (negativa)

> Rebotes: Mavericks G1 = −0,40, à esquerda (negativa); Pacers G1 = 0,12, à direita (positiva)

> Assistências: Mavericks G1 = 0,38, à direita (positiva); Pacers G1 = 0,22, à direita (positiva)

> STL: Mavericks G1 = 0,51, à direita (positiva); Pacers G1 = 0,44, à direita (positiva)

> BLK: Mavericks G1 = 0,75, à direita (positiva); Pacers G1 = 0,43, à direita (positiva)

> PF: Mavericks G1 = 0,02, à direita (positiva); Pacers G1 = −0,11, à esquerda (negativa)

> FG3M: Mavericks G1 = −0,10, à esquerda (negativa); Pacers G1 = 0,14, à direita (positiva)

**3. Intensidade da assimetria** _(origem: interpretacao.py: _textos_assimetria)_

> Critério adotado: |G1| < 0,5 aproximadamente simétrica; 0,5 ≤ |G1| < 1,0 moderada; |G1| ≥ 1,0 forte (convenção de Bulmer, usual para amostras deste tamanho).

> Aproximadamente simétrica: 12 caso(s).

> Moderada: 2 caso(s) — STL (Mavericks, 0,51), BLK (Mavericks, 0,75).

> Forte: 0 caso(s).

**4. Confirmação visual: histograma com KDE e boxplot** _(origem: interpretacao.py: _textos_assimetria)_

> No histograma, assimetria positiva aparece como cauda mais longa à direita da KDE; no boxplot, como mediana mais próxima de Q1 e bigode/outliers mais longos para cima (o inverso para negativa). Use os seletores abaixo para ver cada variável.

> O coeficiente e os gráficos contam a mesma história em 12 de 14 casos (G1, Bowley e média − mediana com o mesmo sinal, ou G1 tão perto de zero que o sinal é ruído, |G1| < 0,20).

> Rebotes (Mavericks): G1 = −0,40, Bowley = 0,25 e média − mediana = 0,53 apontam direções diferentes. G1 pesa as caudas (momentos de 3ª ordem), enquanto Bowley e a posição da mediana descrevem o miolo da distribuição; a cauda e o centro estão inclinados para lados opostos. Os outliers inferiores (26,00, 28,00) alongam essa cauda e explicam o sinal de G1.

> BLK (Mavericks): G1 = 0,75, mas sem 1 o outlier (15,00) cai para 0,18. A assimetria vem de poucos jogos extremos: no histograma aparece como uma barra isolada na cauda e no boxplot como ponto fora do bigode, enquanto a caixa (Bowley = 0,00) é quase simétrica.

**5. Comparação entre variáveis e entre times** _(origem: interpretacao.py: _textos_assimetria)_

> Ordem por |G1| médio dos dois times (mais assimétrica primeiro): BLK (0,59), STL (0,48), Assistências (0,30), Pontos (0,28), Rebotes (0,26), FG3M (0,12), PF (0,06).

> As mais assimétricas são BLK e STL; as mais simétricas, PF e FG3M.

> A direção se repete nos dois times em Assistências, STL, BLK; em Pontos, Rebotes, PF, FG3M os times têm sinais opostos — nesses casos |G1| é pequeno e a diferença é de formato sutil, não de comportamento.

**6. Implicação prática: média ou mediana?** _(origem: interpretacao.py: _textos_assimetria)_

> Onde |G1| < 0,5, média e mediana praticamente coincidem e a média é um bom valor típico. A maior distância relativa ocorre em BLK (Pacers): |média − mediana| = 0,63 tocos por jogo, 31,15% de um desvio padrão.

> STL (Mavericks): média 7,45 × mediana 7,00 (roubos de bola por jogo); a mediana representa melhor o valor típico; métodos robustos são preferíveis.

> BLK (Mavericks): média 5,18 × mediana 5,00 (tocos por jogo); a mediana representa melhor o valor típico; métodos robustos são preferíveis.

> Nenhuma variável atinge |G1| ≥ 1, então transformação logarítmica não é necessária; quando houver assimetria moderada causada por poucos jogos extremos, métodos robustos (mediana, IQR) bastam.

### /cv

**1. Fórmula e convenções** _(origem: interpretacao.py: _textos_cv)_

> CV = s / x̄ × 100, com s = desvio padrão amostral (divisor n − 1) e x̄ = média aritmética. O resultado é apresentado em percentual (%), com 2 casas — mesma convenção do desvio padrão e da variância da tabela descritiva.

**2. Condição de validade** _(origem: interpretacao.py: _textos_cv)_

> Escala de razão: todas as sete variáveis são contagens por jogo, com zero absoluto (0 tocos significa ausência de tocos), então razões entre valores fazem sentido e o CV é aplicável. Todas as médias são positivas.

> Critério de cautela: média < 10 por jogo. Com média pequena, o denominador do CV é pequeno e qualquer variação de 1 ou 2 unidades vira um percentual alto. Além disso, em contagens do tipo Poisson a variância é próxima da média, logo CV ≈ 100/√média: há um piso de CV que depende só da escala, não da regularidade do time.

> STL (Mavericks): média 7,45, CV 41,66% e piso Poisson 100/√média = 36,65% — o CV fica só 5,01 pontos percentuais acima do piso, ou seja, quase todo o CV alto vem da escala pequena e não de irregularidade do time. Interpretar com cautela.

> STL (Pacers): média 7,24, CV 36,53% e piso Poisson 100/√média = 37,16% — o CV não passa do piso esperado pela escala: o valor alto não indica irregularidade do time. Interpretar com cautela.

> BLK (Mavericks): média 5,18, CV 50,50% e piso Poisson 100/√média = 43,96% — o CV fica só 6,54 pontos percentuais acima do piso, ou seja, quase todo o CV alto vem da escala pequena e não de irregularidade do time. Interpretar com cautela.

> BLK (Pacers): média 4,63, CV 43,49% e piso Poisson 100/√média = 46,49% — o CV não passa do piso esperado pela escala: o valor alto não indica irregularidade do time. Interpretar com cautela.

**3. Interpretação prática** _(origem: interpretacao.py: _textos_cv)_

> Faixas adotadas: CV < 15% consistente; 15–30% variabilidade moderada; > 30% irregular de um jogo para outro.

> Pontos: Mavericks 11,11% (consistente); Pacers 10,47% (consistente). Na prática, nos Mavericks é comum um jogo ficar ±12,65 pontos por jogo em torno da média de 113,85.

> Rebotes: Mavericks 13,76% (consistente); Pacers 14,85% (consistente). Na prática, nos Pacers é comum um jogo ficar ±6,19 rebotes por jogo em torno da média de 41,69.

> Assistências: Mavericks 21,19% (moderada); Pacers 19,55% (moderada). Na prática, nos Mavericks é comum um jogo ficar ±5,37 assistências por jogo em torno da média de 25,34.

> STL: Mavericks 41,66% (irregular); Pacers 36,53% (irregular). Na prática, nos Mavericks é comum um jogo ficar ±3,10 roubos de bola por jogo em torno da média de 7,45.

> BLK: Mavericks 50,50% (irregular); Pacers 43,49% (irregular). Na prática, nos Mavericks é comum um jogo ficar ±2,61 tocos por jogo em torno da média de 5,18.

> PF: Mavericks 21,86% (moderada); Pacers 22,56% (moderada). Na prática, nos Pacers é comum um jogo ficar ±4,79 faltas por jogo em torno da média de 21,21.

> FG3M: Mavericks 35,64% (irregular); Pacers 23,22% (moderada). Na prática, nos Mavericks é comum um jogo ficar ±3,84 cestas de 3 por jogo em torno da média de 10,78.

**4. Comparação entre variáveis de escalas diferentes** _(origem: interpretacao.py: _textos_cv)_

> Ordem por CV médio dos dois times (mais dispersa primeiro): BLK (46,99%), STL (39,09%), FG3M (29,43%), PF (22,21%), Assistências (20,37%), Rebotes (14,31%), Pontos (10,79%).

> Relativamente mais dispersas: BLK e STL; mais estáveis: Pontos e Rebotes.

> O desvio padrão bruto levaria à conclusão errada: Pontos tem o maior DP (12,20 pontos por jogo) e BLK o menor (2,31 tocos por jogo), mas o DP está na unidade de cada variável e cresce com a escala. O CV divide pelo nível médio e é adimensional, por isso permite a comparação.

**5. Homogeneidade entre os times** _(origem: interpretacao.py: _textos_cv)_

> Pontos: Pacers é mais consistente (10,47%) e Mavericks mais irregular (11,11%).

> Rebotes: Mavericks é mais consistente (13,76%) e Pacers mais irregular (14,85%).

> Assistências: Pacers é mais consistente (19,55%) e Mavericks mais irregular (21,19%).

> STL: Pacers é mais consistente (36,53%) e Mavericks mais irregular (41,66%).

> BLK: Pacers é mais consistente (43,49%) e Mavericks mais irregular (50,50%).

> PF: Mavericks é mais consistente (21,86%) e Pacers mais irregular (22,56%).

> FG3M: Pacers é mais consistente (23,22%) e Mavericks mais irregular (35,64%).

> Pacers é o mais regular em 5 de 7 variáveis e Mavericks em 2; há um padrão predominante, com exceções.

**6. CV × desvio padrão × assimetria** _(origem: interpretacao.py: _textos_cv)_

> O CV usa média e desvio padrão, que são sensíveis a caudas longas. Como alternativa robusta mostramos IQR/Mediana × 100. Para dados aproximadamente normais, IQR/Mediana ≈ 1,35 × CV; razões muito diferentes disso indicam que extremos ou o formato pesam no CV.

> STL (Mavericks): G1 = 0,51, CV = 41,66%, IQR/Mediana = 57,14% (razão 1,37). Com assimetria moderada, a medida robusta é a mais adequada para descrever a dispersão típica.

> BLK (Mavericks): G1 = 0,75, CV = 50,50%, IQR/Mediana = 80,00% (razão 1,58). Com assimetria moderada, a medida robusta é a mais adequada para descrever a dispersão típica.

**7. Destaques do quadro-resumo** _(origem: interpretacao.py: _textos_cv)_

> Maior CV: BLK (Mavericks), 50,50%. Menor CV: Pontos (Pacers), 10,47%.

> Maior diferença entre os times: FG3M, 12,42 pontos percentuais.

### /iqr

**1. Fórmula e método dos quartis** _(origem: interpretacao.py: _textos_iqr)_

> IQR = Q3 − Q1. Os quartis são calculados por interpolação linear entre as estatísticas de ordem (método padrão de numpy/pandas, tipo 7 de Hyndman & Fan): posição h = (n − 1)·p + 1 nos dados ordenados. É o mesmo método usado na tabela descritiva e no boxplot, portanto os três mostram os mesmos Q1, Q3 e limites.

**2. Q1, Q3 e IQR lado a lado** _(origem: interpretacao.py: _textos_iqr)_

> A tabela abaixo mostra Q1, Q3 e IQR por variável e por time, junto da amplitude e do desvio padrão para as comparações dos próximos itens.

**3. Interpretação prática** _(origem: interpretacao.py: _textos_iqr)_

> O IQR é a largura da faixa que contém os 50% centrais dos jogos: IQR baixo = time concentrado em torno do seu típico; IQR alto = desempenho central espalhado.

> Pontos (pontos por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 105,50 e 121,75 (faixa de 16,25); 50% centrais dos jogos dos Pacers ficaram entre 105,00 e 119,00 (faixa de 14,00).

> Rebotes (rebotes por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 41,00 e 49,00 (faixa de 8,00); 50% centrais dos jogos dos Pacers ficaram entre 38,00 e 45,00 (faixa de 7,00).

> Assistências (assistências por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 22,00 e 28,75 (faixa de 6,75); 50% centrais dos jogos dos Pacers ficaram entre 23,50 e 31,00 (faixa de 7,50).

> STL (roubos de bola por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 5,00 e 9,00 (faixa de 4,00); 50% centrais dos jogos dos Pacers ficaram entre 6,00 e 9,00 (faixa de 3,00).

> BLK (tocos por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 3,00 e 7,00 (faixa de 4,00); 50% centrais dos jogos dos Pacers ficaram entre 3,00 e 6,00 (faixa de 3,00).

> PF (faltas por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 15,25 e 21,00 (faixa de 5,75); 50% centrais dos jogos dos Pacers ficaram entre 18,00 e 24,00 (faixa de 6,00).

> FG3M (cestas de 3 por jogo): 50% centrais dos jogos dos Mavericks ficaram entre 9,00 e 14,00 (faixa de 5,00); 50% centrais dos jogos dos Pacers ficaram entre 11,00 e 15,00 (faixa de 4,00).

**4. IQR × amplitude** _(origem: interpretacao.py: _textos_iqr)_

> Referência: para uma distribuição normal com n ≈ 75, amplitude/IQR fica em torno de 3,5–4. Acima de 4 a amplitude está sendo esticada por jogos extremos — a amplitude depende só do mínimo e do máximo, o IQR ignora os 25% de cada ponta.

> PF (Pacers): amplitude 30,00 = 5,00 × IQR (6,00); 2 outliers: 7,00, 37,00.

> Rebotes (Pacers): amplitude 30,00 = 4,29 × IQR (7,00); 2 outliers: 26,00, 56,00.

> Rebotes (Mavericks): amplitude 34,00 = 4,25 × IQR (8,00); 2 outliers: 26,00, 28,00.

> Pontos (Pacers): amplitude 59,00 = 4,21 × IQR (14,00); 2 outliers: 78,00, 83,00.

**5. IQR × desvio padrão** _(origem: interpretacao.py: _textos_iqr)_

> Comparamos o DP com o σ robusto = IQR/1,349 (o valor que o DP teria se a distribuição fosse normal com aquele IQR) e recalculamos DP e IQR sem os outliers de Tukey. DP/σ robusto > 1,10 indica DP inflado pelas caudas.

> Pontos (Pacers): DP 11,75 → 10,63 sem 2 outliers (−9,53%), enquanto o IQR vai de 14,00 para 14,00 (+0,00%). DP/σ robusto = 1,13.

> Rebotes (Mavericks): DP 6,13 → 5,45 sem 2 outliers (−11,09%), enquanto o IQR vai de 8,00 para 7,25 (−9,38%). DP/σ robusto = 1,03.

> Rebotes (Pacers): DP 6,19 → 5,76 sem 2 outliers (−7,02%), enquanto o IQR vai de 7,00 para 7,00 (+0,00%). DP/σ robusto = 1,19.

> STL (Pacers): DP 2,64 → 2,54 sem 1 outlier (−3,93%), enquanto o IQR vai de 3,00 para 3,00 (+0,00%). DP/σ robusto = 1,19.

> BLK (Mavericks): DP 2,61 → 2,36 sem 1 outlier (−9,72%), enquanto o IQR vai de 4,00 para 4,00 (+0,00%). DP/σ robusto = 0,88.

> PF (Pacers): DP 4,79 → 4,16 sem 2 outliers (−13,16%), enquanto o IQR vai de 6,00 para 6,00 (+0,00%). DP/σ robusto = 1,08.

> A remoção de poucos jogos muda o DP muito mais do que o IQR: evidência de que o IQR é a medida de dispersão robusta.

**6. IQR e a regra de outliers** _(origem: interpretacao.py: _textos_iqr)_

> Regra adotada: k = 1,5 (Tukey). Limites: Q1 − 1,5×IQR e Q3 + 1,5×IQR, recalculados na tabela abaixo. É a regra clássica do boxplot; k = 3 marcaria só valores 'extremos' e é mostrado para comparação.

> Com k = 1,5 há 10 outliers no total; com k = 3, 0.

> Conferência: os outliers listados foram recontados diretamente na base para cada variável e time e coincidem exatamente com os pontos fora dos bigodes do boxplot (mesmos quartis e mesmo k).

> Uma divergência só apareceria se o boxplot usasse outro método de quartis; por isso o gráfico recebe Q1, Q3 e limites prontos do servidor em vez de recalculá-los no navegador.

**7. Comparação entre os times** _(origem: interpretacao.py: _textos_iqr)_

> Pontos: Pacers mais concentrado (IQR 14,00) e Mavericks mais espalhado (16,25).

> Rebotes: Pacers mais concentrado (IQR 7,00) e Mavericks mais espalhado (8,00).

> Assistências: Mavericks mais concentrado (IQR 6,75) e Pacers mais espalhado (7,50).

> STL: Pacers mais concentrado (IQR 3,00) e Mavericks mais espalhado (4,00).

> BLK: Pacers mais concentrado (IQR 3,00) e Mavericks mais espalhado (4,00).

> PF: Mavericks mais concentrado (IQR 5,75) e Pacers mais espalhado (6,00).

> FG3M: Pacers mais concentrado (IQR 4,00) e Mavericks mais espalhado (5,00).

> Pacers é o mais concentrado em 5 de 7 variáveis e Mavericks em 2; há um padrão predominante, com exceções.

**8. Destaques do quadro-resumo** _(origem: interpretacao.py: _textos_iqr)_

> Como o IQR está na unidade de cada variável, a comparação entre variáveis usa IQR/Mediana: BLK 77,50%, STL 50,00%, FG3M 39,19%, PF 28,77%, Assistências 27,66%, Rebotes 17,63%, Pontos 13,38%.

> Entre as três mais dispersas pelo IQR/Mediana e pelo CV coincidem: BLK, FG3M, STL — CV e IQR contam a mesma história de dispersão.

> A variável mais assimétrica, BLK (|G1| médio 0,59), é onde a diferença entre CV e IQR/Mediana mais importa: o IQR descreve o jogo típico sem ser puxado pela cauda.

### /qualidade

**1. Ausentes** _(origem: qualidade.py: _textos_*)_

> A fonte tem 0 valores ausentes em 62.664 células (2238 registros × 28 colunas). O recorte bruto do grupo (149 registros) tem 0 e a base tratada tem 0: a conversão de tipos não gerou ausentes.

> Sem ausentes, o indicador de ausência R é constante e os testes de mecanismo não têm o que comparar (no Little não há segundo padrão; na logística de Fairclough não há variação em R). Por isso eles são aplicados abaixo a cópias com ausência simulada, para mostrar como seriam usados e decididos.

**2. Demonstração dos testes** _(origem: qualidade.py: _textos_*)_

> MCAR simulado (30 de 149 valores de PTS removidos): Little d² = 10,24, gl = 6, p = 0,1150 → não rejeita MCAR. Fairclough: razão de verossimilhança = 10,61, gl = 6, p = 0,1012 → não rejeita MCAR. Os p-valores de Wald abaixo de 0,05 em AST e FG3M não contam como evidência: com o teste global não significativo e 6 coeficientes testados, o corte corrigido de Bonferroni seria 0,0083.

> MAR simulado (48 de 149 valores de PTS removidos): Little d² = 43,05, gl = 6, p = 0,0000 → rejeita MCAR. Fairclough: razão de verossimilhança = 54,14, gl = 6, p = 0,0000 → rejeita MCAR; a ausência é explicada sobretudo por FG3M (razão de chances 6,67 por desvio padrão, p = 0,0000), que deveria entrar no modelo de imputação.

> Sob MCAR verdadeiro, um teste com α = 0,05 ainda rejeita em cerca de 5% das amostras; por isso a semente da simulação (42) é fixa e declarada, e uma única rejeição nunca é tratada como prova.

> Ambos só detectam dependência das variáveis observadas: se a ausência dependesse do próprio PTS (MNAR), o padrão só apareceria via variáveis correlacionadas a ele — e nunca seria confirmado pelos dados.

**3. Duplicatas** _(origem: qualidade.py: _textos_*)_

> Na fonte bruta (2.238 registros, antes de qualquer limpeza): 0 linhas inteiras repetidas e 0 repetições da chave (TEAM_NAME, Game_ID). Os 1.119 Game_ID aparecem exatamente 2 vezes cada (um registro por time), como esperado. No recorte bruto do grupo: 0 linhas e 0 chaves repetidas; o tratamento removeu 0 registros.

**4. Zeros e negativos** _(origem: qualidade.py: _textos_*)_

> Zeros encontrados no recorte: WL = 108; W = 7; W_PCT = 7; BLK = 2. Nenhum deles é código de ausência: são resultados (derrota), acumulados no início da temporada ou contagens que podem ser zero. Valores negativos: 0.

**5. Valores fora de domínio e o caso do MIN** _(origem: qualidade.py: _textos_*)_

> Foram verificadas 17 regras de domínio e coerência; nenhuma teve violação na fonte nem no recorte.

> MIN não é o tempo de jogo, e sim a soma dos minutos dos jogadores: 48 min × 5 = 240 no tempo normal. Valores 265 e 290 parecem fora do domínio de quem espera 240, mas cada prorrogação tem 5 minutos × 5 jogadores = +25: 265 = 1 prorrogação e 290 = 2. São jogos reais, não erros, e foram mantidos.

> No recorte: 8 registros com prorrogação (6 com 1 prorrogação, 2 com 2 prorrogações). Na liga inteira: 86 registros com 265 e 16 com 290 (cada jogo gera um registro por time).

> Efeito na pontuação: Mavericks marcou em média 129,33 pontos nos 6 jogos prorrogados contra 112,49 no tempo normal, sem outliers de PTS pela regra de Tukey; Pacers marcou em média 136,00 pontos nos 2 jogos prorrogados contra 111,56 no tempo normal, e 0 de seus 2 outliers de PTS (Tukey) são jogos prorrogados. Minutos extras aumentam as contagens, então a prorrogação deve ser lembrada ao ler extremos superiores, mas não justifica excluir esses jogos.

**6. Outliers por variável: quantos e quais jogos** _(origem: qualidade.py: _textos_*)_

> Nas 7 variáveis × 2 times, o número de jogos marcados por método é: Z-score 3, IQR / boxplot 10, Teste de Grubbs 2, ECOD 4, K-NN 8, DBSCAN 6, LOF 6. Ao todo, 13 pares (jogo, variável) foram marcados por pelo menos um método e 0 por todos os 7.

> Os casos em que 4 ou mais métodos concordam — os outliers mais sólidos — são: Pontos 78 (Pacers, 17/01/2026 contra DET, 4 de 7 métodos), Rebotes 26 (Mavericks, 23/03/2026 contra GSW, 5 de 7 métodos), BLK 15 (Mavericks, 18/12/2025 contra DET, 6 de 7 métodos) e PF 37 (Pacers, 23/10/2025 contra OKC, 6 de 7 métodos).

> 3 marcações foram feitas por um único método (IQR / boxplot: 1, ECOD: 2). Marcações isoladas são fracas: dependem da regra de um método só e não se sustentam nos demais.

> Nenhum método marcou jogo algum em Pontos (Mavericks), STL (Mavericks), BLK (Pacers), PF (Mavericks) e FG3M (Pacers): distribuições sem valores atípicos.

**7. Concordância entre os métodos** _(origem: qualidade.py: _textos_*)_

> Os pares que mais coincidem são IQR / boxplot e K-NN (8 em comum de 10), IQR / boxplot e DBSCAN (6 em comum de 10) e IQR / boxplot e LOF (5 em comum de 11). Como K-NN, DBSCAN e LOF foram calibrados para marcar, em dados normais, a mesma proporção da regra de Tukey, a coincidência com o IQR indica que eles enxergam os mesmos jogos isolados, e não que copiam a regra.

> O Z-score (|z| > 3) e o Grubbs são mais conservadores: exigem que o valor seja improvável sob uma normal, com corte perto de 3 desvios padrão, enquanto o IQR marca a partir de 2,7. O ECOD univariado depende só do posto do valor; por isso tende a marcar o jogo mais extremo de cada coluna mesmo quando ele está próximo dos demais, e é o que menos concorda com os métodos de distância.

**8. Resumo nas 18 colunas de box-score** _(origem: qualidade.py: _textos_*)_

> No resumo das 18 colunas de box-score × 2 times, os totais de valores marcados são: Mavericks — Z-score 3, IQR / boxplot 5, Teste de Grubbs 1, ECOD 4; Pacers — Z-score 1, IQR / boxplot 14, Teste de Grubbs 1, ECOD 2.

> Somando Z-score, IQR e Grubbs, as colunas com mais marcações são PF (Pacers, 4), REB (Mavericks, 3), BLK (Mavericks, 3) e FTA (Pacers, 2).

**9. Por que os métodos discordam** _(origem: qualidade.py: _textos_*)_

> O IQR marcou mais valores que o Grubbs em 11 de 36 combinações coluna × time. A regra de Tukey olha só para quartis e marca qualquer ponto além de 1,5×IQR; o Grubbs exige que o extremo seja improvável sob uma normal com α = 0,05, e o corte cresce com n (3,28 para n = 74 e 75).

> O Grubbs não marcou nada além do Z-score: o seu corte (G crítico = 3,28 para n = 74 e 75) é mais exigente que |z| > 3, de modo que, aqui, o ganho da iteração (desmascarar um segundo extremo) não chegou a aparecer; em 2 combinações o Z-score marcou um valor entre 3 e o G crítico.

> O Shapiro-Wilk rejeitou a normalidade (p < 0,05) em 9 de 36 combinações — FG_PCT (Mavericks), FTM (Mavericks), FTA (Mavericks), AST (Pacers), STL (Mavericks), STL (Pacers), BLK (Mavericks), BLK (Pacers), TOV (Pacers). Nelas o Z-score e o Grubbs perdem a base teórica e o IQR é a referência; nas contagens pequenas (STL, BLK) os valores discretos e repetidos também pesam na rejeição.

**10. Outliers multivariados** _(origem: qualidade.py: _textos_*)_

> Mavericks (74 jogos, 7 variáveis em σ robusto): ECOD 1, K-NN 1, DBSCAN 1, LOF 0; 0 jogos marcados pelos quatro métodos ao mesmo tempo.

> Pacers (75 jogos, 7 variáveis em σ robusto): ECOD 1, K-NN 3, DBSCAN 3, LOF 3; 1 jogo marcado pelos quatro métodos ao mesmo tempo.

> Os métodos multivariados avaliam o jogo inteiro (as 7 variáveis juntas): um jogo pode ser atípico pela combinação de valores sem ter nenhuma coluna fora dos limites univariados. Os quatro cortes foram calibrados em normais de 7 dimensões para a mesma taxa de referência dos univariados.

**testes de ausência — Teste de Little (MCAR)** _(origem: qualidade.py: TESTES_AUSENCIA)_

> O teste de Little verifica se os dados são MCAR comparando, para cada padrão de ausência, a média das colunas observadas com a média geral estimada por EM. A hipótese nula é que os dados são MCAR: se a ausência fosse puro acaso, os grupos de padrão teriam as mesmas médias. Aqui ele seria aplicado às 7 variáveis (PTS, REB, AST, STL, BLK, PF, FG3M), e d² seria comparado a uma χ².

> Não foi aplicado à base real porque o recorte dos dois times tem 0 valores ausentes em todas as colunas: o indicador de ausência R é constante (sempre 0), não existem padrões de ausência diferentes para comparar e qualquer estatística do teste ficaria indefinida. A demonstração abaixo usa cópias com ausência simulada apenas para mostrar como o teste seria lido.

**testes de ausência — Teste de Jamshidian-Jalal** _(origem: qualidade.py: TESTES_AUSENCIA)_

> O teste de Jamshidian-Jalal testa MCAR olhando a homogeneidade das covariâncias entre os grupos de padrão de ausência, e não só das médias como o Little. A hipótese nula é que os dados são MCAR e que as covariâncias são iguais entre os grupos. Na prática, imputa-se os ausentes, aplica-se o teste de Hawkins e, se ele rejeitar, um teste não paramétrico separa 'não é normal' de 'não é MCAR'. Aqui seria aplicado às 7 variáveis, com cada padrão de ausência como grupo.

> Não foi aplicado à base real porque o recorte dos dois times tem 0 valores ausentes em todas as colunas: o indicador de ausência R é constante (sempre 0), não existem padrões de ausência diferentes para comparar e qualquer estatística do teste ficaria indefinida. Ele também exige vários padrões com casos suficientes, o que não existe sem ausentes; por isso é apresentado só em teoria, sem implementação.

**testes de ausência — Teste de Listing e Schlittgen (LS)** _(origem: qualidade.py: TESTES_AUSENCIA)_

> O teste de Listing e Schlittgen é feito para dados longitudinais com abandono (dropout): verifica se quem deixa de ser medido a partir de certo instante tinha, antes, valores diferentes de quem continua. A hipótese nula é que o abandono é completamente aleatório. No basquete, ele se aplicaria a séries de jogos sucessivos, por exemplo um jogador cujos registros param após uma lesão: compara-se, jogo a jogo, o desempenho anterior de quem saiu com o de quem seguiu, por testes de postos.

> Não foi aplicado à base real porque o recorte dos dois times tem 0 valores ausentes em todas as colunas: o indicador de ausência R é constante (sempre 0), não existem padrões de ausência diferentes para comparar e qualquer estatística do teste ficaria indefinida. Além disso, a base é de times (que jogam todos os jogos), sem séries interrompidas; por isso o teste é apresentado só em teoria, sem implementação.

**testes de ausência — Regressão logística de Fairclough** _(origem: qualidade.py: TESTES_AUSENCIA)_

> A abordagem de Fairclough modela a própria ausência: cria-se Rᵢ = 1 quando o valor falta e ajusta-se uma regressão logística de R sobre as variáveis observadas. A hipótese nula é que nenhuma delas muda a chance de ausência, o que é compatível com MCAR; coeficientes significativos indicam MAR e dizem quais variáveis precisam entrar na imputação. Aqui, R seria o indicador de ausência de uma variável (ex.: PTS) e os preditores, as outras seis.

> Não foi aplicado à base real porque o recorte dos dois times tem 0 valores ausentes em todas as colunas: o indicador de ausência R é constante (sempre 0), não existem padrões de ausência diferentes para comparar e qualquer estatística do teste ficaria indefinida. A demonstração abaixo usa cópias com ausência simulada apenas para mostrar como o teste seria lido. Com R sempre 0, a logística nem pode ser ajustada (não há casos com R = 1).

**mecanismos — MCAR — Missing Completely At Random · Definição** _(origem: qualidade.py: MECANISMOS)_

> A probabilidade de um valor faltar não depende de nenhum dado, observado ou não: P(R | Y_obs, Y_falt) = P(R).

**mecanismos — MCAR — Missing Completely At Random · Exemplo na NBA** _(origem: qualidade.py: MECANISMOS)_

> O arquivo do box-score de alguns jogos se corrompe numa falha do servidor da liga, sorteando jogos sem relação com placar, time ou adversário.

**mecanismos — MCAR — Missing Completely At Random · Consequência** _(origem: qualidade.py: MECANISMOS)_

> Os casos completos são uma subamostra aleatória: excluir linhas só reduz n (perde precisão), sem viés.

**mecanismos — MAR — Missing At Random · Definição** _(origem: qualidade.py: MECANISMOS)_

> A ausência depende apenas de variáveis observadas: P(R | Y_obs, Y_falt) = P(R | Y_obs).

**mecanismos — MAR — Missing At Random · Exemplo na NBA** _(origem: qualidade.py: MECANISMOS)_

> Em jogos fora de casa (MATCHUP com '@', observado) a mesa local de outra arena deixa de registrar os tocos com mais frequência; dado o mando, a falta não depende de quantos tocos houve.

**mecanismos — MAR — Missing At Random · Consequência** _(origem: qualidade.py: MECANISMOS)_

> Excluir linhas gera viés; imputação múltipla ou máxima verossimilhança condicionadas às observadas corrigem.

**mecanismos — MNAR — Missing Not At Random · Definição** _(origem: qualidade.py: MECANISMOS)_

> A ausência depende do próprio valor faltante (ou de algo não medido), mesmo após condicionar nas observadas.

**mecanismos — MNAR — Missing Not At Random · Exemplo na NBA** _(origem: qualidade.py: MECANISMOS)_

> Um time omite do relatório as faltas pessoais justamente nos jogos em que cometeu muitas faltas: a chance de faltar depende do próprio PF.

**mecanismos — MNAR — Missing Not At Random · Consequência** _(origem: qualidade.py: MECANISMOS)_

> Nenhum teste nos dados observados confirma MNAR; exige modelar o mecanismo (seleção, pattern-mixture) e análise de sensibilidade.

**exemplo didático — Nota** _(origem: painel.js)_

> Exemplo didático: cópias do recorte com PTS apagado de propósito (semente 42); variáveis: PTS, REB, AST, STL, BLK, PF, FG3M. Decisão com α = 0,05. A base real não é alterada e continua com 0 ausentes; os números abaixo só ilustram como os testes seriam lidos.

### /sintese

**1. Comparação entre os times** _(origem: sintese.py)_

> Pontos: Mavericks 113,85 pontos por jogo contra 112,21 dos Pacers (diferença de 1,64, Δz = 0,13, efeito desprezível); Rebotes: Mavericks 44,53 rebotes por jogo contra 41,69 dos Pacers (diferença de 2,83, Δz = 0,45, efeito pequeno); Assistências: Pacers 27,20 assistências por jogo contra 25,34 dos Mavericks (diferença de 1,86, Δz = 0,34, efeito pequeno); STL: Mavericks 7,45 roubos de bola por jogo contra 7,24 dos Pacers (diferença de 0,21, Δz = 0,07, efeito desprezível); BLK: Mavericks 5,18 tocos por jogo contra 4,63 dos Pacers (diferença de 0,55, Δz = 0,23, efeito pequeno); PF: Pacers 21,21 faltas por jogo contra 18,27 dos Mavericks (diferença de 2,94, Δz = 0,63, efeito médio; como menos faltas é melhor, a vantagem é de Mavericks); FG3M: Pacers 13,21 cestas de 3 por jogo contra 10,78 dos Mavericks (diferença de 2,43, Δz = 0,66, efeito médio).

> Pela convenção de Cohen (|Δz| < 0,2 desprezível; < 0,5 pequena; < 0,8 média; ≥ 0,8 grande), as diferenças não desprezíveis estão em Rebotes, Assistências, BLK, PF e FG3M. Contando só essas, Mavericks leva vantagem em 3 variáveis (Rebotes, BLK e PF) e Pacers leva vantagem em 2 variáveis (Assistências e FG3M); nenhuma diferença chega a ser grande, e os dois times têm perfis próximos.

**2. Forma das distribuições** _(origem: sintese.py)_

> Das 14 distribuições (7 variáveis × 2 times): 12 aproximadamente simétricas, 2 moderadas. 10 têm G1 positivo, o padrão esperado em contagens limitadas por zero e sem teto rígido.

> As assimetrias moderadas ou fortes estão em STL (Mavericks, G1 = 0,51) e BLK (Mavericks, G1 = 0,75). Em BLK (Mavericks) a assimetria some quando os outliers saem: ela vem de poucos jogos extremos.

> Consequência prática: onde a distribuição é simétrica, média e mediana descrevem o jogo típico; onde há assimetria, a mediana e o IQR são os resumos mais fiéis.

**3. Regularidade (CV)** _(origem: sintese.py)_

> A variável mais regular é Pontos (CV médio 10,79%) e a mais irregular é BLK (46,99%). Mavericks tem CV menor em 2 das 7 variáveis e Pacers em 5.

> STL e BLK têm média abaixo de 10 por jogo: o CV alto delas é, em boa parte, efeito de contagens pequenas, e não necessariamente de um time instável.

**4. Valores atípicos** _(origem: sintese.py)_

> Pela regra de Tukey (1,5×IQR), nas 7 variáveis: Mavericks, 3 outliers; Pacers, 7 outliers. São eles: Pontos 78 (Pacers, 17/01/2026), Pontos 83 (Pacers, 09/11/2025), Rebotes 26 (Mavericks, 23/03/2026), Rebotes 28 (Mavericks, 12/02/2026), Rebotes 26 (Pacers, 21/03/2026), Rebotes 56 (Pacers, 05/11/2025), STL 14 (Pacers, 08/12/2025), BLK 15 (Mavericks, 18/12/2025), PF 7 (Pacers, 12/01/2026) e PF 37 (Pacers, 23/10/2025).

> Com k = 3 restam 0 e o teste de Grubbs (α = 0,05) confirma 2: são valores pouco comuns, mas plausíveis em basquete, e foram mantidos. Excluí-los mudaria médias e DPs sem que haja erro de registro. Os 8 jogos com prorrogação também foram mantidos: os minutos extras são reais.

**5. Onde o z-score entra no gráfico de barras** _(origem: sintese.py)_

> Nas barras em unidades originais, cada variável tem a sua escala: Pontos ficam em torno de 113,03 por jogo e BLK em torno de 4,90. Num mesmo gráfico, a diferença entre os times em BLK desaparece ao lado da escala de Pontos, e a comparação entre variáveis não faz sentido.

> O z-score entra justamente aí: em vez da média bruta, cada barra mostra z = (média do time − média dos jogos dos dois times) ÷ desvio padrão desses jogos. Todas as variáveis passam a ser medidas em desvios padrão, num eixo comum e sem unidade, e as barras ficam comparáveis entre si.

> Lendo o gráfico: a variável que mais separa os times é FG3M (Pacers acima, Δz = 0,66), seguida de PF (Pacers acima, Δz = 0,63) e Rebotes (Mavericks acima, Δz = 0,45); a que menos separa é STL (Mavericks acima, Δz = 0,07). Nenhuma média de time se afasta mais que 0,33 desvio padrão da referência: a diferença entre os times é pequena perto da variação de jogo para jogo.

> Como a referência é formada pelos próprios dois times, a média dos z ponderada pelo número de jogos é zero: as barras dos dois times aparecem quase espelhadas em torno do zero. O que importa é a distância entre elas (Δz), que equivale a uma diferença padronizada de médias.

> O z-score também pode entrar no gráfico por jogo, e não por média: z de cada partida, com |z| > 3 marcando valores extremos — é o critério Z-score usado na página Qualidade dos dados.

**6. Qualidade e preparo da base** _(origem: sintese.py)_

> A fonte tem 2.238 registros e 28 colunas, com 0 ausentes, 0 duplicatas e 0 violações nas 17 regras de domínio. O recorte do grupo tem 149 jogos; as conclusões não dependem de imputação nem de limpeza agressiva.

> Para uso em modelos, 7 colunas são excluídas (Team_ID, Game_ID, MATCHUP, W, L, W_PCT e TEAM_NAME), e WL é o alvo. W, L e W_PCT vazam o resultado: a variação de W é igual a WL em 147 de 147 jogos com jogo anterior.

**7. Limitações** _(origem: sintese.py)_

> Uma única temporada regular, com cerca de 75 jogos por time: medidas de cauda (assimetria, outliers) variam bastante com poucos jogos extremos.

> A análise é univariada e descritiva: não controla adversário, mando de quadra, prorrogação ou desfalques, e as diferenças entre times não foram submetidas a teste de hipótese.

> Os testes de mecanismo de ausência foram demonstrados em dados simulados, porque a base real não tem ausentes; o ECOD e o K-NN marcam ≈ 5% dos jogos por construção.

**8. Conclusão** _(origem: sintese.py)_

> Mavericks e Pacers pontuam de forma muito parecida (Δz = 0,13 em Pontos). O que distingue os estilos está em FG3M (Pacers acima), PF (Pacers acima) e Rebotes (Mavericks acima).

> Nenhuma média de time fica a mais de 0,33 desvio padrão da média conjunta: a variação de jogo para jogo dentro de cada time é bem maior que a diferença entre os times. Por isso, comparações devem olhar a distribuição inteira (boxplot, IQR), e não só a média.

### /dicionario (vazamento)

**Vazamento** _(origem: painel.js: carregarDicionario)_

> Evidência do vazamento em W, L e W_PCT. Ordenando os jogos de cada time pela data, a variação de W de um jogo para o seguinte é igual ao resultado WL em 147 de 147 jogos com jogo anterior, a variação de L é igual à derrota (1 − WL) em 147 de 147, e W + L é exatamente o número do jogo em 149 de 149. Ou seja, os acumulados são registrados depois do jogo e já contêm o resultado que se quer prever.

> MATCHUP. A coluna bruta sai, mas o mando de quadra pode ser derivado dela: 75 jogos em casa ("vs.") e 74 fora ("@").
