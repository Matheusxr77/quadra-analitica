"""Endereços acessados pelo navegador e pelas requisições da página."""

from flask import Blueprint, jsonify, render_template, request

from analise import VARIAVEIS_ANALISADAS, TIMES_ANALISADOS
from servicos.servico_relatorio import ServicoRelatorio


def criar_blueprint(servico: ServicoRelatorio) -> Blueprint:
    rotas = Blueprint("relatorio", __name__)

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

    @rotas.get("/api/estatisticas")
    def api_estatisticas():
        time = request.args.get("time", "Todos", type=str).strip()
        variavel = request.args.get(
            "variavel", VARIAVEIS_ANALISADAS[0], type=str
        ).strip()
        return jsonify(servico.estatisticas(time, variavel))

    return rotas
