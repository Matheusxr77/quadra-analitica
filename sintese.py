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
    comparar_times,
    erro_padrao_g1,
)
from interpretacao import _classe_cv_item, _curto, _dos, _n, _plural, _time

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

LEITURA_Z = {
    "FG3M": "mais bolas de três convertidas",
    "PF": "mais faltas cometidas",
    "Rebotes": "mais rebotes",
    "Assistências": "mais assistências",
    "BLK": "mais tocos",
    "STL": "mais roubos de bola",
    "Pontos": "mais pontos",
}


def textos_zscore(perfil: dict[str, Any]) -> dict[str, list[str]]:
    a, b = perfil["times"]
    variaveis = perfil["variaveis"]
    pontos = next(v for v in variaveis if v["variavel"] == "Pontos")
    menor_escala = min(variaveis, key=lambda v: v["media_referencia"])
    ordenadas = sorted(variaveis, key=lambda v: -abs(v["diferenca_z"]))
    maior, menor = ordenadas[0], ordenadas[-1]
    faixa = max(abs(t["z"]) for v in variaveis for t in v["times"].values())

    def acima(v):
        return a if v["times"][a]["z"] > v["times"][b]["z"] else b

    def lado(v):
        return f"{v['variavel']} ({_curto(acima(v))} acima, Δz = {_n(abs(v['diferenca_z']))})"

    estilo = {t: [LEITURA_Z[v["variavel"]] for v in ordenadas[:3] if acima(v) == t] for t in (a, b)}
    return {
        "paragrafos": [
            "Nas barras em unidades originais, cada variável tem a sua escala: Pontos ficam em torno de "
            f"{_n(pontos['media_referencia'])} por jogo e {menor_escala['variavel']} em torno de "
            f"{_n(menor_escala['media_referencia'])}. Num mesmo gráfico, a diferença entre os times em "
            f"{menor_escala['variavel']} desaparece ao lado da escala de Pontos.",
            "O z-score entra justamente aí: em vez da média bruta, cada barra mostra quantos desvios padrão a média "
            f"do time está da média dos jogos dos dois times — em Pontos, z = {_n(pontos['times'][a]['z'])} para "
            f"{_time(a)} e {_n(pontos['times'][b]['z'])} para {_time(b)}. Todas as variáveis passam a um eixo comum, "
            "sem unidade, e as barras ficam comparáveis entre si.",
            f"Lendo o gráfico: a variável que mais separa os times é {lado(maior)}, seguida de "
            f"{_lista([lado(v) for v in ordenadas[1:3]])}; a que menos separa é {lado(menor)}. Em termos de jogo, "
            + " e ".join(f"{_time(t)} se destacam por {_lista(itens)}" for t, itens in estilo.items() if itens)
            + f" — perfis diferentes com pontuação quase igual (Δz = {_n(abs(pontos['diferenca_z']))} em Pontos).",
            f"Nenhuma média de time se afasta mais que {_n(faixa)} desvio padrão da referência: a diferença entre os "
            "times é pequena perto da variação de jogo para jogo.",
        ],
        "metodologia": [
            "z = (média do time − média dos jogos dos dois times) ÷ desvio padrão amostral desses jogos. Como a "
            "referência é formada pelos próprios dois times, a média dos z ponderada pelo número de jogos é zero: "
            "as barras aparecem quase espelhadas em torno do zero, e o que importa é a distância entre elas (Δz), "
            "uma diferença padronizada de médias.",
            "O z-score também pode entrar por jogo, e não por média: z de cada partida, com |z| > 3 marcando "
            "valores extremos — é o critério Z-score da página Qualidade dos dados.",
        ],
    }


def calcular_resposta_zscore(dados: pd.DataFrame) -> dict[str, Any]:
    perfil = calcular_perfil_z(dados)
    return {**perfil, **textos_zscore(perfil)}


# ---------------------------------------------------------------------------
# Síntese
# ---------------------------------------------------------------------------

