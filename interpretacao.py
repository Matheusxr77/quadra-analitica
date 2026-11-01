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
    FAIXAS_CV,
    LIMITE_ASSIMETRIA_FORTE,
    LIMITE_SIMETRIA,
    MAPA_VARIAVEIS,
    MEDIA_MINIMA_CV,
    REAMOSTRAGENS_BOOTSTRAP,
    TIMES_ANALISADOS,
    calcular_tabela_descritiva,
    comparar_times,
    erro_padrao_g1,
    referencia_amplitude_iqr,
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


# --------------------------------------------------------------------------
# Utilidades de redação
# --------------------------------------------------------------------------

UNIDADE_CURTA = {
    "Pontos": ("ponto", "pontos"),
    "Rebotes": ("rebote", "rebotes"),
    "Assistências": ("assistência", "assistências"),
    "STL": ("roubo de bola", "roubos de bola"),
    "BLK": ("toco", "tocos"),
    "PF": ("falta", "faltas"),
    "FG3M": ("cesta de 3", "cestas de 3"),
}


def _time(time: str, maiuscula: bool = False) -> str:
    """'os Mavericks' — nomes de times da NBA concordam no plural."""
    return f"{'Os' if maiuscula else 'os'} {_curto(time)}"


def _dos(time: str) -> str:
    return f"dos {_curto(time)}"


def _v(valor: float | None) -> str:
    """Contagens inteiras sem casas decimais no texto corrido; demais com 2."""
    if valor is None:
        return "—"
    return _n(valor, 0) if float(valor).is_integer() else _n(valor)


def _un(variavel: str, valor: float) -> str:
    singular, plural = UNIDADE_CURTA[variavel]
    return singular if abs(valor) < 2 else plural


def _qtd(valor: float, variavel: str) -> str:
    return f"{_v(valor)} {_un(variavel, valor)}"


def _lista(itens: list[str]) -> str:
    itens = list(itens)
    if not itens:
        return ""
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _contrair(texto: str) -> str:
    """Contrações obrigatórias geradas pela montagem das frases ('por o jogo' → 'pelo jogo')."""
    for antes, depois in ((" por o jogo", " pelo jogo"), (" por os jogos", " pelos jogos"),
                          (" de o jogo", " do jogo"), (" em o jogo", " no jogo")):
        texto = texto.replace(antes, depois)
    return texto


def _secao(titulo: str, paragrafos: list[str], metodologia: list[str] | None = None) -> dict[str, Any]:
    """Seção de texto: `paragrafos` = interpretação (sempre com números); `metodologia` = método."""
    return {
        "titulo": titulo,
        "metodologia": [_contrair(m) for m in (metodologia or [])],
        "paragrafos": [_contrair(p) for p in paragrafos],
    }


def _jogo_outlier(variavel: str, o: dict[str, Any]) -> str:
    """'o jogo de 15 tocos contra DET (18/12/2025, com 1 prorrogação)'."""
    extra = ""
    if o.get("prorrogacoes"):
        extra = f", com {o['prorrogacoes']} prorrogaç{'ão' if o['prorrogacoes'] == 1 else 'ões'}"
    adversario = f" contra {o['adversario']}" if o.get("adversario") else ""
    return f"o jogo de {_qtd(o['valor'], variavel)}{adversario} ({o['data']}{extra})"


def _pp(valor: float) -> str:
    return f"{_n(valor)} {'ponto percentual' if abs(valor) < 2 else 'pontos percentuais'}"


