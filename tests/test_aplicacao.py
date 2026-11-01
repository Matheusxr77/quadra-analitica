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
