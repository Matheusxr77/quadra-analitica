"""Rotas das páginas e da API."""

from flask import Blueprint, jsonify, render_template, request

from analise import VARIAVEIS_ANALISADAS, TIMES_ANALISADOS
from servicos.servico_relatorio import ServicoRelatorio
from servicos.servico_projeto2 import ServicoProjeto2


def criar_blueprint(
    servico: ServicoRelatorio,
    servico_p2: ServicoProjeto2 | None = None,
) -> Blueprint:
    rotas = Blueprint("relatorio", __name__)
    if servico_p2 is None:
        servico_p2 = ServicoProjeto2(servico._repositorio)

    @rotas.get("/health")
    def verificacao_de_saude():
        return jsonify({"status": "ok", "servico": "quadra-analitica"})

    @rotas.get("/")
    def pagina_principal():
        return render_template(
            "visao_geral.html",
            times=TIMES_ANALISADOS,
            variaveis=VARIAVEIS_ANALISADAS,
            pagina_ativa="visao_geral",
        )

    @rotas.get("/comparativo")
    def pagina_comparativo():
        return render_template(
            "comparativo.html",
            times=TIMES_ANALISADOS,
            variaveis=VARIAVEIS_ANALISADAS,
            pagina_ativa="comparativo",
        )

    @rotas.get("/qualidade")
    def pagina_qualidade():
        return render_template(
            "qualidade.html",
            pagina_ativa="qualidade",
        )

    @rotas.get("/dicionario")
    def pagina_dicionario():
        return render_template(
            "dicionario.html",
            pagina_ativa="dicionario",
        )

    @rotas.get("/api/dicionario")
    def api_dicionario():
        return jsonify(servico.dicionario())

    @rotas.get("/api/qualidade")
    def api_qualidade():
        return jsonify(servico.qualidade())

    @rotas.get("/assimetria")
    def pagina_assimetria():
        return render_template(
            "assimetria.html",
            times=TIMES_ANALISADOS,
            variaveis=VARIAVEIS_ANALISADAS,
            pagina_ativa="assimetria",
        )

    @rotas.get("/cv")
    def pagina_cv():
        return render_template("cv.html", pagina_ativa="cv")

    @rotas.get("/iqr")
    def pagina_iqr():
        return render_template("iqr.html", pagina_ativa="iqr")

    @rotas.get("/api/assimetria")
    def api_assimetria():
        return jsonify(servico.assimetria())

    @rotas.get("/api/cv")
    def api_cv():
        return jsonify(servico.cv())

    @rotas.get("/api/iqr")
    def api_iqr():
        return jsonify(servico.iqr())

    @rotas.get("/sintese")
    def pagina_sintese():
        return render_template("sintese.html", pagina_ativa="sintese")

    @rotas.get("/api/sintese")
    def api_sintese():
        return jsonify(servico.sintese())

    @rotas.get("/api/perfil-z")
    def api_perfil_z():
        return jsonify(servico.perfil_z())

    @rotas.get("/api/descritivas")
    def api_descritivas():
        return jsonify(servico.tabela_descritiva())

    @rotas.get("/api/estatisticas")
    def api_estatisticas():
        time = request.args.get("time", "Todos", type=str).strip()
        variavel = request.args.get(
            "variavel", VARIAVEIS_ANALISADAS[0], type=str
        ).strip()
        return jsonify(servico.estatisticas(time, variavel))

    # =========================================================================
    # ROTAS DO PROJETO 2 (CLUSTERING)
    # =========================================================================

    @rotas.get("/projeto2")
    def pagina_projeto2_visao_geral():
        """Painel de Avaliação de Requisitos e Visão Geral do Projeto 2."""
        return render_template(
            "projeto2_visao_geral.html",
            pagina_ativa="projeto2_visao_geral",
            projeto_ativo=2,
            times=TIMES_ANALISADOS,
        )

    @rotas.get("/projeto2/parte1")
    def pagina_projeto2_parte1():
        """Parte 1: K-Means (Dallas Mavericks & Indiana Pacers) com k=2,3,4."""
        return render_template(
            "projeto2_parte1.html",
            pagina_ativa="projeto2_parte1",
            projeto_ativo=2,
            times=TIMES_ANALISADOS,
        )

    @rotas.get("/projeto2/parte2")
    def pagina_projeto2_parte2():
        """Parte 2: Múltiplos algoritmos (Hierarchical, DBSCAN, GMM, Spectral)."""
        return render_template(
            "projeto2_parte2.html",
            pagina_ativa="projeto2_parte2",
            projeto_ativo=2,
        )

    @rotas.get("/projeto2/parte3")
    def pagina_projeto2_parte3():
        """Parte 3: Análise global da liga (todos os 30 times da NBA)."""
        return render_template(
            "projeto2_parte3.html",
            pagina_ativa="projeto2_parte3",
            projeto_ativo=2,
        )

    @rotas.get("/projeto2/teoria")
    def pagina_projeto2_teoria():
        """Fundamentos teóricos e matemática dos 5 algoritmos."""
        teoria_dados = servico_p2.teoria()
        return render_template(
            "projeto2_teoria.html",
            pagina_ativa="projeto2_teoria",
            projeto_ativo=2,
            teoria=teoria_dados,
        )

    # API Endpoints do Projeto 2

    @rotas.get("/api/projeto2/parte1")
    def api_projeto2_parte1():
        time = request.args.get("time", "Todos", type=str).strip()
        k = request.args.get("k", 3, type=int)
        return jsonify(servico_p2.parte1_kmeans(time=time, k=k))

    @rotas.get("/api/projeto2/comparar-k")
    def api_projeto2_comparar_k():
        time = request.args.get("time", "Todos", type=str).strip()
        return jsonify(servico_p2.parte1_comparar_k(time=time))

    @rotas.get("/api/projeto2/parte2")
    def api_projeto2_parte2():
        k = request.args.get("k", 3, type=int)
        return jsonify(servico_p2.parte2_multiplos_algoritmos(k=k))

    @rotas.get("/api/projeto2/parte3")
    def api_projeto2_parte3():
        k = request.args.get("k", 4, type=int)
        return jsonify(servico_p2.parte3_analise_global(k=k))

    @rotas.get("/api/projeto2/teoria")
    def api_projeto2_teoria():
        return jsonify(servico_p2.teoria())

    return rotas
