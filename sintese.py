"""Síntese do relatório e resposta sobre o z-score no gráfico de barras.

Domínio puro (não conhece Flask). Junta a tabela descritiva, o perfil em
z-score e o diagnóstico de qualidade numa leitura final, sempre citando os
números calculados.
"""

from typing import Any

import pandas as pd

from analise import (
    LIMITE_SIMETRIA,
    MEDIA_MINIMA_CV,
    TIMES_ANALISADOS,
    calcular_perfil_z,
    calcular_tabela_descritiva,
)
from interpretacao import _classe_cv, _curto, _n, _plural

# Para PF (faltas) o valor menor é o desejável; nas demais, o maior.
MENOR_E_MELHOR = {"PF"}
# Convenção de Cohen (1988) para diferenças padronizadas.
FAIXAS_EFEITO = ((0.2, "desprezível"), (0.5, "pequeno"), (0.8, "médio"))
PLURAL_INTENSIDADE = {
    "aproximadamente simétrica": "aproximadamente simétricas",
    "moderada": "moderadas",
    "forte": "fortes",
}


def _efeito(delta: float) -> str:
    for limite, rotulo in FAIXAS_EFEITO:
        if abs(delta) < limite:
            return rotulo
    return "grande"


def _lista(itens: list[str]) -> str:
    if not itens:
        return ""
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


# ---------------------------------------------------------------------------
# Z-score no gráfico de barras
# ---------------------------------------------------------------------------

def textos_zscore(perfil: dict[str, Any]) -> list[str]:
    a, b = perfil["times"]
    variaveis = perfil["variaveis"]
    pontos = next(v for v in variaveis if v["variavel"] == "Pontos")
    menor_escala = min(variaveis, key=lambda v: v["media_referencia"])
    ordenadas = sorted(variaveis, key=lambda v: -abs(v["diferenca_z"]))
    maior, menor = ordenadas[0], ordenadas[-1]
    faixa = max(abs(t["z"]) for v in variaveis for t in v["times"].values())

    def lado(v):
        acima = a if v["times"][a]["z"] > v["times"][b]["z"] else b
        return f"{v['variavel']} ({_curto(acima)} acima, Δz = {_n(abs(v['diferenca_z']))})"

    return [
        "Nas barras em unidades originais, cada variável tem a sua escala: Pontos ficam em torno de "
        f"{_n(pontos['media_referencia'])} por jogo e {menor_escala['variavel']} em torno de "
        f"{_n(menor_escala['media_referencia'])}. Num mesmo gráfico, a diferença entre os times em "
        f"{menor_escala['variavel']} desaparece ao lado da escala de Pontos, e a comparação entre variáveis não faz sentido.",
        "O z-score entra justamente aí: em vez da média bruta, cada barra mostra z = (média do time − média dos "
        "jogos dos dois times) ÷ desvio padrão desses jogos. Todas as variáveis passam a ser medidas em desvios "
        "padrão, num eixo comum e sem unidade, e as barras ficam comparáveis entre si.",
        f"Lendo o gráfico: a variável que mais separa os times é {lado(maior)}, seguida de "
        f"{_lista([lado(v) for v in ordenadas[1:3]])}; a que menos separa é {lado(menor)}. "
        f"Nenhuma média de time se afasta mais que {_n(faixa)} desvio padrão da referência: a diferença entre os "
        "times é pequena perto da variação de jogo para jogo.",
        "Como a referência é formada pelos próprios dois times, a média dos z ponderada pelo número de jogos é "
        "zero: as barras dos dois times aparecem quase espelhadas em torno do zero. O que importa é a distância "
        "entre elas (Δz), que equivale a uma diferença padronizada de médias.",
        "O z-score também pode entrar no gráfico por jogo, e não por média: z de cada partida, com |z| > 3 "
        "marcando valores extremos — é o critério Z-score usado na página Qualidade dos dados.",
    ]


def calcular_resposta_zscore(dados: pd.DataFrame) -> dict[str, Any]:
    perfil = calcular_perfil_z(dados)
    return {**perfil, "paragrafos": textos_zscore(perfil)}


# ---------------------------------------------------------------------------
# Síntese
# ---------------------------------------------------------------------------