def _erros_padrao(valor: float) -> str:
    return f"{_n(valor)} {'erro-padrão' if abs(valor) < 2 else 'erros-padrão'}"


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
            "erro_padrao_g1": erro_padrao_g1(item["n"]),
            "g1_em_erros_padrao": item["assimetria"] / erro_padrao_g1(item["n"]),
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
    pares = list(_pares(tabela))
    tamanhos = sorted({item["n"] for _, _, item in pares})
    ep = {n: erro_padrao_g1(n) for n in tamanhos}
    ep_ref = max(ep.values())
    fatores = " e ".join(_n(sqrt(n * (n - 1)) / (n - 2), 4) for n in tamanhos)
    secoes = [_secao(
        "Coeficiente e fórmula utilizada",
        [
            f"Cada time tem {' e '.join(str(n) for n in tamanhos)} jogos. Nesse tamanho o coeficiente de momento "
            f"de Pearson (g1) é viesado; o fator √(n(n−1))/(n−2) = {fatores} corrige esse viés. A versão "
            "ajustada é a coerente com o desvio padrão amostral (n − 1) usado no restante do projeto.",
            f"Incerteza: com esses n o erro-padrão do G1 é ≈ {_n(ep_ref)}. Um |G1| abaixo de ≈ "
            f"{_n(2 * ep_ref)} (2 erros-padrão) não se distingue de zero a 5%, e essa régua acompanha todas "
            "as leituras abaixo.",
        ],
        [
            "Coeficiente ajustado de Fisher-Pearson (G1), implementado por pandas.Series.skew — o mesmo valor "
            "de scipy.stats.skew(bias=False). Erro-padrão sob normalidade: √(6n(n−1) / ((n−2)(n+1)(n+3))).",
            "O coeficiente de Bowley, (Q3 + Q1 − 2·Mediana)/IQR, é exibido só como verificação robusta: usa "
            "apenas os quartis, não é afetado por jogos extremos, mas também ignora as caudas — por isso não "
            "substitui o G1.",
        ],
    )]

    # Direção
    total = len(pares)
    positivos = sum(1 for _, _, i in pares if i["assimetria"] > 0)
    perto_de_zero = sum(1 for _, _, i in pares if abs(i["assimetria"]) < LIMITE_SINAL_RELEVANTE)

    def direcao(i):
        if abs(i["assimetria"]) < LIMITE_SINAL_RELEVANTE:
            return f"{_n(i['assimetria'])} (≈ simétrica)"
        return f"{_n(i['assimetria'])} ({'à direita' if i['assimetria'] > 0 else 'à esquerda'})"

    por_variavel = "; ".join(
        f"{g['variavel']} — " + ", ".join(f"{_curto(t)} {direcao(g['times'][t])}" for t in TIMES_ANALISADOS)
        for g in tabela
    )
    claras = [
        f"{g['variavel']} {_dos(t)} (G1 = {_n(i['assimetria'])}, "
        f"{_erros_padrao(i['assimetria'] / erro_padrao_g1(i['n']))})"
        for g, t, i in pares if abs(i["assimetria"]) >= 2 * erro_padrao_g1(i["n"])
    ]
    secoes.append(_secao(
        "Direção (pelo sinal do coeficiente)",
        [
            f"{positivos} das {total} combinações variável × time têm G1 positivo e {total - positivos} negativo, "
            f"mas em {perto_de_zero} delas |G1| < {_n(LIMITE_SINAL_RELEVANTE)} e o sinal é ruído. Por variável: "
            f"{por_variavel}.",
            (f"Só {_lista(claras)} {'tem' if len(claras) == 1 else 'têm'} cauda que se distingue da simetria "
             "(mais de 2 erros-padrão); as demais direções são tendências fracas."
             if claras else
             f"Nenhuma combinação passa de 2 erros-padrão ({_n(2 * ep_ref)}): todas as direções são tendências fracas."),
        ],
        [
            "G1 > 0: cauda mais longa à direita (positiva); G1 < 0: cauda à esquerda (negativa). "
            f"Com |G1| < {_n(LIMITE_SINAL_RELEVANTE)} o sinal é tratado como ruído (≈ simétrica).",
        ],
    ))

    # Intensidade
    por_classe: dict[str, list] = {}
    for g, t, i in pares:
        por_classe.setdefault(i["intensidade_assimetria"], []).append((g, t, i))
    simetricas = len(por_classe.get("aproximadamente simétrica", []))
    moderadas = por_classe.get("moderada", [])
    fortes = por_classe.get("forte", [])
    detalhes = []
    for g, t, i in moderadas + fortes:
        z = i["assimetria"] / erro_padrao_g1(i["n"])
        texto = f"{g['variavel']} {_dos(t)} (G1 = {_n(i['assimetria'])}, {_erros_padrao(z)}"
        if z < 2:
            texto += ": no limite, pode ser simétrica"
        if i["quantidade_outliers"] and abs(i["assimetria_sem_outliers"]) < LIMITE_SIMETRIA:
            texto += (f"; cai para {_n(i['assimetria_sem_outliers'])} sem "
                      f"{_lista([_jogo_outlier(g['variavel'], o) for o in i['outliers_detalhe']])}")
        detalhes.append(texto + ")")
    secoes.append(_secao(
        "Intensidade da assimetria",
        [
            f"{simetricas} das {total} distribuições são aproximadamente simétricas, {len(moderadas)} "
            f"{'tem' if len(moderadas) == 1 else 'têm'} assimetria moderada e "
            + (f"{len(fortes)} forte." if fortes else "nenhuma é forte.")
            + (f" As moderadas: {_lista(detalhes)}." if detalhes else ""),
        ],
        [
            f"Critério de Bulmer (1979): |G1| < {_n(LIMITE_SIMETRIA, 1)} aproximadamente simétrica; "
            f"{_n(LIMITE_SIMETRIA, 1)} ≤ |G1| < {_n(LIMITE_ASSIMETRIA_FORTE, 1)} moderada; "
            f"|G1| ≥ {_n(LIMITE_ASSIMETRIA_FORTE, 1)} forte.",
        ],
    ))

    # Coeficiente × gráficos
    concordam, divergem = 0, []
    for g, t, i in pares:
        sinais = {_sinal(i["assimetria"]), _sinal(i["bowley"]), _sinal(i["media"] - i["mediana"])}
        rotulo = f"{g['variavel']} {_dos(t)}"
        mudou_classe = (
            abs(i["assimetria"]) >= LIMITE_SIMETRIA
            and abs(i["assimetria_sem_outliers"]) < LIMITE_SIMETRIA
        )
        if mudou_classe:
            divergem.append(
                f"{rotulo}: G1 = {_n(i['assimetria'])}, mas sem "
                f"{_lista([_jogo_outlier(g['variavel'], o) for o in i['outliers_detalhe']])} cai para "
                f"{_n(i['assimetria_sem_outliers'])}. No histograma isso aparece como uma barra isolada na cauda e "
                f"no boxplot como ponto fora do bigode, enquanto a caixa é simétrica (Bowley = {_n(i['bowley'])})."
            )
        elif abs(i["assimetria"]) >= LIMITE_SINAL_RELEVANTE and len(sinais - {0}) > 1:
            lado = [o for o in i["outliers_detalhe"] if (o["valor"] > i["mediana"]) == (i["assimetria"] > 0)]
            causa = (
                f" {_lista([_jogo_outlier(g['variavel'], o) for o in lado]).capitalize()} alongam essa cauda e "
                "explicam o sinal do G1." if lado else ""
            )
            divergem.append(
                f"{rotulo}: G1 = {_n(i['assimetria'])}, Bowley = {_n(i['bowley'])} e média − mediana = "
                f"{_n(i['media'] - i['mediana'])} apontam direções diferentes: o G1 pesa as caudas, enquanto "
                "Bowley e a posição da mediana descrevem o miolo, e os dois estão inclinados para lados opostos."
                + causa
            )
        else:
            concordam += 1
    secoes.append(_secao(
        "Confirmação visual: histograma com KDE e boxplot",
        [
            f"O coeficiente e os gráficos contam a mesma história em {concordam} de {total} casos "
            "(G1, Bowley e média − mediana com o mesmo sinal, ou G1 tão perto de zero que o sinal é ruído).",
            *divergem,
        ],
        [
            "No histograma, assimetria positiva aparece como cauda mais longa à direita da KDE; no boxplot, como "
            "mediana mais próxima de Q1 e bigode/outliers mais longos para cima (o inverso para negativa). "
            "Use os seletores abaixo para ver cada variável.",
        ],
    ))

    # Comparação entre variáveis e times
    ordem = sorted(tabela, key=lambda g: _media_times(g, "assimetria", absoluto=True), reverse=True)
    mesma = [g for g in tabela if len({_sinal(g["times"][t]["assimetria"]) for t in TIMES_ANALISADOS}) == 1]
    opostas = [g for g in tabela if g not in mesma]
    maior_oposta = max(
        ((abs(g["times"][t]["assimetria"]), g, t) for g in opostas for t in TIMES_ANALISADOS),
        default=None, key=lambda c: c[0],
    )
    paragrafos = [
        "Ordem por |G1| médio dos dois times: "
        + ", ".join(f"{g['variavel']} ({_n(_media_times(g, 'assimetria', True))})" for g in ordem)
        + f". As mais assimétricas são {ordem[0]['variavel']} e {ordem[1]['variavel']}, justamente as de "
        "contagens pequenas (tocos e roubos de bola): a maioria dos jogos fica perto da média e poucos jogos "
        "concentram muitas dessas ações defensivas, o que cria a cauda à direita.",
    ]
    if mesma or opostas:
        texto = (f"A direção se repete nos dois times em {_lista([g['variavel'] for g in mesma])}" if mesma
                 else "Em nenhuma variável a direção se repete nos dois times")
        if opostas and maior_oposta:
            texto += (
                f"; em {_lista([g['variavel'] for g in opostas])} os sinais se opõem, mas o maior |G1| entre elas "
                f"é {_n(maior_oposta[0])} ({maior_oposta[1]['variavel']} {_dos(maior_oposta[2])}), abaixo de "
                f"2 erros-padrão ({_n(2 * ep_ref)}): diferença de formato dentro do ruído amostral."
            )
        paragrafos.append(texto + ("" if opostas else "."))
    secoes.append(_secao("Comparação entre variáveis e entre times", paragrafos))

    # Implicação prática
    distancia = [
        (abs(i["media"] - i["mediana"]) / i["desvio_padrao"], g, t, i)
        for g, t, i in pares if i["desvio_padrao"] > 0
    ]
    maior = max(distancia, key=lambda c: c[0])
    paragrafos = [
        f"A maior distância entre média e mediana está em {maior[1]['variavel']} {_dos(maior[2])}: "
        f"{_qtd(abs(maior[3]['media'] - maior[3]['mediana']), maior[1]['variavel'])} "
        f"({_n(maior[0])} desvio padrão), com G1 = {_n(maior[3]['assimetria'])}"
        + (". Não é cauda longa: em contagens pequenas a mediana anda de 1 em 1 e se afasta da média sem que a "
           "distribuição seja assimétrica." if abs(maior[3]["assimetria"]) < LIMITE_SIMETRIA else
           ": aqui a assimetria puxa a média e a mediana descreve melhor o jogo típico."),
    ]
    for g, t, i in pares:
        if abs(i["assimetria"]) < LIMITE_SIMETRIA:
            continue
        gap = abs(i["media"] - i["mediana"])
        relativo = gap / i["desvio_padrao"]
        if relativo < 0.2:
            leitura = (f"diferença de só {_qtd(gap, g['variavel'])} ({_n(relativo)} DP): média ou mediana "
                       "descrevem o mesmo jogo típico")
        else:
            leitura = (f"diferença de {_qtd(gap, g['variavel'])} ({_n(relativo)} DP): a mediana representa "
                       "melhor o jogo típico")
        if i["quantidade_outliers"]:
            leitura += "; métodos robustos só fazem diferença se os jogos extremos forem mantidos"
        paragrafos.append(
            f"{g['variavel']} {_dos(t)} (G1 = {_n(i['assimetria'])}): média {_v(i['media'])} e mediana "
            f"{_v(i['mediana'])} — {leitura}."
        )
    maior_g1 = max(abs(i["assimetria"]) for _, _, i in pares)
    paragrafos.append(
        f"O maior |G1| é {_n(maior_g1)}: "
        + ("nenhuma variável atinge assimetria forte (|G1| ≥ 1), então a transformação log(x + 1) não é necessária; "
           "mediana e IQR bastam como alternativa robusta." if maior_g1 < LIMITE_ASSIMETRIA_FORTE else
           "há assimetria forte, e log(x + 1) (há jogos com zero) é indicado antes de métodos que supõem normalidade.")
    )
    secoes.append(_secao("Implicação prática: média ou mediana?", paragrafos))
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


