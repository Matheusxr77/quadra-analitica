"""Casos de uso das páginas do relatório."""

from typing import Any

import pandas as pd

from analise import (
    VARIAVEIS_ANALISADAS,
    TIMES_ANALISADOS,
    calcular_dicionario,
    calcular_estatisticas,
    calcular_perfil_z,
    calcular_tabela_descritiva,
    comparar_times,
)
from excecoes import ErroAplicacao
from interpretacao import calcular_assimetria, calcular_cv, calcular_iqr, interpretar_variavel
from qualidade import calcular_qualidade
from sintese import calcular_resposta_zscore, calcular_sintese
from infraestrutura.repositorio_dados import RepositorioDados


class ServicoRelatorio:
    """Valida as escolhas do usuário e chama o domínio."""

    def __init__(self, repositorio: RepositorioDados) -> None:
        self._repositorio = repositorio
        self._qualidade: dict[str, Any] | None = None

    def estatisticas(self, time: str, variavel: str) -> dict[str, Any]:
        if time != "Todos" and time not in TIMES_ANALISADOS:
            raise ErroAplicacao("O time informado não pertence ao escopo do relatório.")
        if variavel not in VARIAVEIS_ANALISADAS:
            raise ErroAplicacao("A variável informada não está disponível no relatório.")
        dados = self._obter_dados()
        resultado = calcular_estatisticas(dados, time, variavel)
        perfil = calcular_perfil_z(dados)
        comparacao = comparar_times(dados, variavel)
        resultado["perfil_z"] = next(v for v in perfil["variaveis"] if v["variavel"] == variavel)
        resultado["comparacao"] = comparacao
        resultado["interpretacao"] = interpretar_variavel(dados, time, variavel, perfil, comparacao)
        return resultado

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
        # Dados estáticos e cálculo custoso: calcula uma vez.
        if self._qualidade is None:
            fonte, recorte = self._repositorio.obter_bases_brutas()
            self._qualidade = calcular_qualidade(self._obter_dados(), fonte, recorte)
        return self._qualidade

    def perfil_z(self) -> dict[str, Any]:
        return calcular_resposta_zscore(self._obter_dados())

    def sintese(self) -> dict[str, Any]:
        return calcular_sintese(self._obter_dados(), self.qualidade(), self.dicionario())

    def _obter_dados(self) -> pd.DataFrame:
        return self._repositorio.obter_dados()