def _quadro(tabela, perfil) -> list[dict[str, Any]]:
    z_por_variavel = {v["variavel"]: v for v in perfil["variaveis"]}
    linhas = []
    for grupo in tabela:
        for time in TIMES_ANALISADOS:
            item = grupo["times"][time]
            linhas.append({
                "variavel": grupo["variavel"],
                "unidade": grupo["unidade"],
                "time": time,
                "media": item["media"],
                "mediana": item["mediana"],
                "desvio_padrao": item["desvio_padrao"],
                "cv_percentual": item["cv_percentual"],
                "classe_cv": _classe_cv(item["cv_percentual"]),
                "assimetria": item["assimetria"],
                "intensidade_assimetria": item["intensidade_assimetria"],
                "iqr": item["iqr"],
                "quantidade_outliers": item["quantidade_outliers"],
                "z": z_por_variavel[grupo["variavel"]]["times"][time]["z"],
            })
    return linhas


def _secao_vantagens(tabela, perfil) -> dict[str, Any]:
    a, b = TIMES_ANALISADOS
    z_por_variavel = {v["variavel"]: v for v in perfil["variaveis"]}
    frases, placar = [], {a: [], b: []}
    for grupo in tabela:
        variavel = grupo["variavel"]
        ma, mb = grupo["times"][a]["media"], grupo["times"][b]["media"]
        maior = a if ma > mb else b
        delta = z_por_variavel[variavel]["diferenca_z"]
        coluna_pf = variavel in MENOR_E_MELHOR
        vantagem = (b if maior == a else a) if coluna_pf else maior
        efeito = _efeito(delta)
        if efeito != "desprezível":
            placar[vantagem].append(variavel)
        menor_time = b if maior == a else a
        frases.append(
            f"{variavel}: {_curto(maior)} {_n(max(ma, mb))} {grupo['unidade']} contra {_n(min(ma, mb))} dos "
            f"{_curto(menor_time)} (diferença de {_n(abs(ma - mb))}, Δz = {_n(abs(delta))}, efeito {efeito}"
            + (f"; como menos faltas é melhor, a vantagem é de {_curto(vantagem)}" if coluna_pf else "") + ")"
        )
    relevantes = [
        v["variavel"] for v in perfil["variaveis"] if _efeito(v["diferenca_z"]) != "desprezível"
    ]
    return {
        "titulo": "Comparação entre os times",
        "paragrafos": [
            "; ".join(frases) + ".",
            f"Pela convenção de Cohen (|Δz| < 0,2 desprezível; < 0,5 pequena; < 0,8 média; ≥ 0,8 grande), "
            f"as diferenças não desprezíveis estão em {_lista(relevantes) or 'nenhuma variável'}. "
            "Contando só essas, "
            + " e ".join(
                f"{_curto(t)} leva vantagem em {_plural(len(v), 'variável', 'variáveis')} ({_lista(v)})"
                for t, v in placar.items() if v
            )
            + "; nenhuma diferença chega a ser grande, e os dois times têm perfis próximos.",
        ],
        "placar": {t: len(v) for t, v in placar.items()},
    }


def _secao_forma(tabela) -> dict[str, Any]:
    celulas = [(g["variavel"], t, g["times"][t]) for g in tabela for t in TIMES_ANALISADOS]
    contagem = {}
    for _, _, item in celulas:
        contagem[item["intensidade_assimetria"]] = contagem.get(item["intensidade_assimetria"], 0) + 1
    assimetricas = [(v, t, i) for v, t, i in celulas if abs(i["assimetria"]) >= LIMITE_SIMETRIA]
    explicadas = [
        f"{v} ({_curto(t)})" for v, t, i in assimetricas
        if i["assimetria_sem_outliers"] is not None and abs(i["assimetria_sem_outliers"]) < LIMITE_SIMETRIA
    ]
    positivas = sum(1 for _, _, i in celulas if i["assimetria"] > 0)
    paragrafos = [
        f"Das {len(celulas)} distribuições (7 variáveis × 2 times): "
        + ", ".join(
            f"{q} {rotulo if q == 1 else PLURAL_INTENSIDADE.get(rotulo, rotulo)}" for rotulo, q in contagem.items()
        )
        + f". {positivas} têm G1 positivo, o padrão esperado em contagens limitadas por zero e sem teto rígido.",
    ]
    if assimetricas:
        paragrafos.append(
            "As assimetrias moderadas ou fortes estão em "
            + _lista([f"{v} ({_curto(t)}, G1 = {_n(i['assimetria'])})" for v, t, i in assimetricas])
            + "."
            + (f" Em {_lista(explicadas)} a assimetria some quando os outliers saem: ela vem de poucos jogos extremos."
               if explicadas else "")
        )
    paragrafos.append(
        "Consequência prática: onde a distribuição é simétrica, média e mediana descrevem o jogo típico; onde há "
        "assimetria, a mediana e o IQR são os resumos mais fiéis."
    )
    return {"titulo": "Forma das distribuições", "paragrafos": paragrafos}


