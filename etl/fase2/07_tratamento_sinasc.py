from datetime import datetime

import numpy as np
import pandas as pd
from comum import ANOS, BRUTOS, TRATADOS, faixa_etaria, ler_csv_em_blocos, padronizar_codigo

COLUNAS = ["DTNASC", "CODMUNRES", "IDADEMAE", "RACACORMAE", "ESCMAE2010",
           "PARTO", "TPROBSON", "CONSPRENAT", "STCESPARTO", "STTRABPART"]

# Códigos válidos segundo o dicionário de dados do SINASC (9 = ignorado).
# STCESPARTO e STTRABPART: 1 = sim, 2 = não, 3 = não se aplica, 9 = ignorado.
VALIDOS = {
    "RACACORMAE": "12345",
    "ESCMAE2010": "0123459",
    "PARTO": "129",
    "STCESPARTO": "1239",
    "STTRABPART": "1239",
}

DIM_MUNICIPIO = ["ano", "cod_mun_res", "faixa_etaria", "cod_raca_cor", "cod_escolaridade"]
DIM_PARTO = ["ano", "cod_uf", "faixa_etaria", "cod_raca_cor", "cod_escolaridade",
             "cod_parto", "grupo_robson", "faixa_prenatal",
             "cod_cesarea_antes_tp", "cod_tp_induzido"]


def faixa_prenatal(consultas: pd.Series) -> pd.Series:
    """Faixas de consultas de pré-natal usadas pelo Ministério da Saúde."""
    n = pd.to_numeric(consultas, errors="coerce")
    n = n.where(n < 99)                       # 99 = ignorado
    return pd.Series(np.select(
        [n == 0, n.between(1, 3), n.between(4, 6), n >= 7],
        ["Nenhuma", "1 a 3", "4 a 6", "7 ou mais"],
        default="Ignorado",
    ), index=consultas.index)


def tratar_bloco(bloco: pd.DataFrame, ano: int) -> pd.DataFrame:
    idade = pd.to_numeric(bloco["IDADEMAE"], errors="coerce")
    idade = idade.where(idade.between(5, 70))  # fora disso: ignorada (ex.: 99)

    robson = pd.to_numeric(bloco["TPROBSON"], errors="coerce")  # '05' e '5' -> 5
    robson = robson.where(robson.between(1, 11)).fillna(99).astype(int)  # 99 = ignorado

    cod_mun = bloco["CODMUNRES"].str[:6]

    return pd.DataFrame({
        "ano": ano,
        "cod_mun_res": cod_mun,
        "cod_uf": cod_mun.str[:2],
        "faixa_etaria": faixa_etaria(idade),
        "cod_raca_cor": padronizar_codigo(bloco["RACACORMAE"], VALIDOS["RACACORMAE"]),
        "cod_escolaridade": padronizar_codigo(bloco["ESCMAE2010"], VALIDOS["ESCMAE2010"]),
        "cod_parto": padronizar_codigo(bloco["PARTO"], VALIDOS["PARTO"]),
        "grupo_robson": robson,
        "faixa_prenatal": faixa_prenatal(bloco["CONSPRENAT"]),
        "cod_cesarea_antes_tp": padronizar_codigo(bloco["STCESPARTO"], VALIDOS["STCESPARTO"]),
        "cod_tp_induzido": padronizar_codigo(bloco["STTRABPART"], VALIDOS["STTRABPART"]),
    })


def agregar(partes: list[pd.Series], dimensoes: list[str]) -> pd.DataFrame:
    """Soma as contagens parciais de cada bloco (um grupo aparece em vários blocos)."""
    total = pd.concat(partes).groupby(level=list(range(len(dimensoes)))).sum()
    total.index.names = dimensoes
    return total.rename("qtd_nascidos").reset_index()


def processar_ano(ano: int):
    arquivo = BRUTOS / f"sinasc_{ano}.csv"
    linhas_lidas = 0
    ano_divergente = 0
    partes_mun, partes_parto = [], []

    for bloco in ler_csv_em_blocos(arquivo, COLUNAS, tamanho=500_000):
        linhas_lidas += len(bloco)
        ano_divergente += int((bloco["DTNASC"].str[-4:] != str(ano)).sum())
        t = tratar_bloco(bloco, ano)
        partes_mun.append(t.groupby(DIM_MUNICIPIO, dropna=False).size())
        partes_parto.append(t.groupby(DIM_PARTO, dropna=False).size())

    fato_mun = agregar(partes_mun, DIM_MUNICIPIO)
    fato_parto = agregar(partes_parto, DIM_PARTO)

    controle = {
        "base": "SINASC",
        "ano": ano,
        "arquivo_origem": arquivo.name,
        "tamanho_mb": round(arquivo.stat().st_size / 1024**2, 1),
        "linhas_lidas": linhas_lidas,
        "linhas_fato_municipio": len(fato_mun),
        "soma_fato_municipio": int(fato_mun["qtd_nascidos"].sum()),
        "linhas_fato_parto": len(fato_parto),
        "soma_fato_parto": int(fato_parto["qtd_nascidos"].sum()),
        "ano_divergente": ano_divergente,
        "processado_em": datetime.now().isoformat(timespec="seconds"),
    }
    return fato_mun, fato_parto, controle


def fmt(n: int) -> str:
    """Formata número com separador de milhar brasileiro (1.234.567)."""
    return f"{n:,}".replace(",", ".")


def main() -> None:
    TRATADOS.mkdir(parents=True, exist_ok=True)
    fatos_mun, fatos_parto, controles = [], [], []

    for ano in ANOS:
        print(f"Processando SINASC {ano}...")
        fato_mun, fato_parto, c = processar_ano(ano)
        fatos_mun.append(fato_mun)
        fatos_parto.append(fato_parto)
        controles.append(c)

        # Veracidade: a agregação não pode perder nem criar nascimentos
        ok = c["soma_fato_municipio"] == c["soma_fato_parto"] == c["linhas_lidas"]
        print(f"  {fmt(c['linhas_lidas'])} nascidos vivos | "
              f"fato município: {fmt(c['linhas_fato_municipio'])} linhas | "
            
              f"fato parto: {fmt(c['linhas_fato_parto'])} linhas | "
              f"somas conferem: {'SIM' if ok else 'NÃO'}")

    pd.concat(fatos_mun, ignore_index=True).to_csv(
        TRATADOS / "fato_nascidos_municipio.csv", index=False, encoding="utf-8")
    pd.concat(fatos_parto, ignore_index=True).to_csv(
        TRATADOS / "fato_nascidos_parto.csv", index=False, encoding="utf-8")
    pd.DataFrame(controles).to_csv(TRATADOS / "controle_sinasc.csv", index=False, encoding="utf-8")

    total_mun = sum(len(f) for f in fatos_mun)
    total_parto = sum(len(f) for f in fatos_parto)
    print(f"\nfato_nascidos_municipio.csv: {fmt(total_mun)} linhas")
    print(f"fato_nascidos_parto.csv: {fmt(total_parto)} linhas")
    print("controle_sinasc.csv: gravado")


if __name__ == "__main__":
    main()