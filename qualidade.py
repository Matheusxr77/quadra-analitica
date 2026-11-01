"""Diagnóstico de qualidade dos dados: ausentes, especiais, domínio e outliers.

Domínio puro (não conhece Flask). Recebe a base tratada usada nos cálculos e
as bases brutas (fonte completa e recorte do grupo antes de qualquer limpeza)
para que duplicatas e ausentes sejam medidos antes do tratamento. Os textos
são gerados a partir dos números calculados.
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from analise import (
    MAPA_VARIAVEIS,
    NOMES_COLUNAS,
    TIMES_ANALISADOS,
    UNIDADES,
    VARIAVEIS_ANALISADAS,
    _estatisticas_de_serie,
)
from deteccao import (
    ALFA_GRUBBS,
    LIMIAR_ZSCORE,
    LOF_REGRA_PRATICA,
    TAXA_REFERENCIA,
    detectar,
    ecod_por_proporcao,
    grubbs_iterativo,
    obter_calibracao,
    valor_critico_grubbs,
)
from interpretacao import _curto, _n, _plural

ALFA_TESTES = 0.05
SEMENTE_DEMONSTRACAO = 42
MINUTOS_REGULAMENTARES = 240  # 48 min × 5 jogadores em quadra
MINUTOS_POR_PRORROGACAO = 25  # 5 min × 5 jogadores

# Estatísticas de box-score: quantidades medidas no jogo. Ficam de fora
# identificadores, o resultado binário (WL), os acumulados da temporada
# (W, L, W_PCT) e MIN, cujo domínio é discreto e tratado à parte.
COLUNAS_BOX_SCORE = [
    "FGM", "FGA", "FG_PCT", "FG3M", "FG3A", "FG3_PCT", "FTM", "FTA", "FT_PCT",
    "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS",
]
COLUNAS_ANALISADAS = {coluna: nome for nome, coluna in MAPA_VARIAVEIS.items()}
COLUNAS_PERCENTUAIS = ["W_PCT", "FG_PCT", "FG3_PCT", "FT_PCT"]
COLUNAS_IDENTIFICADORAS = {"Team_ID", "Game_ID"}

SIGNIFICADO_ZEROS = {
    "WL": "codificação binária do resultado: 0 = derrota, 1 = vitória. Não é ausência nem erro.",
    "W": "vitórias acumuladas antes da primeira vitória da temporada.",
    "L": "derrotas acumuladas antes da primeira derrota da temporada.",
    "W_PCT": "consequência direta de W = 0 (0 vitórias ÷ jogos disputados).",
    "BLK": "jogo sem nenhum toco: incomum (média ≈ 5 por jogo), mas plenamente possível; não é ausência.",
}
SIGNIFICADO_ZERO_CONTAGEM = (
    "contagem legítima: o evento pode simplesmente não ocorrer em um jogo."
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _finito(valor: Any) -> float | None:
    """Converte para float; NaN/inf viram None (JSON válido)."""
    if valor is None:
        return None
    numero = float(valor)
    return numero if np.isfinite(numero) else None


def _jogo(linha: pd.Series) -> dict[str, Any]:
    data = pd.to_datetime(linha.get("GAME_DATE"), errors="coerce")
    return {
        "time": str(linha.get("TEAM_NAME", "")),
        "data": data.strftime("%d/%m/%Y") if pd.notna(data) else None,
        "confronto": str(linha.get("MATCHUP", "")) or None,
    }


def _lista(itens: list[str]) -> str:
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _nome(coluna: str) -> str:
    return NOMES_COLUNAS.get(coluna, coluna)


# ---------------------------------------------------------------------------
# Ausentes, duplicatas, zeros e negativos
# ---------------------------------------------------------------------------

def contar_ausentes(
    fonte: pd.DataFrame, recorte: pd.DataFrame, tratado: pd.DataFrame
) -> list[dict[str, Any]]:
    linhas = []
    for coluna in fonte.columns:
        item = {"coluna": coluna, "nome": _nome(coluna)}
        for chave, base in (("fonte", fonte), ("recorte", recorte), ("tratado", tratado)):
            if coluna in base:
                quantidade = int(base[coluna].isna().sum())
                item[chave] = quantidade
                item[f"{chave}_pct"] = quantidade / len(base) * 100 if len(base) else 0.0
            else:
                item[chave] = None
                item[f"{chave}_pct"] = None
        linhas.append(item)
    return linhas


def contar_duplicatas(
    fonte: pd.DataFrame, recorte: pd.DataFrame, tratado: pd.DataFrame
) -> dict[str, Any]:
    chave = ["TEAM_NAME", "Game_ID"]
    ocorrencias = fonte["Game_ID"].value_counts()
    return {
        "fonte": {
            "registros": int(len(fonte)),
            "linha_inteira": int(fonte.duplicated().sum()),
            "chave_time_jogo": int(fonte.duplicated(subset=chave).sum()),
            "jogos_distintos": int(fonte["Game_ID"].nunique()),
            "jogos_fora_do_par": int((ocorrencias != 2).sum()),
        },
        "recorte": {
            "registros": int(len(recorte)),
            "linha_inteira": int(recorte.duplicated().sum()),
            "chave_time_jogo": int(recorte.duplicated(subset=chave).sum()),
        },
        "removidos_no_tratamento": int(len(recorte) - len(tratado)),
        "registros_tratados": int(len(tratado)),
    }


def contar_zeros_e_negativos(recorte: pd.DataFrame) -> list[dict[str, Any]]:
    linhas = []
    for coluna in recorte.columns:
        if coluna in COLUNAS_IDENTIFICADORAS:
            continue
        serie = pd.to_numeric(recorte[coluna], errors="coerce")
        if serie.notna().sum() == 0:
            continue
        zeros = int((serie == 0).sum())
        negativos = int((serie < 0).sum())
        if zeros or negativos:
            significado = SIGNIFICADO_ZEROS.get(coluna, SIGNIFICADO_ZERO_CONTAGEM)
        else:
            significado = "sem zeros nem negativos."
        linhas.append({
            "coluna": coluna,
            "nome": _nome(coluna),
            "zeros": zeros,
            "negativos": negativos,
            "significado": significado,
        })
    return linhas


# ---------------------------------------------------------------------------
# Domínio
# ---------------------------------------------------------------------------

def classificar_minutos(minutos: float) -> int | None:
    """Número de prorrogações implicado por MIN; None se fora do domínio.

    MIN soma os minutos de todos os jogadores: 48 min × 5 = 240 no tempo
    normal e +5 min × 5 = +25 por prorrogação. Logo, o domínio é 240 + 25k.
    """
    if pd.isna(minutos):
        return None
    excesso = float(minutos) - MINUTOS_REGULAMENTARES
    if excesso < 0 or excesso % MINUTOS_POR_PRORROGACAO:
        return None
    return int(excesso // MINUTOS_POR_PRORROGACAO)


def _numerico(base: pd.DataFrame, coluna: str) -> pd.Series:
    return pd.to_numeric(base[coluna], errors="coerce")


def _regras_dominio() -> list[tuple[str, str, Any]]:
    def pct(coluna):
        return lambda b: ~_numerico(b, coluna).between(0, 1) & _numerico(b, coluna).notna()

    def menor_igual(a, b_):
        return lambda b: _numerico(b, a) > _numerico(b, b_)

    def pct_coerente(pct_col, feitos, tentados):
        def regra(b):
            tent = _numerico(b, tentados)
            calculado = _numerico(b, feitos) / tent.where(tent > 0)
            return (calculado - _numerico(b, pct_col)).abs() > 0.001
        return regra

    regras = [
        ("MIN", "MIN = 240 + 25·k", "Minutos do time: 240 no tempo normal, +25 por prorrogação.",
         lambda b: _numerico(b, "MIN").map(classificar_minutos).isna()),
        ("WL", "WL ∈ {0, 1}", "Resultado binário.",
         lambda b: ~_numerico(b, "WL").isin([0, 1])),
        ("GAME_DATE", "GAME_DATE é data válida", "Data convertível para o tipo data.",
         lambda b: pd.to_datetime(b["GAME_DATE"], errors="coerce").isna()),
    ]
    regras += [
        (c, f"{c} ∈ [0, 1]", "Percentual armazenado como fração.", pct(c))
        for c in COLUNAS_PERCENTUAIS
    ]
    regras += [
        ("FGM", "FGM ≤ FGA", "Não se converte mais do que se tenta.", menor_igual("FGM", "FGA")),
        ("FG3M", "FG3M ≤ FG3A", "Idem para três pontos.", menor_igual("FG3M", "FG3A")),
        ("FTM", "FTM ≤ FTA", "Idem para lances livres.", menor_igual("FTM", "FTA")),
        ("FG3M", "FG3M ≤ FGM", "Cesta de três é uma cesta de quadra.", menor_igual("FG3M", "FGM")),
        ("REB", "REB = OREB + DREB", "Rebotes totais = ofensivos + defensivos.",
         lambda b: _numerico(b, "REB") != _numerico(b, "OREB") + _numerico(b, "DREB")),
        ("PTS", "PTS = 2·FGM + FG3M + FTM", "Cada cesta vale 2, a de três vale 1 a mais e o lance livre 1.",
         lambda b: _numerico(b, "PTS")
         != 2 * _numerico(b, "FGM") + _numerico(b, "FG3M") + _numerico(b, "FTM")),
        ("FG_PCT", "FG_PCT = FGM/FGA (±0,001)", "Percentual coerente com as contagens.",
         pct_coerente("FG_PCT", "FGM", "FGA")),
        ("FG3_PCT", "FG3_PCT = FG3M/FG3A (±0,001)", "Idem para três pontos.",
         pct_coerente("FG3_PCT", "FG3M", "FG3A")),
        ("FT_PCT", "FT_PCT = FTM/FTA (±0,001)", "Idem para lances livres.",
         pct_coerente("FT_PCT", "FTM", "FTA")),
        ("contagens", "Sem negativos nas contagens", "Contagens de box-score não podem ser negativas.",
         lambda b: (b[[c for c in COLUNAS_BOX_SCORE if c in b]].apply(pd.to_numeric, errors="coerce") < 0).any(axis=1)),
    ]
    return regras


def verificar_dominio(fonte: pd.DataFrame, recorte: pd.DataFrame) -> dict[str, Any]:
    regras = []
    for coluna, nome, descricao, funcao in _regras_dominio():
        regras.append({
            "coluna": coluna,
            "regra": nome,
            "descricao": descricao,
            "violacoes_fonte": int(funcao(fonte).fillna(False).sum()),
            "violacoes_recorte": int(funcao(recorte).fillna(False).sum()),
        })

    def resumo_minutos(base):
        contagem = _numerico(base, "MIN").value_counts().sort_index()
        return [
            {"minutos": int(m), "registros": int(q), "prorrogacoes": classificar_minutos(m)}
            for m, q in contagem.items()
        ]

    minutos = _numerico(recorte, "MIN")
    prorrogados = recorte[minutos > MINUTOS_REGULAMENTARES].copy()
    prorrogados["_data"] = pd.to_datetime(prorrogados["GAME_DATE"], errors="coerce")
    jogos = [
        {
            **_jogo(linha),
            "minutos": int(linha["MIN"]),
            "prorrogacoes": classificar_minutos(linha["MIN"]),
            "pontos": int(linha["PTS"]),
        }
        for _, linha in prorrogados.sort_values(["TEAM_NAME", "_data"]).iterrows()
    ]
    # Efeito da prorrogação na pontuação: média de PTS com e sem prorrogação
    # e quantos outliers de Tukey em PTS são jogos prorrogados.
    pontos = _numerico(recorte, "PTS")
    efeito = {}
    for time in TIMES_ANALISADOS:
        do_time = recorte["TEAM_NAME"] == time
        serie = pontos[do_time]
        tukey = _estatisticas_de_serie(serie)
        fora = (serie < tukey["limite_inferior"]) | (serie > tukey["limite_superior"])
        extra = minutos[do_time] > MINUTOS_REGULAMENTARES
        efeito[time] = {
            "media_regular": _finito(serie[~extra].mean()),
            "media_prorrogacao": _finito(serie[extra].mean()) if extra.any() else None,
            "jogos_prorrogacao": int(extra.sum()),
            "outliers_pts": int(fora.sum()),
            "outliers_pts_em_prorrogacao": int((fora & extra).sum()),
        }
    return {
        "regras": regras,
        "minutos_fonte": resumo_minutos(fonte),
        "minutos_recorte": resumo_minutos(recorte),
        "jogos_prorrogacao": jogos,
        "efeito_prorrogacao_pts": efeito,
    }


# ---------------------------------------------------------------------------
# Detectores univariados (Grubbs, ECOD, K-NN, DBSCAN e LOF vêm de deteccao.py)
# ---------------------------------------------------------------------------

def _adversario(confronto: str) -> tuple[str | None, str | None]:
    """'DAL vs. LAC' → ('LAC', 'casa'); 'DAL @ UTA' → ('UTA', 'fora')."""
    texto = str(confronto or "")
    if " vs. " in texto:
        return texto.split(" vs. ")[-1].strip(), "casa"
    if " @ " in texto:
        return texto.split(" @ ")[-1].strip(), "fora"
    return None, None


def _jogo_detalhado(linha: pd.Series, coluna: str) -> dict[str, Any]:
    adversario, mando = _adversario(linha.get("MATCHUP"))
    return {**_jogo(linha), "adversario": adversario, "mando": mando, "valor": float(linha[coluna])}


def _univariados(serie: pd.Series) -> dict[str, Any]:
    """Resumo por coluna (18 colunas): Z-score, IQR, Grubbs e ECOD."""
    serie = serie.dropna().astype(float)
    desvio = serie.std(ddof=1)
    z = (serie - serie.mean()) / desvio if desvio > 0 else serie * 0
    mascara_z = z.abs() > LIMIAR_ZSCORE
    tukey = _estatisticas_de_serie(serie)
    grubbs = grubbs_iterativo(serie)
    ecod = ecod_por_proporcao(serie.to_numpy())
    shapiro_p = _finito(stats.shapiro(serie).pvalue) if serie.nunique() > 2 else None
    return {
        "n": int(serie.size),
        "zscore": {
            "quantidade": int(mascara_z.sum()),
            "valores": sorted(float(v) for v in serie[mascara_z]),
            "z_maximo": _finito(z.abs().max()),
        },
        "iqr": {
            "quantidade": tukey["quantidade_outliers"],
            "valores": tukey["outliers"],
            "limite_inferior": tukey["limite_inferior"],
            "limite_superior": tukey["limite_superior"],
        },
        "grubbs": {
            "quantidade": len(grubbs["valores"]),
            "valores": sorted(grubbs["valores"]),
            "passos": grubbs["passos"],
            "shapiro_p": shapiro_p,
        },
        "ecod": {
            "quantidade": int(ecod["rotulos"].sum()),
            "valores": sorted(float(v) for v in serie.to_numpy()[ecod["rotulos"]]),
            "limiar": ecod["limiar"],
        },
    }


METODOS_UNIVARIADOS = ["zscore", "iqr", "grubbs", "ecod"]
METODOS_DETALHE = ["zscore", "iqr", "grubbs", "ecod", "knn", "dbscan", "lof"]


def outliers_por_coluna(dados: pd.DataFrame) -> list[dict[str, Any]]:
    linhas = []
    for coluna in COLUNAS_BOX_SCORE:
        if coluna not in dados:
            continue
        linhas.append({
            "coluna": coluna,
            "nome": _nome(coluna),
            "analisada": coluna in COLUNAS_ANALISADAS,
            "variavel": COLUNAS_ANALISADAS.get(coluna),
            "times": {
                time: _univariados(dados.loc[dados["TEAM_NAME"] == time, coluna])
                for time in TIMES_ANALISADOS
            },
        })
    return linhas


def _detalhe_variavel(dados: pd.DataFrame, time: str, variavel: str) -> dict[str, Any]:
    """Os 7 métodos numa variável de um time, com os jogos marcados."""
    coluna = MAPA_VARIAVEIS[variavel]
    base = dados[dados["TEAM_NAME"] == time].dropna(subset=[coluna])
    base = base.assign(_data=pd.to_datetime(base["GAME_DATE"], errors="coerce")).sort_values("_data")
    serie = base[coluna].astype(float)
    valores = serie.to_numpy()

    desvio = serie.std(ddof=1)
    z = (serie - serie.mean()) / desvio if desvio > 0 else serie * 0
    tukey = _estatisticas_de_serie(serie)
    grubbs = grubbs_iterativo(serie)
    distancia = detectar(valores)
    mascaras = {
        "zscore": (z.abs() > LIMIAR_ZSCORE).to_numpy(),
        "iqr": ((serie < tukey["limite_inferior"]) | (serie > tukey["limite_superior"])).to_numpy(),
        "grubbs": serie.index.isin(grubbs["indices"]),
        **{m: np.asarray(v, dtype=bool) for m, v in distancia["rotulos"].items()},
    }
    linhas = list(base.iterrows())
    metodos = {
        m: {
            "quantidade": int(mascara.sum()),
            "jogos": [_jogo_detalhado(linhas[i][1], coluna) for i in np.flatnonzero(mascara)],
        }
        for m, mascara in mascaras.items()
    }
    algum = np.logical_or.reduce(list(mascaras.values()))
    concordancia = []
    for i in np.flatnonzero(algum):
        marcas = {m: bool(mascaras[m][i]) for m in METODOS_DETALHE}
        concordancia.append({
            **_jogo_detalhado(linhas[i][1], coluna),
            "z": _finito(z.iloc[i]),
            "metodos": marcas,
            "total": sum(marcas.values()),
        })
    concordancia.sort(key=lambda j: (-j["total"], -abs(j["z"] or 0)))
    return {
        "variavel": variavel,
        "coluna": coluna,
        "unidade": UNIDADES[variavel],
        "time": time,
        "n": int(serie.size),
        "limites_tukey": [tukey["limite_inferior"], tukey["limite_superior"]],
        "grubbs_passos": grubbs["passos"],
        "parametros": distancia["parametros"],
        "metodos": metodos,
        "concordancia": concordancia,
        "_mascaras": mascaras,
    }


def outliers_por_variavel(dados: pd.DataFrame) -> dict[str, Any]:
    """7 variáveis × 2 times × 7 métodos, com jogos e concordância."""
    detalhes = [
        _detalhe_variavel(dados, time, variavel)
        for variavel in VARIAVEIS_ANALISADAS for time in TIMES_ANALISADOS
    ]
    # Matriz de concordância: em quantos pares (jogo, variável) cada dupla de
    # métodos marcou o mesmo jogo. A diagonal é o total de cada método.
    matriz = {
        a: {b: int(sum((d["_mascaras"][a] & d["_mascaras"][b]).sum() for d in detalhes)) for b in METODOS_DETALHE}
        for a in METODOS_DETALHE
    }
    jogos_marcados = sum(len(d["concordancia"]) for d in detalhes)
    unanimes = sum(1 for d in detalhes for j in d["concordancia"] if j["total"] == len(METODOS_DETALHE))
    for d in detalhes:
        del d["_mascaras"]
    parametros = {
        f"{n}": obter_calibracao(n, 1)
        for n in sorted({d["n"] for d in detalhes})
    }
    return {
        "metodos": METODOS_DETALHE,
        "detalhes": detalhes,
        "matriz_concordancia": matriz,
        "jogos_marcados": jogos_marcados,
        "marcados_por_todos": unanimes,
        "parametros_por_n": parametros,
    }


# ---------------------------------------------------------------------------
# Detectores multivariados (7 variáveis analisadas, por time)
# ---------------------------------------------------------------------------

def outliers_multivariados(dados: pd.DataFrame) -> dict[str, Any]:
    colunas = [MAPA_VARIAVEIS[nome] for nome in VARIAVEIS_ANALISADAS]
    resultado = {}
    for time in TIMES_ANALISADOS:
        base = dados[dados["TEAM_NAME"] == time].dropna(subset=colunas)
        deteccao = detectar(base[colunas].to_numpy(dtype=float))
        rotulos = deteccao["rotulos"]
        resultado[time] = {
            "n": int(len(base)),
            "parametros": deteccao["parametros"],
            "metodos": {
                metodo: {
                    "quantidade": int(mascara.sum()),
                    "jogos": [
                        {**_jogo(linha), "adversario": _adversario(linha.get("MATCHUP"))[0],
                         "valores": {c: float(linha[c]) for c in colunas}}
                        for _, linha in base[mascara].iterrows()
                    ],
                }
                for metodo, mascara in rotulos.items()
            },
            "em_todos": int(np.logical_and.reduce(list(rotulos.values())).sum()),
        }
    return {"colunas": colunas, "times": resultado}


# ---------------------------------------------------------------------------
# Testes de mecanismo de ausência (demonstração com ausência simulada)
# ---------------------------------------------------------------------------

def _em_normal(x: np.ndarray, max_iter: int = 1000, tol: float = 1e-8):
    """Média e covariância (máxima verossimilhança) de uma normal com ausentes."""
    n, p = x.shape
    observado = ~np.isnan(x)
    mu = np.nanmean(x, axis=0)
    sigma = np.diag(np.nanvar(x, axis=0))
    for _ in range(max_iter):
        soma = np.zeros(p)
        soma_quadrados = np.zeros((p, p))
        for i in range(n):
            o, m = observado[i], ~observado[i]
            linha = x[i].copy()
            correcao = np.zeros((p, p))
            if m.any():
                beta = sigma[np.ix_(m, o)] @ np.linalg.inv(sigma[np.ix_(o, o)])
                linha[m] = mu[m] + beta @ (x[i, o] - mu[o])
                correcao[np.ix_(m, m)] = sigma[np.ix_(m, m)] - beta @ sigma[np.ix_(o, m)]
            soma += linha
            soma_quadrados += np.outer(linha, linha) + correcao
        novo_mu = soma / n
        novo_sigma = soma_quadrados / n - np.outer(novo_mu, novo_mu)
        mudanca = max(np.abs(novo_mu - mu).max(), np.abs(novo_sigma - sigma).max())
        mu, sigma = novo_mu, novo_sigma
        if mudanca < tol:
            break
    return mu, sigma


def teste_little(x: np.ndarray) -> dict[str, Any]:
    """Little (1988): d² = Σⱼ nⱼ (ȳⱼ − μ̂ⱼ)ᵀ Σ̂ⱼ⁻¹ (ȳⱼ − μ̂ⱼ) ~ χ²(Σ pⱼ − p)."""
    n, p = x.shape
    mu, sigma = _em_normal(x)
    observado = ~np.isnan(x)
    padroes = pd.DataFrame(observado).astype(int).astype(str).agg("".join, axis=1)
    d2, soma_p = 0.0, 0
    for _, linhas in padroes.groupby(padroes).groups.items():
        o = observado[linhas[0]]
        if not o.any():
            continue
        media_grupo = x[np.ix_(linhas, o)].mean(axis=0)
        diferenca = media_grupo - mu[o]
        d2 += len(linhas) * diferenca @ np.linalg.inv(sigma[np.ix_(o, o)]) @ diferenca
        soma_p += int(o.sum())
    gl = soma_p - p
    p_valor = float(stats.chi2.sf(d2, gl)) if gl > 0 else None
    return {
        "estatistica": float(d2),
        "gl": int(gl),
        "p_valor": p_valor,
        "padroes": int(padroes.nunique()),
        "rejeita_mcar": p_valor is not None and p_valor < ALFA_TESTES,
    }


def _logistica(x: np.ndarray, y: np.ndarray, max_iter: int = 100):
    """Regressão logística por Newton-Raphson; devolve β, erros-padrão e log-L."""
    desenho = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(desenho.shape[1])
    for _ in range(max_iter):
        prob = 1 / (1 + np.exp(-desenho @ beta))
        peso = prob * (1 - prob)
        hessiana = desenho.T @ (desenho * peso[:, None])
        passo = np.linalg.solve(hessiana, desenho.T @ (y - prob))
        beta += passo
        if np.abs(passo).max() < 1e-10:
            break
    prob = np.clip(1 / (1 + np.exp(-desenho @ beta)), 1e-12, 1 - 1e-12)
    log_l = float(np.sum(y * np.log(prob) + (1 - y) * np.log(1 - prob)))
    peso = prob * (1 - prob)
    covariancia = np.linalg.inv(desenho.T @ (desenho * peso[:, None]))
    return beta, np.sqrt(np.diag(covariancia)), log_l


def teste_fairclough(
    indicador: np.ndarray, preditores: np.ndarray, nomes: list[str]
) -> dict[str, Any]:
    """Regressão logística do indicador de ausência sobre variáveis observadas.

    H₀ (compatível com MCAR): nenhum preditor altera a chance de ausência.
    Teste global pela razão de verossimilhança contra o modelo só com
    intercepto; coeficientes individuais pelo teste de Wald.
    """
    y = indicador.astype(float)
    desvio = preditores.std(axis=0)
    z = (preditores - preditores.mean(axis=0)) / np.where(desvio == 0, 1, desvio)
    beta, erro, log_l = _logistica(z, y)
    taxa = y.mean()
    log_l_nulo = float(len(y) * (taxa * np.log(taxa) + (1 - taxa) * np.log(1 - taxa)))
    razao = 2 * (log_l - log_l_nulo)
    gl = z.shape[1]
    p_valor = float(stats.chi2.sf(razao, gl))
    coeficientes = [
        {
            "variavel": nome,
            "beta": float(beta[i + 1]),
            "razao_chances": float(np.exp(beta[i + 1])),
            "p_valor": float(2 * stats.norm.sf(abs(beta[i + 1] / erro[i + 1]))),
        }
        for i, nome in enumerate(nomes)
    ]
    return {
        "estatistica": float(razao),
        "gl": gl,
        "p_valor": p_valor,
        "coeficientes": coeficientes,
        "rejeita_mcar": p_valor < ALFA_TESTES,
    }


def demonstrar_testes_ausencia(dados: pd.DataFrame) -> dict[str, Any]:
    """Aplica Little e Fairclough a cópias com PTS removido de forma MCAR e MAR."""
    colunas = [MAPA_VARIAVEIS[nome] for nome in VARIAVEIS_ANALISADAS]
    base = dados[colunas].dropna().to_numpy(dtype=float)
    n = len(base)
    alvo = colunas.index("PTS")
    outras = [c for c in colunas if c != "PTS"]
    gerador = np.random.default_rng(SEMENTE_DEMONSTRACAO)
    proporcao = 0.20

    # MCAR: toda linha tem a mesma probabilidade de perder PTS.
    mcar = np.zeros(n, dtype=bool)
    mcar[gerador.choice(n, size=round(proporcao * n), replace=False)] = True
    # MAR: a chance de perder PTS cresce com FG3M (observada); nada depende do
    # próprio PTS além do que FG3M já explica.
    fg3m = base[:, colunas.index("FG3M")]
    escore = (fg3m - fg3m.mean()) / fg3m.std()
    probabilidade = 1 / (1 + np.exp(-(np.log(proporcao / (1 - proporcao)) + 1.5 * escore)))
    mar = gerador.random(n) < probabilidade

    cenarios = []
    for chave, nome, mascara, descricao in (
        ("mcar", "MCAR simulado", mcar,
         f"{round(proporcao * 100)}% dos valores de PTS apagados por sorteio simples (mesma chance para todo jogo)."),
        ("mar", "MAR simulado", mar,
         "PTS apagado com probabilidade logística crescente em FG3M (cestas de 3, observada): "
         "quem acerta mais de três tende a ficar sem PTS."),
    ):
        copia = base.copy()
        copia[mascara, alvo] = np.nan
        cenarios.append({
            "chave": chave,
            "nome": nome,
            "descricao": descricao,
            "ausentes": int(mascara.sum()),
            "n": n,
            "little": teste_little(copia),
            "fairclough": teste_fairclough(
                mascara, np.delete(base, alvo, axis=1), outras
            ),
        })
    return {"semente": SEMENTE_DEMONSTRACAO, "variavel_alvo": "PTS", "variaveis": colunas,
            "alfa": ALFA_TESTES, "cenarios": cenarios}


# ---------------------------------------------------------------------------
# Teoria (estática) e interpretação (a partir dos números)
# ---------------------------------------------------------------------------

MECANISMOS = [
    {
        "sigla": "MCAR",
        "nome": "Missing Completely At Random",
        "definicao": "A probabilidade de um valor faltar não depende de nenhum dado, observado ou não: P(R | Y_obs, Y_falt) = P(R).",
        "exemplo": "O arquivo do box-score de alguns jogos se corrompe numa falha do servidor da liga, sorteando jogos sem relação com placar, time ou adversário.",
        "consequencia": "Os casos completos são uma subamostra aleatória: excluir linhas só reduz n (perde precisão), sem viés.",
    },
    {
        "sigla": "MAR",
        "nome": "Missing At Random",
        "definicao": "A ausência depende apenas de variáveis observadas: P(R | Y_obs, Y_falt) = P(R | Y_obs).",
        "exemplo": "Em jogos fora de casa (MATCHUP com '@', observado) a mesa local de outra arena deixa de registrar os tocos com mais frequência; dado o mando, a falta não depende de quantos tocos houve.",
        "consequencia": "Excluir linhas gera viés; imputação múltipla ou máxima verossimilhança condicionadas às observadas corrigem.",
    },
    {
        "sigla": "MNAR",
        "nome": "Missing Not At Random",
        "definicao": "A ausência depende do próprio valor faltante (ou de algo não medido), mesmo após condicionar nas observadas.",
        "exemplo": "Um time omite do relatório as faltas pessoais justamente nos jogos em que cometeu muitas faltas: a chance de faltar depende do próprio PF.",
        "consequencia": "Nenhum teste nos dados observados confirma MNAR; exige modelar o mecanismo (seleção, pattern-mixture) e análise de sensibilidade.",
    },
]

MOTIVO_NAO_APLICADO = (
    "Não foi aplicado à base real porque o recorte dos dois times tem 0 valores ausentes em todas as colunas: "
    "o indicador de ausência R é constante (sempre 0), não existem padrões de ausência diferentes para comparar "
    "e qualquer estatística do teste ficaria indefinida. A demonstração abaixo usa cópias com ausência simulada "
    "apenas para mostrar como o teste seria lido."
)

TESTES_AUSENCIA = [
    {
        "nome": "Teste de Little (MCAR)",
        "referencia": "Little (1988), JASA 83(404)",
        "hipotese": "H₀: os dados são MCAR. H₁: não são MCAR.",
        "como": "Agrupa as linhas por padrão de ausência (quais colunas faltam). Estima μ e Σ por EM sob normal multivariada e compara a média observada de cada padrão com μ̂ nas colunas presentes.",
        "estatistica": "d² = Σⱼ nⱼ (ȳⱼ − μ̂ⱼ)ᵀ Σ̂ⱼ⁻¹ (ȳⱼ − μ̂ⱼ) ~ χ² com Σⱼ pⱼ − p graus de liberdade (pⱼ = colunas observadas no padrão j).",
        "decisao": "p < 0,05 → rejeita MCAR (as médias variam com o padrão de ausência).",
        "porque": "É o teste global de MCAR mais usado: um único p-valor para todas as variáveis; decide se a exclusão de linhas é aceitável.",
        "limitacoes": "Supõe normalidade e Σ comum; pouco poder com poucos ausentes; não rejeitar não prova MCAR; não separa MAR de MNAR.",
        "paragrafos": [
            "O teste de Little verifica se os dados são MCAR comparando, para cada padrão de ausência, a média das "
            "colunas observadas com a média geral estimada por EM. A hipótese nula é que os dados são MCAR: se a "
            "ausência fosse puro acaso, os grupos de padrão teriam as mesmas médias. Aqui ele seria aplicado às 7 "
            "variáveis (PTS, REB, AST, STL, BLK, PF, FG3M), e d² seria comparado a uma χ².",
            MOTIVO_NAO_APLICADO,
        ],
        "implementado": True,
    },
    {
        "nome": "Teste de Jamshidian-Jalal",
        "referencia": "Jamshidian & Jalal (2010), Psychometrika 75(4); pacote R MissMech",
        "hipotese": "H₀: MCAR e homogeneidade das covariâncias entre os padrões de ausência.",
        "como": "Imputa os ausentes (sob normalidade ou não paramétrica) e testa se as covariâncias são iguais entre os grupos de padrão: teste de Hawkins (normalidade + homocedasticidade); se rejeitado, um teste não paramétrico (Anderson-Darling k-amostras) separa não normalidade de violação de MCAR.",
        "estatistica": "Hawkins: F de Neyman sobre os p-valores por grupo; não paramétrico: estatística de Anderson-Darling k-amostras.",
        "decisao": "Se Hawkins não rejeita, aceita MCAR. Se rejeita e o Anderson-Darling também, rejeita MCAR; se só Hawkins rejeita, o problema é não normalidade.",
        "porque": "Complementa o Little testando também as covariâncias (não só médias) e distingue 'não é MCAR' de 'não é normal'.",
        "limitacoes": "Exige grupos com casos suficientes por padrão; depende da imputação; não separa MAR de MNAR.",
        "paragrafos": [
            "O teste de Jamshidian-Jalal testa MCAR olhando a homogeneidade das covariâncias entre os grupos de "
            "padrão de ausência, e não só das médias como o Little. A hipótese nula é que os dados são MCAR e que as "
            "covariâncias são iguais entre os grupos. Na prática, imputa-se os ausentes, aplica-se o teste de Hawkins "
            "e, se ele rejeitar, um teste não paramétrico separa 'não é normal' de 'não é MCAR'. Aqui seria aplicado "
            "às 7 variáveis, com cada padrão de ausência como grupo.",
            MOTIVO_NAO_APLICADO.replace(
                " A demonstração abaixo usa cópias com ausência simulada apenas para mostrar como o teste seria lido.",
                " Ele também exige vários padrões com casos suficientes, o que não existe sem ausentes; por isso é "
                "apresentado só em teoria, sem implementação."),
        ],
        "implementado": False,
    },
    {
        "nome": "Teste de Listing e Schlittgen (LS)",
        "referencia": "Listing & Schlittgen (1998), Biometrical Journal 40(8)",
        "hipotese": "H₀: a saída (dropout) em dados longitudinais é completamente aleatória.",
        "como": "Em medidas repetidas, compara, em cada instante, a distribuição dos valores já observados de quem sai com a de quem permanece (testes de postos do tipo Wilcoxon), combinando os instantes numa estatística global.",
        "estatistica": "Soma ponderada das estatísticas de postos por instante, padronizada (aprox. normal).",
        "decisao": "p < 0,05 → quem abandona difere de quem permanece nos valores anteriores: o dropout não é MCAR.",
        "porque": "Não paramétrico e próprio para séries ao longo do tempo, onde o Little não usa a ordem das medidas.",
        "limitacoes": "Exige estrutura longitudinal com dropout monótono; detecta dependência das observadas (MAR), nunca MNAR.",
        "paragrafos": [
            "O teste de Listing e Schlittgen é feito para dados longitudinais com abandono (dropout): verifica se "
            "quem deixa de ser medido a partir de certo instante tinha, antes, valores diferentes de quem continua. "
            "A hipótese nula é que o abandono é completamente aleatório. No basquete, ele se aplicaria a séries de "
            "jogos sucessivos, por exemplo um jogador cujos registros param após uma lesão: compara-se, jogo a jogo, "
            "o desempenho anterior de quem saiu com o de quem seguiu, por testes de postos.",
            MOTIVO_NAO_APLICADO.replace(
                " A demonstração abaixo usa cópias com ausência simulada apenas para mostrar como o teste seria lido.",
                " Além disso, a base é de times (que jogam todos os jogos), sem séries interrompidas; por isso o teste "
                "é apresentado só em teoria, sem implementação."),
        ],
        "implementado": False,
    },
    {
        "nome": "Regressão logística de Fairclough",
        "referencia": "Fairclough (2010), Design and Analysis of Quality of Life Studies in Clinical Trials",
        "hipotese": "H₀: nenhuma variável observada altera a chance de ausência (compatível com MCAR).",
        "como": "Cria o indicador Rᵢ = 1 se o valor falta e ajusta logit P(Rᵢ = 1) = β₀ + β₁x₁ + … + βₖxₖ com as variáveis observadas como preditoras.",
        "estatistica": "Razão de verossimilhança 2(ℓ_modelo − ℓ_intercepto) ~ χ²(k); Wald para cada βⱼ.",
        "decisao": "p < 0,05 → a ausência é previsível pelas observadas: rejeita MCAR e indica quais variáveis entram na imputação (MAR).",
        "porque": "Mostra QUAIS variáveis explicam a ausência e quanto (razão de chances), o que orienta o modelo de imputação.",
        "limitacoes": "Só detecta relação com o que foi observado; MNAR passa despercebido; supõe forma logística linear.",
        "paragrafos": [
            "A abordagem de Fairclough modela a própria ausência: cria-se Rᵢ = 1 quando o valor falta e ajusta-se "
            "uma regressão logística de R sobre as variáveis observadas. A hipótese nula é que nenhuma delas muda a "
            "chance de ausência, o que é compatível com MCAR; coeficientes significativos indicam MAR e dizem quais "
            "variáveis precisam entrar na imputação. Aqui, R seria o indicador de ausência de uma variável (ex.: PTS) "
            "e os preditores, as outras seis.",
            MOTIVO_NAO_APLICADO + " Com R sempre 0, a logística nem pode ser ajustada (não há casos com R = 1).",
        ],
        "implementado": True,
    },
]


def _metodos_outlier(calibracao: dict[str, Any], calibracao_7d: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Teoria de cada detector, com os parâmetros efetivamente usados."""
    taxa = _n(TAXA_REFERENCIA * 100)
    n = calibracao["n"]
    multi = ""
    if calibracao_7d:
        multi = (f" No modo multivariado (7 variáveis): k = {calibracao_7d['knn_k']}, corte "
                 f"{_n(calibracao_7d['knn_corte'])}; ε = {_n(calibracao_7d['dbscan_eps'])}, min_samples = "
                 f"{calibracao_7d['dbscan_min_samples']}; LOF > {_n(calibracao_7d['lof_corte'])}; ECOD > "
                 f"{_n(calibracao_7d['ecod_corte'])}.")
    regra_calibracao = (
        f"Calibração: em {calibracao['repeticoes']} amostras normais simuladas com n = {n} (semente fixa), o corte "
        f"é escolhido para marcar {taxa}% dos pontos — a mesma proporção que a regra de Tukey marca numa normal "
        "(fora de ±2,698 σ). Assim os métodos ficam comparáveis entre si e com o boxplot."
    )
    return [
        {
            "chave": "zscore", "nome": "Z-score", "tipo": "univariado",
            "formula": f"zᵢ = (xᵢ − x̄) / s; outlier se |zᵢ| > {_n(LIMIAR_ZSCORE, 0)}",
            "como": "Mede a distância à média em desvios padrão amostrais (n − 1).",
            "premissas": "Distribuição aproximadamente normal; a média e o DP são inflados pelos próprios extremos (mascaramento).",
            "parametros": f"Limiar |z| > {_n(LIMIAR_ZSCORE, 0)}: convenção do enunciado (≈ 0,27% de uma normal).",
        },
        {
            "chave": "iqr", "nome": "IQR / boxplot (Tukey)", "tipo": "univariado",
            "formula": "outlier se x < Q1 − 1,5·IQR ou x > Q3 + 1,5·IQR",
            "como": "Usa quartis (interpolação linear), que não são afetados pelos extremos; é o critério principal do relatório e o mesmo do boxplot.",
            "premissas": "Nenhuma distribuição; em assimetria forte marca mais pontos na cauda longa.",
            "parametros": f"k = 1,5 (Tukey, 1977); numa normal corresponde a ±2,698 σ e marca {taxa}% dos pontos — a taxa de referência usada para calibrar os demais.",
        },
        {
            "chave": "grubbs", "nome": "Teste de Grubbs (iterativo)", "tipo": "univariado",
            "formula": "G = max|xᵢ − x̄| / s;  G_crít = ((n−1)/√n)·√(t² / (n − 2 + t²)),  t = t_{α/(2n), n−2}",
            "como": f"Testa o valor mais distante da média: H₀ 'não há outlier'. Se G > G_crít (α = {_n(ALFA_GRUBBS)} bilateral), remove o valor e repete com n − 1 até um passo não significativo.",
            "premissas": "Normalidade (o valor crítico vem da distribuição t). O Shapiro-Wilk de cada coluna é exibido: com p < 0,05, o Grubbs deve ser lido com cautela.",
            "parametros": f"α = {_n(ALFA_GRUBBS)} (G_crít = {_n(valor_critico_grubbs(n))} para n = {n}); o α vale por passo, e dois extremos próximos podem mascarar-se (o ESD generalizado de Rosner trata isso).",
        },
        {
            "chave": "ecod", "nome": "ECOD (Li et al., 2022)", "tipo": "univariado e multivariado",
            "formula": "F̂_esq(x) = #{Xᵢ ≤ x}/n, F̂_dir(x) = #{Xᵢ ≥ x}/n;  Oᵢ = max{ Σⱼ −log F̂_esq,ⱼ(xᵢⱼ), Σⱼ −log F̂_dir,ⱼ(xᵢⱼ), Σⱼ cauda pela assimetria γⱼ }",
            "como": "Estima as funções de distribuição empíricas à esquerda e à direita de cada coluna, escolhe a cauda pela assimetria (γ < 0 → esquerda, senão direita) e soma as probabilidades de cauda em escala −log. Implementado com numpy, seguindo o Algoritmo 1 do artigo.",
            "premissas": "Não paramétrico e sem parâmetros de distância; trata as colunas como independentes (soma das caudas). Numa única coluna o score depende só do posto do valor, não da distância.",
            "parametros": f"Univariado: como o score depende só do posto, qualquer corte equivale a fixar uma proporção; usa-se a taxa de referência ({taxa}%, percentil {_n(100 - TAXA_REFERENCIA * 100)} dos scores). Em n = {n} isso marca no máximo o jogo de cauda mais extrema, e só quando nenhum outro jogo tem o mesmo score — inclusive o extremo da cauda oposta: se o mínimo e o máximo são ambos únicos, os dois têm probabilidade de cauda 1/n, empatam e nenhum é marcado (é o que acontece com o jogo de 15 tocos). Multivariado: corte calibrado sob normalidade.",
        },
        {
            "chave": "knn", "nome": "K-NN (distância ao k-ésimo vizinho)", "tipo": "univariado e multivariado",
            "formula": "scoreᵢ = distância ao k-ésimo vizinho mais próximo, em σ robusto ((x − mediana) ÷ (IQR/1,349))",
            "como": "Um jogo isolado fica longe dos seus vizinhos; quanto maior a distância ao k-ésimo, mais isolado.",
            "premissas": "Escalas comparáveis (por isso a padronização robusta); sensível à escolha de k.",
            "parametros": f"k = round(√n) = {calibracao['knn_k']} (regra usual); corte = {_n(calibracao['knn_corte'])} σ robusto. {regra_calibracao}{multi}",
        },
        {
            "chave": "dbscan", "nome": "DBSCAN", "tipo": "univariado e multivariado",
            "formula": "ponto-núcleo: ≥ min_samples vizinhos no raio ε; ruído = ponto que não é núcleo nem está a ≤ ε de um núcleo",
            "como": "Agrupa regiões densas; o que sobra fora de qualquer grupo é ruído (outlier).",
            "premissas": "Densidade homogênea; em várias dimensões as distâncias se concentram e ε precisa crescer.",
            "parametros": f"min_samples = {calibracao['dbscan_min_samples']} (Ester et al., 1996: 4 em baixa dimensão; 2·dimensão acima, Sander et al., 1998); ε = {_n(calibracao['dbscan_eps'])} σ robusto, o menor raio cuja taxa de ruído sob normalidade é ≤ {taxa}% (busca binária).",
        },
        {
            "chave": "lof", "nome": "LOF (Local Outlier Factor)", "tipo": "univariado e multivariado",
            "formula": "LOF(p) = média da densidade local dos vizinhos ÷ densidade local de p; ≈ 1 para pontos típicos",
            "como": "Compara a densidade de cada jogo com a dos vizinhos: detecta pontos isolados em relação à própria região, não ao todo.",
            "premissas": "Escalas comparáveis; depende de n_neighbors; valores repetidos (contagens) aumentam a densidade local.",
            "parametros": f"n_neighbors = {calibracao['lof_vizinhos']} (Breunig et al., 2000, sugerem 10 a 20 ou mais); corte LOF > {_n(calibracao['lof_corte'])}, calibrado sob normalidade — mais exigente que a regra prática LOF > {_n(LOF_REGRA_PRATICA)}, que em dados normais com n = {n} marcaria {_n(calibracao['lof_taxa_regra_pratica'] * 100)}% dos jogos.",
        },
    ]


