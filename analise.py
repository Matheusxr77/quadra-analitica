"""Funções que organizam os dados e calculam as estatísticas do dashboard.

Este arquivo não depende das páginas. Assim, os cálculos podem ser testados e
alterados sem misturar estatística com HTML ou JavaScript.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

CAMINHO_DADOS = (
    Path(__file__).parent / "dados" / "stats_times_regular_final.csv"
)
TIMES_ANALISADOS = ["Dallas Mavericks", "Indiana Pacers"]
VARIAVEIS_ANALISADAS = ["Pontos", "Rebotes", "Assistências", "STL", "BLK", "PF", "FG3M"]

NOMES_COLUNAS = {
    "GAME_DATE": "Data do jogo",
    "MATCHUP": "Confronto",
    "WL": "Resultado",
    "W": "Vitórias acumuladas",
    "L": "Derrotas acumuladas",
    "W_PCT": "Percentual de vitórias",
    "MIN": "Minutos",
    "FGM": "Cestas de quadra convertidas",
    "FGA": "Arremessos de quadra tentados",
    "FG_PCT": "Percentual de cestas de quadra",
    "FG3M": "Cestas de três convertidas",
    "FG3A": "Arremessos de três tentados",
    "FG3_PCT": "Percentual de três pontos",
    "FTM": "Lances livres convertidos",
    "FTA": "Lances livres tentados",
    "FT_PCT": "Percentual de lances livres",
    "OREB": "Rebotes ofensivos",
    "DREB": "Rebotes defensivos",
    "REB": "Rebotes totais",
    "AST": "Assistências",
    "STL": "Roubos de bola",
    "BLK": "Tocos",
    "TOV": "Turnovers",
    "PF": "Faltas pessoais",
    "PTS": "Pontos",
    "TEAM_NAME": "Time",
}

MAPA_VARIAVEIS = {
    "Pontos": "PTS",
    "Rebotes": "REB",
    "Assistências": "AST",
    "STL": "STL",
    "BLK": "BLK",
    "PF": "PF",
    "FG3M": "FG3M",
}

UNIDADES = {
    "Pontos": "pontos por jogo",
    "Rebotes": "rebotes por jogo",
    "Assistências": "assistências por jogo",
    "STL": "roubos de bola por jogo",
    "BLK": "tocos por jogo",
    "PF": "faltas por jogo",
    "FG3M": "cestas de 3 por jogo",
}

METADADOS_CAMPOS = {
    "PTS": ("Desempenho", "Pontos marcados no jogo.", "Variável principal de pontuação."),
    "REB": ("Desempenho", "Rebotes totais no jogo.", "Combina rebotes ofensivos e defensivos."),
    "AST": ("Desempenho", "Assistências realizadas.", "Indica participação na criação de cestas."),
    "STL": ("Defesa", "Roubos de bola.", "Ações defensivas que recuperam a posse."),
    "BLK": ("Defesa", "Tocos realizados.", "Arremessos adversários bloqueados."),
    "PF": ("Disciplina", "Faltas pessoais cometidas.", "Ajuda a observar o custo defensivo e disciplinar."),
    "FG3M": ("Arremessos", "Cestas de três pontos convertidas.", "Produção em arremessos de longa distância."),
    "GAME_DATE": ("Identificação", "Data em que a partida ocorreu.", "Convertida para o tipo data para ordenar e contextualizar os jogos."),
    "MATCHUP": ("Identificação", "Confronto e mando de quadra.", "Texto com adversário e indicação vs. ou @."),
    "TEAM_NAME": ("Identificação", "Nome do time.", "Usado para manter somente os dois times do grupo."),
    "WL": ("Resultado", "Resultado binário da partida.", "Convertido para inteiro: 1 representa vitória e 0 derrota."),
}


def _normalizar_percentual(coluna: pd.Series) -> pd.Series:
    """Garante percentuais em fração, no intervalo [0, 1].

    Na fonte atual todos os percentuais já estão em fração (a página de
    Qualidade confere isso). A regra é defensiva: se uma atualização trouxer
    valores acima de 1 em milésimos de proporção, dividi-los por 1000 os põe
    na mesma escala. O que ainda ficar fora de [0, 1] vira ausente para não
    contaminar os resumos.
    """
    serie = pd.to_numeric(coluna, errors="coerce")
    serie = serie.where(serie <= 1, serie / 1000)
    return serie.where(serie.between(0, 1))


def carregar_dados() -> pd.DataFrame:
    """Carrega os dados usando o mesmo caminho adotado pela aplicação."""
    from infraestrutura.repositorio_dados import RepositorioDados

    return RepositorioDados(CAMINHO_DADOS).obter_dados()


def _valores(dados: pd.DataFrame, time: str, variavel: str) -> pd.Series:
    filtrados = dados if time == "Todos" else dados[dados["TEAM_NAME"] == time]
    return filtrados[MAPA_VARIAVEIS[variavel]].dropna().astype(float)


LIMITE_SIMETRIA = 0.5
LIMITE_ASSIMETRIA_FORTE = 1.0
FAIXAS_CV = (15.0, 30.0)  # % — abaixo: consistente; entre: moderada; acima: irregular
MEDIA_MINIMA_CV = 10.0  # abaixo disso (contagens pequenas) o CV é lido com cautela
CONSTANTE_SIGMA_ROBUSTO = 1.349  # IQR de uma normal = 1,349 σ


def _intensidade_assimetria(valor: float) -> str:
    if abs(valor) < LIMITE_SIMETRIA:
        return "aproximadamente simétrica"
    return "moderada" if abs(valor) < LIMITE_ASSIMETRIA_FORTE else "forte"


def _direcao_assimetria(valor: float) -> str:
    """A direção vem só do sinal do coeficiente, como pede o enunciado."""
    if valor > 0:
        return "à direita (positiva)"
    if valor < 0:
        return "à esquerda (negativa)"
    return "simétrica"


def _classificar_assimetria(valor: float) -> str:
    return f"{_intensidade_assimetria(valor)}; distribuição {_direcao_assimetria(valor)}"


def _skew(serie: pd.Series) -> float:
    """Coeficiente ajustado de Fisher-Pearson (G1), igual a pandas.Series.skew."""
    return float(serie.skew()) if len(serie) > 2 else 0.0


def _estatisticas_de_serie(serie: pd.Series) -> dict[str, Any]:
    """Calcula as medidas estatísticas de uma variável.

    O desvio padrão usa n - 1 porque os jogos observados representam uma
    amostra do comportamento que pode ocorrer em outras partidas.
    """
    quartil_1 = float(serie.quantile(0.25, interpolation="linear"))
    quartil_3 = float(serie.quantile(0.75, interpolation="linear"))
    media = float(serie.mean())
    desvio = float(serie.std(ddof=1))
    contagens = serie.value_counts()
    # Se nenhum valor se repete, a série é amodal: todos seriam "moda".
    amodal = contagens.empty or int(contagens.max()) == 1
    modas = [] if amodal else sorted(
        float(valor) for valor in contagens[contagens == contagens.max()].index
    )
    valor_moda = modas[0] if modas else None
    assimetria = _skew(serie)
    limite_inferior = quartil_1 - 1.5 * (quartil_3 - quartil_1)
    limite_superior = quartil_3 + 1.5 * (quartil_3 - quartil_1)
    mascara_atipicos = (serie < limite_inferior) | (serie > limite_superior)
    valores_atipicos = serie[mascara_atipicos].sort_values()
    # Bigodes de Tukey: vão até o valor OBSERVADO mais extremo que ainda está
    # dentro dos limites, e não até os limites em si.
    dentro = serie[~mascara_atipicos]
    cv = desvio / media if media > 0 else None
    iqr = quartil_3 - quartil_1
    mediana = float(serie.median())
    q1_sem = float(dentro.quantile(0.25, interpolation="linear"))
    q3_sem = float(dentro.quantile(0.75, interpolation="linear"))
    desvio_sem = float(dentro.std(ddof=1))
    sigma_robusto = iqr / CONSTANTE_SIGMA_ROBUSTO
    extremos_3iqr = serie[(serie < quartil_1 - 3 * iqr) | (serie > quartil_3 + 3 * iqr)]
    return {
        "n": int(serie.size),
        "media": media,
        "mediana": float(serie.median()),
        "moda": valor_moda,
        "modas": modas,
        "amodal": amodal,
        "minimo": float(serie.min()),
        "maximo": float(serie.max()),
        "amplitude": float(serie.max() - serie.min()),
        "desvio_padrao": desvio,
        "variancia": float(serie.var(ddof=1)),
        "q1": quartil_1,
        "q3": quartil_3,
        "iqr": quartil_3 - quartil_1,
        "limite_inferior": limite_inferior,
        "limite_superior": limite_superior,
        "bigode_inferior": float(dentro.min()),
        "bigode_superior": float(dentro.max()),
        "outliers": [float(valor) for valor in valores_atipicos],
        "quantidade_outliers": int(valores_atipicos.size),
        "assimetria": assimetria,
        "classificacao_assimetria": _classificar_assimetria(assimetria),
        "direcao_assimetria": _direcao_assimetria(assimetria),
        "intensidade_assimetria": _intensidade_assimetria(assimetria),
        # Bowley (quartis): verificação robusta, não depende das caudas.
        "bowley": (quartil_3 + quartil_1 - 2 * mediana) / iqr if iqr > 0 else None,
        "assimetria_sem_outliers": _skew(dentro),
        "cv": cv,
        "cv_percentual": cv * 100 if cv is not None else None,
        "cv_robusto_iqr": iqr / mediana * 100 if mediana > 0 else None,
        # Em contagens tipo Poisson, DP ≈ √média ⇒ CV ≈ 100/√média: piso esperado.
        "cv_poisson_ref": 100 / np.sqrt(media) if media > 0 else None,
        "desvio_sem_outliers": desvio_sem,
        "iqr_sem_outliers": q3_sem - q1_sem,
        "sigma_robusto": sigma_robusto,
        "razao_dp_sigma_robusto": desvio / sigma_robusto if sigma_robusto > 0 else None,
        "razao_amplitude_iqr": float(serie.max() - serie.min()) / iqr if iqr > 0 else None,
        "limite_inferior_3iqr": quartil_1 - 3 * iqr,
        "limite_superior_3iqr": quartil_3 + 3 * iqr,
        "quantidade_outliers_3iqr": int(extremos_3iqr.size),
    }


def _detalhar_outliers(
    dados: pd.DataFrame, serie: pd.Series, outliers_idx: pd.Index
) -> list[dict[str, Any]]:
    """Identifica em quais jogos ocorreram os valores atípicos."""
    detalhes = []
    for indice in outliers_idx:
        linha = dados.loc[indice]
        data = linha.get("GAME_DATE")
        detalhes.append({
            "valor": float(serie.loc[indice]),
            "data": data.strftime("%d/%m/%Y") if pd.notna(data) else None,
            "confronto": str(linha.get("MATCHUP", "")) or None,
        })
    return detalhes


def _estatisticas_com_jogos(
    dados: pd.DataFrame, time: str, variavel: str
) -> dict[str, Any]:
    serie = _valores(dados, time, variavel)
    resultado = _estatisticas_de_serie(serie)
    atipicos = serie[
        (serie < resultado["limite_inferior"]) | (serie > resultado["limite_superior"])
    ].sort_values()
    resultado["outliers_detalhe"] = _detalhar_outliers(dados, serie, atipicos.index)
    resultado["valores"] = _serie_para_grafico(serie)
    return resultado


def calcular_tabela_descritiva(dados: pd.DataFrame) -> dict[str, Any]:
    """Tabela completa de medidas descritivas: cada variável × cada time."""
    variaveis = []
    for variavel in VARIAVEIS_ANALISADAS:
        times = {}
        for time in TIMES_ANALISADOS:
            estatisticas = _estatisticas_com_jogos(dados, time, variavel)
            estatisticas.pop("valores")
            times[time] = estatisticas
        variaveis.append({
            "variavel": variavel,
            "unidade": UNIDADES[variavel],
            "times": times,
        })
    return {"times": TIMES_ANALISADOS, "variaveis": variaveis}


def _largura_freedman_diaconis(serie: pd.Series) -> int:
    """h = 2·IQR·n^(-1/3), arredondado para inteiro ≥ 1.

    As sete variáveis são contagens inteiras; uma faixa fracionária deixaria
    faixas vazias alternadas e distorceria o formato do histograma.
    """
    iqr = float(serie.quantile(0.75) - serie.quantile(0.25))
    if iqr <= 0 or serie.size == 0:
        return 1
    return max(1, int(round(2 * iqr * serie.size ** (-1 / 3))))


def calcular_histograma_kde(dados: pd.DataFrame, variavel: str) -> dict[str, Any]:
    """Histograma com faixas comuns aos dois times + KDE gaussiana por time.

    As bordas são calculadas com os dois times juntos para que as barras
    sejam comparáveis. A KDE (scipy.stats.gaussian_kde, banda de Scott) é
    multiplicada por n·h para ficar na mesma escala do histograma
    (número de jogos por faixa).
    """
    conjunto = pd.concat([_valores(dados, time, variavel) for time in TIMES_ANALISADOS])
    largura = _largura_freedman_diaconis(conjunto)
    inicio = np.floor(conjunto.min()) - 0.5
    fim = np.ceil(conjunto.max()) + 0.5
    bordas = np.arange(inicio, fim + largura, largura)
    bordas = bordas[: np.searchsorted(bordas, fim) + 1]
    grade = np.linspace(inicio - largura, bordas[-1] + largura, 200)
    por_time = {}
    for time in TIMES_ANALISADOS:
        serie = _valores(dados, time, variavel)
        contagens, _ = np.histogram(serie, bins=bordas)
        kde = stats.gaussian_kde(serie.to_numpy()) if serie.nunique() > 1 else None
        densidade = kde(grade) if kde is not None else np.zeros_like(grade)
        por_time[time] = {
            "n": int(serie.size),
            "contagens": [int(valor) for valor in contagens],
            "kde_x": [float(valor) for valor in grade],
            "kde_densidade": [float(valor) for valor in densidade],
            "kde_frequencia": [float(valor) for valor in densidade * serie.size * largura],
            "banda_kde": float(kde.factor * serie.std(ddof=1)) if kde is not None else None,
        }
    return {
        "regra": "Freedman–Diaconis (h = 2·IQR·n^(−1/3), arredondado para inteiro)",
        "largura": largura,
        "bordas": [float(valor) for valor in bordas],
        "centros": [float((a + b) / 2) for a, b in zip(bordas[:-1], bordas[1:])],
        "times": por_time,
    }


def _serie_para_grafico(serie: pd.Series) -> list[float]:
    return [float(valor) for valor in serie.tolist()]


def calcular_estatisticas(
    dados: pd.DataFrame, time: str, variavel: str
) -> dict[str, Any]:
    """Prepara os números que a página usa nos cartões e gráficos."""
    if variavel not in VARIAVEIS_ANALISADAS:
        variavel = VARIAVEIS_ANALISADAS[0]
    times = ["Todos"] if time == "Todos" else [time]
    por_time = {
        nome_time: _estatisticas_com_jogos(dados, nome_time, variavel)
        for nome_time in times
    }
    comparativo = {
        nome_time: _estatisticas_com_jogos(dados, nome_time, variavel)
        for nome_time in TIMES_ANALISADOS
    }
    return {
        "time": time,
        "variavel": variavel,
        "unidade": UNIDADES[variavel],
        "por_time": por_time,
        "comparativo": comparativo,
        "histograma": calcular_histograma_kde(dados, variavel),
    }


TIPOS_DADOS = ["numérica", "categórica", "texto", "data", "binária"]
COLUNAS_IDENTIFICADORAS = {"Team_ID", "Game_ID", "TEAM_NAME"}
COLUNAS_ACUMULADAS = {"W", "L", "W_PCT"}
COLUNA_ALVO = "WL"

EXCLUSOES_ML = {
    "Team_ID": "Identificador numérico do time: o número não mede desempenho, e o modelo decoraria códigos em vez de aprender padrões de jogo.",
    "Game_ID": "Identificador da partida: único por jogo, não se repete em jogos futuros e não carrega informação estatística.",
    "TEAM_NAME": "Nome do time (redundante com Team_ID): o modelo aprenderia 'quem joga' em vez de 'como jogou' e não generalizaria para outros times.",
    "MATCHUP": "Texto livre ('DAL vs. LAC', 'DAL @ UTA'). Não entra cru em um modelo; o mando de quadra (vs. = casa, @ = fora) e o adversário podem ser extraídos como variáveis derivadas.",
    "W": "Vazamento: vitórias acumuladas DEPOIS do jogo; a variação de W de um jogo para o seguinte é o próprio resultado (WL).",
    "L": "Vazamento: derrotas acumuladas DEPOIS do jogo; W + L é o número do jogo e a variação de L revela a derrota.",
    "W_PCT": "Vazamento: W ÷ (W + L) já incorpora o resultado do próprio jogo.",
}


def _classificar_tipo(coluna: str, serie: pd.Series) -> tuple[str, str]:
    """Tipo conceitual (numérica, categórica, texto, data, binária) e subtipo.

    O tipo vem do significado da coluna, não do dtype: Team_ID é armazenado
    como inteiro, mas é um rótulo (categórico), e WL é inteiro com só 0/1.
    """
    if coluna == "GAME_DATE" or pd.api.types.is_datetime64_any_dtype(serie):
        return "data", "data do jogo (datetime)"
    if coluna == "MATCHUP":
        return "texto", "texto livre com sigla, mando (vs./@) e adversário"
    if coluna in COLUNAS_IDENTIFICADORAS:
        return "categórica", "nominal (identificador)"
    valores = set(serie.dropna().unique())
    if valores and valores <= {0, 1}:
        return "binária", "0 = derrota, 1 = vitória" if coluna == COLUNA_ALVO else "0/1"
    if serie.dtype == "object":
        return "categórica", "nominal"
    if coluna in COLUNAS_ACUMULADAS:
        sufixo = " (proporção 0–1)" if coluna.endswith("PCT") else " (contagem)"
        return "numérica", "acumulado da temporada" + sufixo
    if coluna.endswith("_PCT"):
        return "numérica", "contínua (proporção 0–1)"
    if coluna == "MIN":
        return "numérica", "discreta (minutos do time: 240 + 25 por prorrogação)"
    return "numérica", "discreta (contagem por jogo)"


def verificar_vazamento_wl(dados: pd.DataFrame) -> dict[str, Any]:
    """Confere se W/L são acumulados após o jogo (e portanto revelam WL)."""
    comparaveis = coincidem_w = coincidem_l = ordinal = total = 0
    for _, grupo in dados.sort_values("GAME_DATE").groupby("TEAM_NAME"):
        w = grupo["W"].astype(float)
        l = grupo["L"].astype(float)
        wl = grupo["WL"].astype(float)
        diferenca_w, diferenca_l = w.diff(), l.diff()
        validos = diferenca_w.notna()
        comparaveis += int(validos.sum())
        coincidem_w += int((diferenca_w[validos] == wl[validos]).sum())
        coincidem_l += int((diferenca_l[validos] == 1 - wl[validos]).sum())
        ordinal += int(((w + l).to_numpy() == np.arange(1, len(grupo) + 1)).sum())
        total += len(grupo)
    return {
        "jogos": total,
        "jogos_com_anterior": comparaveis,
        "variacao_w_igual_wl": coincidem_w,
        "variacao_l_igual_derrota": coincidem_l,
        "w_mais_l_igual_numero_do_jogo": ordinal,
    }


def calcular_dicionario(dados: pd.DataFrame) -> dict[str, Any]:
    """Descreve os campos da base depois do tratamento."""
    padrao = ("Contexto do jogo", "Medida registrada na partida.", "Convertida para numérico quando aplicável.")
    linhas = []
    for coluna in dados.columns:
        tipo, subtipo = _classificar_tipo(coluna, dados[coluna])
        if coluna in EXCLUSOES_ML:
            uso, justificativa = "excluída", EXCLUSOES_ML[coluna]
        elif coluna == COLUNA_ALVO:
            uso, justificativa = "alvo", "Resultado a prever (vitória/derrota); não entra como variável explicativa."
        elif coluna == "GAME_DATE":
            uso, justificativa = "feature", "Mantida para ordenar os jogos e derivar variáveis (dias de descanso, sequência), não como data crua."
        else:
            uso, justificativa = "feature", "Estatística do jogo, utilizável como variável explicativa."
        categoria, explicacao, tratamento = METADADOS_CAMPOS.get(coluna, padrao)
        linhas.append({
            "coluna_original": coluna,
            "nome_apresentacao": NOMES_COLUNAS.get(coluna, coluna),
            "tipo": tipo,
            "subtipo": subtipo,
            "armazenamento": str(dados[coluna].dtype),
            "uso_ml": uso,
            "justificativa_ml": justificativa,
            "ausentes": int(dados[coluna].isna().sum()),
            "descricao": NOMES_COLUNAS.get(coluna, "Identificador técnico"),
            "categoria": categoria,
            "explicacao": explicacao,
            "tratamento": tratamento,
        })
    mando = dados["MATCHUP"].astype(str)
    return {
        "linhas": int(len(dados)),
        "colunas": int(len(dados.columns)),
        "campos": linhas,
        "tipos": {tipo: sum(1 for l in linhas if l["tipo"] == tipo) for tipo in TIPOS_DADOS},
        "exclusoes": [
            {"coluna": l["coluna_original"], "tipo": l["tipo"], "motivo": l["justificativa_ml"]}
            for l in linhas if l["uso_ml"] == "excluída"
        ],
        "vazamento": verificar_vazamento_wl(dados),
        "mando": {
            "casa": int(mando.str.contains(" vs. ", regex=False).sum()),
            "fora": int(mando.str.contains(" @ ", regex=False).sum()),
        },
        "features": sum(1 for l in linhas if l["uso_ml"] == "feature"),
    }


def calcular_perfil_z(dados: pd.DataFrame) -> dict[str, Any]:
    """Médias dos times em z-score, com referência nos jogos dos dois times.

    z = (média do time − média dos jogos dos dois times) / DP amostral desses
    jogos. Coloca variáveis de escalas diferentes (PTS ≈ 113, BLK ≈ 5) num
    mesmo eixo, em desvios padrão.
    """
    variaveis = []
    for variavel in VARIAVEIS_ANALISADAS:
        coluna = MAPA_VARIAVEIS[variavel]
        conjunto = dados.loc[dados["TEAM_NAME"].isin(TIMES_ANALISADOS), coluna].dropna()
        media, desvio = float(conjunto.mean()), float(conjunto.std(ddof=1))
        times = {}
        for time in TIMES_ANALISADOS:
            serie = _valores(dados, time, variavel)
            media_time = float(serie.mean())
            times[time] = {
                "n": int(serie.size),
                "media": media_time,
                "z": (media_time - media) / desvio if desvio > 0 else 0.0,
            }
        a, b = TIMES_ANALISADOS
        variaveis.append({
            "variavel": variavel,
            "unidade": UNIDADES[variavel],
            "media_referencia": media,
            "desvio_referencia": desvio,
            "n_referencia": int(conjunto.size),
            "times": times,
            "diferenca_z": times[a]["z"] - times[b]["z"],
        })
    return {"times": TIMES_ANALISADOS, "referencia": "jogos dos dois times", "variaveis": variaveis}