def _classe_cv_item(item: dict[str, Any]) -> str:
    """Faixas de CV; em contagens pequenas, a régua é o piso de Poisson."""
    if item["media"] < MEDIA_MINIMA_CV and item["cv_poisson_ref"]:
        excesso = item["cv_percentual"] - item["cv_poisson_ref"]
        return "compatível com a escala" if excesso < 10 else "acima do piso da escala"
    return _classe_cv(item["cv_percentual"])


LEITURA_CV = {
    "Pontos": ("o ataque produz de forma estável de um jogo para outro",
               "a produção ofensiva oscila bastante entre jogos"),
    "Rebotes": ("a disputa de rebotes rende um volume parecido em quase todo jogo",
                "o volume de rebotes depende muito do jogo"),
    "Assistências": ("a circulação de bola varia, mas sem extremos",
                     "a criação de jogadas coletivas muda bastante de jogo para jogo"),
    "PF": ("o número de faltas varia de forma moderada, como esperado com arbitragens e adversários diferentes",
           "o número de faltas muda muito conforme o jogo"),
    "FG3M": ("a produção de três é relativamente previsível",
             "a bola de três depende das noites de arremesso, com jogos muito bons e muito ruins"),
}


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
            "classe": _classe_cv_item(item),
            "cautela": item["media"] < MEDIA_MINIMA_CV,
            "cv_poisson_ref": item["cv_poisson_ref"],
            "cv_robusto_iqr": item["cv_robusto_iqr"],
            "g1": item["assimetria"],
        }
        for grupo, time, item in _pares(tabela)
    ]
    comparacoes = {g["variavel"]: comparar_times(dados, g["variavel"]) for g in tabela}
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, "cv_percentual"),
        "linhas": linhas,
        "comparacoes": comparacoes,
        "secoes": _textos_cv(tabela, comparacoes),
        "faixas": list(FAIXAS_CV),
        "media_minima": MEDIA_MINIMA_CV,
    }


