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
    caminho = Path(__file__).parents[1] / "dados" / "estatisticas_times_selecionados.csv"
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
