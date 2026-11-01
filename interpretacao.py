"""Quadros-resumo e interpretação textual de Assimetria, CV e IQR.

Domínio puro (não conhece Flask). Cada função monta, a partir da tabela
descritiva, o quadro variáveis × times, as linhas de detalhe e os textos de
interpretação — um bloco por subitem do enunciado — sempre citando os números
calculados, nunca frases fixas.
"""

from math import sqrt
from typing import Any

import pandas as pd

from analise import (
    CONSTANTE_SIGMA_ROBUSTO,
    FAIXAS_CV,
    LIMITE_ASSIMETRIA_FORTE,
    LIMITE_SIMETRIA,
    MAPA_VARIAVEIS,
    MEDIA_MINIMA_CV,
    TIMES_ANALISADOS,
    calcular_tabela_descritiva,
)

# Abaixo deste |G1| o sinal é ruído: G1 e Bowley podem discordar sem que haja
# divergência real de formato.
LIMITE_SINAL_RELEVANTE = 0.2
# Para uma normal com n ≈ 75, amplitude/IQR fica em torno de 3,5–4.
LIMITE_AMPLITUDE_IQR = 4.0
LIMITE_DP_INFLADO = 1.10  # DP > 10% acima do σ robusto (IQR/1,349)


def _n(valor: float | None, casas: int = 2) -> str:
    """Número no padrão brasileiro com casas fixas."""
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return texto.replace("-", "−")


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _curto(time: str) -> str:
    return time.split()[-1]


def _sinal(valor: float | None) -> int:
    if valor is None or valor == 0:
        return 0
    return 1 if valor > 0 else -1


def _tabela(dados: pd.DataFrame) -> list[dict[str, Any]]:
    return calcular_tabela_descritiva(dados)["variaveis"]


def _quadro(tabela, chave: str) -> list[dict[str, Any]]:
    return [
        {
            "variavel": grupo["variavel"],
            "unidade": grupo["unidade"],
            "valores": {time: grupo["times"][time][chave] for time in TIMES_ANALISADOS},
        }
        for grupo in tabela
    ]


def _pares(tabela):
    for grupo in tabela:
        for time in TIMES_ANALISADOS:
            yield grupo, time, grupo["times"][time]


def _media_times(grupo, chave: str, absoluto: bool = False) -> float:
    valores = [grupo["times"][time][chave] for time in TIMES_ANALISADOS]
    valores = [abs(v) if absoluto else v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else 0.0


def _vencedor(grupo, chave: str, menor: bool = True) -> str:
    a, b = (grupo["times"][time][chave] for time in TIMES_ANALISADOS)
    if a == b:
        return "empate"
    return TIMES_ANALISADOS[0] if (a < b) == menor else TIMES_ANALISADOS[1]


def _padrao_times(tabela, chave: str, rotulo: str) -> str:
    """Resume quantas variáveis cada time 'vence' e se o padrão se mantém."""
    vitorias = {time: 0 for time in TIMES_ANALISADOS}
    for grupo in tabela:
        vencedor = _vencedor(grupo, chave)
        if vencedor in vitorias:
            vitorias[vencedor] += 1
    total = len(tabela)
    lider, segundo = sorted(vitorias, key=vitorias.get, reverse=True)
    if vitorias[lider] >= total - 1:
        leitura = "o padrão praticamente se mantém em todas as variáveis"
    elif vitorias[lider] >= (total // 2) + 2:
        leitura = "há um padrão predominante, com exceções"
    else:
        leitura = "o padrão muda conforme a variável; nenhum time domina"
    return (
        f"{_curto(lider)} é {rotulo} em {vitorias[lider]} de {total} variáveis e "
        f"{_curto(segundo)} em {vitorias[segundo]}; {leitura}."
    )


# --------------------------------------------------------------------------
# Assimetria
# --------------------------------------------------------------------------

def calcular_assimetria(dados: pd.DataFrame) -> dict[str, Any]:
    tabela = _tabela(dados)
    linhas = [
        {
            "variavel": grupo["variavel"],
            "unidade": grupo["unidade"],
            "time": time,
            "n": item["n"],
            "g1": item["assimetria"],
            "direcao": item["direcao_assimetria"],
            "intensidade": item["intensidade_assimetria"],
            "bowley": item["bowley"],
            "media_menos_mediana": item["media"] - item["mediana"],
            "g1_sem_outliers": item["assimetria_sem_outliers"],
            "quantidade_outliers": item["quantidade_outliers"],
        }
        for grupo, time, item in _pares(tabela)
    ]
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, "assimetria"),
        "linhas": linhas,
        "secoes": _textos_assimetria(tabela),
    }


