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

- Percentuais inconsistentes da origem (alguns em fração, outros em milésimos, como `506` para `0,506`) são convertidos para a faixa `[0, 1]` dividindo os valores acima de 1 por 1000.
- Quartis usam interpolação linear do pandas em todas as tabelas e gráficos.
- O desvio padrão e a variância são amostrais (`n - 1`), pois a temporada é tratada como observação de um processo de jogos futuros.
- Outliers principais usam os limites de Tukey `Q1 - 1,5×IQR` e `Q3 + 1,5×IQR`; os demais métodos solicitados são apresentados como diagnóstico complementar.
- A assimetria usa o coeficiente ajustado de Fisher-Pearson (`pandas.Series.skew`). A classificação adotada é: `|g1| < 0,5` aproximadamente simétrica; `0,5 ≤ |g1| < 1` moderada; `|g1| ≥ 1` forte.
- O CV é `desvio padrão amostral / média × 100`. Ele é interpretado com cautela em métricas com média próxima de zero, como STL e BLK.

## Equipe
- Matheus Marcos
- Mayara Karoline
- Yasmin Muniz