"""
Configurações e funções compartilhadas pelos scripts do ETL (fase 2).

Os scripts importam daqui os caminhos, os anos analisados e as regras
comuns ao SIM e ao SINASC, para que a mesma decisão nunca seja
implementada de dois jeitos diferentes.
"""
from pathlib import Path
import pandas as pd

# Caminhos (calculados a partir da pasta deste arquivo: etl/fase2/)
RAIZ = Path(__file__).resolve().parents[2]
BRUTOS = RAIZ / "dados" / "brutos"
TRATADOS = RAIZ / "dados" / "tratados"

# Recorte temporal definido na fase 1: três anos mais recentes consolidados
ANOS = [2022, 2023, 2024]

_LIMITES = [-1, 9, 14, 19, 24, 29, 34, 39, 44, 49, 200]
_ROTULOS = ["<10", "10-14", "15-19", "20-24", "25-29",
            "30-34", "35-39", "40-44", "45-49", "50+"]


def faixa_etaria(idade: pd.Series) -> pd.Series:
    """Converte idade em anos para a faixa etária; sem idade -> 'Ignorada'."""
    faixa = pd.cut(idade, bins=_LIMITES, labels=_ROTULOS)
    return faixa.astype("string").fillna("Ignorada")


def padronizar_codigo(serie: pd.Series, validos: str, ignorado: str = "9") -> pd.Series:
    """
    Mantém apenas os códigos válidos do dicionário de dados.
    Vazio, nulo ou código fora da lista vira o código de 'ignorado' (9),
    unificando as duas formas de ausência encontradas na exploração.
    """
    serie = serie.fillna("").str.strip()
    return serie.where(serie.isin(list(validos)), ignorado)


def ler_csv_em_blocos(arquivo: Path, colunas: list[str], tamanho: int = 200_000):
    """
    Lê o CSV em blocos, apenas com as colunas pedidas (minimização de dados).
    Os nomes são padronizados em maiúsculas, porque a caixa muda entre
    os anos (ex.: 'contador' em 2024 e 'CONTADOR' em 2022/2023).
    Vazios são lidos como texto vazio, igual nos arquivos CSV e DBC.
    """
    leitor = pd.read_csv(
        arquivo, sep=";", encoding="latin-1", dtype=str,
        usecols=lambda c: c.upper() in colunas,
        keep_default_na=False, chunksize=tamanho,
    )
    for bloco in leitor:
        bloco.columns = bloco.columns.str.upper()
        yield bloco