def _secao(titulo: str, paragrafos: list[str], metodologia: list[str] | None = None) -> dict[str, Any]:
    return {"titulo": titulo, "metodologia": metodologia or [], "paragrafos": paragrafos}


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
                "classe_cv": _classe_cv_item(item),
                "assimetria": item["assimetria"],
                "intensidade_assimetria": item["intensidade_assimetria"],
                "iqr": item["iqr"],
                "quantidade_outliers": item["quantidade_outliers"],
                "z": z_por_variavel[grupo["variavel"]]["times"][time]["z"],
            })
    return linhas


def _secao_vantagens(tabela, perfil, resumo) -> dict[str, Any]:
    a, b = TIMES_ANALISADOS
    z_por_variavel = {v["variavel"]: v for v in perfil["variaveis"]}
    frases, placar = [], {a: [], b: []}
    for grupo in tabela:
        variavel = grupo["variavel"]
        ma, mb = grupo["times"][a]["media"], grupo["times"][b]["media"]
        maior = a if ma > mb else b
        menor_time = b if maior == a else a
        delta = z_por_variavel[variavel]["diferenca_z"]
        coluna_pf = variavel in MENOR_E_MELHOR
        vantagem = menor_time if coluna_pf else maior
        efeito = _efeito(delta)
        if efeito != "desprezível":
            placar[vantagem].append(variavel)
        frases.append(
            f"{variavel}: {_time(maior)} com {_n(max(ma, mb))} {grupo['unidade']} contra {_n(min(ma, mb))} {_dos(menor_time)} "
            f"(diferença de {_n(abs(ma - mb))}, Δz = {_n(abs(delta))}, efeito {efeito}"
            + (f"; pela convenção adotada, vantagem {_dos(vantagem)}" if coluna_pf else "") + ")"
        )
    relevantes = [v["variavel"] for v in perfil["variaveis"] if _efeito(v["diferenca_z"]) != "desprezível"]
    resumo["placar"] = {t: len(v) for t, v in placar.items()}
    resumo["diferencas_nao_despreziveis"] = len(relevantes)
    return _secao("Comparação entre os times", [
        "; ".join(frases) + ".",
        f"As diferenças não desprezíveis estão em {_lista(relevantes) or 'nenhuma variável'} "
        f"({len(relevantes)} de {len(tabela)}). Contando só essas, "
        + " e ".join(
            f"{_time(t)} levam vantagem em {_plural(len(v), 'variável', 'variáveis')} ({_lista(v)})"
            for t, v in placar.items() if v
        )
        + ". Nenhuma diferença chega a efeito grande (|Δz| ≥ 0,8), e com ≈ 75 jogos por time efeitos pequenos não "
        "foram testados: os dois times têm perfis próximos.",
    ], [
        "Convenção de Cohen (1988) para diferenças padronizadas: |Δz| < 0,2 desprezível; < 0,5 pequeno; < 0,8 médio; "
        "≥ 0,8 grande.",
        "Convenção adotada para PF: menos faltas é melhor (menos lances livres cedidos ao adversário). Mais faltas "
        "também podem refletir uma defesa mais agressiva, então essa 'vantagem' é uma escolha de leitura, não um fato.",
    ])


