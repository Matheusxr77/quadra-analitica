from pathlib import Path
from threading import Lock

import pandas as pd

from analise import TIMES_ANALISADOS
from excecoes import ErroDados
from infraestrutura.preparador_dados import gerar_base_dos_times



"""Lê e prepara a base que será usada pela análise."""


class RepositorioDados:
    """Mantém os dados prontos em memória e entrega uma cópia para cada uso."""

    colunas_obrigatorias = {
        "TEAM_NAME",
        "Game_ID",
        "GAME_DATE",
        "PTS",
        "REB",
        "AST",
        "STL",
        "BLK",
        "PF",
        "FG3M",
    }

    def __init__(
        self, caminho: Path, caminho_selecionados: Path | None = None
    ) -> None:
        self._caminho_origem = caminho
        self._caminho_selecionados = caminho_selecionados or (
            caminho.parent / "estatisticas_times_selecionados.csv"
        )
        self._dados: pd.DataFrame | None = None
        self._brutas: tuple[pd.DataFrame, pd.DataFrame] | None = None
        self._bloqueio = Lock()

    def obter_dados(self) -> pd.DataFrame:
        """Prepara os dados no primeiro uso e devolve uma cópia segura."""
        if self._dados is None:
            with self._bloqueio:
                if self._dados is None:
                    self._dados = self._carregar()
        return self._dados.copy(deep=True)

    def obter_bases_brutas(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Fonte completa e recorte do grupo exatamente como estão nos CSVs.

        Usadas só no diagnóstico de qualidade: duplicatas e ausentes precisam
        ser medidos antes da tipagem e da deduplicação feitas em _carregar.
        """
        self.obter_dados()  # garante que o recorte derivado exista
        with self._bloqueio:
            if self._brutas is None:
                try:
                    self._brutas = (
                        pd.read_csv(self._caminho_origem),
                        pd.read_csv(self._caminho_selecionados),
                    )
                except (OSError, pd.errors.ParserError) as erro:
                    raise ErroDados("Não foi possível ler as bases brutas.") from erro
            fonte, recorte = self._brutas
        return fonte.copy(deep=True), recorte.copy(deep=True)

    def recarregar(self) -> None:
        """Lê novamente a fonte, regenera a base filtrada e atualiza o cache."""
        with self._bloqueio:
            self._dados = self._carregar()
            self._brutas = None

    def _carregar(self) -> pd.DataFrame:
        gerar_base_dos_times(
            self._caminho_origem, self._caminho_selecionados
        )
        try:
            dados = pd.read_csv(self._caminho_selecionados)
        except (OSError, pd.errors.ParserError) as erro:
            raise ErroDados("Não foi possível ler a fonte estatística.") from erro
        faltantes = self.colunas_obrigatorias.difference(dados.columns)
        if faltantes:
            nomes = ", ".join(sorted(faltantes))
            raise ErroDados(f"A fonte estatística não contém colunas obrigatórias: {nomes}.")
        dados["GAME_DATE"] = pd.to_datetime(dados["GAME_DATE"], errors="coerce")
        for coluna in dados.columns:
            if coluna not in ("GAME_DATE", "MATCHUP", "TEAM_NAME"):
                dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")
        for coluna in ("W_PCT", "FG_PCT", "FG3_PCT", "FT_PCT"):
            if coluna in dados:
                serie = dados[coluna]
                serie = serie.where(serie <= 1, serie / 1000)
                dados[coluna] = serie.where(serie.between(0, 1))
        dados["WL"] = dados["WL"].astype("Int64")
        dados = dados[dados["TEAM_NAME"].isin(TIMES_ANALISADOS)].copy()
        dados = dados.drop_duplicates(subset=["TEAM_NAME", "Game_ID"])
        return dados.sort_values(
            ["TEAM_NAME", "GAME_DATE"], ascending=[True, False]
        ).reset_index(drop=True)
