"""Erros da aplicação com mensagens seguras para o usuário."""


class ErroAplicacao(Exception):
    """Problema conhecido, como uma escolha inválida."""

    def __init__(self, mensagem: str, codigo_http: int = 400) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo_http = codigo_http


class ErroDados(ErroAplicacao):
    """Base ausente ou fora do formato esperado."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem, 503)
