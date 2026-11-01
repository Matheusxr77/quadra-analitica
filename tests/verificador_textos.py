"""Confere os números citados nos textos de interpretação contra os dados da API.

Usado pelos testes: (i) todo parágrafo de interpretação cita pelo menos um
número calculado; (ii) todo número citado, fora as constantes declaradas,
coincide com um valor da API (em 0 a 4 casas, em módulo ou em percentual) ou
com um derivado obtido por fórmula explícita abaixo.
"""

import re
from collections.abc import Iterable
from typing import Any

# Constantes declaradas no método (limiares, convenções e definições). Não
# contam como "número calculado" e não precisam vir da API.
CONSTANTES = {
    "0", "1", "2", "3", "5", "7", "15", "25", "30", "48", "95", "100", "240", "265", "290",
    "0,05", "0,1", "0,2", "0,20", "0,5", "0,8", "1,0", "1,5", "1,10", "1,349", "1,35", "2,698", "2,7",
}


def numeros(texto: str) -> list[str]:
    """Números de um texto em pt-BR (vírgula decimal, ponto de milhar)."""
    t = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", " ", texto)          # datas
    t = re.sub(r"\b[A-Za-zÀ-ÿ_]+\d+[A-Za-z_]*\b", " ", t)     # FG3M, Q1, G1, H0
    t = re.sub(r"[₀-₉ⱼᵢₖ²]", " ", t)
    t = re.sub(r"\d+\s*[×x]\s*(?=IQR)", " ", t)                # 1,5×IQR
    achados = re.findall(r"(?<![\w,.])[−-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?|(?<![\w,.])[−-]?\d+(?:,\d+)?", t)
    return [a.replace("−", "-") for a in achados]


def formatos(valor: float) -> set[str]:
    saida = set()
    for v in (valor, abs(valor), valor * 100, abs(valor) * 100):
        for casas in (0, 1, 2, 3, 4):
            texto = f"{v:,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")
            saida.add(texto)
            saida.add(texto.replace(".", ""))
    return saida


def valores(*objetos: Any) -> set[str]:
    """Todos os números das respostas da API, mais o tamanho de cada lista exibida."""
    saida: set[str] = set()

    def visitar(objeto):
        if isinstance(objeto, bool):
            return
        if isinstance(objeto, (int, float)):
            saida.update(formatos(float(objeto)))
        elif isinstance(objeto, dict):
            for v in objeto.values():
                visitar(v)
        elif isinstance(objeto, list):
            saida.update(formatos(float(len(objeto))))
            for v in objeto:
                visitar(v)

    for objeto in objetos:
        visitar(objeto)
    return saida


def _ep_g1(n: int) -> float:
    return (6 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3))) ** 0.5


def derivados(descritivas: dict[str, Any]) -> set[str]:
    """Valores que os textos calculam a partir da tabela descritiva (fórmulas explícitas)."""
    extra: set[str] = set()
    for g in descritivas["variaveis"]:
        itens = list(g["times"].values())
        a, b = itens
        for chave in ("media", "mediana", "desvio_padrao", "cv_percentual", "iqr", "assimetria", "amplitude",
                      "cv_robusto_iqr"):
            if a.get(chave) is not None and b.get(chave) is not None:
                extra |= formatos(a[chave] - b[chave])                 # diferença entre os times
                extra |= formatos((a[chave] + b[chave]) / 2)           # média dos dois times
                extra |= formatos((abs(a[chave]) + abs(b[chave])) / 2)
        extra |= formatos(max(a["q1"], b["q1"]))
        extra |= formatos(min(a["q3"], b["q3"]))
        for item in itens:
            n = item["n"]
            ep = _ep_g1(n)
            extra |= formatos(ep) | formatos(2 * ep) | formatos(item["assimetria"] / ep)
            extra |= formatos((n * (n - 1)) ** 0.5 / (n - 2))           # fator de correção do G1
            extra |= formatos(item["media"] - item["mediana"])
            extra |= formatos(item["media"] - item["desvio_padrao"])
            extra |= formatos(item["media"] + item["desvio_padrao"])
            if item["desvio_padrao"]:
                extra |= formatos((item["media"] - item["mediana"]) / item["desvio_padrao"])
            if item["cv_poisson_ref"] is not None:
                extra |= formatos(item["cv_percentual"] - item["cv_poisson_ref"])
            if item["cv_percentual"]:
                extra |= formatos(item["cv_robusto_iqr"] / item["cv_percentual"])
            extra |= formatos((item["desvio_sem_outliers"] - item["desvio_padrao"]) / item["desvio_padrao"] * 100)
            if item["iqr"]:
                extra |= formatos((item["iqr_sem_outliers"] - item["iqr"]) / item["iqr"] * 100)
    return extra


def conferir(texto: str, pool: set[str]) -> tuple[list[str], list[str]]:
    """(números calculados conferidos, números que não batem com a API)."""
    calculados, nao_conferem = [], []
    for numero in numeros(texto):
        if numero.lstrip("-") in CONSTANTES or numero in CONSTANTES:
            continue
        (calculados if numero.lstrip("-") in pool else nao_conferem).append(numero)
    return calculados, nao_conferem


def paragrafos_de(secoes: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(s["titulo"], p) for s in secoes for p in s["paragrafos"]]