def _textos_cv(tabela, comparacoes) -> list[dict[str, Any]]:
    a, b = TIMES_ANALISADOS
    pares = list(_pares(tabela))
    secoes = [_secao("Fórmula e convenções", [], [
        "CV = s / x̄ × 100, com s = desvio padrão amostral (divisor n − 1) e x̄ = média aritmética. O resultado "
        "é apresentado em percentual (%), com 2 casas — mesma convenção do desvio padrão e da variância da "
        "tabela descritiva.",
    ])]

    menor_media = min(pares, key=lambda c: c[2]["media"])
    pequenas = [(g, t, i) for g, t, i in pares if i["media"] < MEDIA_MINIMA_CV]
    paragrafos = [
        f"As 7 variáveis são contagens com zero absoluto e todas as médias são positivas; a menor é "
        f"{_qtd(menor_media[2]['media'], menor_media[0]['variavel'])} por jogo ({menor_media[0]['variavel']} "
        f"{_dos(menor_media[1])}). O CV é aplicável, com a ressalva das médias pequenas.",
    ]
    if pequenas:
        itens = []
        for g, t, i in pequenas:
            excesso = i["cv_percentual"] - i["cv_poisson_ref"]
            itens.append(
                f"{g['variavel']} {_dos(t)} {_n(i['cv_percentual'])}% contra piso de {_n(i['cv_poisson_ref'])}% "
                + (f"(+{_n(excesso)})" if excesso > 0 else "(abaixo do piso)")
            )
        maior_excesso = max(i["cv_percentual"] - i["cv_poisson_ref"] for _, _, i in pequenas)
        paragrafos.append(
            f"{_lista(sorted({g['variavel'] for g, _, _ in pequenas}))} têm média abaixo de "
            f"{_n(MEDIA_MINIMA_CV, 0)} por jogo, e o CV delas fica no piso esperado só pela escala ou até "
            f"{_n(maior_excesso)} pontos acima: {_lista(itens)}. O CV alto dessas variáveis é efeito do tamanho "
            "das contagens, não irregularidade dos times — por isso elas não são classificadas pelas faixas de "
            "15% e 30%."
        )
    secoes.append(_secao("Condição de validade", paragrafos, [
        "Escala de razão: as variáveis são contagens por jogo com zero absoluto (0 tocos = nenhum toco), então "
        "razões entre valores fazem sentido.",
        f"Critério de cautela: média < {_n(MEDIA_MINIMA_CV, 0)} por jogo. Com média pequena, o denominador do CV "
        "é pequeno e qualquer variação de 1 ou 2 unidades vira um percentual alto. Em contagens do tipo Poisson "
        "a variância é próxima da média, logo CV ≈ 100/√média: um piso que depende só da escala.",
    ]))

    paragrafos = []
    for g in tabela:
        itens = {t: g["times"][t] for t in TIMES_ANALISADOS}
        classes = {t: _classe_cv_item(i) for t, i in itens.items()}
        partes = "; ".join(f"{_curto(t)} {_n(i['cv_percentual'])}% ({classes[t]})" for t, i in itens.items())
        if g["variavel"] in LEITURA_CV:
            estavel, instavel = LEITURA_CV[g["variavel"]]
            mais = max(itens, key=lambda t: itens[t]["cv_percentual"])
            i = itens[mais]
            leitura = instavel if classes[mais] == "irregular" else estavel
            paragrafos.append(
                f"{g['variavel']}: {partes}. Cerca de 2 em cada 3 jogos {_dos(mais)} ficam entre "
                f"{_v(i['media'] - i['desvio_padrao'])} e {_v(i['media'] + i['desvio_padrao'])} "
                f"{_un(g['variavel'], i['media'])} (média ± 1 DP): {leitura}."
            )
        else:
            paragrafos.append(
                f"{g['variavel']}: {partes}. Com médias de {_v(itens[a]['media'])} e {_v(itens[b]['media'])} por "
                "jogo, a dispersão é a esperada para contagens desse tamanho."
            )
    secoes.append(_secao("Interpretação prática", paragrafos, [
        f"Faixas adotadas: CV < {_n(FAIXAS_CV[0], 0)}% consistente; {_n(FAIXAS_CV[0], 0)}–{_n(FAIXAS_CV[1], 0)}% "
        f"variabilidade moderada; > {_n(FAIXAS_CV[1], 0)}% irregular. Para médias abaixo de "
        f"{_n(MEDIA_MINIMA_CV, 0)}, a referência é o piso de Poisson. O intervalo média ± 1 DP contém cerca de 2 "
        "em cada 3 jogos quando a distribuição é próxima da normal.",
    ]))

    ordem = sorted(tabela, key=lambda g: _media_times(g, "cv_percentual"), reverse=True)
    grandes = [g for g in ordem if _media_times(g, "media") >= MEDIA_MINIMA_CV]
    maior_dp = max(tabela, key=lambda g: _media_times(g, "desvio_padrao"))
    menor_dp = min(tabela, key=lambda g: _media_times(g, "desvio_padrao"))
    secoes.append(_secao("Comparação entre variáveis de escalas diferentes", [
        "Ordem por CV médio dos dois times: "
        + ", ".join(f"{g['variavel']} ({_n(_media_times(g, 'cv_percentual'))}%)" for g in ordem)
        + f". {ordem[0]['variavel']} e {ordem[1]['variavel']} lideram, mas pelo efeito da escala visto acima; "
        f"entre as variáveis de média alta, a mais dispersa é {grandes[0]['variavel']} "
        f"({_n(_media_times(grandes[0], 'cv_percentual'))}%) e as mais estáveis são {grandes[-1]['variavel']} "
        f"({_n(_media_times(grandes[-1], 'cv_percentual'))}%) e {grandes[-2]['variavel']} "
        f"({_n(_media_times(grandes[-2], 'cv_percentual'))}%).",
        f"O desvio padrão bruto levaria à conclusão errada: {maior_dp['variavel']} tem o maior DP "
        f"({_n(_media_times(maior_dp, 'desvio_padrao'))} {maior_dp['unidade']}) e {menor_dp['variavel']} o menor "
        f"({_n(_media_times(menor_dp, 'desvio_padrao'))} {menor_dp['unidade']}), mas o DP está na unidade de cada "
        "variável e cresce com a escala. O CV divide pelo nível médio, é adimensional e permite a comparação.",
    ]))

    relevantes = [g for g in tabela if comparacoes[g["variavel"]]["cv"]["relevante"]]
    nao_relevantes = [g for g in tabela if g not in relevantes]
    paragrafos = []
    for g in relevantes:
        c = comparacoes[g["variavel"]]["cv"]
        regular = a if c["diferenca"] < 0 else b
        irregular = b if regular == a else a
        paragrafos.append(
            f"{g['variavel']}: {_time(regular)} são mais regulares ({_n(g['times'][regular]['cv_percentual'])}%) "
            f"que {_time(irregular)} ({_n(g['times'][irregular]['cv_percentual'])}%); a diferença de "
            f"{_pp(abs(c['diferenca']))} tem IC 95% de {_n(abs(c['ic95'][0]) if c['diferenca'] > 0 else abs(c['ic95'][1]))} "
            f"a {_n(abs(c['ic95'][1]) if c['diferenca'] > 0 else abs(c['ic95'][0]))} e não se explica pelo acaso."
            + (f" Na prática, para {_time(irregular)}, {LEITURA_CV[g['variavel']][1]}."
               if g["variavel"] in LEITURA_CV else "")
        )
    if nao_relevantes:
        exemplo = min(nao_relevantes, key=lambda g: abs(comparacoes[g["variavel"]]["cv"]["diferenca"]))
        ce = comparacoes[exemplo["variavel"]]["cv"]
        menores = {t: sum(1 for g in tabela if _vencedor(g, "cv_percentual") == t) for t in TIMES_ANALISADOS}
        paragrafos.append(
            f"Nas outras {len(nao_relevantes)} variáveis ({_lista([g['variavel'] for g in nao_relevantes])}) o IC 95% "
            f"da diferença de CV contém zero — por exemplo, {exemplo['variavel']}: diferença de "
            f"{_pp(abs(ce['diferenca']))}, IC de {_n(ce['ic95'][0])} a {_n(ce['ic95'][1])}. Os Pacers têm o CV "
            f"menor em {menores[b]} de 7 variáveis e os Mavericks em {menores[a]}, mas, fora "
            f"{_lista([g['variavel'] for g in relevantes]) or 'nenhuma'}, essas diferenças não permitem dizer que um "
            "time é mais regular que o outro."
        )
    secoes.append(_secao("Homogeneidade entre os times", paragrafos, [
        f"Diferença de CV entre os times com intervalo de confiança de 95% por bootstrap ({REAMOSTRAGENS_BOOTSTRAP} "
        "reamostragens dos jogos de cada time, semente fixa). Só se declara um time mais regular quando o "
        "intervalo não contém zero.",
    ]))

    paragrafos = []
    for g, t, i in pares:
        if abs(i["assimetria"]) < LIMITE_SIMETRIA or not i["cv_percentual"]:
            continue
        razao = i["cv_robusto_iqr"] / i["cv_percentual"]
        if abs(razao / 1.35 - 1) <= 0.15:
            leitura = ("quase a razão esperada numa normal: CV e IQR/Mediana contam a mesma história e o CV é "
                       "adequado")
        elif razao > 1.35:
            leitura = (f"acima do esperado: com mediana {_v(i['mediana'])} e IQR {_v(i['iqr'])} em valores "
                       "inteiros, a medida robusta fica grosseira; o CV, puxado pela cauda, segue informativo se o "
                       "jogo extremo for lembrado")
        else:
            leitura = "abaixo do esperado: a cauda infla o CV e a medida robusta descreve melhor a dispersão típica"
        paragrafos.append(
            f"{g['variavel']} {_dos(t)}: G1 = {_n(i['assimetria'])}, CV = {_n(i['cv_percentual'])}%, IQR/Mediana = "
            f"{_n(i['cv_robusto_iqr'])}% (razão {_n(razao)}), {leitura}."
        )
    if not paragrafos:
        paragrafos.append(f"Nenhuma combinação tem |G1| ≥ {_n(LIMITE_SIMETRIA)}: o CV clássico é adequado em todas.")
    secoes.append(_secao("CV × desvio padrão × assimetria", paragrafos, [
        "O CV usa média e desvio padrão, sensíveis a caudas longas. A alternativa robusta é IQR/Mediana × 100. "
        "Numa normal, IQR/Mediana ≈ 1,35 × CV; razões muito diferentes indicam que extremos ou o formato pesam "
        "no CV.",
    ]))

    celulas = [(i["cv_percentual"], g, t) for g, t, i in pares]
    maior, menor = max(celulas, key=lambda c: c[0]), min(celulas, key=lambda c: c[0])
    gap = max(tabela, key=lambda g: abs(comparacoes[g["variavel"]]["cv"]["diferenca"]))
    cg = comparacoes[gap["variavel"]]["cv"]
    secoes.append(_secao("Destaques do quadro-resumo", [
        f"Maior CV: {maior[1]['variavel']} {_dos(maior[2])}, {_n(maior[0])}% (efeito de escala); menor CV: "
        f"{menor[1]['variavel']} {_dos(menor[2])}, {_n(menor[0])}%.",
        f"A maior diferença entre os times está em {gap['variavel']} ({_n(abs(cg['diferenca']))} pontos percentuais) "
        + ("e é a única que se distingue do acaso: " if cg["relevante"] else "mas mesmo ela está dentro do acaso: ")
        + f"{_time(a)} fazem {_v(gap['times'][a]['media'])} {_un(gap['variavel'], gap['times'][a]['media'])} por "
        f"jogo com CV de {_n(gap['times'][a]['cv_percentual'])}%, e {_time(b)}, {_v(gap['times'][b]['media'])} com "
        f"{_n(gap['times'][b]['cv_percentual'])}%.",
    ]))
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
    comparacoes = {g["variavel"]: comparar_times(dados, g["variavel"]) for g in tabela}
    referencias = {str(n): referencia_amplitude_iqr(n) for n in sorted({l["n"] for l in (i for _, _, i in _pares(tabela))})}
    return {
        "times": TIMES_ANALISADOS,
        "quadro": _quadro(tabela, "iqr"),
        "linhas": linhas,
        "comparacoes": comparacoes,
        "referencia_amplitude_iqr": referencias,
        "secoes": _textos_iqr(dados, tabela, comparacoes, referencias),
    }