def _textos_assimetria(tabela) -> list[dict[str, Any]]:
    tamanhos = sorted({item["n"] for _, _, item in _pares(tabela)})
    fatores = ", ".join(
        f"{_n(sqrt(n * (n - 1)) / (n - 2), 4)} para n = {n}" for n in tamanhos
    )
    secoes = [{
        "titulo": "Coeficiente e fórmula utilizada",
        "paragrafos": [
            "Usamos o coeficiente ajustado de Fisher-Pearson (G1), implementado por "
            "pandas.Series.skew — o mesmo valor de scipy.stats.skew(bias=False).",
            f"Justificativa: cada time tem {' e '.join(str(n) for n in tamanhos)} jogos. O coeficiente de "
            "momento de Pearson (g1) é viesado em amostras finitas; o fator √(n(n−1))/(n−2) corrige esse viés "
            f"({fatores}). Como os jogos são uma amostra do desempenho do time, a versão ajustada é a coerente "
            "com o desvio padrão amostral (n − 1) usado no restante do projeto.",
            "O coeficiente de Bowley, (Q3 + Q1 − 2·Mediana)/IQR, é exibido só como verificação robusta: ele usa "
            "apenas os quartis e por isso não é afetado por jogos extremos, mas também ignora as caudas — por "
            "isso não substitui o G1.",
        ],
    }]

    # Direção
    positivos = [(g, t, i) for g, t, i in _pares(tabela) if i["assimetria"] > 0]
    total = len(tabela) * len(TIMES_ANALISADOS)
    detalhes = [
        f"{g['variavel']}: " + "; ".join(
            f"{_curto(t)} G1 = {_n(g['times'][t]['assimetria'])}, {g['times'][t]['direcao_assimetria']}"
            for t in TIMES_ANALISADOS
        )
        for g in tabela
    ]
    secoes.append({
        "titulo": "Direção (pelo sinal do coeficiente)",
        "paragrafos": [
            "G1 > 0: cauda mais longa à direita (positiva); G1 < 0: cauda à esquerda (negativa); "
            "G1 = 0: simétrica.",
            f"{len(positivos)} das {total} combinações variável × time têm assimetria positiva e "
            f"{total - len(positivos)} negativa.",
            *detalhes,
        ],
    })

    # Intensidade
    por_classe: dict[str, list[str]] = {}
    for g, t, i in _pares(tabela):
        por_classe.setdefault(i["intensidade_assimetria"], []).append(
            f"{g['variavel']} ({_curto(t)}, {_n(i['assimetria'])})"
        )
    paragrafos = [
        f"Critério adotado: |G1| < {_n(LIMITE_SIMETRIA, 1)} aproximadamente simétrica; "
        f"{_n(LIMITE_SIMETRIA, 1)} ≤ |G1| < {_n(LIMITE_ASSIMETRIA_FORTE, 1)} moderada; "
        f"|G1| ≥ {_n(LIMITE_ASSIMETRIA_FORTE, 1)} forte (convenção de Bulmer, usual para amostras deste tamanho).",
    ]
    for classe in ("aproximadamente simétrica", "moderada", "forte"):
        itens = por_classe.get(classe, [])
        paragrafos.append(
            f"{classe.capitalize()}: {len(itens)} caso(s)"
            + (f" — {', '.join(itens)}." if itens and classe != "aproximadamente simétrica" else ".")
        )
    secoes.append({"titulo": "Intensidade da assimetria", "paragrafos": paragrafos})

    # Coeficiente × gráficos
    concordam, divergem = [], []
    for g, t, i in _pares(tabela):
        sinais = {_sinal(i["assimetria"]), _sinal(i["bowley"]), _sinal(i["media"] - i["mediana"])}
        rotulo = f"{g['variavel']} ({_curto(t)})"
        mudou_classe = (
            abs(i["assimetria"]) >= LIMITE_SIMETRIA
            and abs(i["assimetria_sem_outliers"]) < LIMITE_SIMETRIA
        )
        if mudou_classe:
            divergem.append(
                f"{rotulo}: G1 = {_n(i['assimetria'])}, mas sem "
                f"{_plural(i['quantidade_outliers'], 'o outlier', 'os outliers')} "
                f"({', '.join(_n(v) for v in i['outliers'])}) cai para {_n(i['assimetria_sem_outliers'])}. "
                "A assimetria vem de poucos jogos extremos: no histograma aparece como uma barra isolada na "
                "cauda e no boxplot como ponto fora do bigode, enquanto a caixa (Bowley = "
                f"{_n(i['bowley'])}) é quase simétrica."
            )
        elif abs(i["assimetria"]) >= LIMITE_SINAL_RELEVANTE and len(sinais - {0}) > 1:
            lado = [v for v in i["outliers"] if (v > i["mediana"]) == (i["assimetria"] > 0)]
            causa = (
                f" Os outliers {'superiores' if i['assimetria'] > 0 else 'inferiores'} "
                f"({', '.join(_n(v) for v in lado)}) alongam essa cauda e explicam o sinal de G1."
                if lado else ""
            )
            divergem.append(
                f"{rotulo}: G1 = {_n(i['assimetria'])}, Bowley = {_n(i['bowley'])} e média − mediana = "
                f"{_n(i['media'] - i['mediana'])} apontam direções diferentes. G1 pesa as caudas (momentos "
                "de 3ª ordem), enquanto Bowley e a posição da mediana descrevem o miolo da distribuição; "
                "a cauda e o centro estão inclinados para lados opostos." + causa
            )
        else:
            concordam.append(rotulo)
    secoes.append({
        "titulo": "Confirmação visual: histograma com KDE e boxplot",
        "paragrafos": [
            "No histograma, assimetria positiva aparece como cauda mais longa à direita da KDE; no boxplot, como "
            "mediana mais próxima de Q1 e bigode/outliers mais longos para cima (o inverso para negativa). "
            "Use os seletores abaixo para ver cada variável.",
            f"O coeficiente e os gráficos contam a mesma história em {len(concordam)} de {total} casos "
            "(G1, Bowley e média − mediana com o mesmo sinal, ou G1 tão perto de zero que o sinal é ruído, "
            f"|G1| < {_n(LIMITE_SINAL_RELEVANTE)}).",
            *(divergem or ["Não há divergências relevantes entre coeficiente e gráficos."]),
        ],
    })

    # Comparação entre variáveis e times
    ordem = sorted(tabela, key=lambda g: _media_times(g, "assimetria", absoluto=True), reverse=True)
    mesma_direcao = [
        g["variavel"] for g in tabela
        if len({_sinal(g["times"][t]["assimetria"]) for t in TIMES_ANALISADOS}) == 1
    ]
    direcao_oposta = [g["variavel"] for g in tabela if g["variavel"] not in mesma_direcao]
    secoes.append({
        "titulo": "Comparação entre variáveis e entre times",
        "paragrafos": [
            "Ordem por |G1| médio dos dois times (mais assimétrica primeiro): "
            + ", ".join(f"{g['variavel']} ({_n(_media_times(g, 'assimetria', True))})" for g in ordem) + ".",
            f"As mais assimétricas são {ordem[0]['variavel']} e {ordem[1]['variavel']}; as mais simétricas, "
            f"{ordem[-1]['variavel']} e {ordem[-2]['variavel']}.",
            (f"A direção se repete nos dois times em {', '.join(mesma_direcao)}" if mesma_direcao
             else "Em nenhuma variável a direção se repete nos dois times")
            + (f"; em {', '.join(direcao_oposta)} os times têm sinais opostos — nesses casos |G1| é pequeno e "
               "a diferença é de formato sutil, não de comportamento." if direcao_oposta else "."),
        ],
    })

    # Implicação prática
    paragrafos = []
    for g, t, i in _pares(tabela):
        if abs(i["assimetria"]) >= LIMITE_SIMETRIA:
            recomendacao = (
                "transformação log(x + 1) (há jogos com zero) ou métodos robustos são recomendados em análises "
                "posteriores" if abs(i["assimetria"]) >= LIMITE_ASSIMETRIA_FORTE
                else "a mediana representa melhor o valor típico; métodos robustos são preferíveis"
            )
            paragrafos.append(
                f"{g['variavel']} ({_curto(t)}): média {_n(i['media'])} × mediana {_n(i['mediana'])} "
                f"({g['unidade']}); {recomendacao}."
            )
    maior_gap = max(
        (abs(i["media"] - i["mediana"]) / i["desvio_padrao"], g, t, i)
        for g, t, i in _pares(tabela) if i["desvio_padrao"] > 0
    )
    fortes = [1 for _, _, i in _pares(tabela) if abs(i["assimetria"]) >= LIMITE_ASSIMETRIA_FORTE]
    secoes.append({
        "titulo": "Implicação prática: média ou mediana?",
        "paragrafos": [
            "Onde |G1| < 0,5, média e mediana praticamente coincidem e a média é um bom valor típico. A maior "
            f"distância relativa ocorre em {maior_gap[1]['variavel']} ({_curto(maior_gap[2])}): "
            f"|média − mediana| = {_n(abs(maior_gap[3]['media'] - maior_gap[3]['mediana']))} "
            f"{maior_gap[1]['unidade']}, {_n(maior_gap[0] * 100)}% de um desvio padrão.",
            *(paragrafos or ["Nenhuma combinação tem assimetria moderada ou forte: a média pode ser usada como "
                             "valor típico em todas as variáveis."]),
            ("Há variáveis com assimetria forte, para as quais log(x + 1) é indicada antes de métodos que "
             "supõem normalidade." if fortes else
             "Nenhuma variável atinge |G1| ≥ 1, então transformação logarítmica não é necessária; quando houver "
             "assimetria moderada causada por poucos jogos extremos, métodos robustos (mediana, IQR) bastam."),
        ],
    })
    return secoes