NOMES_METODOS = {
    "zscore": "Z-score", "iqr": "IQR / boxplot (Tukey)", "grubbs": "Teste de Grubbs (iterativo)",
    "ecod": "ECOD (Li et al., 2022)", "knn": "K-NN (distância ao k-ésimo vizinho)", "dbscan": "DBSCAN",
    "lof": "LOF (Local Outlier Factor)",
}


def _textos_por_variavel(por_variavel: dict[str, Any]) -> list[dict[str, Any]]:
    metodos = por_variavel["metodos"]
    detalhes = por_variavel["detalhes"]
    matriz = por_variavel["matriz_concordancia"]
    totais = ", ".join(f"{NOMES_METODOS[m].split(' (')[0]} {matriz[m][m]}" for m in metodos)
    fortes = [
        (d, j) for d in detalhes for j in d["concordancia"] if j["total"] >= 4
    ]
    isolados = [
        (d, j) for d in detalhes for j in d["concordancia"] if j["total"] == 1
    ]
    sem_marcas = [f"{d['variavel']} ({_curto(d['time'])})" for d in detalhes if not d["concordancia"]]

    def jogo(d, j):
        return (f"{d['variavel']} {_n(j['valor'], 0)} ({_curto(d['time'])}, {j['data']} contra "
                f"{j['adversario']}, {j['total']} de {len(metodos)} métodos)")

    paragrafos = [
        f"Nas 7 variáveis × 2 times, o número de jogos marcados por método é: {totais}. "
        f"Ao todo, {por_variavel['jogos_marcados']} pares (jogo, variável) foram marcados por pelo menos um método "
        f"e {por_variavel['marcados_por_todos']} por todos os {len(metodos)}.",
    ]
    if fortes:
        paragrafos.append(
            "Os casos em que 4 ou mais métodos concordam — os outliers mais sólidos — são: "
            + _lista([jogo(d, j) for d, j in fortes]) + "."
        )
    if isolados:
        por_metodo: dict[str, int] = {}
        for _, j in isolados:
            metodo = next(m for m, v in j["metodos"].items() if v)
            por_metodo[metodo] = por_metodo.get(metodo, 0) + 1
        paragrafos.append(
            f"{_plural(len(isolados), 'marcação foi feita', 'marcações foram feitas')} por um único método ("
            + ", ".join(f"{NOMES_METODOS[m].split(' (')[0]}: {q}" for m, q in por_metodo.items())
            + "). Marcações isoladas são fracas: dependem da regra de um método só e não se sustentam nos demais."
        )
    if sem_marcas:
        paragrafos.append(
            f"Nenhum método marcou jogo algum em {_lista(sem_marcas)}: distribuições sem valores atípicos."
        )
    secoes = [{"titulo": "Outliers por variável: quantos e quais jogos", "paragrafos": paragrafos}]

    pares = sorted(
        ((a, b, matriz[a][b]) for i, a in enumerate(metodos) for b in metodos[i + 1:]),
        key=lambda item: -item[2],
    )

    def concordancia(a, b, q):
        uniao = matriz[a][a] + matriz[b][b] - q
        return f"{NOMES_METODOS[a].split(' (')[0]} e {NOMES_METODOS[b].split(' (')[0]} ({q} em comum de {uniao})"

    secoes.append({"titulo": "Concordância entre os métodos", "paragrafos": [
        "Os pares que mais coincidem são " + _lista([concordancia(*p) for p in pares[:3] if p[2] > 0])
        + ". Como K-NN, DBSCAN e LOF foram calibrados para marcar, em dados normais, a mesma proporção da regra "
        "de Tukey, a coincidência com o IQR indica que eles enxergam os mesmos jogos isolados, e não que copiam a regra.",
        "O Z-score (|z| > 3) e o Grubbs são mais conservadores: exigem que o valor seja improvável sob uma normal, "
        "com corte perto de 3 desvios padrão, enquanto o IQR marca a partir de 2,7. O ECOD univariado depende só do "
        "posto do valor; por isso tende a marcar o jogo mais extremo de cada coluna mesmo quando ele está próximo "
        "dos demais, e é o que menos concorda com os métodos de distância.",
    ]})
    return secoes


