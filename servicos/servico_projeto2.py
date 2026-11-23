"""Serviço de aplicação para os requisitos do Projeto 2 (Clustering)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from analise import TIMES_ANALISADOS
import clustering
from excecoes import ErroAplicacao
from infraestrutura.repositorio_dados import RepositorioDados


class ServicoProjeto2:
    """Orquestra as operações analíticas das Partes 1, 2 e 3 do Projeto 2."""

    def __init__(self, repositorio: RepositorioDados) -> None:
        self._repositorio = repositorio
        self._cache_parte2: dict[int, dict[str, Any]] = {}
        self._cache_parte3: dict[int, dict[str, Any]] = {}

    def obter_dados_selecionados(self, time: str = "Todos") -> pd.DataFrame:
        """Obtém dados tratados dos times atribuídos ao grupo (Dallas Mavericks e Indiana Pacers)."""
        dados = self._repositorio.obter_dados()
        if time != "Todos":
            if time not in TIMES_ANALISADOS:
                raise ErroAplicacao(f"O time '{time}' não pertence ao escopo do trabalho.")
            dados = dados[dados["TEAM_NAME"] == time].copy()
        return dados

    def obter_dados_liga(self) -> pd.DataFrame:
        """Obtém a base tratada de todos os 30 times da NBA."""
        fonte, _ = self._repositorio.obter_bases_brutas()
        for col in clustering.VARIAVEIS_CLUSTERING:
            if col in fonte.columns:
                fonte[col] = pd.to_numeric(fonte[col], errors="coerce")
        if "GAME_DATE" in fonte.columns:
            fonte["GAME_DATE"] = pd.to_datetime(fonte["GAME_DATE"], errors="coerce")
        fonte = fonte.dropna(subset=clustering.VARIAVEIS_CLUSTERING + ["TEAM_NAME"])
        return fonte.drop_duplicates(subset=["TEAM_NAME", "Game_ID"])

    def parte1_kmeans(self, time: str = "Todos", k: int = 3) -> dict[str, Any]:
        """Calcula a Parte 1: K-Means (K=2, 3 ou 4) para Dallas Mavericks e Indiana Pacers."""
        if k < 2 or k > 6:
            raise ErroAplicacao("O valor de K deve ser no mínimo 2 (permitido: 2, 3, 4, 5, 6).")
        df = self.obter_dados_selecionados(time)
        resultado = clustering.executar_kmeans(df, k=k)
        resultado["time_selecionado"] = time
        resultado["times_disponiveis"] = ["Todos"] + TIMES_ANALISADOS
        return resultado

    def parte1_comparar_k(self, time: str = "Todos") -> dict[str, Any]:
        """Calcula o Silhouette Score e métricas comparativas entre K=2, K=3 e K=4."""
        df = self.obter_dados_selecionados(time)
        return clustering.comparar_configuracoes_k(df, valores_k=[2, 3, 4])

    def parte2_multiplos_algoritmos(self, k: int = 3) -> dict[str, Any]:
        """Calcula a Parte 2: comparação dos 5 algoritmos de clustering."""
        if k not in self._cache_parte2:
            df = self.obter_dados_selecionados("Todos")
            self._cache_parte2[k] = clustering.executar_parte2_multiplos_algoritmos(df, k=k)
        return self._cache_parte2[k]

    def parte3_analise_global(self, k: int = 4) -> dict[str, Any]:
        """Calcula a Parte 3: análise global de todos os 30 times da NBA."""
        if k not in self._cache_parte3:
            df_liga = self.obter_dados_liga()
            self._cache_parte3[k] = clustering.executar_parte3_analise_global(df_liga, k=k)
        return self._cache_parte3[k]

    def teoria(self) -> dict[str, Any]:
        """Retorna os fundamentos teóricos e formulação matemática exigida."""
        return clustering.obter_fundamentos_teoricos()