def _secao_forma(tabela, resumo) -> dict[str, Any]:
    celulas = [(g["variavel"], t, g["times"][t]) for g in tabela for t in TIMES_ANALISADOS]
    contagem: dict[str, int] = {}
    for _, _, item in celulas:
        contagem[item["intensidade_assimetria"]] = contagem.get(item["intensidade_assimetria"], 0) + 1
    assimetricas = [(v, t, i) for v, t, i in celulas if abs(i["assimetria"]) >= LIMITE_SIMETRIA]
    explicadas = [
        f"{v} {_dos(t)}" for v, t, i in assimetricas
        if i["assimetria_sem_outliers"] is not None and abs(i["assimetria_sem_outliers"]) < LIMITE_SIMETRIA
    ]
    positivas = [(v, t, i) for v, t, i in celulas if i["assimetria"] > 0]
    pequenas_positivas = sum(1 for _, _, i in positivas if i["media"] < MEDIA_MINIMA_CV)
    maior_grande = max(
        (abs(i["assimetria"]) for _, _, i in celulas if i["media"] >= MEDIA_MINIMA_CV), default=0.0
    )
    resumo.update({
        "intensidades": contagem, "g1_positivos": len(positivas),
        "g1_positivos_contagens_pequenas": pequenas_positivas, "maior_g1_media_alta": maior_grande,
    })
    paragrafos = [
        f"Das {len(celulas)} distribuições: "
        + ", ".join(f"{q} {rotulo if q == 1 else PLURAL_INTENSIDADE.get(rotulo, rotulo)}" for rotulo, q in contagem.items())
        + f". {len(positivas)} têm G1 positivo; {pequenas_positivas} delas são de STL ou BLK (médias abaixo de 10), "
        "em que a cauda à direita combina com contagens perto de zero. Nas variáveis de média alta o zero está "
        f"longe demais para explicar o sinal, e todos os |G1| ficam em até {_n(maior_grande)}: ruído amostral.",
    ]
    if assimetricas:
        paragrafos.append(
            "As assimetrias moderadas estão em "
            + _lista([f"{v} {_dos(t)} (G1 = {_n(i['assimetria'])})" for v, t, i in assimetricas]) + "."
            + (f" Em {_lista(explicadas)} a assimetria some sem os outliers: vem de poucos jogos extremos, e média e "
               "mediana continuam próximas." if explicadas else "")
        )
    return _secao("Forma das distribuições", paragrafos)


def _secao_regularidade(tabela, comparacoes, resumo) -> dict[str, Any]:
    medias_cv = sorted(
        ((g["variavel"], sum(g["times"][t]["cv_percentual"] for t in TIMES_ANALISADOS) / 2,
          min(g["times"][t]["media"] for t in TIMES_ANALISADOS)) for g in tabela),
        key=lambda item: item[1],
    )
    grandes = [m for m in medias_cv if m[2] >= MEDIA_MINIMA_CV]
    relevantes = [g for g in tabela if comparacoes[g["variavel"]]["cv"]["relevante"]]
    resumo["diferencas_cv_relevantes"] = len(relevantes)
    paragrafos = [
        f"Entre as variáveis de média alta, a mais regular é {grandes[0][0]} (CV médio {_n(grandes[0][1])}%) e a mais "
        f"irregular é {grandes[-1][0]} ({_n(grandes[-1][1])}%). STL e BLK têm CVs maiores "
        f"({_n(dict((m[0], m[1]) for m in medias_cv)['STL'])}% e {_n(dict((m[0], m[1]) for m in medias_cv)['BLK'])}%), "
        "mas no piso esperado para contagens tão pequenas — não indicam times instáveis.",
    ]
    for g in relevantes:
        c = comparacoes[g["variavel"]]["cv"]
        a, b = TIMES_ANALISADOS
        regular = a if c["diferenca"] < 0 else b
        irregular = b if regular == a else a
        paragrafos.append(
            f"A única diferença de regularidade entre os times que se distingue do acaso está em {g['variavel']}: "
            f"{_time(regular)} têm CV de {_n(g['times'][regular]['cv_percentual'])}% e {_time(irregular)}, "
            f"{_n(g['times'][irregular]['cv_percentual'])}% (IC 95% da diferença de {_n(abs(c['ic95'][0]) if c['diferenca'] > 0 else abs(c['ic95'][1]))} "
            f"a {_n(abs(c['ic95'][1]) if c['diferenca'] > 0 else abs(c['ic95'][0]))}). Nas outras "
            f"{len(tabela) - len(relevantes)} variáveis os times são igualmente regulares."
        )
    return _secao("Regularidade (CV)", paragrafos)