# --------------------------------------------------------------------------
# Coeficiente de variação
# --------------------------------------------------------------------------

def _classe_cv(cv: float | None) -> str:
    if cv is None:
        return "indefinido"
    if cv < FAIXAS_CV[0]:
        return "consistente"
    return "moderada" if cv < FAIXAS_CV[1] else "irregular"


def calcular_cv(dados: pd.DataFrame) -> dict[str, Any]:
    tabela = _tabela(dados)
    linhas = [
        {
            "variavel": grupo["variavel"],
            "unidade": grupo["unidade"],
            "time": time,
            "media": item["media"],
            "desvio_padrao": item["desvio_padrao"],
            "cv_percentual": item["cv_percentual"],
            "classe": _classe_cv(item["cv_percentual"]),
            "cautela": item["media"] < MEDIA_MINIMA_CV,
            "cv_poisson_ref": item["cv_poisson_ref"],
            "cv_robusto_iqr": item["cv_robusto_iqr"],
            "g1": item["assimetria"],
        }
        for grupo, time, item in _pares(tabela)
    ]
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, "cv_percentual"),
        "linhas": linhas,
        "secoes": _textos_cv(tabela),
        "faixas": list(FAIXAS_CV),
        "media_minima": MEDIA_MINIMA_CV,
    }


