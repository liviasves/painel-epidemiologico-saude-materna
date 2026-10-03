import pandas as pd

from comum import BRUTOS, TRATADOS

CID = BRUTOS / "cid10"


def salvar(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    df.to_csv(TRATADOS / f"{nome}.csv", index=False, encoding="utf-8")
    print(f"  {nome}: {len(df)} linhas")
    return df


def tabela(linhas: list[tuple], colunas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(linhas, columns=colunas)


# Dimensões categóricas (fonte: dicionários de dados do SIM e do SINASC)
def dimensoes_categoricas() -> dict[str, pd.DataFrame]:
    d = {}
    d["dim_raca_cor"] = tabela([
        ("1", "Branca", "Branca"),
        ("2", "Preta", "Negra (preta + parda)"),
        ("3", "Amarela", "Amarela"),
        ("4", "Parda", "Negra (preta + parda)"),
        ("5", "Indígena", "Indígena"),
        ("9", "Ignorado", "Ignorado"),
    ], ["cod_raca_cor", "raca_cor", "raca_cor_agregada"])

    d["dim_escolaridade"] = tabela([
        ("0", "Sem escolaridade", 0),
        ("1", "Fundamental I (1ª a 4ª série)", 1),
        ("2", "Fundamental II (5ª a 8ª série)", 2),
        ("3", "Médio", 3),
        ("4", "Superior incompleto", 4),
        ("5", "Superior completo", 5),
        ("9", "Ignorado", 9),
    ], ["cod_escolaridade", "escolaridade", "ordem"])

    d["dim_estado_civil"] = tabela([
        ("1", "Solteira"), ("2", "Casada"), ("3", "Viúva"),
        ("4", "Separada judicialmente/divorciada"), ("5", "União estável"),
        ("9", "Ignorado"),
    ], ["cod_estado_civil", "estado_civil"])

    d["dim_local_ocorrencia"] = tabela([
        ("1", "Hospital"), ("2", "Outros estabelecimentos de saúde"),
        ("3", "Domicílio"), ("4", "Via pública"), ("5", "Outros"),
        ("6", "Aldeia indígena"), ("9", "Ignorado"),
    ], ["cod_local_ocorrencia", "local_ocorrencia"])

    d["dim_momento_obito"] = tabela([
        ("1", "Na gravidez"), ("2", "No parto"), ("3", "No abortamento"),
        ("4", "Até 42 dias após o parto"), ("5", "De 43 dias a 1 ano após a gestação"),
        ("8", "Não ocorreu nestes períodos"), ("9", "Ignorado"),
    ], ["cod_momento_obito", "momento_obito"])

    d["dim_tipo_parto"] = tabela([
        ("1", "Vaginal"), ("2", "Cesáreo"), ("9", "Ignorado"),
    ], ["cod_parto", "tipo_parto"])

    # Usada por STCESPARTO, STTRABPART, OBITOGRAV, ASSISTMED
    d["dim_sim_nao"] = tabela([
        ("1", "Sim"), ("2", "Não"), ("3", "Não se aplica"), ("9", "Ignorado"),
    ], ["cod_sim_nao", "descricao"])

    # Classificação de Robson (OMS) para monitorar as taxas de cesárea
    d["dim_grupo_robson"] = tabela([
        (1, "Nulípara, gestação única, cefálica, ≥37 semanas, trabalho de parto espontâneo", "1 a 4 (baixo risco)"),
        (2, "Nulípara, gestação única, cefálica, ≥37 semanas, parto induzido ou cesárea antes do trabalho de parto", "1 a 4 (baixo risco)"),
        (3, "Multípara sem cesárea anterior, única, cefálica, ≥37 semanas, trabalho de parto espontâneo", "1 a 4 (baixo risco)"),
        (4, "Multípara sem cesárea anterior, única, cefálica, ≥37 semanas, parto induzido ou cesárea antes do trabalho de parto", "1 a 4 (baixo risco)"),
        (5, "Multípara com cesárea anterior, única, cefálica, ≥37 semanas", "5 (cesárea anterior)"),
        (6, "Nulípara com apresentação pélvica", "6 a 10"),
        (7, "Multípara com apresentação pélvica (inclui cesárea anterior)", "6 a 10"),
        (8, "Gestação múltipla (inclui cesárea anterior)", "6 a 10"),
        (9, "Situação transversa ou oblíqua (inclui cesárea anterior)", "6 a 10"),
        (10, "Gestação única, cefálica, <37 semanas (inclui cesárea anterior)", "6 a 10"),
        (11, "Não classificado por falta de informação", "Não classificado"),
        (99, "Ignorado", "Não classificado"),
    ], ["grupo_robson", "descricao", "agrupamento"])

    faixas = ["<10", "10-14", "15-19", "20-24", "25-29", "30-34",
              "35-39", "40-44", "45-49", "50+", "Ignorada"]
    d["dim_faixa_etaria"] = pd.DataFrame({"faixa_etaria": faixas, "ordem": range(len(faixas))})

    prenatal = ["Nenhuma", "1 a 3", "4 a 6", "7 ou mais", "Ignorado"]
    d["dim_faixa_prenatal"] = pd.DataFrame({"faixa_prenatal": prenatal, "ordem": range(len(prenatal))})

    d["dim_tipo_obito"] = tabela([
        ("Materno (entra na RMM)", True),
        ("Materno tardio", False),
        ("Associado a causa externa", False),
    ], ["tipo_obito", "entra_rmm"])
    return d



# Municípios e UFs (fonte: API de Localidades do IBGE)
def dimensoes_geograficas(codigos_usados: set[str]) -> dict[str, pd.DataFrame]:
    ibge = pd.read_csv(TRATADOS / "dim_municipio_ibge.csv", dtype=str)

    dim_uf = (ibge[["cod_mun_6", "uf_sigla", "uf_nome", "regiao"]]
              .assign(cod_uf=ibge["cod_mun_6"].str[:2])
              .drop(columns="cod_mun_6").drop_duplicates()
              .sort_values("cod_uf")[["cod_uf", "uf_sigla", "uf_nome", "regiao"]])

    municipios = ibge[["cod_mun_6", "cod_ibge_7", "municipio"]].rename(columns={"cod_mun_6": "cod_mun_res"})
    municipios["cod_uf"] = municipios["cod_mun_res"].str[:2]
    municipios["municipio_ignorado"] = False

    faltantes = sorted(codigos_usados - set(municipios["cod_mun_res"]))
    extras = pd.DataFrame({"cod_mun_res": faltantes})
    extras["cod_uf"] = extras["cod_mun_res"].str[:2]
    extras.loc[~extras["cod_uf"].isin(dim_uf["cod_uf"]), "cod_uf"] = "99"
    extras["cod_ibge_7"] = pd.NA
    extras["municipio"] = "Município ignorado"
    extras["municipio_ignorado"] = True
    if faltantes:
        print(f"  códigos de município fora do IBGE tratados como ignorados: {faltantes}")

    if (extras["cod_uf"] == "99").any():
        dim_uf = pd.concat([dim_uf, pd.DataFrame([{
            "cod_uf": "99", "uf_sigla": "IG", "uf_nome": "Ignorada", "regiao": "Ignorada"}])])

    dim_municipio = pd.concat([municipios, extras], ignore_index=True)
    return {"dim_uf": dim_uf, "dim_municipio": dim_municipio}

def ler_cid(nome: str) -> pd.DataFrame:
    df = pd.read_csv(CID / nome, sep=";", encoding="latin-1", dtype=str)
    return df.loc[:, ~df.columns.str.startswith("Unnamed")]

CID_MANUAL = {
    "O987": "Doença pelo HIV complicando a gravidez, o parto e o puerpério",
    "O142": "Síndrome HELLP",
}
O93 = "Óbito materno associado a causa externa (marcador O93, uso exclusivo do Brasil)"


def dimensao_causas(codigos: set[str]) -> pd.DataFrame:
    sub = ler_cid("CID-10-SUBCATEGORIAS.CSV").set_index("SUBCAT")["DESCRICAO"]
    cat = ler_cid("CID-10-CATEGORIAS.CSV").set_index("CAT")["DESCRICAO"]
    grupos = ler_cid("CID-10-GRUPOS.CSV")
    capitulos = ler_cid("CID-10-CAPITULOS.CSV")

    causas = pd.DataFrame({"cod_causa": sorted(codigos)})
    c = causas["cod_causa"]

    # descrição em cascata: subcategoria -> tabela manual -> categoria -> O93
    causas["descricao"] = (c.map(sub)
                           .fillna(c.map(CID_MANUAL))
                           .fillna(c.str[:3].map(cat))
                           .fillna(c.where(c.str.startswith("O93")).map(lambda _: O93)))
    causas["categoria"] = c.str[:3]

    def faixa(tab, inicio, fim, rotulo):
        rotulos = pd.Series(pd.NA, index=c.index, dtype="string")
        for _, g in tab.iterrows():
            dentro = (causas["categoria"] >= g[inicio]) & (causas["categoria"] <= g[fim])
            rotulos = rotulos.mask(dentro & rotulos.isna(), g[rotulo])
        return rotulos

    causas["grupo_cid"] = faixa(grupos, "CATINIC", "CATFIM", "DESCRICAO")
    causas["capitulo_cid"] = faixa(capitulos, "CATINIC", "CATFIM", "DESCRICAO")
    causas.loc[c.str.startswith("O93"), "grupo_cid"] = "Óbito materno associado a causa externa"
    return causas

def checar_integridade(fatos: dict, dims: dict) -> bool:
    """Todo código usado em uma fato precisa existir na dimensão."""
    regras = [
        ("fato_obito_materno", "cod_mun_res", "dim_municipio", "cod_mun_res"),
        ("fato_obito_materno", "cod_raca_cor", "dim_raca_cor", "cod_raca_cor"),
        ("fato_obito_materno", "cod_escolaridade", "dim_escolaridade", "cod_escolaridade"),
        ("fato_obito_materno", "cod_estado_civil", "dim_estado_civil", "cod_estado_civil"),
        ("fato_obito_materno", "cod_local_ocorrencia", "dim_local_ocorrencia", "cod_local_ocorrencia"),
        ("fato_obito_materno", "cod_momento_obito", "dim_momento_obito", "cod_momento_obito"),
        ("fato_obito_materno", "faixa_etaria", "dim_faixa_etaria", "faixa_etaria"),
        ("fato_obito_materno", "cod_causa_basica", "dim_causa_obito", "cod_causa"),
        ("fato_obito_materno", "cod_causa_externa", "dim_causa_obito", "cod_causa"),
        ("fato_obito_materno", "tipo_obito", "dim_tipo_obito", "tipo_obito"),
        ("fato_nascidos_municipio", "cod_mun_res", "dim_municipio", "cod_mun_res"),
        ("fato_nascidos_municipio", "faixa_etaria", "dim_faixa_etaria", "faixa_etaria"),
        ("fato_nascidos_municipio", "cod_raca_cor", "dim_raca_cor", "cod_raca_cor"),
        ("fato_nascidos_municipio", "cod_escolaridade", "dim_escolaridade", "cod_escolaridade"),
        ("fato_nascidos_parto", "cod_uf", "dim_uf", "cod_uf"),
        ("fato_nascidos_parto", "cod_parto", "dim_tipo_parto", "cod_parto"),
        ("fato_nascidos_parto", "grupo_robson", "dim_grupo_robson", "grupo_robson"),
        ("fato_nascidos_parto", "faixa_prenatal", "dim_faixa_prenatal", "faixa_prenatal"),
        ("fato_nascidos_parto", "cod_cesarea_antes_tp", "dim_sim_nao", "cod_sim_nao"),
        ("fato_nascidos_parto", "cod_tp_induzido", "dim_sim_nao", "cod_sim_nao"),
    ]
    tudo_ok = True
    for fato, col, dim, chave in regras:
        usados = set(fatos[fato][col].dropna().astype(str))
        existentes = set(dims[dim][chave].astype(str))
        orfaos = usados - existentes
        if orfaos:
            tudo_ok = False
            print(f"  ERRO {fato}.{col} -> {dim}: {sorted(orfaos)[:10]}")
    return tudo_ok


def main() -> None:
    fatos = {
        nome: pd.read_csv(TRATADOS / f"{nome}.csv", dtype=str)
        for nome in ["fato_obito_materno", "fato_nascidos_municipio", "fato_nascidos_parto"]
    }

    print("Gerando dimensões...")
    dims = dimensoes_categoricas()

    codigos_mun = set(fatos["fato_obito_materno"]["cod_mun_res"].dropna()) | \
        set(fatos["fato_nascidos_municipio"]["cod_mun_res"].dropna())
    dims.update(dimensoes_geograficas(codigos_mun))

    ob = fatos["fato_obito_materno"]
    causas = set(ob["cod_causa_basica"].dropna()) | set(ob["cod_causa_externa"].dropna())
    dims["dim_causa_obito"] = dimensao_causas(causas)

    for nome, df in dims.items():
        salvar(df, nome)

    sem_desc = dims["dim_causa_obito"]["descricao"].isna().sum()
    print(f"\nCausas sem descrição: {sem_desc}")
    print("Integridade referencial:", "OK" if checar_integridade(fatos, dims) else "COM ERROS")


if __name__ == "__main__":
    main()