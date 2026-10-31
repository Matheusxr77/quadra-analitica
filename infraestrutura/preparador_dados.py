from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

from analise import TIMES_ANALISADOS
from excecoes import ErroDados

"""Cria um CSV separado somente com os dois times do grupo."""


def gerar_base_dos_times(
    caminho_origem: Path, caminho_destino: Path
) -> Path:
    """Seleciona os dois times do grupo e salva um CSV antes dos cálculos.

    Assim, a análise nunca precisa consultar os registros dos outros times.
    """
    if not caminho_origem.is_file():
        raise ErroDados("A fonte original dos dados não foi encontrada.")
    try:
        dados = pd.read_csv(caminho_origem)
    except (OSError, pd.errors.ParserError) as erro:
        raise ErroDados("Não foi possível ler a fonte original dos dados.") from erro
    if "TEAM_NAME" not in dados.columns:
        raise ErroDados("A fonte original não possui a coluna TEAM_NAME.")

    dados_selecionados = dados[
        dados["TEAM_NAME"].isin(TIMES_ANALISADOS)
    ].copy()
    if dados_selecionados.empty:
        raise ErroDados("A fonte não possui registros dos times selecionados.")

    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".csv",
        dir=caminho_destino.parent,
        delete=False,
    ) as arquivo_temporario:
        caminho_temporario = Path(arquivo_temporario.name)
    try:
        dados_selecionados.to_csv(
            caminho_temporario, index=False, encoding="utf-8"
        )
        caminho_temporario.replace(caminho_destino)
    except OSError as erro:
        caminho_temporario.unlink(missing_ok=True)
        raise ErroDados("Não foi possível gerar a base dos times selecionados.") from erro
    return caminho_destino
