# Quadra Analítica — Mavericks e Pacers

Dashboard Flask para o Projeto 1 de Laboratório de Ciência de Dados. A aplicação apresenta as análises exigidas no enunciado diretamente no navegador: dicionário de dados, qualidade, medidas descritivas, IQR, CV, assimetria, comparações e visualizações interativas.

## Arquitetura

A aplicação foi organizada para que uma alteração futura não precise atravessar
todo o sistema:

```text
web/rotas.py                  HTTP, parâmetros e respostas JSON
web/erros.py                  tratamento uniforme e sem vazamento de detalhes
servicos/servico_relatorio.py casos de uso e validação das entradas
infraestrutura/repositorio_dados.py leitura, tipagem, limpeza e cache da fonte
infraestrutura/preparador_dados.py geração física do CSV exclusivo do grupo
analise.py                    domínio estatístico puro sobre DataFrames
configuracao.py               caminhos e limites da aplicação
```

O fluxo é unidirecional: rota → serviço → repositório/domínio. A rota não lê
CSV e o domínio não conhece Flask. Antes do repositório estatístico, o
preparador lê a fonte original e gera
`dados/estatisticas_times_selecionados.csv`, contendo exclusivamente os Dallas
Mavericks e Indiana Pacers. O repositório lê somente esse CSV derivado para
os cálculos; registros dos demais times não entram na análise. O repositório entrega cópias do DataFrame,
evitando que uma requisição altere o estado usado por outra. O carregamento é
preguiçoso e protegido por bloqueio, portanto importar a aplicação não falha
apenas porque a fonte ainda não foi acessada.

### Proteções implementadas

- Validação de time e variável por lista permitida (evita entradas arbitrárias).
- Limite de tamanho de requisição configurável.
- Respostas de erro padronizadas; exceções inesperadas recebem identificador
  para rastreamento, sem expor stack trace ao usuário.
- `X-Request-ID` e log de método, rota, status e duração.
- Content Security Policy, proteção contra MIME sniffing, clickjacking,
  restrição de permissões do navegador e política de referenciador.
- O servidor de produção deve ser executado com Gunicorn, nunca com o servidor
  de desenvolvimento do Flask.
- O endpoint `/health` pode ser usado pelo Render ou por um monitor externo.

Como o relatório é público e não possui dados pessoais ou operações de escrita,
não foi adicionada autenticação artificial. Em uma futura área administrativa,
ela deve ser criada como uma camada separada, com sessão, autorização e
auditoria, sem misturar credenciais às rotas públicas.

## Executar localmente

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app app:aplicacao run
```

Abra `http://localhost:5000`.

Na hospedagem, o Render executará o Gunicorn. Localmente, o comando acima usa
o servidor integrado do Flask apenas para desenvolvimento e apresentação.

Testes:

```powershell
pytest -q
```

## Configurações opcionais

| Variável | Padrão | Uso |
|---|---|---|
| `CAMINHO_DADOS` | `dados/stats_times_regular_final.csv` | Permite trocar a fonte completa sem editar o código |
| `CAMINHO_DADOS_SELECIONADOS` | `dados/estatisticas_times_selecionados.csv` | Caminho da base física exclusiva do grupo |
| `LIMITE_REQUISICAO_BYTES` | `1048576` | Limite de corpo HTTP aceito |

## Base analítica do grupo

O arquivo [stats_times_regular_final.csv](./dados/stats_times_regular_final.csv)
contém a liga inteira e é mantido em `dados/` como fonte bruta. Na
inicialização do primeiro acesso aos dados, o sistema executa a etapa de
preparação e gera `dados/estatisticas_times_selecionados.csv`.
Essa base derivada é um artefato local e está no `.gitignore`: ela não precisa
ser enviada ao GitHub, pois é recriada automaticamente a partir do CSV original.
Esse arquivo possui somente os registros dos dois times atribuídos ao grupo e
é a única base entregue ao cálculo estatístico. Ele contém 149 jogos no recorte
atual (74 Mavericks e 75 Pacers). Se o CSV original for atualizado, a base
selecionada é regenerada automaticamente antes de ser lida.

## Exploração do dicionário

A página **Dicionário de dados** não é apenas uma tabela: permite pesquisar por
nome, campo ou significado; filtrar por tipo e categoria; visualizar a
quantidade de campos em cada categoria; e abrir a explicação individual de
cada variável. Isso torna explícito o que cada coluna representa e qual
tratamento recebeu antes da análise.

## Decisões estatísticas