def _textos_cv(tabela) -> list[dict[str, Any]]:
    secoes = [{
        "titulo": "Fórmula e convenções",
        "paragrafos": [
            "CV = s / x̄ × 100, com s = desvio padrão amostral (divisor n − 1) e x̄ = média aritmética. O resultado "
            "é apresentado em percentual (%), com 2 casas — mesma convenção do desvio padrão e da variância da "
            "tabela descritiva.",
        ],
    }]

    pequenas = [
        (g, t, i) for g, t, i in _pares(tabela) if i["media"] < MEDIA_MINIMA_CV
    ]
    paragrafos = [
        "Escala de razão: todas as sete variáveis são contagens por jogo, com zero absoluto (0 tocos significa "
        "ausência de tocos), então razões entre valores fazem sentido e o CV é aplicável. Todas as médias são "
        "positivas.",
        f"Critério de cautela: média < {_n(MEDIA_MINIMA_CV, 0)} por jogo. Com média pequena, o denominador do CV "
        "é pequeno e qualquer variação de 1 ou 2 unidades vira um percentual alto. Além disso, em contagens "
        "do tipo Poisson a variância é próxima da média, logo CV ≈ 100/√média: há um piso de CV que depende só "
        "da escala, não da regularidade do time.",
    ]
    for g, t, i in pequenas:
        excesso = i["cv_percentual"] - i["cv_poisson_ref"]
        leitura = (
            f"o CV fica só {_n(excesso)} pontos percentuais acima do piso, ou seja, quase todo o CV alto vem da "
            "escala pequena e não de irregularidade do time"
            if excesso > 0 else
            "o CV não passa do piso esperado pela escala: o valor alto não indica irregularidade do time"
        )
        paragrafos.append(
            f"{g['variavel']} ({_curto(t)}): média {_n(i['media'])}, CV {_n(i['cv_percentual'])}% e piso "
            f"Poisson 100/√média = {_n(i['cv_poisson_ref'])}% — {leitura}. Interpretar com cautela."
        )
    secoes.append({"titulo": "Condição de validade", "paragrafos": paragrafos})

    paragrafos = [
        f"Faixas adotadas: CV < {_n(FAIXAS_CV[0], 0)}% consistente; {_n(FAIXAS_CV[0], 0)}–{_n(FAIXAS_CV[1], 0)}% "
        f"variabilidade moderada; > {_n(FAIXAS_CV[1], 0)}% irregular de um jogo para outro.",
    ]
    for g in tabela:
        partes = []
        for t in TIMES_ANALISADOS:
            i = g["times"][t]
            partes.append(f"{_curto(t)} {_n(i['cv_percentual'])}% ({_classe_cv(i['cv_percentual'])})")
        mais_irregular = max(TIMES_ANALISADOS, key=lambda t: g["times"][t]["cv_percentual"])
        i = g["times"][mais_irregular]
        paragrafos.append(
            f"{g['variavel']}: {'; '.join(partes)}. Na prática, nos {_curto(mais_irregular)} é comum um jogo "
            f"ficar ±{_n(i['desvio_padrao'])} {g['unidade']} em torno da média de {_n(i['media'])}."
        )
    secoes.append({"titulo": "Interpretação prática", "paragrafos": paragrafos})

    ordem = sorted(tabela, key=lambda g: _media_times(g, "cv_percentual"), reverse=True)
    maior_dp = max(tabela, key=lambda g: _media_times(g, "desvio_padrao"))
    menor_dp = min(tabela, key=lambda g: _media_times(g, "desvio_padrao"))
    secoes.append({
        "titulo": "Comparação entre variáveis de escalas diferentes",
        "paragrafos": [
            "Ordem por CV médio dos dois times (mais dispersa primeiro): "
            + ", ".join(f"{g['variavel']} ({_n(_media_times(g, 'cv_percentual'))}%)" for g in ordem) + ".",
            f"Relativamente mais dispersas: {ordem[0]['variavel']} e {ordem[1]['variavel']}; mais estáveis: "
            f"{ordem[-1]['variavel']} e {ordem[-2]['variavel']}.",
            f"O desvio padrão bruto levaria à conclusão errada: {maior_dp['variavel']} tem o maior DP "
            f"({_n(_media_times(maior_dp, 'desvio_padrao'))} {maior_dp['unidade']}) e {menor_dp['variavel']} o "
            f"menor ({_n(_media_times(menor_dp, 'desvio_padrao'))} {menor_dp['unidade']}), mas o DP está na "
            "unidade de cada variável e cresce com a escala. O CV divide pelo nível médio e é adimensional, "
            "por isso permite a comparação.",
        ],
    })

    paragrafos = []
    for g in tabela:
        regular = _vencedor(g, "cv_percentual")
        if regular == "empate":
            paragrafos.append(f"{g['variavel']}: os dois times têm o mesmo CV.")
            continue
        irregular = [t for t in TIMES_ANALISADOS if t != regular][0]
        paragrafos.append(
            f"{g['variavel']}: {_curto(regular)} é mais consistente ({_n(g['times'][regular]['cv_percentual'])}%) "
            f"e {_curto(irregular)} mais irregular ({_n(g['times'][irregular]['cv_percentual'])}%)."
        )
    paragrafos.append(_padrao_times(tabela, "cv_percentual", "o mais regular"))
    secoes.append({"titulo": "Homogeneidade entre os times", "paragrafos": paragrafos})

    paragrafos = [
        "O CV usa média e desvio padrão, que são sensíveis a caudas longas. Como alternativa robusta mostramos "
        "IQR/Mediana × 100. Para dados aproximadamente normais, IQR/Mediana ≈ 1,35 × CV; razões muito "
        "diferentes disso indicam que extremos ou o formato pesam no CV.",
    ]
    assimetricas = [(g, t, i) for g, t, i in _pares(tabela) if abs(i["assimetria"]) >= LIMITE_SIMETRIA]
    for g, t, i in assimetricas:
        razao = i["cv_robusto_iqr"] / i["cv_percentual"] if i["cv_percentual"] else None
        paragrafos.append(
            f"{g['variavel']} ({_curto(t)}): G1 = {_n(i['assimetria'])}, CV = {_n(i['cv_percentual'])}%, "
            f"IQR/Mediana = {_n(i['cv_robusto_iqr'])}% (razão {_n(razao)}). Com assimetria "
            f"{i['intensidade_assimetria']}, a medida robusta é a mais adequada para descrever a dispersão típica."
        )
    if not assimetricas:
        paragrafos.append(
            "Nenhuma combinação tem |G1| ≥ 0,5, então o CV clássico é adequado em todas as variáveis."
        )
    secoes.append({"titulo": "CV × desvio padrão × assimetria", "paragrafos": paragrafos})

    celulas = [(i["cv_percentual"], g, t) for g, t, i in _pares(tabela)]
    maior, menor = max(celulas, key=lambda c: c[0]), min(celulas, key=lambda c: c[0])
    gap = max(
        tabela,
        key=lambda g: abs(g["times"][TIMES_ANALISADOS[0]]["cv_percentual"] - g["times"][TIMES_ANALISADOS[1]]["cv_percentual"]),
    )
    diferenca = abs(gap["times"][TIMES_ANALISADOS[0]]["cv_percentual"] - gap["times"][TIMES_ANALISADOS[1]]["cv_percentual"])
    secoes.append({
        "titulo": "Destaques do quadro-resumo",
        "paragrafos": [
            f"Maior CV: {maior[1]['variavel']} ({_curto(maior[2])}), {_n(maior[0])}%. Menor CV: "
            f"{menor[1]['variavel']} ({_curto(menor[2])}), {_n(menor[0])}%.",
            f"Maior diferença entre os times: {gap['variavel']}, {_n(diferenca)} pontos percentuais.",
        ],
    })
    return secoes


