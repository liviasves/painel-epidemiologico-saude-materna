import requests
from collections import Counter

URL = ("https://apidadosabertos.saude.gov.br/vigilancia-e-meio-ambiente/"
       "sistema-de-informacao-sobre-mortalidade")


def buscar(offset, limit=1000):
    resp = requests.get(URL, params={"limit": limit, "offset": offset},
                        headers={"accept": "application/json"}, timeout=120)
    return resp.json().get("sim", [])


# 1. Amostra páginas em pontos diferentes
print("Amostragem de páginas:")
for offset in [0, 10, 100, 500, 1000, 1500, 2000]:
    try:
        regs = buscar(offset)
        anos = Counter(r["dtobito"][-4:] for r in regs if r.get("dtobito"))
        print(f"  offset {offset:>5}: {len(regs):>4} registros | anos: {dict(anos)}")
    except Exception as e:
        print(f"  offset {offset:>5}: ERRO {e}")

# 2. Busca binária para achar a última página com dados
baixo, alto = 0, 5000
while baixo < alto:
    meio = (baixo + alto + 1) // 2
    if buscar(meio):
        baixo = meio
    else:
        alto = meio - 1
print(f"\nÚltima página com dados: offset = {baixo}")
print(f"Total aproximado de registros: {(baixo + 1) * 1000:,}".replace(",", "."))