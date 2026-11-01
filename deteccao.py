"""Detectores de outliers com numpy, scipy e scikit-learn.

Grubbs iterativo, ECOD (Li et al., 2022) e K-NN, DBSCAN e LOF com limiares calibrados
para marcar, em dados normais, a mesma proporção da regra de Tukey (≈ 0,70%).
"""

import json
from functools import lru_cache
from math import sqrt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors

ALFA_GRUBBS = 0.05
LIMIAR_ZSCORE = 3.0
CONSTANTE_SIGMA_ROBUSTO = 1.349  # IQR de uma normal padrão
# Cerca de Tukey numa normal: Q3 + 1,5·IQR = 0,6745 + 1,5·1,349 ≈ 2,698 σ.
CERCA_TUKEY_NORMAL = stats.norm.ppf(0.75) * (1 + 2 * 1.5)
TAXA_REFERENCIA = float(2 * stats.norm.sf(CERCA_TUKEY_NORMAL))  # ≈ 0,0070
LOF_VIZINHOS = 20          # Breunig et al. (2000): MinPts entre 10 e 20+
LOF_REGRA_PRATICA = 1.5    # corte usual na literatura (e no scikit-learn)
REPETICOES_CALIBRACAO = 200
SEMENTE_CALIBRACAO = 2024


# ---------------------------------------------------------------------------
# Grubbs
# ---------------------------------------------------------------------------

def valor_critico_grubbs(n: int, alfa: float = ALFA_GRUBBS) -> float:
    """G crítico bilateral: ((n−1)/√n)·√(t²/(n−2+t²)), t = t_{α/(2n), n−2}."""
    t = stats.t.ppf(1 - alfa / (2 * n), n - 2)
    return (n - 1) / sqrt(n) * sqrt(t**2 / (n - 2 + t**2))


def grubbs_iterativo(serie: pd.Series, alfa: float = ALFA_GRUBBS) -> dict[str, Any]:
    """Grubbs bilateral iterativo: remove o valor mais distante da média enquanto G > G crítico."""
    restante = serie.dropna().astype(float)
    passos, indices = [], []
    while len(restante) >= 3:
        n = len(restante)
        desvio = restante.std(ddof=1)
        if not desvio > 0:
            break
        distancias = (restante - restante.mean()).abs()
        indice = distancias.idxmax()
        g = float(distancias.loc[indice] / desvio)
        g_critico = valor_critico_grubbs(n, alfa)
        significativo = g > g_critico
        passos.append({
            "n": n, "media": float(restante.mean()), "desvio": float(desvio),
            "valor": float(restante.loc[indice]), "g": g, "g_critico": g_critico,
            "significativo": bool(significativo),
        })
        if not significativo:
            break
        indices.append(indice)
        restante = restante.drop(indice)
    return {"indices": indices, "valores": [float(serie.loc[i]) for i in indices], "passos": passos}


# ---------------------------------------------------------------------------
# ECOD — Li, Zhao, Hu, Botta, Ionescu e Chen (2022), IEEE TKDE
# ---------------------------------------------------------------------------