def _textos_iqr(dados: pd.DataFrame, tabela, comparacoes, referencias) -> list[dict[str, Any]]:
    a, b = TIMES_ANALISADOS
    pares = list(_pares(tabela))
    secoes = [
        _secao("Fórmula e método dos quartis", [], [
            "IQR = Q3 − Q1. Os quartis são calculados por interpolação linear entre as estatísticas de ordem "
            "(método padrão de numpy/pandas, tipo 7 de Hyndman & Fan): posição h = (n − 1)·p + 1 nos dados "
            "ordenados. É o mesmo método da tabela descritiva e do boxplot, portanto os três mostram os mesmos "
            "Q1, Q3 e limites.",
        ]),
        _secao("Q1, Q3 e IQR lado a lado", [], [
            "A tabela abaixo mostra Q1, Q3 e IQR por variável e por time, junto da amplitude e do desvio padrão "
            "usados nas comparações seguintes.",
        ]),
    ]

    paragrafos = []
    for g in tabela:
        ia, ib = g["times"][a], g["times"][b]
        inicio, fim = max(ia["q1"], ib["q1"]), min(ia["q3"], ib["q3"])
        diferenca_mediana = ia["mediana"] - ib["mediana"]
        texto = (
            f"{g['variavel']}: os 50% centrais dos jogos {_dos(a)} ficam entre {_v(ia['q1'])} e {_v(ia['q3'])} "
            f"(IQR {_v(ia['iqr'])}) e os {_dos(b)}, entre {_v(ib['q1'])} e {_v(ib['q3'])} (IQR {_v(ib['iqr'])})."
        )
        if abs(diferenca_mediana) >= 0.5 * min(ia["iqr"], ib["iqr"]):
            acima = a if diferenca_mediana > 0 else b
            texto += (
                f" As faixas se sobrepõem só de {_v(inicio)} a {_v(fim)}: {_time(acima)} jogam num patamar "
                f"{_qtd(abs(diferenca_mediana), g['variavel'])} acima na mediana — a diferença é de nível, não de "
                "dispersão."
            )
        else:
            texto += (
                f" As faixas se sobrepõem de {_v(inicio)} a {_v(fim)} e as medianas são iguais: o jogo típico dos "
                "dois times é o mesmo." if diferenca_mediana == 0 else
                f" As faixas se sobrepõem de {_v(inicio)} a {_v(fim)} e as medianas diferem em "
                f"{_qtd(abs(diferenca_mediana), g['variavel'])}: como a sobreposição é grande, os times se "
                "distinguem pouco no jogo típico."
            )
        paragrafos.append(texto)
    secoes.append(_secao("Interpretação prática", paragrafos, [
        "O IQR é a largura da faixa que contém os 50% centrais dos jogos: IQR baixo = time concentrado em torno "
        "do seu típico; IQR alto = desempenho central espalhado.",
    ]))

    ref = referencias[str(max(int(n) for n in referencias))]
    esticadas = [(g, t, i) for g, t, i in pares
                 if i["razao_amplitude_iqr"] and i["razao_amplitude_iqr"] > referencias[str(i["n"])]["p95"]]
    acima_mediana = [(g, t, i) for g, t, i in pares
                     if i["razao_amplitude_iqr"] and referencias[str(i["n"])]["mediana"] < i["razao_amplitude_iqr"]
                     <= referencias[str(i["n"])]["p95"]]
    paragrafos = [
        f"Em amostras normais com n = {max(int(n) for n in referencias)}, a razão amplitude/IQR tem mediana "
        f"{_n(ref['mediana'])} e só passa de {_n(ref['p95'])} em 5% dos casos. Acima disso a amplitude está "
        "esticada por jogos extremos.",
    ]
    for g, t, i in sorted(esticadas, key=lambda c: c[2]["razao_amplitude_iqr"], reverse=True):
        paragrafos.append(
            f"{g['variavel']} {_dos(t)}: amplitude de {_qtd(i['amplitude'], g['variavel'])}, "
            f"{_n(i['razao_amplitude_iqr'])} vezes o IQR ({_v(i['iqr'])}) — acima da referência, esticada por "
            f"{_lista([_jogo_outlier(g['variavel'], o) for o in i['outliers_detalhe']]) or 'caudas longas'}."
        )
    paragrafos.append(
        (f"Outras {len(acima_mediana)} combinações ficam acima da mediana da referência mas abaixo de "
         f"{_n(ref['p95'])} (a maior é {_n(max(i['razao_amplitude_iqr'] for _, _, i in acima_mediana))}): amplitude "
         "um pouco larga, dentro do que o acaso produz com esse n."
         if acima_mediana else
         f"Nas demais combinações a razão fica abaixo de {_n(ref['mediana'])}: a amplitude acompanha o miolo.")
    )
    secoes.append(_secao("IQR × amplitude", paragrafos, [
        "A amplitude depende só do mínimo e do máximo; o IQR ignora os 25% de cada ponta. A referência vem de "
        "4.000 amostras normais simuladas com o mesmo n (semente fixa).",
    ]))

    inflados = [(g, t, i) for g, t, i in pares
                if i["quantidade_outliers"] and i["desvio_sem_outliers"] < i["desvio_padrao"]]
    paragrafos = []
    iqr_estavel = 0
    for g, t, i in inflados:
        queda_dp = (1 - i["desvio_sem_outliers"] / i["desvio_padrao"]) * 100
        variacao_iqr = (i["iqr_sem_outliers"] / i["iqr"] - 1) * 100 if i["iqr"] else 0.0
        iqr_estavel += abs(variacao_iqr) < 1e-9
        efeito_iqr = (
            "o IQR não muda" if abs(variacao_iqr) < 1e-9
            else f"o IQR vai de {_v(i['iqr'])} para {_v(i['iqr_sem_outliers'])} ({'+' if variacao_iqr > 0 else '−'}"
                 f"{_n(abs(variacao_iqr))}%)"
        )
        veredito = (
            f"DP/σ robusto = {_n(i['razao_dp_sigma_robusto'])} > {_n(LIMITE_DP_INFLADO)}: DP inflado pelas caudas"
            if i["razao_dp_sigma_robusto"] > LIMITE_DP_INFLADO else
            f"mesmo assim DP/σ robusto = {_n(i['razao_dp_sigma_robusto'])} ≤ {_n(LIMITE_DP_INFLADO)}: o DP não está "
            "inflado no conjunto, só sensível "
            + ("ao jogo extremo" if i["quantidade_outliers"] == 1 else "aos jogos extremos")
        )
        paragrafos.append(
            f"{g['variavel']} {_dos(t)}: o DP cai de {_n(i['desvio_padrao'])} para {_n(i['desvio_sem_outliers'])} "
            f"(−{_n(queda_dp)}%) sem {'o outlier' if i['quantidade_outliers'] == 1 else 'os ' + str(i['quantidade_outliers']) + ' outliers'}, enquanto "
            f"{efeito_iqr}; {veredito}."
        )
    if inflados:
        excecoes = [f"{g['variavel']} {_dos(t)}" for g, t, i in inflados
                    if abs(i["iqr_sem_outliers"] - i["iqr"]) > 1e-9]
        paragrafos.append(
            f"Em {iqr_estavel} dos {len(inflados)} casos o IQR não muda quando os outliers saem, enquanto o DP cai: "
            "evidência de que o IQR é a medida robusta."
            + (f" A exceção é {_lista(excecoes)}, em que o IQR também se move, porque ao retirar jogos os quartis são "
               "recalculados sobre menos valores e um dos outliers fica perto do Q1." if excecoes else "")
        )
    else:
        paragrafos.append("Nenhuma variável tem outliers que inflem o desvio padrão (0 casos).")
    secoes.append(_secao("IQR × desvio padrão", paragrafos, [
        "σ robusto = IQR/1,349 (o DP que uma normal com aquele IQR teria). DP e IQR são recalculados sem os "
        f"outliers de Tukey; DP/σ robusto > {_n(LIMITE_DP_INFLADO)} indica DP inflado pelas caudas.",
    ]))

    divergencias = []
    for g, t, i in pares:
        serie = dados.loc[dados["TEAM_NAME"] == t, MAPA_VARIAVEIS[g["variavel"]]].dropna()
        fora = sorted(float(v) for v in serie[(serie < i["limite_inferior"]) | (serie > i["limite_superior"])])
        if fora != i["outliers"]:
            divergencias.append(f"{g['variavel']} {_dos(t)}")
    total_15 = sum(i["quantidade_outliers"] for _, _, i in pares)
    total_3 = sum(i["quantidade_outliers_3iqr"] for _, _, i in pares)
    com_prorrogacao = [(g, o) for g, _, i in pares for o in i["outliers_detalhe"] if o.get("prorrogacoes")]
    secoes.append(_secao("IQR e a regra de outliers", [
        f"Com k = 1,5 há {total_15} outliers nas 7 variáveis dos dois times; com k = 3, {total_3} — nenhum jogo é "
        f"extremo a ponto de sugerir erro de registro. {len(com_prorrogacao)} dos {total_15} são jogos com "
        "prorrogação"
        + (f" ({_lista([g['variavel'] + ' ' + _v(o['valor']) for g, o in com_prorrogacao])})" if com_prorrogacao else "")
        + ", em que os minutos extras explicam parte do valor.",
        f"A recontagem direta na base, com os limites da tabela, encontrou {total_15} outliers "
        + (f"e divergiu em {_lista(divergencias)}." if divergencias else
           "— os mesmos do boxplot. Como os dois usam os mesmos quartis calculados no servidor, essa conferência "
           "só detectaria um erro de implementação."),
    ], [
        "Regra adotada: k = 1,5 (Tukey). Limites: Q1 − 1,5×IQR e Q3 + 1,5×IQR, recalculados na tabela abaixo. "
        "k = 3 marcaria só valores 'extremos' e é mostrado para comparação.",
        "O boxplot recebe Q1, Q3 e limites prontos do servidor em vez de recalculá-los no navegador, para que "
        "gráfico e tabela usem o mesmo método de quartis.",
    ]))

    maior = max(tabela, key=lambda g: abs(comparacoes[g["variavel"]]["iqr"]["diferenca"]))
    cm = comparacoes[maior["variavel"]]["iqr"]
    relevantes = [g for g in tabela if comparacoes[g["variavel"]]["iqr"]["relevante"]]
    paragrafos = [
        (f"A diferença de IQR entre os times se distingue do acaso em {_lista([g['variavel'] for g in relevantes])}."
         if relevantes else
         f"Nenhuma diferença de IQR entre os times se distingue do acaso: a maior é a de {maior['variavel']} "
         f"({_v(abs(cm['diferenca']))}, IC 95% de {_n(cm['ic95'][0])} a {_n(cm['ic95'][1])}). Com valores inteiros "
         "e ≈ 75 jogos, diferenças de 1 unidade no IQR são comuns só por acaso.")
    ]
    divergentes = []
    for g in tabela:
        venc_cv, venc_iqr = _vencedor(g, "cv_percentual"), _vencedor(g, "iqr")
        if "empate" not in (venc_cv, venc_iqr) and venc_cv != venc_iqr:
            divergentes.append((g, venc_cv, venc_iqr))
    for g, venc_cv, venc_iqr in divergentes:
        maior_media = a if g["times"][a]["media"] > g["times"][b]["media"] else b
        paragrafos.append(
            f"{g['variavel']}: pelo IQR {_time(venc_iqr)} são mais concentrados ({_v(g['times'][venc_iqr]['iqr'])} "
            f"contra {_v(g['times'][venc_cv]['iqr'])}); pelo CV, {_time(venc_cv)} "
            f"({_n(g['times'][venc_cv]['cv_percentual'])}% contra {_n(g['times'][venc_iqr]['cv_percentual'])}%). Não é contradição: o CV divide pela média, e "
            f"{_time(maior_media)} têm média {_qtd(abs(g['times'][a]['media'] - g['times'][b]['media']), g['variavel'])} "
            "maior; além disso o CV usa o DP, que pesa as caudas, e o IQR olha só o miolo. Como nenhuma das duas "
            "diferenças é significativa, a leitura é de regularidade equivalente."
        )
    secoes.append(_secao("Comparação entre os times", paragrafos, [
        f"Diferença de IQR com IC 95% por bootstrap ({REAMOSTRAGENS_BOOTSTRAP} reamostragens, semente fixa); "
        "um time só é declarado mais concentrado quando o intervalo não contém zero.",
    ]))

    relativo = sorted(tabela, key=lambda g: _media_times(g, "cv_robusto_iqr"), reverse=True)
    ordem_cv = sorted(tabela, key=lambda g: _media_times(g, "cv_percentual"), reverse=True)
    comuns = [g["variavel"] for g in relativo[:3] if g["variavel"] in {x["variavel"] for x in ordem_cv[:3]}]
    assimetricas = [(g, t, i) for g, t, i in pares if abs(i["assimetria"]) >= LIMITE_SIMETRIA]
    paragrafos = [
        "Comparando variáveis pelo IQR/Mediana (o IQR está na unidade de cada uma): "
        + ", ".join(f"{g['variavel']} {_n(_media_times(g, 'cv_robusto_iqr'))}%" for g in relativo)
        + f". As três mais dispersas coincidem com as do CV em {len(comuns)} de 3 ({_lista(comuns)}): as duas "
        "medidas contam a mesma história de dispersão.",
    ]
    for g, t, i in assimetricas:
        paragrafos.append(
            f"{g['variavel']} {_dos(t)} (G1 = {_n(i['assimetria'])}): IQR/Mediana de {_n(i['cv_robusto_iqr'])}% contra "
            f"CV de {_n(i['cv_percentual'])}%. O IQR ({_v(i['iqr'])}) descreve o jogo típico sem ser puxado "
            + (f"por {_lista([_jogo_outlier(g['variavel'], o) for o in i['outliers_detalhe']])}."
               if i["outliers_detalhe"] else "pela cauda direita.")
        )
    secoes.append(_secao("Destaques do quadro-resumo", paragrafos))
    return secoes


