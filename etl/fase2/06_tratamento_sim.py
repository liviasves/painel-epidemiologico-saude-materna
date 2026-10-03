from datetime import datetime

import numpy as np
import pandas as pd

from comum import ANOS, BRUTOS, TRATADOS, faixa_etaria, ler_csv_em_blocos, padronizar_codigo

# Colunas lidas do arquivo bruto. Todas as demais (datas de nascimento,
# estabelecimento, ocupação, naturalidade etc.) são descartadas por LGPD.
COLUNAS = ["DTOBITO", "SEXO", "IDADE", "RACACOR", "ESTCIV", "ESC2010",
           "CODMUNRES", "LOCOCOR", "CAUSABAS", "CAUSAMAT",
           "TPMORTEOCO", "OBITOGRAV", "OBITOPUERP", "ASSISTMED"]

# Códigos válidos segundo o dicionário de dados do SIM (9 = ignorado)
VALIDOS = {
    "RACACOR": "12345",
    "ESTCIV": "123459",
    "ESC2010": "0123459",
    "LOCOCOR": "1234569",
    "TPMORTEOCO": "1234589",
    "OBITOGRAV": "129",
    "OBITOPUERP": "1239",
    "ASSISTMED": "129",
}

# Total oficial do Painel de Monitoramento da Mortalidade Materna
# (consulta em 03/10/2026, óbitos por residência, "Maternos declarados")
PAINEL_MS = {2022: 1368, 2023: 1319, 2024: 1326}


def decodificar_idade(idade: pd.Series) -> pd.Series:
    """
    IDADE tem 3 dígitos: o 1º é a unidade e os 2 seguintes a quantidade.
    4 = anos (ex.: 425 -> 25 anos); 5 = mais de 100 anos (ex.: 502 -> 102).
    Outras unidades (minutos, horas, meses) não se aplicam a óbito materno.
    """
    unidade = idade.str[:1]
    quantidade = pd.to_numeric(idade.str[1:3], errors="coerce")
    anos = np.select([unidade == "4", unidade == "5"],
                     [quantidade, 100 + quantidade], default=np.nan)
    return pd.Series(anos, index=idade.index).astype("Int64")


def classificar(causabas: pd.Series) -> pd.Series:
    """Classificação do óbito, validada contra o MAT_CLAS e o painel do MS."""
    cap_o = causabas.str.startswith("O")
    tardio = causabas.str[:3].isin(["O96", "O97"])
    return pd.Series(np.select(
        [cap_o & ~tardio, tardio, ~cap_o],
        ["Materno (entra na RMM)", "Materno tardio", "Associado a causa externa"],
        default="Não classificado",
    ), index=causabas.index)


def processar_ano(ano: int) -> tuple[pd.DataFrame, dict]:
    arquivo = BRUTOS / f"sim_{ano}.csv"
    linhas_lidas = 0
    selecionados = []

    # 1. Leitura em blocos + seleção dos óbitos maternos
    for bloco in ler_csv_em_blocos(arquivo, COLUNAS):
        linhas_lidas += len(bloco)
        feminino = bloco["SEXO"].isin(["2", "F"])
        cap_o = bloco["CAUSABAS"].str.startswith("O")
        marcador_o93 = bloco["CAUSAMAT"].str.strip() != ""
        selecionados.append(bloco[feminino & (cap_o | marcador_o93)])

    df = pd.concat(selecionados, ignore_index=True)

    # 2. Transformações
    data = pd.to_datetime(df["DTOBITO"], format="%d%m%Y", errors="coerce")
    idade = decodificar_idade(df["IDADE"])

    fato = pd.DataFrame({
        "ano": ano,
        "mes": data.dt.month.astype("Int64"),
        "data_obito": data.dt.date,
        "cod_mun_res": df["CODMUNRES"].str[:6],
        "idade": idade,
        "faixa_etaria": faixa_etaria(idade),
        "cod_raca_cor": padronizar_codigo(df["RACACOR"], VALIDOS["RACACOR"]),
        "cod_estado_civil": padronizar_codigo(df["ESTCIV"], VALIDOS["ESTCIV"]),
        "cod_escolaridade": padronizar_codigo(df["ESC2010"], VALIDOS["ESC2010"]),
        "cod_local_ocorrencia": padronizar_codigo(df["LOCOCOR"], VALIDOS["LOCOCOR"]),
        "cod_causa_basica": df["CAUSABAS"].str.strip(),
        "cod_causa_externa": df["CAUSAMAT"].str.strip().replace("", pd.NA),
        "cod_momento_obito": padronizar_codigo(df["TPMORTEOCO"], VALIDOS["TPMORTEOCO"]),
        "obito_gravidez": padronizar_codigo(df["OBITOGRAV"], VALIDOS["OBITOGRAV"]),
        "obito_puerperio": padronizar_codigo(df["OBITOPUERP"], VALIDOS["OBITOPUERP"]),
        "assistencia_medica": padronizar_codigo(df["ASSISTMED"], VALIDOS["ASSISTMED"]),
        "tipo_obito": classificar(df["CAUSABAS"]),
    })
    fato["entra_rmm"] = fato["tipo_obito"] == "Materno (entra na RMM)"

    # 3. Registro de controle (rastreabilidade: origem -> resultado)
    tipos = fato["tipo_obito"].value_counts()
    controle = {
        "base": "SIM",
        "ano": ano,
        "arquivo_origem": arquivo.name,
        "tamanho_mb": round(arquivo.stat().st_size / 1024**2, 1),
        "linhas_lidas": linhas_lidas,
        "linhas_selecionadas": len(fato),
        "entra_rmm": int(tipos.get("Materno (entra na RMM)", 0)),
        "tardio": int(tipos.get("Materno tardio", 0)),
        "causa_externa": int(tipos.get("Associado a causa externa", 0)),
        "datas_invalidas": int(data.isna().sum()),
        "ano_divergente": int((data.dt.year != ano).sum()),
        "idade_ignorada": int(idade.isna().sum()),
        "painel_ms": PAINEL_MS.get(ano),
        "processado_em": datetime.now().isoformat(timespec="seconds"),
    }
    return fato, controle


def fmt(n: int) -> str:
    """Formata número com separador de milhar brasileiro (1.234.567)."""
    return f"{n:,}".replace(",", ".")


def main() -> None:
    TRATADOS.mkdir(parents=True, exist_ok=True)
    fatos, controles = [], []

    for ano in ANOS:
        print(f"Processando SIM {ano}...")
        fato, controle = processar_ano(ano)
        fatos.append(fato)
        controles.append(controle)

        dif = controle["entra_rmm"] - controle["painel_ms"]
        print(f"  {fmt(controle['linhas_lidas'])} lidas -> {fmt(controle['linhas_selecionadas'])} "
              f"selecionadas | RMM: {fmt(controle['entra_rmm'])} "
              f"(painel MS: {fmt(controle['painel_ms'])}, diferença {dif:+d})")

    fato = pd.concat(fatos, ignore_index=True)
    fato.insert(0, "id_obito", range(1, len(fato) + 1))  # chave substituta

    fato.to_csv(TRATADOS / "fato_obito_materno.csv", index=False, encoding="utf-8")
    pd.DataFrame(controles).to_csv(TRATADOS / "controle_sim.csv", index=False, encoding="utf-8")

    print(f"\nfato_obito_materno.csv: {fmt(len(fato))} linhas, {fato.shape[1]} colunas")
    print("controle_sim.csv: gravado")


if __name__ == "__main__":
    main()