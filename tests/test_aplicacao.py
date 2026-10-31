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
