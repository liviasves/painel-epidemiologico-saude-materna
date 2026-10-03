-- Modelo estrela: Painel Epidemiológico de Mortalidade Materna e Violência Obstétrica

DROP TABLE IF EXISTS fato_obito_materno, fato_nascidos_municipio, fato_nascidos_parto,
    dim_municipio, dim_uf, dim_raca_cor, dim_escolaridade, dim_estado_civil,
    dim_local_ocorrencia, dim_momento_obito, dim_tipo_parto, dim_sim_nao,
    dim_grupo_robson, dim_faixa_etaria, dim_faixa_prenatal, dim_tipo_obito,
    dim_causa_obito, controle_sim, controle_sinasc, controle_carga CASCADE;

-- Dimensões ---------------------------------------------------------------

CREATE TABLE dim_uf (
    cod_uf      CHAR(2) PRIMARY KEY,
    uf_sigla    CHAR(2)     NOT NULL,
    uf_nome     VARCHAR(30) NOT NULL,
    regiao      VARCHAR(20) NOT NULL
);

CREATE TABLE dim_municipio (
    cod_mun_res         CHAR(6) PRIMARY KEY,
    cod_ibge_7          CHAR(7),
    municipio           VARCHAR(60) NOT NULL,
    cod_uf              CHAR(2) NOT NULL REFERENCES dim_uf,
    municipio_ignorado  BOOLEAN NOT NULL
);

CREATE TABLE dim_raca_cor (
    cod_raca_cor        CHAR(1) PRIMARY KEY,
    raca_cor            VARCHAR(20) NOT NULL,
    raca_cor_agregada   VARCHAR(30) NOT NULL
);

CREATE TABLE dim_escolaridade (
    cod_escolaridade    CHAR(1) PRIMARY KEY,
    escolaridade        VARCHAR(40) NOT NULL,
    ordem               SMALLINT NOT NULL
);

CREATE TABLE dim_estado_civil (
    cod_estado_civil    CHAR(1) PRIMARY KEY,
    estado_civil        VARCHAR(40) NOT NULL
);

CREATE TABLE dim_local_ocorrencia (
    cod_local_ocorrencia    CHAR(1) PRIMARY KEY,
    local_ocorrencia        VARCHAR(40) NOT NULL
);

CREATE TABLE dim_momento_obito (
    cod_momento_obito   CHAR(1) PRIMARY KEY,
    momento_obito       VARCHAR(50) NOT NULL
);

CREATE TABLE dim_tipo_parto (
    cod_parto   CHAR(1) PRIMARY KEY,
    tipo_parto  VARCHAR(20) NOT NULL
);

CREATE TABLE dim_sim_nao (
    cod_sim_nao CHAR(1) PRIMARY KEY,
    descricao   VARCHAR(20) NOT NULL
);

CREATE TABLE dim_grupo_robson (
    grupo_robson    SMALLINT PRIMARY KEY,
    descricao       VARCHAR(150) NOT NULL,
    agrupamento     VARCHAR(30)  NOT NULL
);

CREATE TABLE dim_faixa_etaria (
    faixa_etaria    VARCHAR(10) PRIMARY KEY,
    ordem           SMALLINT NOT NULL
);

CREATE TABLE dim_faixa_prenatal (
    faixa_prenatal  VARCHAR(12) PRIMARY KEY,
    ordem           SMALLINT NOT NULL
);

CREATE TABLE dim_tipo_obito (
    tipo_obito  VARCHAR(40) PRIMARY KEY,
    entra_rmm   BOOLEAN NOT NULL
);

CREATE TABLE dim_causa_obito (
    cod_causa       VARCHAR(4) PRIMARY KEY,
    descricao       TEXT NOT NULL,
    categoria       CHAR(3) NOT NULL,
    grupo_cid       VARCHAR(150),
    capitulo_cid    VARCHAR(150)
);

-- Fatos -------------------------------------------------------------------