def _textos_outliers(
    por_coluna: list[dict[str, Any]], por_variavel: dict[str, Any], multivariados: dict[str, Any]
) -> list[dict[str, Any]]:
    secoes = _textos_por_variavel(por_variavel)
    totais = {
        time: {m: sum(l["times"][time][m]["quantidade"] for l in por_coluna) for m in METODOS_UNIVARIADOS}
        for time in TIMES_ANALISADOS
    }
    celulas = len(por_coluna) * len(TIMES_ANALISADOS)
    paragrafos = [
        f"No resumo das {len(por_coluna)} colunas de box-score × {len(TIMES_ANALISADOS)} times, os totais de valores "
        "marcados são: "
        + "; ".join(
            f"{_curto(t)} — " + ", ".join(f"{NOMES_METODOS[m].split(' (')[0]} {totais[t][m]}" for m in METODOS_UNIVARIADOS)
            for t in TIMES_ANALISADOS
        ) + "."
    ]
    ordem = sorted(
        ((l["coluna"], t, sum(l["times"][t][m]["quantidade"] for m in ("zscore", "iqr", "grubbs")))
         for l in por_coluna for t in TIMES_ANALISADOS),
        key=lambda item: -item[2],
    )
    destaques = [f"{c} ({_curto(t)}, {q})" for c, t, q in ordem[:4] if q > 0]
    if destaques:
        paragrafos.append(
            "Somando Z-score, IQR e Grubbs, as colunas com mais marcações são " + _lista(destaques) + "."
        )
    secoes.append({"titulo": "Resumo nas 18 colunas de box-score", "paragrafos": paragrafos})

    nao_normais = [
        (l["coluna"], t) for l in por_coluna for t in TIMES_ANALISADOS
        if (l["times"][t]["grubbs"]["shapiro_p"] or 1) < ALFA_TESTES
    ]
    iqr_sem_grubbs = sum(
        1 for l in por_coluna for t in TIMES_ANALISADOS
        if l["times"][t]["iqr"]["quantidade"] > l["times"][t]["grubbs"]["quantidade"]
    )
    grubbs_alem_z = sum(
        1 for l in por_coluna for t in TIMES_ANALISADOS
        if l["times"][t]["grubbs"]["quantidade"] > l["times"][t]["zscore"]["quantidade"]
    )
    z_alem_grubbs = sum(
        1 for l in por_coluna for t in TIMES_ANALISADOS
        if l["times"][t]["zscore"]["quantidade"] > l["times"][t]["grubbs"]["quantidade"]
    )
    tamanhos = sorted({l["times"][t]["n"] for l in por_coluna for t in TIMES_ANALISADOS})
    por_valor: dict[str, list[int]] = {}
    for n in tamanhos:
        por_valor.setdefault(_n(valor_critico_grubbs(n)), []).append(n)
    criticos = " e ".join(
        f"{valor} para n = {' e '.join(str(n) for n in ns)}" for valor, ns in por_valor.items()
    )
    if grubbs_alem_z:
        texto_z = (
            f"O Grubbs marcou mais que o Z-score em {grubbs_alem_z} combinações: ao remover o primeiro extremo, "
            "a média e o DP encolhem e o seguinte pode passar a ser significativo, enquanto o Z-score usa uma "
            "única vez o DP inflado pelos próprios extremos."
        )
    else:
        texto_z = (
            "O Grubbs não marcou nada além do Z-score: o seu corte (G crítico = "
            f"{criticos}) é mais exigente que |z| > {_n(LIMIAR_ZSCORE, 0)}, de modo que, aqui, o ganho da "
            "iteração (desmascarar um segundo extremo) não chegou a aparecer"
            + (f"; em {z_alem_grubbs} combinações o Z-score marcou um valor entre 3 e o G crítico."
               if z_alem_grubbs else ".")
        )
    lista_normais = ", ".join(f"{c} ({_curto(t)})" for c, t in nao_normais)
    secoes.append({"titulo": "Por que os métodos discordam", "paragrafos": [
        f"O IQR marcou mais valores que o Grubbs em {iqr_sem_grubbs} de {celulas} combinações coluna × time. "
        "A regra de Tukey olha só para quartis e marca qualquer ponto além de 1,5×IQR; o Grubbs exige que o extremo "
        f"seja improvável sob uma normal com α = {_n(ALFA_GRUBBS)}, e o corte cresce com n ({criticos}).",
        texto_z,
        f"O Shapiro-Wilk rejeitou a normalidade (p < 0,05) em {len(nao_normais)} de {celulas} combinações"
        + (f" — {lista_normais}" if nao_normais else "")
        + ". Nelas o Z-score e o Grubbs perdem a base teórica e o IQR é a referência; nas contagens pequenas "
        "(STL, BLK) os valores discretos e repetidos também pesam na rejeição.",
    ]})

    paragrafos_mv = []
    for time in TIMES_ANALISADOS:
        info = multivariados["times"][time]
        contagens = ", ".join(
            f"{NOMES_METODOS[m].split(' (')[0]} {info['metodos'][m]['quantidade']}" for m in ("ecod", "knn", "dbscan", "lof")
        )
        paragrafos_mv.append(
            f"{_curto(time)} ({info['n']} jogos, 7 variáveis em σ robusto): {contagens}; "
            f"{_plural(info['em_todos'], 'jogo marcado', 'jogos marcados')} pelos quatro métodos ao mesmo tempo."
        )
    paragrafos_mv.append(
        "Os métodos multivariados avaliam o jogo inteiro (as 7 variáveis juntas): um jogo pode ser atípico pela "
        "combinação de valores sem ter nenhuma coluna fora dos limites univariados. Os quatro cortes foram "
        "calibrados em normais de 7 dimensões para a mesma taxa de referência dos univariados."
    )
    secoes.append({"titulo": "Outliers multivariados", "paragrafos": paragrafos_mv})
    return secoes