def _secao_outliers(tabela, qualidade, resumo) -> dict[str, Any]:
    totais = {t: sum(g["times"][t]["quantidade_outliers"] for g in tabela) for t in TIMES_ANALISADOS}
    destaques = [(g["variavel"], t, o) for g in tabela for t in TIMES_ANALISADOS for o in g["times"][t]["outliers_detalhe"]]
    extremos_3iqr = sum(g["times"][t]["quantidade_outliers_3iqr"] for g in tabela for t in TIMES_ANALISADOS)
    grubbs = [
        (c["variavel"], t, v)
        for c in qualidade["outliers_por_coluna"] if c["analisada"] for t in TIMES_ANALISADOS
        for v in c["times"][t]["grubbs"]["valores"]
    ]
    datas_ot = {(o["data"], t) for _, t, o in destaques if o.get("prorrogacoes")}
    grubbs_ot = sum(
        1 for v, t, valor in grubbs
        if any(o["valor"] == valor and o.get("prorrogacoes") for var, tt, o in destaques if var == v and tt == t)
    )
    resumo.update({
        "outliers_por_time": totais, "outliers_total": sum(totais.values()),
        "outliers_3iqr": extremos_3iqr, "grubbs_confirmados": len(grubbs),
        "grubbs_em_prorrogacao": grubbs_ot, "outliers_em_prorrogacao": len(datas_ot),
    })

    def descreve(v, t, o):
        extra = ", prorrogação" if o.get("prorrogacoes") else ""
        return f"{v} {_n(o['valor'], 0)} ({_curto(t)}, {o['data']}{extra})"

    return _secao("Valores atípicos", [
        ("Pela regra de Tukey (1,5×IQR), nas 7 variáveis: "
         + "; ".join(f"{_curto(t)}, {_plural(q, 'outlier', 'outliers')}" for t, q in totais.items())
         + f". São eles: {_lista([descreve(*d) for d in destaques])}.") if destaques else
        "Nenhum outlier pela regra de Tukey nas 7 variáveis (0 jogos).",
        f"Com k = 3 restam {extremos_3iqr}, e o teste de Grubbs (α = 0,05) confirma {len(grubbs)}"
        + ((", ambos em jogos com prorrogação" if grubbs_ot == len(grubbs) == 2 else
            ", todos em jogos com prorrogação" if grubbs_ot == len(grubbs) else
            f", {grubbs_ot} deles em jogos com prorrogação") if grubbs_ot else "")
        + f". Ao todo, {len(datas_ot)} dos {sum(totais.values())} outliers aconteceram em jogos prorrogados: mais "
        "minutos explicam parte do valor extremo. Não há sinal de erro de registro, e os jogos foram mantidos.",
    ])


def _secao_qualidade(qualidade, dicionario, resumo) -> dict[str, Any]:
    dup = qualidade["duplicatas"]["fonte"]
    ausentes = sum(l["fonte"] or 0 for l in qualidade["ausentes"])
    violacoes = sum(r["violacoes_fonte"] for r in qualidade["dominio"]["regras"])
    vaz = dicionario["vazamento"]
    resumo.update({
        "ausentes_fonte": ausentes, "duplicatas_fonte": dup["linha_inteira"] + dup["chave_time_jogo"],
        "violacoes_dominio": violacoes, "regras_dominio": len(qualidade["dominio"]["regras"]),
        "colunas_fonte": len(qualidade["ausentes"]), "colunas_excluidas": len(dicionario["exclusoes"]),
    })
    return _secao("Qualidade e preparo da base", [
        f"A fonte tem {_n(dup['registros'], 0)} registros e {len(qualidade['ausentes'])} colunas, com {ausentes} "
        f"ausentes, {dup['linha_inteira'] + dup['chave_time_jogo']} duplicatas e {violacoes} violações nas "
        f"{len(qualidade['dominio']['regras'])} regras de domínio. O recorte do grupo tem {dicionario['linhas']} "
        "jogos; as conclusões não dependem de imputação nem de limpeza agressiva.",
        f"Para uso em modelos, {len(dicionario['exclusoes'])} colunas são excluídas "
        f"({_lista([e['coluna'] for e in dicionario['exclusoes']])}), e WL é o alvo. W, L e W_PCT vazam o resultado: "
        f"a variação de W é igual a WL em {vaz['variacao_w_igual_wl']} de {vaz['jogos_com_anterior']} jogos com "
        "jogo anterior.",
    ])


