"""Erros próprios da aplicação, com mensagens seguras para o usuário."""


class ErroAplicacao(Exception):
    """Representa um problema conhecido, como uma escolha inválida."""

    def __init__(self, mensagem: str, codigo_http: int = 400) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo_http = codigo_http


class ErroDados(ErroAplicacao):
    """Indica que a base não existe ou não tem o formato esperado."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem, 503)