def _textos_base(
    ausentes, duplicatas, zeros, dominio, demonstracao
) -> list[dict[str, Any]]:
    total_fonte = sum(l["fonte"] or 0 for l in ausentes)
    celulas = duplicatas["fonte"]["registros"] * len(ausentes)
    secoes = [{"titulo": "Ausentes", "paragrafos": [
        f"A fonte tem {_n(total_fonte, 0)} valores ausentes em {_n(celulas, 0)} células "
        f"({duplicatas['fonte']['registros']} registros × {len(ausentes)} colunas). O recorte bruto do grupo "
        f"({duplicatas['recorte']['registros']} registros) tem {sum(l['recorte'] or 0 for l in ausentes)} e a "
        f"base tratada tem {sum(l['tratado'] or 0 for l in ausentes)}: a conversão de tipos não gerou ausentes.",
        "Sem ausentes, o indicador de ausência R é constante e os testes de mecanismo não têm o que comparar "
        "(no Little não há segundo padrão; na logística de Fairclough não há variação em R). Por isso eles são "
        "aplicados abaixo a cópias com ausência simulada, para mostrar como seriam usados e decididos.",
    ]}]

    paragrafos_demo = []
    for cenario in demonstracao["cenarios"]:
        little, fair = cenario["little"], cenario["fairclough"]
        k = len(fair["coeficientes"])
        bonferroni = ALFA_TESTES / k
        texto = (
            f"{cenario['nome']} ({cenario['ausentes']} de {cenario['n']} valores de PTS removidos): Little d² = "
            f"{_n(little['estatistica'])}, gl = {little['gl']}, p = {_n(little['p_valor'], 4)} → "
            f"{'rejeita' if little['rejeita_mcar'] else 'não rejeita'} MCAR. Fairclough: razão de verossimilhança = "
            f"{_n(fair['estatistica'])}, gl = {fair['gl']}, p = {_n(fair['p_valor'], 4)} → "
            f"{'rejeita' if fair['rejeita_mcar'] else 'não rejeita'} MCAR"
        )
        if fair["rejeita_mcar"]:
            principal = max(fair["coeficientes"], key=lambda c: abs(c["beta"]))
            texto += (
                f"; a ausência é explicada sobretudo por {principal['variavel']} (razão de chances "
                f"{_n(principal['razao_chances'])} por desvio padrão, p = {_n(principal['p_valor'], 4)}), "
                "que deveria entrar no modelo de imputação."
            )
        else:
            soltos = [c["variavel"] for c in fair["coeficientes"] if c["p_valor"] < ALFA_TESTES]
            texto += "."
            if soltos:
                texto += (
                    f" Os p-valores de Wald abaixo de 0,05 em {_lista(soltos)} não contam como evidência: "
                    f"com o teste global não significativo e {k} coeficientes testados, o corte corrigido de "
                    f"Bonferroni seria {_n(bonferroni, 4)}."
                )
        paragrafos_demo.append(texto)
    paragrafos_demo.append(
        f"Sob MCAR verdadeiro, um teste com α = {_n(ALFA_TESTES)} ainda rejeita em cerca de 5% das amostras; "
        f"por isso a semente da simulação ({demonstracao['semente']}) é fixa e declarada, e uma única rejeição "
        "nunca é tratada como prova."
    )
    paragrafos_demo.append(
        "Ambos só detectam dependência das variáveis observadas: se a ausência dependesse do próprio PTS (MNAR), "
        "o padrão só apareceria via variáveis correlacionadas a ele — e nunca seria confirmado pelos dados."
    )
    secoes.append({"titulo": "Demonstração dos testes", "paragrafos": paragrafos_demo})

    fonte, recorte = duplicatas["fonte"], duplicatas["recorte"]
    secoes.append({"titulo": "Duplicatas", "paragrafos": [
        f"Na fonte bruta ({_n(fonte['registros'], 0)} registros, antes de qualquer limpeza): "
        f"{fonte['linha_inteira']} linhas inteiras repetidas e {fonte['chave_time_jogo']} repetições da chave "
        f"(TEAM_NAME, Game_ID). Os {_n(fonte['jogos_distintos'], 0)} Game_ID aparecem "
        + ("exatamente 2 vezes cada (um registro por time), como esperado."
           if fonte["jogos_fora_do_par"] == 0
           else f"fora do par esperado em {fonte['jogos_fora_do_par']} casos.")
        + f" No recorte bruto do grupo: {recorte['linha_inteira']} linhas e {recorte['chave_time_jogo']} chaves "
        f"repetidas; o tratamento removeu {duplicatas['removidos_no_tratamento']} registros.",
    ]})

    com_zero = [z for z in zeros if z["zeros"]]
    negativos = sum(z["negativos"] for z in zeros)
    secoes.append({"titulo": "Zeros e negativos", "paragrafos": [
        "Zeros encontrados no recorte: "
        + "; ".join(f"{z['coluna']} = {z['zeros']}" for z in com_zero)
        + ". Nenhum deles é código de ausência: são resultados (derrota), acumulados no início da temporada ou "
        f"contagens que podem ser zero. Valores negativos: {negativos}.",
    ]})

    regras_violadas = [r for r in dominio["regras"] if r["violacoes_fonte"] or r["violacoes_recorte"]]
    prorrogados = dominio["jogos_prorrogacao"]
    por_k = {}
    for jogo in prorrogados:
        por_k[jogo["prorrogacoes"]] = por_k.get(jogo["prorrogacoes"], 0) + 1
    fonte_min = {m["minutos"]: m["registros"] for m in dominio["minutos_fonte"]}
    secoes.append({"titulo": "Valores fora de domínio e o caso do MIN", "paragrafos": [
        f"Foram verificadas {len(dominio['regras'])} regras de domínio e coerência; "
        + ("nenhuma teve violação na fonte nem no recorte."
           if not regras_violadas
           else "violações em: " + ", ".join(
               f"{r['regra']} ({r['violacoes_fonte']} na fonte, {r['violacoes_recorte']} no recorte)"
               for r in regras_violadas) + "."),
        "MIN não é o tempo de jogo, e sim a soma dos minutos dos jogadores: 48 min × 5 = 240 no tempo normal. "
        "Valores 265 e 290 parecem fora do domínio de quem espera 240, mas cada prorrogação tem 5 minutos × 5 "
        "jogadores = +25: 265 = 1 prorrogação e 290 = 2. São jogos reais, não erros, e foram mantidos.",
        f"No recorte: {len(prorrogados)} registros com prorrogação"
        + (" (" + ", ".join(f"{q} com {k} prorrogaç{'ão' if k == 1 else 'ões'}" for k, q in sorted(por_k.items())) + ")"
           if por_k else "")
        + f". Na liga inteira: {fonte_min.get(265, 0)} registros com 265 e {fonte_min.get(290, 0)} com 290 "
        "(cada jogo gera um registro por time).",
        "Efeito na pontuação: "
        + "; ".join(
            f"{_curto(t)} marcou em média {_n(e['media_prorrogacao'])} pontos nos "
            f"{e['jogos_prorrogacao']} jogos prorrogados contra {_n(e['media_regular'])} no tempo normal"
            + (
                ", sem outliers de PTS pela regra de Tukey" if not e["outliers_pts"]
                else f", e {e['outliers_pts_em_prorrogacao']} de seus {e['outliers_pts']} outliers de PTS (Tukey) "
                f"{'é jogo prorrogado' if e['outliers_pts_em_prorrogacao'] == 1 else 'são jogos prorrogados'}"
            )
            for t, e in dominio["efeito_prorrogacao_pts"].items() if e["jogos_prorrogacao"]
        )
        + ". Minutos extras aumentam as contagens, então a prorrogação deve ser lembrada ao ler extremos "
        "superiores, mas não justifica excluir esses jogos.",
    ]})
    return secoes


