"""Transforma erros em respostas claras sem revelar detalhes internos."""

import logging
from uuid import uuid4

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from excecoes import ErroAplicacao

registro = logging.getLogger(__name__)


def registrar_tratamento_de_erros(aplicacao: Flask) -> None:
    @aplicacao.errorhandler(ErroAplicacao)
    def tratar_erro_de_aplicacao(erro: ErroAplicacao):
        return jsonify({"erro": erro.mensagem}), erro.codigo_http

    @aplicacao.errorhandler(RequestEntityTooLarge)
    def tratar_requisicao_grande(_erro: RequestEntityTooLarge):
        return jsonify({"erro": "A requisição excede o limite permitido."}), 413

    @aplicacao.errorhandler(HTTPException)
    def tratar_erro_http(erro: HTTPException):
        return jsonify({"erro": erro.description}), erro.code

    @aplicacao.errorhandler(Exception)
    def tratar_erro_inesperado(erro: Exception):
        identificador = str(uuid4())
        registro.exception(
            "Erro inesperado na requisição %s %s, id=%s",
            request.method,
            request.path,
            identificador,
        )
        return jsonify(
            {
                "erro": "Ocorreu um erro interno. Consulte o identificador.",
                "identificador": identificador,
            }
        ), 500