def _secao_regularidade(tabela) -> dict[str, Any]:
    a, b = TIMES_ANALISADOS
    medias_cv = sorted(
        ((g["variavel"], sum(g["times"][t]["cv_percentual"] for t in TIMES_ANALISADOS) / 2,
          min(g["times"][t]["media"] for t in TIMES_ANALISADOS)) for g in tabela),
        key=lambda item: item[1],
    )
    mais_regular, mais_irregular = medias_cv[0], medias_cv[-1]
    regular_a = sum(1 for g in tabela if g["times"][a]["cv_percentual"] < g["times"][b]["cv_percentual"])
    cautela = [v for v, _, media in medias_cv if media < MEDIA_MINIMA_CV]
    return {"titulo": "Regularidade (CV)", "paragrafos": [
        f"A variável mais regular é {mais_regular[0]} (CV médio {_n(mais_regular[1])}%) e a mais irregular é "
        f"{mais_irregular[0]} ({_n(mais_irregular[1])}%). {_curto(a)} tem CV menor em {regular_a} das "
        f"{len(tabela)} variáveis e {_curto(b)} em {len(tabela) - regular_a}.",
        (f"{_lista(cautela)} têm média abaixo de {_n(MEDIA_MINIMA_CV, 0)} por jogo: o CV alto delas é, em boa parte, "
         "efeito de contagens pequenas, e não necessariamente de um time instável." if cautela else
         "Todas as médias estão longe de zero, então os CVs são comparáveis entre si."),
    ]}


def _secao_outliers(tabela, qualidade) -> dict[str, Any]:
    totais = {t: sum(g["times"][t]["quantidade_outliers"] for g in tabela) for t in TIMES_ANALISADOS}
    destaques = []
    for g in tabela:
        for t in TIMES_ANALISADOS:
            for o in g["times"][t]["outliers_detalhe"]:
                destaques.append((g["variavel"], t, o))
    extremos_3iqr = sum(g["times"][t]["quantidade_outliers_3iqr"] for g in tabela for t in TIMES_ANALISADOS)
    grubbs = sum(
        c["times"][t]["grubbs"]["quantidade"]
        for c in qualidade["outliers_por_coluna"] if c["analisada"] for t in TIMES_ANALISADOS
    )
    prorrogados = len(qualidade["dominio"]["jogos_prorrogacao"])
    lista = _lista([
        f"{v} {_n(o['valor'], 0)} ({_curto(t)}, {o['data']})" for v, t, o in destaques
    ])
    return {"titulo": "Valores atípicos", "paragrafos": [
        "Pela regra de Tukey (1,5×IQR), nas 7 variáveis: "
        + "; ".join(f"{_curto(t)}, {_plural(q, 'outlier', 'outliers')}" for t, q in totais.items())
        + f". São eles: {lista}." if destaques else "Nenhum outlier pela regra de Tukey nas 7 variáveis.",
        f"Com k = 3 restam {extremos_3iqr} e o teste de Grubbs (α = 0,05) confirma {grubbs}: são valores pouco "
        "comuns, mas plausíveis em basquete, e foram mantidos. Excluí-los mudaria médias e DPs sem que haja erro "
        f"de registro. Os {prorrogados} jogos com prorrogação também foram mantidos: os minutos extras são reais.",
    ]}