def calcular_qualidade(
    dados: pd.DataFrame, fonte: pd.DataFrame, recorte: pd.DataFrame
) -> dict[str, Any]:
    ausentes = contar_ausentes(fonte, recorte, dados)
    duplicatas = contar_duplicatas(fonte, recorte, dados)
    zeros = contar_zeros_e_negativos(recorte)
    dominio = verificar_dominio(fonte, recorte)
    por_coluna = outliers_por_coluna(dados)
    por_variavel = outliers_por_variavel(dados)
    multivariados = outliers_multivariados(dados)
    demonstracao = demonstrar_testes_ausencia(dados)
    total_ausentes = sum(l["tratado"] or 0 for l in ausentes)
    status = (
        "Não aplicável à base real: 0 valores ausentes, o indicador de ausência é constante."
        if total_ausentes == 0
        else f"Aplicável: {total_ausentes} valores ausentes na base tratada."
    )
    return {
        "times": TIMES_ANALISADOS,
        "ausentes": ausentes,
        "duplicatas": duplicatas,
        "zeros_negativos": zeros,
        "dominio": dominio,
        "mecanismos": MECANISMOS,
        "testes_ausencia": [
            {**t, "status_base_real": status,
             # O motivo "0 ausentes" só vale se for verdade nos dados.
             "paragrafos": t["paragrafos"] if total_ausentes == 0 else [t["paragrafos"][0], status]}
            for t in TESTES_AUSENCIA
        ],
        "demonstracao": demonstracao,
        "metodos": _metodos_outlier(
            obter_calibracao(max(d["n"] for d in por_variavel["detalhes"]), 1),
            next(iter(multivariados["times"].values()))["parametros"],
        ),
        "parametros": {
            "alfa_grubbs": ALFA_GRUBBS,
            "limiar_zscore": LIMIAR_ZSCORE,
            "taxa_referencia": TAXA_REFERENCIA,
        },
        "outliers_por_coluna": por_coluna,
        "outliers_por_variavel": por_variavel,
        "outliers_multivariados": multivariados,
        "secoes": _textos_base(ausentes, duplicatas, zeros, dominio, demonstracao)
        + _textos_outliers(por_coluna, por_variavel, multivariados),
    }