def ecod_componentes(matriz: np.ndarray) -> dict[str, np.ndarray]:
    """Caudas empíricas −log por dimensão e score final do ECOD.

    Para cada dimensão j:
      F̂_esq(x) = #{Xᵢⱼ ≤ x}/n   e   F̂_dir(x) = #{Xᵢⱼ ≥ x}/n
      U_esq = −log F̂_esq,  U_dir = −log F̂_dir
      U_assim = U_esq se a assimetria γⱼ < 0, senão U_dir
    Score (Algoritmo 1 do artigo): O = max(Σⱼ U_esq, Σⱼ U_dir, Σⱼ U_assim).
    """
    x = np.asarray(matriz, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n, d = x.shape
    u_esq = np.empty_like(x)
    u_dir = np.empty_like(x)
    for j in range(d):
        ordenado = np.sort(x[:, j])
        u_esq[:, j] = -np.log(np.searchsorted(ordenado, x[:, j], side="right") / n)
        u_dir[:, j] = -np.log((n - np.searchsorted(ordenado, x[:, j], side="left")) / n)
    assimetria = stats.skew(x, axis=0)
    u_assim = np.where(assimetria < 0, u_esq, u_dir)
    scores = np.maximum.reduce([u_esq.sum(axis=1), u_dir.sum(axis=1), u_assim.sum(axis=1)])
    return {"u_esq": u_esq, "u_dir": u_dir, "u_assim": u_assim, "assimetria": assimetria, "scores": scores}


def ecod_por_proporcao(matriz: np.ndarray, proporcao: float = TAXA_REFERENCIA) -> dict[str, Any]:
    """Marca a proporção dada dos maiores scores (score > percentil 100·(1 − proporção)), como o pyod."""
    scores = ecod_componentes(matriz)["scores"]
    limiar = float(np.percentile(scores, 100 * (1 - proporcao)))
    return {"scores": scores, "limiar": limiar, "rotulos": scores > limiar}


# ---------------------------------------------------------------------------
# K-NN, DBSCAN e LOF com calibração sob normalidade
# ---------------------------------------------------------------------------

def padronizar_robusto(matriz: np.ndarray) -> np.ndarray:
    """(x − mediana) / (IQR/1,349)."""
    x = np.asarray(matriz, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    q1, mediana, q3 = np.percentile(x, [25, 50, 75], axis=0)
    sigma = (q3 - q1) / CONSTANTE_SIGMA_ROBUSTO
    sigma = np.where(sigma > 0, sigma, x.std(axis=0, ddof=1))
    sigma = np.where(sigma > 0, sigma, 1.0)
    return (x - mediana) / sigma


def vizinhos_knn(n: int) -> int:
    """k = round(√n)."""
    return max(2, int(round(sqrt(n))))


def minimo_dbscan(dimensao: int) -> int:
    """min_samples: 4 em 1 ou 2 dimensões (Ester et al., 1996); 2·dim acima (Sander et al., 1998)."""
    return max(4, 2 * dimensao)


def score_knn(z: np.ndarray, k: int) -> np.ndarray:
    distancias, _ = NearestNeighbors(n_neighbors=k + 1).fit(z).kneighbors(z)
    return distancias[:, -1]  # coluna 0 = o próprio ponto


def score_lof(z: np.ndarray) -> np.ndarray:
    modelo = LocalOutlierFactor(n_neighbors=min(LOF_VIZINHOS, len(z) - 1)).fit(z)
    return -modelo.negative_outlier_factor_


def ruido_dbscan(z: np.ndarray, eps: float, minimo: int) -> np.ndarray:
    return DBSCAN(eps=eps, min_samples=minimo).fit_predict(z) == -1


@lru_cache(maxsize=16)
def calibrar(n: int, dimensao: int = 1) -> dict[str, Any]:
    """Limiares que marcam ≈ TAXA_REFERENCIA em N(0, I) com o mesmo n e dimensão.

    Monte Carlo com semente fixa. K-NN, LOF e ECOD: quantil (1 − taxa) do score.
    DBSCAN: menor ε com taxa de ruído ≤ taxa (busca binária).
    """
    gerador = np.random.default_rng(SEMENTE_CALIBRACAO + 1000 * dimensao + n)
    amostras = gerador.standard_normal((REPETICOES_CALIBRACAO, n, dimensao))
    k = vizinhos_knn(n)
    minimo = minimo_dbscan(dimensao)
    knn = np.concatenate([score_knn(a, k) for a in amostras])
    lof = np.concatenate([score_lof(a) for a in amostras])
    ecod = np.concatenate([ecod_componentes(a)["scores"] for a in amostras])

    baixo, alto = 0.01, 4.0 * sqrt(dimensao) + 2.0
    for _ in range(14):
        meio = (baixo + alto) / 2
        taxa = np.mean([ruido_dbscan(a, meio, minimo).mean() for a in amostras])
        baixo, alto = (baixo, meio) if taxa <= TAXA_REFERENCIA else (meio, alto)
    quantil = 1 - TAXA_REFERENCIA
    return {
        "n": n,
        "dimensao": dimensao,
        "taxa_referencia": TAXA_REFERENCIA,
        "repeticoes": REPETICOES_CALIBRACAO,
        "knn_k": k,
        "knn_corte": float(np.quantile(knn, quantil)),
        "dbscan_min_samples": minimo,
        "dbscan_eps": float(alto),
        "lof_vizinhos": min(LOF_VIZINHOS, n - 1),
        "lof_corte": float(np.quantile(lof, quantil)),
        "lof_taxa_regra_pratica": float(np.mean(lof > LOF_REGRA_PRATICA)),
        "ecod_corte": float(np.quantile(ecod, quantil)),
    }


ARQUIVO_CALIBRACAO = Path(__file__).parent / "dados" / "calibracao_outliers.json"


@lru_cache(maxsize=1)
def _tabela_calibracao() -> dict[str, dict[str, Any]]:
    try:
        conteudo = json.loads(ARQUIVO_CALIBRACAO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    valida = (
        conteudo.get("semente") == SEMENTE_CALIBRACAO
        and conteudo.get("repeticoes") == REPETICOES_CALIBRACAO
        and abs(conteudo.get("taxa_referencia", 0) - TAXA_REFERENCIA) < 1e-12
    )
    return conteudo.get("entradas", {}) if valida else {}


def obter_calibracao(n: int, dimensao: int = 1) -> dict[str, Any]:
    """Lê a tabela pré-calculada (evita segundos de cálculo na 1ª requisição) ou calibra na hora."""
    registro = _tabela_calibracao().get(f"{n}x{dimensao}")
    return dict(registro) if registro else calibrar(n, dimensao)


def detectar(matriz: np.ndarray) -> dict[str, Any]:
    """K-NN, DBSCAN, LOF e ECOD numa matriz n × d."""
    x = np.asarray(matriz, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n, d = x.shape
    parametros = obter_calibracao(n, d)
    z = padronizar_robusto(x)
    knn = score_knn(z, parametros["knn_k"])
    lof = score_lof(z)
    if d == 1:
        ecod = ecod_por_proporcao(x)
        rotulos_ecod, limiar_ecod = ecod["rotulos"], ecod["limiar"]
        scores_ecod = ecod["scores"]
    else:
        scores_ecod = ecod_componentes(x)["scores"]
        limiar_ecod = parametros["ecod_corte"]
        rotulos_ecod = scores_ecod > limiar_ecod
    return {
        "parametros": {**parametros, "ecod_limiar_aplicado": limiar_ecod},
        "rotulos": {
            "ecod": rotulos_ecod,
            "knn": knn > parametros["knn_corte"],
            "dbscan": ruido_dbscan(z, parametros["dbscan_eps"], parametros["dbscan_min_samples"]),
            "lof": lof > parametros["lof_corte"],
        },
        "scores": {"ecod": scores_ecod, "knn": knn, "lof": lof},
    }


def gerar_tabela_calibracao(tamanhos: tuple[int, ...] = (74, 75), dimensoes: tuple[int, ...] = (1, 7)) -> Path:
    """Recalcula e grava dados/calibracao_outliers.json."""
    entradas = {f"{n}x{d}": calibrar(n, d) for n in tamanhos for d in dimensoes}
    ARQUIVO_CALIBRACAO.write_text(json.dumps({
        "descricao": "Limiares de K-NN, DBSCAN, LOF e ECOD calibrados sob normalidade (ver deteccao.py).",
        "semente": SEMENTE_CALIBRACAO,
        "repeticoes": REPETICOES_CALIBRACAO,
        "taxa_referencia": TAXA_REFERENCIA,
        "entradas": entradas,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _tabela_calibracao.cache_clear()
    return ARQUIVO_CALIBRACAO


if __name__ == "__main__":
    print(f"Tabela gravada em {gerar_tabela_calibracao()}")
