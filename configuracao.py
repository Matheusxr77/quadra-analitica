"""Define os caminhos e opções usados pela aplicação."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Configuracao:
    """Reúne as configurações usadas pela aplicação."""

    caminho_dados: Path
    limite_requisicao: int
    caminho_dados_selecionados: Path | None = None

    @classmethod
    def a_partir_das_variaveis(cls) -> "Configuracao":
        """Lê caminhos e limites definidos para a execução da aplicação."""
        return cls(
            caminho_dados=Path(
                os.getenv(
                    "CAMINHO_DADOS",
                    Path(__file__).parent
                    / "dados"
                    / "stats_times_regular_final.csv",
                )
            ),
            limite_requisicao=int(os.getenv("LIMITE_REQUISICAO_BYTES", "1048576")),
            caminho_dados_selecionados=Path(
                os.getenv(
                    "CAMINHO_DADOS_SELECIONADOS",
                    Path(__file__).parent
                    / "dados"
                    / "estatisticas_times_selecionados.csv",
                )
            ),
        )
