from pathlib import Path

import pandas as pd

from app import criar_aplicacao
from configuracao import Configuracao


def criar_cliente():
    configuracao = Configuracao(
        caminho_dados=Path(__file__).parents[1]
        / "dados"
        / "stats_times_regular_final.csv",
        limite_requisicao=1024 * 1024,
    )
    return criar_aplicacao(configuracao).test_client()


def test_pagina_principal_e_cabecalhos_de_seguranca():
    resposta = criar_cliente().get("/")
    assert resposta.status_code == 200
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "DENY"


def test_paginas_do_relatorio_sao_rotas_distintas():
    cliente = criar_cliente()
    for caminho, texto in (
        ("/comparativo", "Distribuição por jogo"),
        ("/qualidade", "Qualidade dos dados"),
        ("/dicionario", "Dicionário de dados"),
    ):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200
        assert texto.encode("utf-8") in resposta.data


def test_api_rejeita_time_invalido():
    resposta = criar_cliente().get("/api/estatisticas?time=Outro%20time")
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]


def test_api_entrega_estatisticas_validas():
    resposta = criar_cliente().get(
        "/api/estatisticas?time=Indiana%20Pacers&variavel=BLK"
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["variavel"] == "BLK"


def test_base_fisica_e_dicionario_respeitam_escopo_do_grupo():
    from infraestrutura.repositorio_dados import RepositorioDados

    raiz = Path(__file__).parents[1] / "dados"
    caminho = raiz / "estatisticas_times_selecionados.csv"
    # Num clone limpo o CSV derivado não existe: o repositório deve gerá-lo
    # no caminho padrão (ao lado da fonte) ao carregar os dados.
    RepositorioDados(raiz / "stats_times_regular_final.csv").obter_dados()
    assert caminho.exists()
    assert not (raiz / "dados").exists()
    dados = pd.read_csv(caminho)
    assert set(dados["TEAM_NAME"]) == {"Dallas Mavericks", "Indiana Pacers"}
    campos = criar_cliente().get("/api/dicionario").get_json()["campos"]
    assert all("categoria" in campo for campo in campos)
    assert all("explicacao" in campo for campo in campos)


def test_bigodes_ficam_no_valor_observado_dentro_dos_limites_de_tukey():
    from analise import _estatisticas_de_serie

    serie = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
    resultado = _estatisticas_de_serie(serie)
    assert resultado["outliers"] == [100.0]
    assert resultado["quantidade_outliers"] == 1
    assert resultado["bigode_inferior"] == 1.0
    assert resultado["bigode_superior"] == 5.0
    # O bigode é um valor observado, não o limite teórico.
    assert resultado["bigode_superior"] in serie.values
    assert resultado["bigode_superior"] < resultado["limite_superior"]
    assert resultado["limite_inferior"] <= resultado["bigode_inferior"]


def test_modas_multiplas_e_serie_amodal():
    from analise import _estatisticas_de_serie

    bimodal = _estatisticas_de_serie(pd.Series([1.0, 1.0, 2.0, 2.0, 3.0]))
    assert bimodal["modas"] == [1.0, 2.0]
    assert bimodal["amodal"] is False
    amodal = _estatisticas_de_serie(pd.Series([1.0, 2.0, 3.0]))
    assert amodal["modas"] == []
    assert amodal["amodal"] is True


def test_medidas_conferem_com_pandas():
    from analise import _estatisticas_de_serie

    serie = pd.Series([10.0, 12.0, 15.0, 15.0, 20.0, 31.0, 7.0])
    resultado = _estatisticas_de_serie(serie)
    assert resultado["media"] == serie.mean()
    assert resultado["variancia"] == serie.var(ddof=1)
    assert resultado["desvio_padrao"] == serie.std(ddof=1)
    assert resultado["q1"] == serie.quantile(0.25, interpolation="linear")
    assert resultado["q3"] == serie.quantile(0.75, interpolation="linear")
    assert resultado["amplitude"] == 24.0


def test_api_descritivas_cobre_todas_as_variaveis_e_times():
    from analise import TIMES_ANALISADOS, VARIAVEIS_ANALISADAS

    resposta = criar_cliente().get("/api/descritivas")
    assert resposta.status_code == 200
    corpo = resposta.get_json()
    assert [grupo["variavel"] for grupo in corpo["variaveis"]] == VARIAVEIS_ANALISADAS
    chaves = {
        "media", "mediana", "moda", "modas", "minimo", "maximo", "amplitude",
        "desvio_padrao", "variancia", "q1", "q3", "quantidade_outliers",
        "outliers", "outliers_detalhe", "bigode_inferior", "bigode_superior",
    }
    for grupo in corpo["variaveis"]:
        assert grupo["unidade"].endswith("por jogo")
        assert set(grupo["times"]) == set(TIMES_ANALISADOS)
        for item in grupo["times"].values():
            assert chaves <= set(item)
            assert item["quantidade_outliers"] == len(item["outliers"])
            assert len(item["outliers_detalhe"]) == len(item["outliers"])
            assert item["limite_inferior"] <= item["bigode_inferior"] <= item["q1"]
            assert item["q3"] <= item["bigode_superior"] <= item["limite_superior"]


def test_pagina_comparativo_tem_tabela_descritiva():
    resposta = criar_cliente().get("/comparativo")
    assert b"tabela-descritiva" in resposta.data


# --- Assimetria, CV, IQR e histograma/KDE ----------------------------------

def test_g1_igual_ao_scipy_ajustado_e_bowley():
    from scipy import stats

    from analise import _estatisticas_de_serie

    serie = pd.Series([2.0, 3.0, 3.0, 4.0, 5.0, 6.0, 9.0, 15.0])
    resultado = _estatisticas_de_serie(serie)
    assert abs(resultado["assimetria"] - stats.skew(serie, bias=False)) < 1e-12
    q1, q3, md = serie.quantile(0.25), serie.quantile(0.75), serie.median()
    assert abs(resultado["bowley"] - (q3 + q1 - 2 * md) / (q3 - q1)) < 1e-12
    assert resultado["direcao_assimetria"] == "à direita (positiva)"


def test_cv_amostral_em_percentual_e_medidas_robustas():
    from analise import _estatisticas_de_serie

    serie = pd.Series([4.0, 6.0, 8.0, 10.0, 12.0])
    resultado = _estatisticas_de_serie(serie)
    assert abs(resultado["cv_percentual"] - serie.std(ddof=1) / serie.mean() * 100) < 1e-12
    assert abs(resultado["cv_robusto_iqr"] - resultado["iqr"] / serie.median() * 100) < 1e-12
    assert abs(resultado["sigma_robusto"] - resultado["iqr"] / 1.349) < 1e-12


def test_outlier_muda_g1_e_dp_mas_nao_o_iqr():
    from analise import _estatisticas_de_serie

    serie = pd.Series([float(v) for v in range(1, 21)] + [80.0])
    resultado = _estatisticas_de_serie(serie)
    assert resultado["outliers"] == [80.0]
    assert resultado["assimetria_sem_outliers"] < resultado["assimetria"]
    assert resultado["desvio_sem_outliers"] < resultado["desvio_padrao"]
    assert resultado["quantidade_outliers_3iqr"] == 1


def test_histograma_freedman_diaconis_e_kde():
    import numpy as np

    from analise import TIMES_ANALISADOS, VARIAVEIS_ANALISADAS, calcular_histograma_kde
    from infraestrutura.repositorio_dados import RepositorioDados

    raiz = Path(__file__).parents[1] / "dados"
    dados = RepositorioDados(
        raiz / "stats_times_regular_final.csv", raiz / "estatisticas_times_selecionados.csv"
    ).obter_dados()
    for variavel in VARIAVEIS_ANALISADAS:
        hist = calcular_histograma_kde(dados, variavel)
        assert isinstance(hist["largura"], int) and hist["largura"] >= 1
        assert np.allclose(np.diff(hist["bordas"]), hist["largura"])
        for time in TIMES_ANALISADOS:
            item = hist["times"][time]
            assert sum(item["contagens"]) == item["n"]
            assert len(item["contagens"]) == len(hist["centros"])
            integral = np.trapezoid(item["kde_densidade"], item["kde_x"])
            assert 0.97 < integral <= 1.001


def test_apis_de_assimetria_cv_e_iqr():
    from analise import VARIAVEIS_ANALISADAS

    cliente = criar_cliente()
    for caminho in ("/api/assimetria", "/api/cv", "/api/iqr"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200, caminho
        corpo = resposta.get_json()
        assert [q["variavel"] for q in corpo["quadro"]] == VARIAVEIS_ANALISADAS
        assert all(len(q["valores"]) == 2 for q in corpo["quadro"])
        assert len(corpo["linhas"]) == 14
        assert len(corpo["secoes"]) >= 6
        for secao in corpo["secoes"]:
            assert secao["titulo"] and secao["paragrafos"]
        texto = " ".join(p for s in corpo["secoes"] for p in s["paragrafos"])
        assert any(caractere.isdigit() for caractere in texto)


def test_paginas_de_medidas_exibem_formula():
    cliente = criar_cliente()
    for caminho, trecho in (
        ("/assimetria", "Fisher-Pearson"),
        ("/cv", "amostral"),
        ("/iqr", "interpolação linear"),
    ):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200
        corpo = resposta.data.decode("utf-8")
        assert "FÓRMULA UTILIZADA" in corpo and trecho in corpo


def test_estatisticas_incluem_histograma_com_kde():
    corpo = criar_cliente().get("/api/estatisticas?variavel=BLK").get_json()
    hist = corpo["histograma"]
    assert hist["regra"].startswith("Freedman")
    assert set(hist["times"]) == {"Dallas Mavericks", "Indiana Pacers"}


# --- Qualidade dos dados ----------------------------------------------------

def test_valor_critico_de_grubbs_confere_com_a_tabela():
    from deteccao import valor_critico_grubbs

    # Tabela de Grubbs (bilateral, α = 0,05): n = 10 → 2,290; n = 20 → 2,709.
    assert abs(valor_critico_grubbs(10) - 2.290) < 0.001
    assert abs(valor_critico_grubbs(20) - 2.709) < 0.001


def test_grubbs_iterativo_remove_extremos_ate_passo_nao_significativo():
    import numpy as np

    from deteccao import grubbs_iterativo

    base = list(np.random.default_rng(0).normal(50, 2, 30))
    sem_extremos = grubbs_iterativo(pd.Series(base))
    assert sem_extremos["valores"] == []
    assert sem_extremos["passos"][-1]["significativo"] is False

    resultado = grubbs_iterativo(pd.Series(base + [80.0, 75.0]))
    assert sorted(resultado["valores"]) == [75.0, 80.0]
    assert [p["significativo"] for p in resultado["passos"]] == [True, True, False]
    primeiro = resultado["passos"][0]
    serie = pd.Series(base + [80.0, 75.0])
    assert abs(primeiro["g"] - (80 - serie.mean()) / serie.std(ddof=1)) < 1e-12


def test_grubbs_reproduz_o_exemplo_do_nist():
    from deteccao import grubbs_iterativo

    # NIST/SEMATECH e-Handbook, seção 1.3.5.17: G = 2,4687; G crítico (α = 0,05, bilateral, n = 8) = 2,1266.
    serie = pd.Series([199.31, 199.53, 200.19, 200.82, 201.92, 201.95, 202.18, 245.57])
    passo = grubbs_iterativo(serie)["passos"][0]
    assert abs(passo["g"] - 2.4687) < 1e-4
    assert abs(passo["g_critico"] - 2.1266) < 1e-4
    assert passo["valor"] == 245.57 and passo["significativo"]


def test_ecod_proprio_marca_outlier_obvio():
    import numpy as np

    from deteccao import ecod_componentes, ecod_por_proporcao

    dados = np.random.default_rng(1).normal(size=(80, 3))
    dados[17] = [8.0, 7.5, 9.0]  # muito acima nas três colunas
    scores = ecod_componentes(dados)["scores"]
    assert int(np.argmax(scores)) == 17
    # Em 1D: F̂ esquerda/direita contam empates (≤ e ≥).
    coluna = np.array([1.0, 2.0, 2.0, 3.0, 10.0])
    comp = ecod_componentes(coluna)
    assert np.allclose(comp["u_esq"][:, 0], -np.log([1 / 5, 3 / 5, 3 / 5, 4 / 5, 5 / 5]))
    assert np.allclose(comp["u_dir"][:, 0], -np.log([5 / 5, 4 / 5, 4 / 5, 2 / 5, 1 / 5]))
    # Mínimo e máximo únicos têm a mesma cauda (1/n): empatam e nenhum é marcado.
    assert not ecod_por_proporcao(coluna, 0.2)["rotulos"].any()
    # Com o mínimo repetido, só o 10 fica com a menor probabilidade de cauda.
    assimetrica = np.array([1.0, 1.0, 2.0, 3.0, 10.0])
    assert ecod_por_proporcao(assimetrica, 0.2)["rotulos"].tolist() == [False, False, False, False, True]


def test_ecod_proprio_igual_ao_pyod_quando_disponivel():
    import numpy as np

    pytest = __import__("pytest")
    ecod_pyod = pytest.importorskip("pyod.models.ecod").ECOD
    from deteccao import TAXA_REFERENCIA, ecod_componentes, ecod_por_proporcao

    gerador = np.random.default_rng(3)
    for _ in range(10):
        coluna = np.round(gerador.gamma(2, 3, size=(80, 1)))  # contagens com empates
        esperado = ecod_pyod(contamination=TAXA_REFERENCIA).fit(coluna)
        obtido = ecod_por_proporcao(coluna)
        assert np.allclose(obtido["scores"], esperado.decision_scores_)
        assert (obtido["rotulos"] == esperado.labels_.astype(bool)).all()
    # Em várias dimensões as caudas por coluna coincidem; o score final segue o
    # artigo (máximo das somas), enquanto o pyod soma os máximos por coluna.
    matriz = gerador.normal(size=(60, 4))
    modelo = ecod_pyod().fit(matriz)
    componentes = ecod_componentes(matriz)
    assert np.allclose(componentes["u_esq"], modelo.U_l)
    assert np.allclose(componentes["u_dir"], modelo.U_r)


def test_teste_de_little_calibrado_e_graus_de_liberdade():
    import numpy as np

    from qualidade import teste_little

    rejeicoes = 0
    for semente in range(60):
        gerador = np.random.default_rng(semente)
        x = gerador.multivariate_normal([0, 0, 0], [[1, .5, .3], [.5, 1, .4], [.3, .4, 1]], size=120)
        x[gerador.random(120) < 0.2, 0] = np.nan
        resultado = teste_little(x)
        assert resultado["gl"] == 2  # padrões: (3 colunas) + (2 colunas) − 3
        rejeicoes += resultado["rejeita_mcar"]
    assert rejeicoes / 60 < 0.15  # sob MCAR, ≈ α = 5%

    gerador = np.random.default_rng(7)
    x = gerador.multivariate_normal([0, 0], [[1, .6], [.6, 1]], size=200)
    x[x[:, 1] > 0.3, 0] = np.nan  # MAR: depende da coluna observada
    assert teste_little(x)["rejeita_mcar"]


def test_demonstracao_mcar_nao_rejeita_e_mar_rejeita():
    from infraestrutura.repositorio_dados import RepositorioDados
    from qualidade import demonstrar_testes_ausencia

    raiz = Path(__file__).parents[1] / "dados"
    dados = RepositorioDados(raiz / "stats_times_regular_final.csv").obter_dados()
    cenarios = {c["chave"]: c for c in demonstrar_testes_ausencia(dados)["cenarios"]}
    assert not cenarios["mcar"]["little"]["rejeita_mcar"]
    assert not cenarios["mcar"]["fairclough"]["rejeita_mcar"]
    assert cenarios["mar"]["little"]["rejeita_mcar"]
    assert cenarios["mar"]["fairclough"]["rejeita_mcar"]


def test_duplicatas_contadas_na_base_bruta_antes_do_tratamento():
    from qualidade import contar_duplicatas

    bruto = pd.DataFrame({"TEAM_NAME": ["A", "A", "B", "B"], "Game_ID": [1, 1, 1, 2], "PTS": [100, 100, 90, 95]})
    tratado = bruto.drop_duplicates(subset=["TEAM_NAME", "Game_ID"])
    resultado = contar_duplicatas(bruto, bruto, tratado)
    assert resultado["fonte"]["linha_inteira"] == 1
    assert resultado["fonte"]["chave_time_jogo"] == 1
    assert resultado["removidos_no_tratamento"] == 1


def test_minutos_com_prorrogacao_sao_dominio_valido():
    from qualidade import classificar_minutos

    assert classificar_minutos(240) == 0
    assert classificar_minutos(265) == 1
    assert classificar_minutos(290) == 2
    assert classificar_minutos(250) is None
    assert classificar_minutos(200) is None


def test_api_e_pagina_de_qualidade():
    cliente = criar_cliente()
    corpo = cliente.get("/api/qualidade").get_json()
    fonte = pd.read_csv(Path(__file__).parents[1] / "dados" / "stats_times_regular_final.csv")
    assert [linha["coluna"] for linha in corpo["ausentes"]] == list(fonte.columns)
    assert {m["sigla"] for m in corpo["mecanismos"]} == {"MCAR", "MAR", "MNAR"}
    assert len(corpo["testes_ausencia"]) == 4
    assert {m["chave"] for m in corpo["metodos"]} == {"zscore", "iqr", "grubbs", "ecod", "knn", "dbscan", "lof"}
    assert len(corpo["outliers_por_coluna"]) == 18
    assert len(corpo["dominio"]["jogos_prorrogacao"]) == 8
    # IQR por coluna = mesma contagem da tabela descritiva (mesmos limites de Tukey).
    descritiva = cliente.get("/api/descritivas").get_json()
    por_coluna = {c["coluna"]: c for c in corpo["outliers_por_coluna"]}
    from analise import MAPA_VARIAVEIS
    for grupo in descritiva["variaveis"]:
        coluna = por_coluna[MAPA_VARIAVEIS[grupo["variavel"]]]
        for time, item in grupo["times"].items():
            assert coluna["times"][time]["iqr"]["quantidade"] == item["quantidade_outliers"]
    pagina = cliente.get("/qualidade").data.decode("utf-8")
    for trecho in ("MCAR, MAR e MNAR", "Grubbs", "ECOD", "Ausentes por coluna"):
        assert trecho in pagina


def test_diagnostico_completo_nao_usa_pyod():
    import subprocess
    import sys

    codigo = (
        "import sys, app\n"
        "from tests.test_aplicacao import criar_cliente\n"
        "assert criar_cliente().get('/api/qualidade').status_code == 200\n"
        "print('pyod' in sys.modules)"
    )
    saida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                           cwd=Path(__file__).parents[1], check=True)
    assert saida.stdout.strip().splitlines()[-1] == "False"


def _bases_brutas():
    raiz = Path(__file__).parents[1] / "dados"
    criar_cliente().get("/api/qualidade")  # garante o CSV derivado
    fonte = pd.read_csv(raiz / "stats_times_regular_final.csv")
    recorte = pd.read_csv(raiz / "estatisticas_times_selecionados.csv")
    return fonte, recorte


def test_valores_especiais_batem_com_a_base_bruta():
    corpo = criar_cliente().get("/api/qualidade").get_json()
    fonte, recorte = _bases_brutas()
    assert set(recorte["TEAM_NAME"]) == {"Dallas Mavericks", "Indiana Pacers"}
    dup = corpo["duplicatas"]
    assert dup["recorte"]["registros"] == len(recorte)
    assert dup["recorte"]["linha_inteira"] == int(recorte.duplicated().sum())
    assert dup["recorte"]["chave_time_jogo"] == int(recorte.duplicated(["TEAM_NAME", "Game_ID"]).sum())
    assert dup["fonte"]["linha_inteira"] == int(fonte.duplicated().sum())
    numericas = recorte.drop(columns=["Team_ID", "Game_ID"]).select_dtypes("number")
    zeros = {z["coluna"]: z for z in corpo["zeros_negativos"]}
    for coluna in numericas.columns:
        assert zeros[coluna]["zeros"] == int((numericas[coluna] == 0).sum()), coluna
        assert zeros[coluna]["negativos"] == int((numericas[coluna] < 0).sum()), coluna
    assert "legítim" in zeros["BLK"]["significado"] or "possível" in zeros["BLK"]["significado"]
    regras = {(r["coluna"], r["regra"]): r for r in corpo["dominio"]["regras"]}
    for coluna in ("W_PCT", "FG_PCT", "FG3_PCT", "FT_PCT"):
        esperado = int((~recorte[coluna].between(0, 1)).sum())
        assert regras[(coluna, f"{coluna} ∈ [0, 1]")]["violacoes_recorte"] == esperado
    assert regras[("FGM", "FGM ≤ FGA")]["violacoes_recorte"] == int((recorte.FGM > recorte.FGA).sum())
    assert regras[("FG3M", "FG3M ≤ FG3A")]["violacoes_recorte"] == int((recorte.FG3M > recorte.FG3A).sum())
    assert regras[("FTM", "FTM ≤ FTA")]["violacoes_recorte"] == int((recorte.FTM > recorte.FTA).sum())
    assert regras[("REB", "REB = OREB + DREB")]["violacoes_recorte"] == int(
        (recorte.REB != recorte.OREB + recorte.DREB).sum())
    fora_min = int((((recorte.MIN - 240) % 25 != 0) | (recorte.MIN < 240)).sum())
    assert regras[("MIN", "MIN = 240 + 25·k")]["violacoes_recorte"] == fora_min
    assert len(corpo["dominio"]["jogos_prorrogacao"]) == int((recorte.MIN > 240).sum())


def test_dominio_detecta_violacoes_injetadas():
    from qualidade import verificar_dominio

    _, recorte = _bases_brutas()
    sujo = recorte.copy()
    sujo.loc[0, "FG_PCT"] = 506  # percentual em milésimos
    sujo.loc[1, "FGM"] = sujo.loc[1, "FGA"] + 1
    sujo.loc[2, "MIN"] = 250
    regras = {(r["coluna"], r["regra"]): r["violacoes_recorte"] for r in verificar_dominio(sujo, sujo)["regras"]}
    assert regras[("FG_PCT", "FG_PCT ∈ [0, 1]")] == 1
    assert regras[("FGM", "FGM ≤ FGA")] == 1
    assert regras[("MIN", "MIN = 240 + 25·k")] == 1


def test_calibracao_reproduz_tabela_e_taxa_de_referencia():
    import numpy as np

    from deteccao import (TAXA_REFERENCIA, _tabela_calibracao, calibrar, detectar,
                          obter_calibracao)

    assert abs(TAXA_REFERENCIA - 0.00698) < 1e-4  # Tukey numa normal: P(|z| > 2,698)
    tabela = _tabela_calibracao()
    assert {"74x1", "75x1", "74x7", "75x7"} <= set(tabela)
    calibrar.cache_clear()
    recalculado = calibrar(75, 1)
    for chave, valor in tabela["75x1"].items():
        assert recalculado[chave] == valor, chave
    assert obter_calibracao(75, 1) == tabela["75x1"]
    # Em normais novas (outra semente), cada método marca perto de 0,7%.
    gerador = np.random.default_rng(99)
    marcados = {m: 0 for m in ("knn", "dbscan", "lof")}
    total = 0
    for _ in range(60):
        amostra = gerador.standard_normal(75)
        rotulos = detectar(amostra)["rotulos"]
        for m in marcados:
            marcados[m] += int(rotulos[m].sum())
        total += 75
    for m, q in marcados.items():
        assert q / total < 0.03, m


def test_outliers_por_variavel_lista_jogos_e_concordancia():
    corpo = criar_cliente().get("/api/qualidade").get_json()
    pv = corpo["outliers_por_variavel"]
    metodos = ["zscore", "iqr", "grubbs", "ecod", "knn", "dbscan", "lof"]
    assert pv["metodos"] == metodos
    assert len(pv["detalhes"]) == 14
    descritiva = {
        (g["variavel"], t): item
        for g in criar_cliente().get("/api/descritivas").get_json()["variaveis"]
        for t, item in g["times"].items()
    }
    for d in pv["detalhes"]:
        iqr = d["metodos"]["iqr"]
        assert iqr["quantidade"] == descritiva[(d["variavel"], d["time"])]["quantidade_outliers"]
        assert sorted(j["valor"] for j in iqr["jogos"]) == descritiva[(d["variavel"], d["time"])]["outliers"]
        for m in metodos:
            assert d["metodos"][m]["quantidade"] == len(d["metodos"][m]["jogos"])
            for jogo in d["metodos"][m]["jogos"]:
                assert jogo["data"] and jogo["adversario"]
        for j in d["concordancia"]:
            assert j["total"] == sum(j["metodos"].values()) >= 1
    matriz = pv["matriz_concordancia"]
    for a in metodos:
        assert matriz[a][a] == sum(d["metodos"][a]["quantidade"] for d in pv["detalhes"])
        for b in metodos:
            assert matriz[a][b] == matriz[b][a] <= min(matriz[a][a], matriz[b][b])
    # O jogo de 15 tocos dos Mavericks é marcado por quase todos os métodos.
    blk = next(d for d in pv["detalhes"] if d["variavel"] == "BLK" and d["time"] == "Dallas Mavericks")
    assert blk["concordancia"][0]["valor"] == 15 and blk["concordancia"][0]["total"] >= 5
    textos = {t["nome"]: t for t in corpo["testes_ausencia"]}
    for teste in textos.values():
        assert 1 <= len(teste["paragrafos"]) <= 2
        assert "0 valores ausentes" in teste["paragrafos"][-1]


# --- Base e síntese -----------------------------------------------------------

def test_dicionario_classifica_os_cinco_tipos():
    campos = {c["coluna_original"]: c for c in criar_cliente().get("/api/dicionario").get_json()["campos"]}
    assert campos["GAME_DATE"]["tipo"] == "data"
    assert campos["WL"]["tipo"] == "binária"
    assert campos["MATCHUP"]["tipo"] == "texto"
    for coluna in ("TEAM_NAME", "Team_ID", "Game_ID"):
        assert campos[coluna]["tipo"] == "categórica"
    assert campos["PTS"]["tipo"] == "numérica"
    assert campos["FG_PCT"]["subtipo"].startswith("contínua")
    assert {c["tipo"] for c in campos.values()} == {"numérica", "categórica", "texto", "data", "binária"}


def test_exclusoes_para_ml_e_vazamento_de_w_l():
    corpo = criar_cliente().get("/api/dicionario").get_json()
    excluidas = {e["coluna"] for e in corpo["exclusoes"]}
    assert excluidas == {"Team_ID", "Game_ID", "MATCHUP", "TEAM_NAME", "W", "L", "W_PCT"}
    assert all(e["motivo"] for e in corpo["exclusoes"])
    usos = {c["coluna_original"]: c["uso_ml"] for c in corpo["campos"]}
    assert usos["WL"] == "alvo" and usos["PTS"] == "feature"
    vazamento = corpo["vazamento"]
    # W e L são acumulados após o jogo: a variação de W é o próprio resultado.
    assert vazamento["variacao_w_igual_wl"] == vazamento["jogos_com_anterior"] > 0
    assert vazamento["variacao_l_igual_derrota"] == vazamento["jogos_com_anterior"]
    assert vazamento["w_mais_l_igual_numero_do_jogo"] == vazamento["jogos"]


def test_perfil_z_usa_os_jogos_dos_dois_times_como_referencia():
    from analise import MAPA_VARIAVEIS, calcular_perfil_z
    from infraestrutura.repositorio_dados import RepositorioDados

    raiz = Path(__file__).parents[1] / "dados"
    dados = RepositorioDados(raiz / "stats_times_regular_final.csv").obter_dados()
    perfil = calcular_perfil_z(dados)
    for item in perfil["variaveis"]:
        serie = dados[MAPA_VARIAVEIS[item["variavel"]]]
        assert abs(item["media_referencia"] - serie.mean()) < 1e-9
        assert abs(item["desvio_referencia"] - serie.std(ddof=1)) < 1e-9
        ponderada = sum(t["n"] * t["z"] for t in item["times"].values())
        assert abs(ponderada) < 1e-9  # referência = os próprios dois times
        for time, t in item["times"].items():
            esperado = (t["media"] - serie.mean()) / serie.std(ddof=1)
            assert abs(t["z"] - esperado) < 1e-12


def test_zscore_no_comparativo_e_pagina_de_sintese():
    cliente = criar_cliente()
    perfil = cliente.get("/api/perfil-z").get_json()
    assert len(perfil["variaveis"]) == 7 and len(perfil["paragrafos"]) >= 4
    assert "Onde o z-score entra" in cliente.get("/comparativo").data.decode("utf-8")

    sintese = cliente.get("/api/sintese").get_json()
    assert len(sintese["quadro"]) == 14
    titulos = [s["titulo"] for s in sintese["secoes"]]
    for titulo in ("Comparação entre os times", "Onde o z-score entra no gráfico de barras", "Limitações", "Conclusão"):
        assert titulo in titulos
    texto = " ".join(p for s in sintese["secoes"] for p in s["paragrafos"])
    assert any(c.isdigit() for c in texto)
    pagina = cliente.get("/sintese")
    assert pagina.status_code == 200 and "Síntese" in pagina.data.decode("utf-8")