def _secao_qualidade(qualidade, dicionario) -> dict[str, Any]:
    dup = qualidade["duplicatas"]["fonte"]
    ausentes = sum(l["fonte"] or 0 for l in qualidade["ausentes"])
    violacoes = sum(r["violacoes_fonte"] for r in qualidade["dominio"]["regras"])
    vaz = dicionario["vazamento"]
    return {"titulo": "Qualidade e preparo da base", "paragrafos": [
        f"A fonte tem {_n(dup['registros'], 0)} registros e {len(qualidade['ausentes'])} colunas, com {ausentes} "
        f"ausentes, {dup['linha_inteira'] + dup['chave_time_jogo']} duplicatas e {violacoes} violações nas "
        f"{len(qualidade['dominio']['regras'])} regras de domínio. O recorte do grupo tem "
        f"{dicionario['linhas']} jogos; as conclusões não dependem de imputação nem de limpeza agressiva.",
        f"Para uso em modelos, {len(dicionario['exclusoes'])} colunas são excluídas "
        f"({_lista([e['coluna'] for e in dicionario['exclusoes']])}), e WL é o alvo. W, L e W_PCT vazam o "
        f"resultado: a variação de W é igual a WL em {vaz['variacao_w_igual_wl']} de "
        f"{vaz['jogos_com_anterior']} jogos com jogo anterior.",
    ]}


def _secao_limitacoes() -> dict[str, Any]:
    return {"titulo": "Limitações", "paragrafos": [
        "Uma única temporada regular, com cerca de 75 jogos por time: medidas de cauda (assimetria, outliers) "
        "variam bastante com poucos jogos extremos.",
        "A análise é univariada e descritiva: não controla adversário, mando de quadra, prorrogação ou "
        "desfalques, e as diferenças entre times não foram submetidas a teste de hipótese.",
        "Os testes de mecanismo de ausência foram demonstrados em dados simulados, porque a base real não tem "
        "ausentes; o ECOD e o K-NN marcam ≈ 5% dos jogos por construção.",
    ]}


def _secao_conclusao(tabela, perfil, vantagens) -> dict[str, Any]:
    a, b = TIMES_ANALISADOS
    ordenadas = sorted(perfil["variaveis"], key=lambda v: -abs(v["diferenca_z"]))
    principais = [
        f"{v['variavel']} ({_curto(a if v['diferenca_z'] > 0 else b)} acima)" for v in ordenadas[:3]
    ]
    pontos = next(v for v in perfil["variaveis"] if v["variavel"] == "Pontos")
    faixa = max(abs(t["z"]) for v in perfil["variaveis"] for t in v["times"].values())
    return {"titulo": "Conclusão", "paragrafos": [
        f"Mavericks e Pacers pontuam de forma muito parecida (Δz = {_n(abs(pontos['diferenca_z']))} em Pontos). "
        f"O que distingue os estilos está em {_lista(principais)}.",
        f"Nenhuma média de time fica a mais de {_n(faixa)} desvio padrão da média conjunta: a variação de jogo "
        "para jogo dentro de cada time é bem maior que a diferença entre os times. Por isso, comparações devem "
        "olhar a distribuição inteira (boxplot, IQR), e não só a média.",
    ]}


def calcular_sintese(
    dados: pd.DataFrame, qualidade: dict[str, Any], dicionario: dict[str, Any]
) -> dict[str, Any]:
    tabela = calcular_tabela_descritiva(dados)["variaveis"]
    perfil = calcular_perfil_z(dados)
    vantagens = _secao_vantagens(tabela, perfil)
    secoes = [
        vantagens,
        _secao_forma(tabela),
        _secao_regularidade(tabela),
        _secao_outliers(tabela, qualidade),
        {"titulo": "Onde o z-score entra no gráfico de barras", "paragrafos": textos_zscore(perfil)},
        _secao_qualidade(qualidade, dicionario),
        _secao_limitacoes(),
        _secao_conclusao(tabela, perfil, vantagens),
    ]
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, perfil),
        "secoes": [{"titulo": s["titulo"], "paragrafos": s["paragrafos"]} for s in secoes],
    }