# --------------------------------------------------------------------------
# Intervalo interquartil
# --------------------------------------------------------------------------

def calcular_iqr(dados: pd.DataFrame) -> dict[str, Any]:
    tabela = _tabela(dados)
    linhas = [
        {
            "variavel": grupo["variavel"],
            "unidade": grupo["unidade"],
            "time": time,
            "q1": item["q1"],
            "q3": item["q3"],
            "iqr": item["iqr"],
            "amplitude": item["amplitude"],
            "razao_amplitude_iqr": item["razao_amplitude_iqr"],
            "desvio_padrao": item["desvio_padrao"],
            "sigma_robusto": item["sigma_robusto"],
            "desvio_sem_outliers": item["desvio_sem_outliers"],
            "iqr_sem_outliers": item["iqr_sem_outliers"],
            "limite_inferior": item["limite_inferior"],
            "limite_superior": item["limite_superior"],
            "quantidade_outliers": item["quantidade_outliers"],
            "outliers": item["outliers"],
            "quantidade_outliers_3iqr": item["quantidade_outliers_3iqr"],
        }
        for grupo, time, item in _pares(tabela)
    ]
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, "iqr"),
        "linhas": linhas,
        "secoes": _textos_iqr(dados, tabela),
    }


def _textos_iqr(dados: pd.DataFrame, tabela) -> list[dict[str, Any]]:
    secoes = [{
        "titulo": "Fórmula e método dos quartis",
        "paragrafos": [
            "IQR = Q3 − Q1. Os quartis são calculados por interpolação linear entre as estatísticas de ordem "
            "(método padrão de numpy/pandas, tipo 7 de Hyndman & Fan): posição h = (n − 1)·p + 1 nos dados "
            "ordenados. É o mesmo método "
            "usado na tabela descritiva e no boxplot, portanto os três mostram os mesmos Q1, Q3 e limites.",
        ],
    }, {
        "titulo": "Q1, Q3 e IQR lado a lado",
        "paragrafos": [
            "A tabela abaixo mostra Q1, Q3 e IQR por variável e por time, junto da amplitude e do desvio padrão "
            "para as comparações dos próximos itens.",
        ],
    }]

    paragrafos = [
        "O IQR é a largura da faixa que contém os 50% centrais dos jogos: IQR baixo = time concentrado em "
        "torno do seu típico; IQR alto = desempenho central espalhado."
    ]
    for g in tabela:
        partes = [
            f"50% centrais dos jogos dos {_curto(t)} ficaram entre {_n(g['times'][t]['q1'])} e "
            f"{_n(g['times'][t]['q3'])} (faixa de {_n(g['times'][t]['iqr'])})"
            for t in TIMES_ANALISADOS
        ]
        paragrafos.append(f"{g['variavel']} ({g['unidade']}): " + "; ".join(partes) + ".")
    secoes.append({"titulo": "Interpretação prática", "paragrafos": paragrafos})

    amplas = [(g, t, i) for g, t, i in _pares(tabela)
              if i["razao_amplitude_iqr"] and i["razao_amplitude_iqr"] > LIMITE_AMPLITUDE_IQR]
    paragrafos = [
        f"Referência: para uma distribuição normal com n ≈ 75, amplitude/IQR fica em torno de 3,5–4. Acima de "
        f"{_n(LIMITE_AMPLITUDE_IQR, 0)} a amplitude está sendo esticada por jogos extremos — a amplitude depende "
        "só do mínimo e do máximo, o IQR ignora os 25% de cada ponta.",
    ]
    for g, t, i in sorted(amplas, key=lambda c: c[2]["razao_amplitude_iqr"], reverse=True):
        paragrafos.append(
            f"{g['variavel']} ({_curto(t)}): amplitude {_n(i['amplitude'])} = {_n(i['razao_amplitude_iqr'])} × IQR "
            f"({_n(i['iqr'])}); {_plural(i['quantidade_outliers'], 'outlier', 'outliers')}"
            + (f": {', '.join(_n(v) for v in i['outliers'])}." if i["outliers"] else
               " — a cauda é longa mesmo sem pontos além de 1,5×IQR.")
        )
    if not amplas:
        paragrafos.append("Nenhuma variável tem amplitude desproporcional ao IQR.")
    secoes.append({"titulo": "IQR × amplitude", "paragrafos": paragrafos})

    inflados = [(g, t, i) for g, t, i in _pares(tabela)
                if i["quantidade_outliers"] and i["desvio_sem_outliers"] < i["desvio_padrao"]]
    paragrafos = [
        "Comparamos o DP com o σ robusto = IQR/1,349 (o valor que o DP teria se a distribuição fosse normal "
        f"com aquele IQR) e recalculamos DP e IQR sem os outliers de Tukey. DP/σ robusto > {_n(LIMITE_DP_INFLADO)} "
        "indica DP inflado pelas caudas.",
    ]
    for g, t, i in inflados:
        queda_dp = (1 - i["desvio_sem_outliers"] / i["desvio_padrao"]) * 100
        variacao_iqr = (i["iqr_sem_outliers"] / i["iqr"] - 1) * 100 if i["iqr"] else 0.0
        paragrafos.append(
            f"{g['variavel']} ({_curto(t)}): DP {_n(i['desvio_padrao'])} → {_n(i['desvio_sem_outliers'])} sem "
            f"{_plural(i['quantidade_outliers'], 'outlier', 'outliers')} (−{_n(queda_dp)}%), enquanto o IQR vai de {_n(i['iqr'])} para "
            f"{_n(i['iqr_sem_outliers'])} ({'+' if variacao_iqr >= 0 else '−'}{_n(abs(variacao_iqr))}%). "
            f"DP/σ robusto = {_n(i['razao_dp_sigma_robusto'])}."
        )
    if not inflados:
        paragrafos.append("Nenhuma variável tem outliers que inflem o desvio padrão.")
    paragrafos.append(
        "A remoção de poucos jogos muda o DP muito mais do que o IQR: evidência de que o IQR é a medida de "
        "dispersão robusta."
    )
    secoes.append({"titulo": "IQR × desvio padrão", "paragrafos": paragrafos})

    # Regra de outliers + conferência com os dados brutos
    divergencias = []
    for g, t, i in _pares(tabela):
        serie = dados.loc[dados["TEAM_NAME"] == t, MAPA_VARIAVEIS[g["variavel"]]].dropna()
        fora = sorted(
            float(v) for v in serie[(serie < i["limite_inferior"]) | (serie > i["limite_superior"])]
        )
        if fora != i["outliers"]:
            divergencias.append(f"{g['variavel']} ({_curto(t)})")
    total_15 = sum(i["quantidade_outliers"] for _, _, i in _pares(tabela))
    total_3 = sum(i["quantidade_outliers_3iqr"] for _, _, i in _pares(tabela))
    secoes.append({
        "titulo": "IQR e a regra de outliers",
        "paragrafos": [
            "Regra adotada: k = 1,5 (Tukey). Limites: Q1 − 1,5×IQR e Q3 + 1,5×IQR, recalculados na tabela abaixo. "
            "É a regra clássica do boxplot; k = 3 marcaria só valores 'extremos' e é mostrado para comparação.",
            f"Com k = 1,5 há {total_15} outliers no total; com k = 3, {total_3}.",
            "Conferência: os outliers listados foram recontados diretamente na base para cada variável e time e "
            + (f"divergem em {', '.join(divergencias)}." if divergencias else
               "coincidem exatamente com os pontos fora dos bigodes do boxplot (mesmos quartis e mesmo k)."),
            "Uma divergência só apareceria se o boxplot usasse outro método de quartis; por isso o gráfico recebe "
            "Q1, Q3 e limites prontos do servidor em vez de recalculá-los no navegador.",
        ],
    })

    paragrafos = []
    for g in tabela:
        concentrado = _vencedor(g, "iqr")
        if concentrado == "empate":
            paragrafos.append(f"{g['variavel']}: IQR igual nos dois times ({_n(g['times'][TIMES_ANALISADOS[0]]['iqr'])}).")
            continue
        espalhado = [t for t in TIMES_ANALISADOS if t != concentrado][0]
        paragrafos.append(
            f"{g['variavel']}: {_curto(concentrado)} mais concentrado (IQR {_n(g['times'][concentrado]['iqr'])}) e "
            f"{_curto(espalhado)} mais espalhado ({_n(g['times'][espalhado]['iqr'])})."
        )
    paragrafos.append(_padrao_times(tabela, "iqr", "o mais concentrado"))
    secoes.append({"titulo": "Comparação entre os times", "paragrafos": paragrafos})

    relativo = sorted(
        tabela,
        key=lambda g: _media_times(g, "cv_robusto_iqr"),
        reverse=True,
    )
    ordem_cv = sorted(tabela, key=lambda g: _media_times(g, "cv_percentual"), reverse=True)
    mesma_ordem_topo = {g["variavel"] for g in relativo[:3]} & {g["variavel"] for g in ordem_cv[:3]}
    maior_assim = max(tabela, key=lambda g: _media_times(g, "assimetria", absoluto=True))
    secoes.append({
        "titulo": "Destaques do quadro-resumo",
        "paragrafos": [
            "Como o IQR está na unidade de cada variável, a comparação entre variáveis usa IQR/Mediana: "
            + ", ".join(f"{g['variavel']} {_n(_media_times(g, 'cv_robusto_iqr'))}%" for g in relativo) + ".",
            f"Entre as três mais dispersas pelo IQR/Mediana e pelo CV coincidem: "
            f"{', '.join(sorted(mesma_ordem_topo)) or 'nenhuma'} — "
            + ("CV e IQR contam a mesma história de dispersão." if len(mesma_ordem_topo) >= 2 else
               "as medidas divergem, sinal de que caudas e extremos pesam no CV."),
            f"A variável mais assimétrica, {maior_assim['variavel']} (|G1| médio "
            f"{_n(_media_times(maior_assim, 'assimetria', True))}), é onde a diferença entre CV e IQR/Mediana "
            "mais importa: o IQR descreve o jogo típico sem ser puxado pela cauda.",
        ],
    })
    return secoes