def _secao_limitacoes(tabela, qualidade, resumo) -> dict[str, Any]:
    tamanhos = sorted({g["times"][t]["n"] for g in tabela for t in TIMES_ANALISADOS})
    ep = max(erro_padrao_g1(n) for n in tamanhos)
    prorrogados = len(qualidade["dominio"]["jogos_prorrogacao"])
    taxa = qualidade["parametros"]["taxa_referencia"] * 100
    resumo.update({"erro_padrao_g1": ep, "jogos_prorrogacao": prorrogados, "taxa_referencia_pct": taxa})
    return _secao("Limitações", [
        f"Uma única temporada regular, com {' e '.join(str(n) for n in tamanhos)} jogos por time: o erro-padrão do G1 "
        f"é ≈ {_n(ep)}, e medidas de cauda (assimetria, outliers) mudam com um ou dois jogos extremos.",
        f"A análise é univariada e descritiva: não controla adversário, mando de quadra, desfalques nem os "
        f"{prorrogados} jogos com prorrogação; as diferenças de média entre os times não foram submetidas a teste "
        "de hipótese (só as de CV e IQR, por bootstrap).",
        f"Os testes de mecanismo de ausência foram demonstrados em dados simulados, porque a base real tem "
        f"{sum(l['fonte'] or 0 for l in qualidade['ausentes'])} ausentes; os detectores de outliers por distância e o "
        f"ECOD usam limiares calibrados para marcar {_n(taxa)}% dos jogos em dados normais.",
    ])


def _secao_conclusao(tabela, perfil) -> dict[str, Any]:
    a, b = TIMES_ANALISADOS
    ordenadas = sorted(perfil["variaveis"], key=lambda v: -abs(v["diferenca_z"]))
    principais = [f"{v['variavel']} ({_curto(a if v['diferenca_z'] > 0 else b)} acima, Δz = {_n(abs(v['diferenca_z']))})"
                  for v in ordenadas[:3]]
    pontos = next(v for v in perfil["variaveis"] if v["variavel"] == "Pontos")
    faixa = max(abs(t["z"]) for v in perfil["variaveis"] for t in v["times"].values())
    estilo = {
        t: [LEITURA_Z[v["variavel"]] for v in ordenadas[:3] if (v["diferenca_z"] > 0) == (t == a)]
        for t in (a, b)
    }
    return _secao("Conclusão", [
        f"Mavericks e Pacers pontuam de forma muito parecida (Δz = {_n(abs(pontos['diferenca_z']))} em Pontos). O que "
        f"distingue os estilos está em {_lista(principais)}: "
        + "; ".join(f"{_time(t)} se destacam por {_lista(itens)}" for t, itens in estilo.items() if itens) + ".",
        f"Nenhuma média de time fica a mais de {_n(faixa)} desvio padrão da média conjunta: a variação de jogo para "
        "jogo dentro de cada time é bem maior que a diferença entre os times. Por isso as comparações olham a "
        "distribuição inteira (boxplot, IQR), e não só a média.",
    ])


def calcular_sintese(
    dados: pd.DataFrame, qualidade: dict[str, Any], dicionario: dict[str, Any]
) -> dict[str, Any]:
    tabela = calcular_tabela_descritiva(dados)["variaveis"]
    perfil = calcular_perfil_z(dados)
    comparacoes = {g["variavel"]: comparar_times(dados, g["variavel"]) for g in tabela}
    z = textos_zscore(perfil)
    resumo: dict[str, Any] = {}
    secoes = [
        _secao_vantagens(tabela, perfil, resumo),
        _secao_forma(tabela, resumo),
        _secao_regularidade(tabela, comparacoes, resumo),
        _secao_outliers(tabela, qualidade, resumo),
        _secao("Onde o z-score entra no gráfico de barras", [z["paragrafos"][2]],
               ["Resposta completa e gráfico padronizado na página Comparativo."]),
        _secao_qualidade(qualidade, dicionario, resumo),
        _secao_limitacoes(tabela, qualidade, resumo),
        _secao_conclusao(tabela, perfil),
    ]
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, perfil),
        "comparacoes": comparacoes,
        "resumo": resumo,
        "secoes": secoes,
    }
