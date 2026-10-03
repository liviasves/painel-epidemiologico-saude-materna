import pandas as pd
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO = RAIZ / "dados" / "brutos" / "sinasc_2024.csv"

df = pd.read_csv(ARQUIVO, sep=";", encoding="latin-1",
                 nrows=1000, dtype=str)
print(df.columns.tolist())
print(df.head())