# --------------------------------------------------------------------------
# Comparativo: texto da variável e do time selecionados
# --------------------------------------------------------------------------

def _paragrafos_time(variavel: str, unidade: str, time: str, i: dict[str, Any]) -> list[str]:
    nome = _time(time, True) if time != "Todos" else "Nos dois times juntos, os jogos"
    sujeito_verbo = f"{nome} têm" if time != "Todos" else nome + " têm"
    gap = i["media"] - i["mediana"]
    relativo = gap / i["desvio_padrao"] if i["desvio_padrao"] else 0.0
    if i["amodal"]:
        moda = "não há moda (nenhum valor se repete)"
    elif len(i["modas"]) > 1:
        tipo = "bimodal" if len(i["modas"]) == 2 else "multimodal"
        moda = f"a distribuição é {tipo} (modas {_lista([_v(m) for m in i['modas']])})"
    else:
        moda = f"a moda é {_qtd(i['modas'][0], variavel)}"
    if abs(relativo) < 0.1:
        leitura = "média e mediana descrevem o mesmo jogo típico"
    elif i["media"] < MEDIA_MINIMA_CV and abs(i["assimetria"]) < LIMITE_SIMETRIA:
        leitura = ("não é cauda longa (G1 = " + _n(i["assimetria"]) + "), e sim efeito de contagens pequenas, em que "
                   "a mediana anda de 1 em 1 e se afasta da média sem que a distribuição seja assimétrica")
    elif relativo > 0:
        leitura = "alguns jogos altos puxam a média para cima; o jogo típico fica mais perto da mediana"
    else:
        leitura = "alguns jogos baixos puxam a média para baixo; o jogo típico fica mais perto da mediana"
    central = (
        f"{sujeito_verbo} média de {_qtd(i['media'], variavel)} por jogo e mediana de {_v(i['mediana'])}; {moda}. "
        f"A média fica {_qtd(abs(gap), variavel)} {'acima' if gap >= 0 else 'abaixo'} da mediana "
        f"({_n(abs(relativo))} DP): {leitura}."
    )
    razao = i["razao_amplitude_iqr"]
    ref = referencia_amplitude_iqr(i["n"])
    dispersao = (
        f"Os jogos vão de {_v(i['minimo'])} a {_v(i['maximo'])} (amplitude {_v(i['amplitude'])}); a metade central "
        f"fica entre {_v(i['q1'])} e {_v(i['q3'])} (IQR {_v(i['iqr'])}), com DP de {_n(i['desvio_padrao'])} e "
        f"variância de {_n(i['variancia'])}, na unidade ao quadrado. "
        + (f"A amplitude é {_n(razao)} vezes o IQR, acima do esperado ao acaso ({_n(ref['p95'])}): poucos jogos "
           "esticam as pontas." if razao and razao > ref["p95"] else
           f"A amplitude é {_n(razao)} vezes o IQR, dentro do esperado para {i['n']} jogos.")
    )
    posicao = (i["mediana"] - i["q1"]) / i["iqr"] if i["iqr"] else 0.5
    caixa = ("no meio da caixa" if 0.4 <= posicao <= 0.6 else
             "mais perto de Q1 (cauda para cima)" if posicao < 0.4 else "mais perto de Q3 (cauda para baixo)")
    if i["outliers_detalhe"]:
        com_ot = sum(1 for o in i["outliers_detalhe"] if o.get("prorrogacoes"))
        outliers = (
            f"O boxplot marca {_plural(i['quantidade_outliers'], 'outlier', 'outliers')}: "
            f"{_lista([_jogo_outlier(variavel, o) for o in i['outliers_detalhe']])}"
            + ((f" — {com_ot} deles com prorrogação" if i["quantidade_outliers"] > 1 else "")
               + "; os minutos extras explicam parte do valor" if com_ot else "")
            + f". Os bigodes vão de {_v(i['bigode_inferior'])} a {_v(i['bigode_superior'])} e a mediana fica {caixa}."
        )
    else:
        outliers = (
            f"Nenhum jogo fica fora dos limites de Tukey ({_n(i['limite_inferior'])} a {_n(i['limite_superior'])}); "
            f"os bigodes vão de {_v(i['bigode_inferior'])} a {_v(i['bigode_superior'])} e a mediana fica {caixa}."
        )
    ep = erro_padrao_g1(i["n"])
    forma = (
        f"G1 = {_n(i['assimetria'])} ({i['intensidade_assimetria']}"
        + (f", {'à direita' if i['assimetria'] > 0 else 'à esquerda'}" if abs(i["assimetria"]) >= LIMITE_SINAL_RELEVANTE else "")
        + f"); com erro-padrão de {_n(ep)}, "
        + ("o formato se distingue da simetria." if abs(i["assimetria"]) >= 2 * ep else
           "o formato não se distingue da simetria.")
    )
    return [central, dispersao, outliers + " " + forma]


