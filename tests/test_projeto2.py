"""Testes automatizados dos requisitos do Projeto 2 (Clustering)."""

from pathlib import Path
import pytest
from app import criar_aplicacao
from configuracao import Configuracao


@pytest.fixture
def cliente():
    configuracao = Configuracao(
        caminho_dados=Path(__file__).parents[1] / "dados" / "stats_times_regular_final.csv",
        limite_requisicao=1024 * 1024,
    )
    return criar_aplicacao(configuracao).test_client()


def test_rotas_html_projeto2_respondem_200(cliente):
    rotas = [
        "/projeto2",
        "/projeto2/parte1",
        "/projeto2/parte2",
        "/projeto2/parte3",
        "/projeto2/teoria",
    ]
    for rota in rotas:
        resposta = cliente.get(rota)
        assert resposta.status_code == 200, f"Falha na rota {rota}"
        assert b"PROJETO 2" in resposta.data or b"Projeto 2" in resposta.data


def test_menu_contem_divisao_projeto1_e_projeto2(cliente):
    resposta = cliente.get("/projeto2")
    assert resposta.status_code == 200
    # Verifica que ambos os blocos existem no menu
    assert b"menu-projeto-2" in resposta.data
    assert b"menu-projeto-1" in resposta.data
    assert b"tag-p2" in resposta.data
    assert b"tag-p1" in resposta.data
    assert b"filtro-projeto-menu" in resposta.data


def test_api_projeto2_parte1_kmeans_retorna_dados_completos(cliente):
    for k in (2, 3, 4):
        resposta = cliente.get(f"/api/projeto2/parte1?time=Todos&k={k}")
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["k"] == k
        assert len(dados["clusters"]) == k
        assert -1.0 <= dados["score_silhueta"] <= 1.0
        assert dados["inercia"] > 0
        assert len(dados["pontos_scatter"]) == 149
        assert len(dados["centroides_scatter"]) == k
        assert "radar" in dados
        assert "boxplots" in dados
        assert "histogramas" in dados
        assert "evolucao_temporal" in dados
        assert "barras_quantidade" in dados
        assert "destaques_enunciado" in dados
        # Checar se os 6 perfis táticos do enunciado estão presentes
        destaques = dados["destaques_enunciado"]
        assert "maior_pontuacao" in destaques
        assert "maior_assistencias" in destaques
        assert "maior_rebotes" in destaques
        assert "maior_tres_pontos" in destaques
        assert "maior_faltas" in destaques
        assert "equilibrado" in destaques


def test_api_projeto2_parte1_filtro_por_time(cliente):
    for time in ("Dallas Mavericks", "Indiana Pacers"):
        resposta = cliente.get(f"/api/projeto2/parte1?time={time}&k=3")
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["time_selecionado"] == time
        assert dados["n_observacoes"] in (74, 75)


def test_api_projeto2_parte1_validacao_erros(cliente):
    # Time inválido
    resp_time = cliente.get("/api/projeto2/parte1?time=TimeInexistente&k=3")
    assert resp_time.status_code == 400
    assert "erro" in resp_time.get_json()

    # K inválido
    resp_k = cliente.get("/api/projeto2/parte1?time=Todos&k=1")
    assert resp_k.status_code == 400


def test_api_projeto2_comparar_k(cliente):
    resposta = cliente.get("/api/projeto2/comparar-k?time=Todos")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert len(dados["comparativo"]) == 3
    assert [c["k"] for c in dados["comparativo"]] == [2, 3, 4]
    assert dados["k_recomendado"] == 3
    assert len(dados["justificativa_escolha"]) > 50


def test_api_projeto2_parte2_multiplos_algoritmos(cliente):
    resposta = cliente.get("/api/projeto2/parte2?k=3")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert len(dados["comparativo"]) == 5
    nomes_algoritmos = [c["algoritmo"] for c in dados["comparativo"]]
    assert "K-Means" in nomes_algoritmos
    assert "Hierarchical Clustering" in nomes_algoritmos
    assert "DBSCAN" in nomes_algoritmos
    assert "Gaussian Mixture Model (GMM)" in nomes_algoritmos
    assert "Spectral Clustering" in nomes_algoritmos
    assert "scatter" in dados
    assert "sintese_decisao" in dados


def test_api_projeto2_parte3_analise_global_30_times(cliente):
    resposta = cliente.get("/api/projeto2/parte3?k=4")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["n_times"] == 30
    assert len(dados["clusters"]) == 4
    assert len(dados["tabela_times"]) == 30
    assert len(dados["perguntas_respostas"]) == 6
    # Checar se respondeu às 6 perguntas
    perguntas_ids = [p["id"] for p in dados["perguntas_respostas"]]
    assert perguntas_ids == [1, 2, 3, 4, 5, 6]


def test_api_projeto2_teoria(cliente):
    resposta = cliente.get("/api/projeto2/teoria")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert "kmeans" in dados
    assert len(dados["kmeans"]["topicos"]) == 7
    assert len(dados["algoritmos"]) == 5
