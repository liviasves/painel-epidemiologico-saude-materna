"""
10 - Validação da carga no PostgreSQL

Calcula os indicadores principais direto no banco, com SQL, usando os
relacionamentos entre fatos e dimensões, e compara com fontes oficiais:

- óbitos maternos: Painel de Monitoramento da Mortalidade Materna (MS);
- nascidos vivos: TabNet/DATASUS (Nascidos Vivos - Brasil, residência da mãe).

Execução (a partir da raiz do projeto ou de etl/fase2):
    python etl/fase2/10_validacao_carga.py
"""
import importlib

import pandas as pd
import psycopg

carga = importlib.import_module("09_carga_postgres")

# Fontes oficiais (consulta em 03/10/2026)
PAINEL_OBITOS = {2022: 1368, 2023: 1319, 2024: 1326}
TABNET_NASCIDOS = {2022: 2561922, 2023: 2537576, 2024: 2389325}
PAINEL_UF_2024 = {
    "RO": 7, "AC": 7, "AM": 41, "RR": 16, "PA": 82, "AP": 9, "TO": 16,
    "MA": 66, "PI": 35, "CE": 54, "RN": 26, "PB": 27, "PE": 50, "AL": 23,
    "SE": 15, "BA": 97, "MG": 125, "ES": 24, "RJ": 100, "SP": 201,
    "PR": 82, "SC": 44, "RS": 53, "MS": 17, "MT": 27, "GO": 67, "DF": 15,
}

SQL_RMM_ANO = """
WITH obitos AS (
    SELECT ano, count(*) AS obitos_rmm
    FROM fato_obito_materno
    WHERE entra_rmm
    GROUP BY ano
), nascidos AS (
    SELECT ano, sum(qtd_nascidos) AS nascidos_vivos
    FROM fato_nascidos_municipio
    GROUP BY ano
)
SELECT n.ano, o.obitos_rmm, n.nascidos_vivos,
       round(o.obitos_rmm * 100000.0 / n.nascidos_vivos, 1) AS rmm
FROM nascidos n JOIN obitos o USING (ano)
ORDER BY n.ano
"""

SQL_OBITOS_UF_2024 = """
SELECT u.uf_sigla, count(*) AS obitos_rmm
FROM fato_obito_materno f
JOIN dim_municipio m USING (cod_mun_res)
JOIN dim_uf u ON u.cod_uf = m.cod_uf
WHERE f.entra_rmm AND f.ano = 2024
GROUP BY u.uf_sigla
"""

SQL_RMM_RACA = """
WITH obitos AS (
    SELECT r.raca_cor_agregada, count(*) AS obitos_rmm
    FROM fato_obito_materno f JOIN dim_raca_cor r USING (cod_raca_cor)
    WHERE f.entra_rmm
    GROUP BY r.raca_cor_agregada
), nascidos AS (
    SELECT r.raca_cor_agregada, sum(n.qtd_nascidos) AS nascidos_vivos
    FROM fato_nascidos_municipio n JOIN dim_raca_cor r USING (cod_raca_cor)
    GROUP BY r.raca_cor_agregada
)
SELECT raca_cor_agregada, obitos_rmm, nascidos_vivos,
       round(obitos_rmm * 100000.0 / nascidos_vivos, 1) AS rmm
FROM obitos JOIN nascidos USING (raca_cor_agregada)
ORDER BY rmm DESC
"""

SQL_CESAREA_ANO = """
SELECT ano,
       round(100.0 * sum(qtd_nascidos) FILTER (WHERE p.tipo_parto = 'Cesáreo')
             / sum(qtd_nascidos) FILTER (WHERE p.tipo_parto IN ('Vaginal', 'Cesáreo')), 1)
           AS pct_cesarea,
       round(100.0 * sum(qtd_nascidos) FILTER (WHERE p.tipo_parto = 'Cesáreo' AND f.cod_cesarea_antes_tp = '1')
             / sum(qtd_nascidos) FILTER (WHERE p.tipo_parto = 'Cesáreo'), 1)
           AS pct_cesareas_antes_do_tp
FROM fato_nascidos_parto f JOIN dim_tipo_parto p USING (cod_parto)
GROUP BY ano
ORDER BY ano
"""


def consultar(cur, sql: str) -> pd.DataFrame:
    cur.execute(sql)
    colunas = [c.name for c in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=colunas)


def main() -> None:
    with psycopg.connect(carga.ler_database_url()) as conn, conn.cursor() as cur:
        print("=== Óbitos, nascidos vivos e RMM por ano ===")
        rmm = consultar(cur, SQL_RMM_ANO)
        rmm["painel_ms"] = rmm["ano"].map(PAINEL_OBITOS)
        rmm["dif_obitos"] = rmm["obitos_rmm"] - rmm["painel_ms"]
        rmm["tabnet"] = rmm["ano"].map(TABNET_NASCIDOS)
        rmm["dif_nascidos"] = rmm["nascidos_vivos"] - rmm["tabnet"]
        print(rmm.to_string(index=False))

        print("\n=== Óbitos maternos por UF em 2024 x Painel MS ===")
        uf = consultar(cur, SQL_OBITOS_UF_2024).set_index("uf_sigla")["obitos_rmm"]
        oficial = pd.Series(PAINEL_UF_2024)
        divergentes = (uf.reindex(oficial.index, fill_value=0) != oficial).sum()
        print(f"UFs comparadas: {len(oficial)} | divergentes: {divergentes}")

        print("\n=== RMM por raça/cor da mulher (2022 a 2024) ===")
        print(consultar(cur, SQL_RMM_RACA).to_string(index=False))

        print("\n=== Cesáreas por ano ===")
        print(consultar(cur, SQL_CESAREA_ANO).to_string(index=False))


if __name__ == "__main__":
    main()