-- Um registro por óbito materno (SIM)
CREATE TABLE fato_obito_materno (
    id_obito                INTEGER PRIMARY KEY,
    ano                     SMALLINT NOT NULL,
    mes                     SMALLINT,
    data_obito              DATE,
    cod_mun_res             CHAR(6)  NOT NULL REFERENCES dim_municipio,
    idade                   SMALLINT,
    faixa_etaria            VARCHAR(10) NOT NULL REFERENCES dim_faixa_etaria,
    cod_raca_cor            CHAR(1) NOT NULL REFERENCES dim_raca_cor,
    cod_estado_civil        CHAR(1) NOT NULL REFERENCES dim_estado_civil,
    cod_escolaridade        CHAR(1) NOT NULL REFERENCES dim_escolaridade,
    cod_local_ocorrencia    CHAR(1) NOT NULL REFERENCES dim_local_ocorrencia,
    cod_causa_basica        VARCHAR(4) NOT NULL REFERENCES dim_causa_obito,
    cod_causa_externa       VARCHAR(4) REFERENCES dim_causa_obito,
    cod_momento_obito       CHAR(1) NOT NULL REFERENCES dim_momento_obito,
    obito_gravidez          CHAR(1) NOT NULL REFERENCES dim_sim_nao,
    obito_puerperio         CHAR(1) NOT NULL,
    assistencia_medica      CHAR(1) NOT NULL REFERENCES dim_sim_nao,
    tipo_obito              VARCHAR(40) NOT NULL REFERENCES dim_tipo_obito,
    entra_rmm               BOOLEAN NOT NULL
);

-- Nascidos vivos agregados por município (denominador da RMM)
CREATE TABLE fato_nascidos_municipio (
    ano                 SMALLINT NOT NULL,
    cod_mun_res         CHAR(6) NOT NULL REFERENCES dim_municipio,
    faixa_etaria        VARCHAR(10) NOT NULL REFERENCES dim_faixa_etaria,
    cod_raca_cor        CHAR(1) NOT NULL REFERENCES dim_raca_cor,
    cod_escolaridade    CHAR(1) NOT NULL REFERENCES dim_escolaridade,
    qtd_nascidos        INTEGER NOT NULL,
    PRIMARY KEY (ano, cod_mun_res, faixa_etaria, cod_raca_cor, cod_escolaridade)
);

-- Nascidos vivos agregados por UF com variáveis do parto (violência obstétrica)
CREATE TABLE fato_nascidos_parto (
    ano                     SMALLINT NOT NULL,
    cod_uf                  CHAR(2) NOT NULL REFERENCES dim_uf,
    faixa_etaria            VARCHAR(10) NOT NULL REFERENCES dim_faixa_etaria,
    cod_raca_cor            CHAR(1) NOT NULL REFERENCES dim_raca_cor,
    cod_escolaridade        CHAR(1) NOT NULL REFERENCES dim_escolaridade,
    cod_parto               CHAR(1) NOT NULL REFERENCES dim_tipo_parto,
    grupo_robson            SMALLINT NOT NULL REFERENCES dim_grupo_robson,
    faixa_prenatal          VARCHAR(12) NOT NULL REFERENCES dim_faixa_prenatal,
    cod_cesarea_antes_tp    CHAR(1) NOT NULL REFERENCES dim_sim_nao,
    cod_tp_induzido         CHAR(1) NOT NULL REFERENCES dim_sim_nao,
    qtd_nascidos            INTEGER NOT NULL,
    PRIMARY KEY (ano, cod_uf, faixa_etaria, cod_raca_cor, cod_escolaridade, cod_parto,
                 grupo_robson, faixa_prenatal, cod_cesarea_antes_tp, cod_tp_induzido)
);

-- Rastreabilidade ---------------------------------------------------------

CREATE TABLE controle_sim (
    base                VARCHAR(10),
    ano                 SMALLINT,
    arquivo_origem      VARCHAR(60),
    tamanho_mb          NUMERIC(8,1),
    linhas_lidas        INTEGER,
    linhas_selecionadas INTEGER,
    entra_rmm           INTEGER,
    tardio              INTEGER,
    causa_externa       INTEGER,
    datas_invalidas     INTEGER,
    ano_divergente      INTEGER,
    idade_ignorada      INTEGER,
    painel_ms           INTEGER,
    processado_em       TIMESTAMP
);

CREATE TABLE controle_sinasc (
    base                    VARCHAR(10),
    ano                     SMALLINT,
    arquivo_origem          VARCHAR(60),
    tamanho_mb              NUMERIC(8,1),
    linhas_lidas            INTEGER,
    linhas_fato_municipio   INTEGER,
    soma_fato_municipio     INTEGER,
    linhas_fato_parto       INTEGER,
    soma_fato_parto         INTEGER,
    ano_divergente          INTEGER,
    processado_em           TIMESTAMP
);

CREATE TABLE controle_carga (
    tabela          VARCHAR(40) PRIMARY KEY,
    linhas_csv      INTEGER NOT NULL,
    linhas_banco    INTEGER NOT NULL,
    tamanho_banco   VARCHAR(20),
    carregado_em    TIMESTAMP NOT NULL DEFAULT now()
);

-- Índices para os filtros do dashboard (ano, local, raça/cor)
CREATE INDEX ix_obito_ano_mun   ON fato_obito_materno (ano, cod_mun_res);
CREATE INDEX ix_nasc_mun_mun    ON fato_nascidos_municipio (cod_mun_res);