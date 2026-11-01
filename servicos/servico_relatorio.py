"""Regras que atendem às solicitações feitas pelas páginas do relatório."""

from typing import Any

import pandas as pd

from analise import (
    VARIAVEIS_ANALISADAS,
    TIMES_ANALISADOS,
    calcular_dicionario,
    calcular_estatisticas,
    calcular_qualidade,
    calcular_tabela_descritiva,
)
from excecoes import ErroAplicacao
from interpretacao import calcular_assimetria, calcular_cv, calcular_iqr
from infraestrutura.repositorio_dados import RepositorioDados


class ServicoRelatorio:
    """Valida as escolhas do usuário e pede os dados e cálculos necessários."""

    def __init__(self, repositorio: RepositorioDados) -> None:
        self._repositorio = repositorio

    def estatisticas(self, time: str, variavel: str) -> dict[str, Any]:
        if time != "Todos" and time not in TIMES_ANALISADOS:
            raise ErroAplicacao("O time informado não pertence ao escopo do relatório.")
        if variavel not in VARIAVEIS_ANALISADAS:
            raise ErroAplicacao("A variável informada não está disponível no relatório.")
        return calcular_estatisticas(self._obter_dados(), time, variavel)

    def tabela_descritiva(self) -> dict[str, Any]:
        return calcular_tabela_descritiva(self._obter_dados())

    def assimetria(self) -> dict[str, Any]:
        return calcular_assimetria(self._obter_dados())

    def cv(self) -> dict[str, Any]:
        return calcular_cv(self._obter_dados())

    def iqr(self) -> dict[str, Any]:
        return calcular_iqr(self._obter_dados())

    def dicionario(self) -> dict[str, Any]:
        return calcular_dicionario(self._obter_dados())

    def qualidade(self) -> dict[str, Any]:
        return calcular_qualidade(self._obter_dados())

    def _obter_dados(self) -> pd.DataFrame:
        return self._repositorio.obter_dados()
