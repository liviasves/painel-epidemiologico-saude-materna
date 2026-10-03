import requests
from datetime import datetime

BASE = "https://apidadosabertos.saude.gov.br/vigilancia-e-meio-ambiente/"

ENDPOINTS = {
    "SINASC": BASE + "sistema-de-informacao-sobre-nascidos-vivos",
    "SIM":    BASE + "sistema-de-informacao-sobre-mortalidade",
}

TESTES = [
    {"limit": 10,   "offset": 0},
    {"limit": 10,   "offset": 1},
    {"limit": 1000, "offset": 0},
    {"limit": 1000, "offset": 100},
]


def extrair_registros(dados):
    """Retorna (chave, lista) da primeira lista encontrada no JSON."""
    if isinstance(dados, list):
        return "(lista direta)", dados
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if isinstance(valor, list):
                return chave, valor
    return None, []


print(f"Teste executado em: {datetime.now():%d/%m/%Y %H:%M}")

for nome, url in ENDPOINTS.items():
    print(f"\n{'=' * 50}\n{nome}\n{'=' * 50}")

    for params in TESTES:
        try:
            resp = requests.get(url, params=params,
                                headers={"accept": "application/json"},
                                timeout=60)
            dados = resp.json()
            chave, registros = extrair_registros(dados)

            print(f"{params} -> HTTP {resp.status_code} | "
                  f"chave: {chave} | registros: {len(registros)}")

            if registros:
                print("  Campos:", list(registros[0].keys()))
                print("  Exemplo:", registros[0])
                break  # achou dados, passa para o próximo endpoint

        except requests.exceptions.RequestException as e:
            print(f"{params} -> ERRO de conexão: {e}")
        except ValueError:
            print(f"{params} -> HTTP {resp.status_code} | "
                  f"resposta não é JSON: {resp.text[:200]}")