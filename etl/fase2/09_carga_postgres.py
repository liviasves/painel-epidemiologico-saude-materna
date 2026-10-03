"""
09 - Carga no PostgreSQL (Aiven)

Recria o schema do modelo estrela (etl/sql/01_schema.sql) e carrega as
tabelas de dados/tratados com o comando COPY, que é a forma mais rápida
de inserir grandes volumes no PostgreSQL.

A conexão vem da variável DATABASE_URL do arquivo .env (fora do Git),
gerado a partir do output do Terraform.

Ao final, registra na tabela controle_carga as linhas de cada CSV e de
cada tabela no banco, e mostra o espaço ocupado (limite do plano: 1 GB).

Execução (a partir da raiz do projeto ou de etl/fase2):
    python etl/fase2/09_carga_postgres.py
"""
import psycopg

from comum import RAIZ, TRATADOS

SCHEMA = RAIZ / "etl" / "sql" / "01_schema.sql"

# Ordem de carga: dimensões antes das fatos (chaves estrangeiras)
TABELAS = [
    "dim_uf", "dim_municipio", "dim_raca_cor", "dim_escolaridade",
    "dim_estado_civil", "dim_local_ocorrencia", "dim_momento_obito",
    "dim_tipo_parto", "dim_sim_nao", "dim_grupo_robson", "dim_faixa_etaria",
    "dim_faixa_prenatal", "dim_tipo_obito", "dim_causa_obito",
    "fato_obito_materno", "fato_nascidos_municipio", "fato_nascidos_parto",
    "controle_sim", "controle_sinasc",
]


def ler_database_url() -> str:
    for linha in (RAIZ / ".env").read_text(encoding="utf-8-sig").splitlines():
        if linha.startswith("DATABASE_URL="):
            return linha.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL não encontrada no arquivo .env")


def copiar_csv(cur, tabela: str) -> int:
    arquivo = TRATADOS / f"{tabela}.csv"
    with open(arquivo, encoding="utf-8") as f:
        colunas = f.readline().strip()
        linhas = sum(1 for _ in f)

    with open(arquivo, "rb") as f, \
            cur.copy(f"COPY {tabela} ({colunas}) FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
        while bloco := f.read(1024 * 1024):
            copy.write(bloco)
    return linhas


def main() -> None:
    with psycopg.connect(ler_database_url()) as conn:
        with conn.cursor() as cur:
            print("Criando o schema...")
            cur.execute(SCHEMA.read_text(encoding="utf-8"))

            print("Carregando tabelas...")
            linhas_csv = {}
            for tabela in TABELAS:
                linhas_csv[tabela] = copiar_csv(cur, tabela)

            print(f"\n{'tabela':<26}{'csv':>10}{'banco':>10}{'tamanho':>12}")
            tudo_ok = True
            for tabela in TABELAS:
                cur.execute(f"SELECT count(*), pg_size_pretty(pg_total_relation_size('{tabela}')) FROM {tabela}")
                no_banco, tamanho = cur.fetchone()
                ok = no_banco == linhas_csv[tabela]
                tudo_ok &= ok
                print(f"{tabela:<26}{linhas_csv[tabela]:>10}{no_banco:>10}{tamanho:>12}{'' if ok else '  <- DIVERGENTE'}")
                cur.execute(
                    "INSERT INTO controle_carga (tabela, linhas_csv, linhas_banco, tamanho_banco) "
                    "VALUES (%s, %s, %s, %s)",
                    (tabela, linhas_csv[tabela], no_banco, tamanho),
                )

            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            print(f"\nTamanho total do banco: {cur.fetchone()[0]} (limite do plano: 1 GB)")
            print("Contagens CSV x banco:", "OK" if tudo_ok else "COM DIVERGÊNCIAS")
        conn.commit()


if __name__ == "__main__":
    main()