def interpretar_variavel(
    dados: pd.DataFrame, time: str, variavel: str, perfil: dict[str, Any], comparacao: dict[str, Any]
) -> list[dict[str, Any]]:
    """Texto do Comparativo para o time (ou 'Todos') e a variável selecionados."""
    tabela = {g["variavel"]: g for g in _tabela(dados)}[variavel]
    unidade = tabela["unidade"]
    a, b = TIMES_ANALISADOS
    z = next(v for v in perfil["variaveis"] if v["variavel"] == variavel)
    secoes = []
    if time == "Todos":
        for t in TIMES_ANALISADOS:
            secoes.append(_secao(_curto(t), _paragrafos_time(variavel, unidade, t, tabela["times"][t])))
    else:
        secoes.append(_secao(_curto(time), _paragrafos_time(variavel, unidade, time, tabela["times"][time])))

    ia, ib = tabela["times"][a], tabela["times"][b]
    maior = a if ia["media"] >= ib["media"] else b
    delta = z["diferenca_z"]
    efeito = ("desprezível" if abs(delta) < 0.2 else "pequeno" if abs(delta) < 0.5
              else "médio" if abs(delta) < 0.8 else "grande")
    c = comparacao["cv"]
    if ia["media"] < MEDIA_MINIMA_CV or ib["media"] < MEDIA_MINIMA_CV:
        regularidade = (
            f"Os CVs {_dos(a)} ({_n(ia['cv_percentual'])}%) e {_dos(b)} ({_n(ib['cv_percentual'])}%) parecem altos, "
            f"mas estão perto do piso esperado para contagens desse tamanho ({_n(ia['cv_poisson_ref'])}% e "
            f"{_n(ib['cv_poisson_ref'])}%): não indicam irregularidade."
        )
    elif c["relevante"]:
        regular = a if c["diferenca"] < 0 else b
        regularidade = (
            f"{_time(regular, True)} são mais regulares (CV {_n(tabela['times'][regular]['cv_percentual'])}% contra "
            f"{_n(tabela['times'][b if regular == a else a]['cv_percentual'])}%), diferença que se distingue do acaso."
        )
    else:
        regularidade = (
            f"Os CVs {_dos(a)} ({_n(ia['cv_percentual'])}%) e {_dos(b)} ({_n(ib['cv_percentual'])}%) diferem em "
            f"{_pp(abs(c['diferenca']))}, dentro do acaso (IC 95% de {_n(c['ic95'][0])} a {_n(c['ic95'][1])}): regularidade equivalente."
        )
    secoes.append(_secao("Comparação entre os times", [
        f"{_time(maior, True)} têm a maior média ({_qtd(max(ia['media'], ib['media']), variavel)} contra "
        f"{_v(min(ia['media'], ib['media']))}), diferença de {_qtd(abs(ia['media'] - ib['media']), variavel)} — "
        f"Δz = {_n(abs(delta))}, efeito {efeito} pela convenção de Cohen. {regularidade}",
    ]))
    return secoes
