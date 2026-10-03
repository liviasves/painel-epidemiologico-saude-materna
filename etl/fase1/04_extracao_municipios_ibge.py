import requests
import pandas as pd
from pathlib import Path

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

# caminho calculado a partir da pasta do próprio script
RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "tratados" / "dim_municipio_ibge.csv"

resp = requests.get(URL, timeout=60)
print(f"HTTP {resp.status_code}")

municipios = resp.json()
print(f"Municípios retornados: {len(municipios)}")
print("\nExemplo do JSON bruto (aninhado):")
print(municipios[0])


def achatar(m):
    """Transforma o JSON aninhado em uma linha de tabela."""
    if m.get("microrregiao"):
        uf = m["microrregiao"]["mesorregiao"]["UF"]
    else:
        uf = m["regiao-imediata"]["regiao-intermediaria"]["UF"]

    return {
        "cod_ibge_7": str(m["id"]),
        "cod_mun_6": str(m["id"])[:6],   # chave para join com SIM/SINASC
        "municipio": m["nome"],
        "uf_sigla": uf["sigla"],
        "uf_nome": uf["nome"],
        "regiao": uf["regiao"]["nome"],
    }


df = pd.DataFrame([achatar(m) for m in municipios])

print("\nTabela achatada:")
print(df.head())
print("\nMunicípios por região:")
print(df["regiao"].value_counts())

SAIDA.parent.mkdir(parents=True, exist_ok=True)  # cria a pasta se não existir
df.to_csv(SAIDA, index=False, encoding="utf-8")
print(f"\nArquivo salvo: {SAIDA}")