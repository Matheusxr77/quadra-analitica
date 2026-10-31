"""Cria e inicia a aplicação Flask."""

import logging
import time
from uuid import uuid4

from flask import Flask, g, request

from configuracao import Configuracao
from infraestrutura.repositorio_dados import RepositorioDados
from servicos.servico_relatorio import ServicoRelatorio
from web.erros import registrar_tratamento_de_erros
from web.rotas import criar_blueprint


def criar_aplicacao(configuracao: Configuracao | None = None) -> Flask:
    """Monta a aplicação e liga suas partes sem carregar dados ainda."""
    configuracao = configuracao or Configuracao.a_partir_das_variaveis()
    aplicacao = Flask(__name__)
    aplicacao.config.from_mapping(
        MAX_CONTENT_LENGTH=configuracao.limite_requisicao,
        JSON_SORT_KEYS=False,
    )

    repositorio = RepositorioDados(
        configuracao.caminho_dados,
        configuracao.caminho_dados_selecionados,
    )
    servico = ServicoRelatorio(repositorio)
    aplicacao.register_blueprint(criar_blueprint(servico))
    registrar_tratamento_de_erros(aplicacao)
    _registrar_protecoes_http(aplicacao)
    return aplicacao


def _registrar_protecoes_http(aplicacao: Flask) -> None:
    registro = logging.getLogger("quadra_analitica.http")

    @aplicacao.before_request
    def iniciar_requisicao() -> None:
        g.identificador_requisicao = str(uuid4())
        g.inicio_requisicao = time.perf_counter()

    @aplicacao.after_request
    def concluir_requisicao(resposta):
        resposta.headers["X-Request-ID"] = g.get("identificador_requisicao", "")
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resposta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        duracao = (time.perf_counter() - g.get("inicio_requisicao", time.perf_counter())) * 1000
        registro.info(
            "%s %s status=%s duracao_ms=%.2f id=%s",
            request.method,
            request.path,
            resposta.status_code,
            duracao,
            g.get("identificador_requisicao"),
        )
        return resposta


aplicacao = criar_aplicacao()


if __name__ == "__main__":
    aplicacao.run(host="0.0.0.0", port=5000)