- Quartis usam interpolação linear do pandas em todas as tabelas e gráficos.
- O desvio padrão e a variância são amostrais (`n - 1`), pois a temporada é tratada como observação de um processo de jogos futuros.
- Outliers principais usam os limites de Tukey `Q1 - 1,5×IQR` e `Q3 + 1,5×IQR`; os demais métodos solicitados são apresentados como diagnóstico complementar.
- A assimetria usa o coeficiente ajustado de Fisher-Pearson (`pandas.Series.skew`). A classificação adotada é: `|g1| < 0,5` aproximadamente simétrica; `0,5 ≤ |g1| < 1` moderada; `|g1| ≥ 1` forte.
- O CV é `desvio padrão amostral / média × 100`. Ele é interpretado com cautela em métricas com média próxima de zero, como STL e BLK.
- Assimetria, CV e IQR têm páginas próprias (`/assimetria`, `/cv`, `/iqr`) com fórmula, quadro-resumo variáveis × times e interpretação gerada a partir dos números (`interpretacao.py`).
- O coeficiente de Bowley `(Q3 + Q1 − 2·Mediana)/IQR` é exibido como verificação robusta do sinal de G1; G1 também é recalculado sem os outliers para mostrar quando poucos jogos extremos explicam a assimetria.
- Faixas do CV: `< 15%` consistente, `15–30%` moderada, `> 30%` irregular. Com média `< 10` por jogo o CV é lido com cautela e comparado ao piso de contagens tipo Poisson (`100/√média`); `IQR/Mediana × 100` é a alternativa robusta.
- Tipos de dado no dicionário seguem o significado da coluna, não só o armazenamento: numérica (contagens e proporções), categórica (`TEAM_NAME`, `Team_ID`, `Game_ID`, que são rótulos mesmo guardados como inteiros), texto (`MATCHUP`), data (`GAME_DATE`) e binária (`WL`).
- Colunas excluídas para aprendizado de máquina: `Team_ID`, `Game_ID` e `TEAM_NAME` (identificadores), `MATCHUP` (texto livre; o mando pode ser derivado) e `W`, `L`, `W_PCT` por **vazamento** — são acumulados registrados depois do jogo, e a variação de `W` é igual a `WL` em todos os jogos com jogo anterior (verificado na página). `WL` é o alvo.
- Z-score no gráfico de barras (Comparativo): `z = (média do time − média dos 149 jogos dos dois times) / DP desses jogos`, para comparar as 7 variáveis num eixo comum. A referência é o próprio recorte, para não usar dados de outros times; por isso as barras dos dois times ficam quase espelhadas e o que se lê é a distância entre elas (Δz).
- A página **Síntese** (`/sintese`, módulo `sintese.py`) reúne o quadro-resumo e a leitura final; diferenças entre os times são classificadas pela convenção de Cohen (`|Δz|` < 0,2 desprezível; < 0,5 pequena; < 0,8 média).
- Qualidade (`/qualidade`, módulo `qualidade.py`): ausentes por coluna e duplicatas são medidos nas bases **brutas** (fonte completa e recorte do grupo), antes da tipagem e da deduplicação. A fonte atual não tem ausentes nem duplicatas, e nenhum percentual está fora de `[0, 1]`.
- `MIN` é a soma dos minutos dos jogadores: o domínio é `240 + 25·k` (48 min × 5 no tempo normal, +5 min × 5 por prorrogação). Os valores 265 e 290 são uma e duas prorrogações, não erros.
- Testes de mecanismo de ausência: como a base não tem ausentes, Little (EM sob normal multivariada) e a regressão logística de Fairclough (razão de verossimilhança) são demonstrados em cópias com ausência MCAR e MAR simuladas (semente 42). Jamshidian-Jalal e Listing-Schlittgen são apresentados em teoria.
- Outliers (módulo `deteccao.py`, só numpy/scipy/scikit-learn — sem `pyod`): para cada uma das 7 variáveis e cada time, sete métodos com os jogos marcados (data e adversário) e tabela de concordância. Z-score `|z| > 3`; Tukey 1,5×IQR (mesmos limites do boxplot); Grubbs bilateral iterativo com `α = 0,05` e valor crítico pela distribuição t (confere com o exemplo do NIST e-Handbook); ECOD implementado conforme Li et al. (2022) — ECDF à esquerda e à direita, cauda escolhida pela assimetria e soma de −log; em uma dimensão é idêntico ao `pyod`, verificado em teste quando ele está instalado.
- Parâmetros de K-NN, DBSCAN e LOF não são fixos à mão: cada limiar é **calibrado** para que, em dados normais com o mesmo n e dimensão, o método marque a mesma proporção que a regra de Tukey numa normal (P(|z| > 2,698) ≈ 0,70%). k = round(√n); `min_samples` = 4 (Ester et al.) ou 2·dimensão (Sander et al.); `n_neighbors` = 20 (Breunig et al.). Distâncias medidas em σ robusto (IQR/1,349). A calibração (Monte Carlo, semente fixa) fica em `dados/calibracao_outliers.json` para não pesar na primeira requisição; `python -m deteccao` a regenera e um teste confere que a tabela é reproduzível.
- O ECOD univariado depende só do posto do valor, então o corte equivale a fixar uma proporção: usa-se a mesma taxa de referência (0,70%). Por isso ele marca no máximo o jogo mais extremo da coluna, e nenhum quando o mínimo e o máximo empatam na probabilidade de cauda.
- Também há um resumo de Z-score, IQR, Grubbs e ECOD nas 18 colunas de box-score e uma seção multivariada (as 7 variáveis juntas) com os cortes calibrados em 7 dimensões.
- O histograma usa faixas de Freedman–Diaconis (`h = 2·IQR·n^(−1/3)`, arredondado para inteiro porque as variáveis são contagens), comuns aos dois times. A curva de densidade é `scipy.stats.gaussian_kde` (banda de Scott), calculada no servidor e escalada por `n·h` para ficar na mesma unidade das barras (nº de jogos).

## Equipe
- Matheus Marcos
- Mayara Karoline
- Yasmin Muniz