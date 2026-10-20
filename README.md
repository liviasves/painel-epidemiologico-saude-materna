# Painel Epidemiológico de Mortalidade Materna e Violência Obstétrica

Pipeline de dados que trata os microdados públicos do SIM e do SINASC (2022 a 2024), valida os resultados contra fontes oficiais e armazena a base em um PostgreSQL na nuvem (Aiven, plano gratuito), provisionado com Terraform.

**Disciplina:** Big Data e Analytics · **ODS:** 5 (Igualdade de Gênero) e 18 (Igualdade Étnico-Racial)
**Equipe:** Alison Andrade Rocha, Lívia Alves de Souza e Vitor Carvalho Ferreira

---

## 1. Dados utilizados

### Fontes e identificação das bases

- **SIM – Sistema de Informações sobre Mortalidade:** declarações de óbito. Os anos de 2022 e 2023 foram obtidos na página de Transferência de Arquivos do DATASUS (`DOBR2022.dbc` e `DOBR2023.dbc`), e o de 2024 no OpenDataSUS (`DO24OPEN.csv`).
- **SINASC – Sistema de Informações sobre Nascidos Vivos:** declarações de nascido vivo de 2022 a 2024, em CSV, do OpenDataSUS.
- **API de Localidades do IBGE:** nome do município, UF e região, em JSON.
- **CID-10 (DATASUS):** descrição oficial das causas de óbito, em CSV.
- **Dicionários de dados do SIM e do SINASC (Ministério da Saúde):** significado dos códigos de cada variável, em PDF.

### Recorte

- **Período:** 2022 a 2024, os três anos mais recentes já consolidados (o ano de 2025 ainda é preliminar).
- **SIM:** apenas óbitos maternos (mulheres, causa básica no capítulo XV da CID-10 ou marcador O93).
- **SINASC:** todos os nascidos vivos, armazenados como contagens agregadas.

### Características relevantes

- O SIM soma 4.541.891 registros nos três anos (86 a 88 colunas, cerca de 525 MB por ano), e o SINASC, 7.488.823 registros (61 a 62 colunas, cerca de 540 MB por ano).
- Os arquivos são separados por `;`, com encoding `latin-1`, e os campos vêm codificados (ex.: raça/cor `4` = parda).
- A ausência de informação aparece de duas formas: campo vazio e código `9` ("ignorado").
- Os óbitos maternos representam cerca de 0,1% dos óbitos do SIM.
- Classificação dos dados: estruturados (CSV e DBC), semiestruturados (JSON do IBGE) e não estruturados (dicionários em PDF).

---

## 2. Tratamento realizado

A exploração completa, com os resultados de cada verificação, está no notebook `etl/fase2/05_exploracao_bases.ipynb`.

### Problemas identificados

- **SIM 2022 e 2023 sem cabeçalho:** os CSVs desses anos no OpenDataSUS não têm a linha com os nomes das colunas, além de usarem outro formato de data (`21-04-2022`) e terem colunas a mais. O problema foi identificado na comparação das colunas dos três anos e resolvido com os arquivos DBC oficiais do DATASUS, que trazem os nomes das colunas e foram convertidos para CSV.
- **Layout diferente entre os anos:** nomes com caixa diferente (`contador` e `CONTADOR`) e colunas que só existem em 2024, como a `MAT_CLAS`. Os nomes foram padronizados em maiúsculas e só são lidas as colunas usadas, presentes nos três anos.
- **Duas colunas de raça/cor no SINASC:** a `RACACOR` é do recém-nascido e a `RACACORMAE` é da mãe. Foi usada a da mãe.
- **Código O93 no SIM:** não existe na CID-10 internacional. É um código brasileiro para óbito materno associado a causa externa, tratado conforme o protocolo de codificações especiais do Ministério da Saúde.
- **25 causas sem descrição na CID-10 de 2008:** códigos de atualizações posteriores ou registrados só no nível de categoria.
- **19 códigos de município ignorado (UF + `0000`):** não existem no IBGE e foram incluídos na dimensão de municípios para não perder registros.

### Decisões, transformações e justificativas

- **Regra de óbito materno pela CID-10:** seleção dos óbitos femininos com causa básica de O00 a O99 ou com o marcador O93, classificados em "entra na RMM", "tardio" (O96 e O97) e "causa externa". Segue a definição oficial da Razão de Mortalidade Materna (RMM) e não depende da `MAT_CLAS`, que só existe em 2024 e foi usada apenas para validar a regra.
- **Descrição das causas em cascata:** subcategoria da CID-10, depois uma tabela manual com os códigos incluídos pela OMS após 2008 (O98.7 e O14.2) e, por fim, a categoria.
- **Padronização dos ignorados:** vazio, nulo e `9` foram unificados como `9` ("Ignorado"), já que as duas formas têm o mesmo significado.
- **Conversão de tipos:** `DTOBITO` convertida para data; `IDADE` decodificada em anos (`425` = 25 anos); `TPROBSON` (`05`) convertido para inteiro. O código de município foi mantido como texto de 6 caracteres, para preservar zeros e permitir o relacionamento com o IBGE.
- **Faixas etárias e de pré-natal:** idade em faixas de 5 anos, iguais no SIM e no SINASC, para permitir a divisão de óbitos por nascidos; consultas de pré-natal em nenhuma, 1 a 3, 4 a 6 e 7 ou mais.
- **Minimização de dados (LGPD):** foram descartadas datas de nascimento, estabelecimento de saúde, ocupação, naturalidade e horários, que não são usados na análise e poderiam ajudar a reidentificar pessoas.
- **Agregação do SINASC, sem amostragem:** os 7,5 milhões de registros viraram 1,26 milhão de linhas de contagens, sem perder nenhum nascimento. A amostragem eliminaria grupos pequenos nos cruzamentos por raça/cor e território.
- **Dois níveis de agregação no SINASC:** uma tabela por município (denominador da RMM) e outra por UF com as variáveis do parto, já que o detalhe obstétrico por município geraria grupos de 1 ou 2 partos, sem valor analítico.

### Validação

| Ano | Óbitos (projeto) | Óbitos (Painel MS) | Nascidos vivos (projeto) | Nascidos vivos (TabNet) | RMM |
| --- | --- | --- | --- | --- | --- |
| 2022 | 1.370 | 1.368 | 2.561.922 | 2.561.922 | 53,5 |
| 2023 | 1.324 | 1.319 | 2.537.576 | 2.537.576 | 52,2 |
| 2024 | 1.326 | 1.326 | 2.389.325 | 2.389.325 | 55,5 |

Em 2024, os óbitos coincidem com o Painel de Monitoramento da Mortalidade Materna também nas 27 UFs. As diferenças de 2022 e 2023 (até 0,4%) vêm da versão da base: o painel é atualizado continuamente após as investigações de óbito. Consultas em 03/10/2026.

As decisões completas estão no relatório técnico da fase 2 (`docs/relatorio_fase2.docx`).

---

## 3. Modelagem

### Estratégia

Banco **relacional** (PostgreSQL) em **modelo estrela**: tabelas fato com as medidas e tabelas de dimensão com os recortes. A escolha se justifica porque os dados são estruturados, os relacionamentos são fixos e as consultas do painel são agregações. As três fatos compartilham as dimensões de município, faixa etária, raça/cor e escolaridade, o que permite calcular a RMM em qualquer combinação desses recortes.

### Estrutura do banco

| Tabela | Cada linha representa | Linhas | Tamanho |
| --- | --- | --- | --- |
| `fato_obito_materno` | um óbito materno | 4.914 | 992 kB |
| `fato_nascidos_municipio` | contagem por ano, município, faixa etária, raça/cor e escolaridade da mãe | 711.592 | 70 MB |
| `fato_nascidos_parto` | contagem por ano, UF, perfil da mãe, tipo de parto, Robson, pré-natal, cesárea antes do trabalho de parto e indução | 553.327 | 65 MB |
| `dim_municipio` e `dim_uf` | município (IBGE + ignorados) e UF | 5.590 e 27 | < 1 MB |
| `dim_causa_obito` | causa de óbito (CID-10) | 269 | 88 kB |
| 11 dimensões de códigos | raça/cor, escolaridade, estado civil, local de ocorrência, momento do óbito, tipo de óbito, tipo de parto, Robson, faixa etária, faixa de pré-natal e sim/não | 3 a 12 cada | < 1 MB |
| `controle_sim`, `controle_sinasc` e `controle_carga` | arquivo de origem e linhas lidas, geradas e carregadas | 3, 3 e 19 | < 1 MB |

As tabelas somam **cerca de 137 MB**, bem abaixo do limite de 1 GB do plano gratuito. Cada fato se liga às dimensões por chave estrangeira, e as fatos de nascidos usam chave primária composta pelas próprias dimensões, garantindo uma linha por combinação.

### Representação

- Schema completo, com campos, tipos e chaves: `etl/sql/01_schema.sql`
- Diagrama do modelo: `docs/modelo_dados.png`

---

## 4. Infraestrutura

- **Serviço:** Aiven for PostgreSQL (PaaS gerenciado).
- **Recurso provisionado:** serviço `pg-saude-materna` (recurso `aiven_pg`).
- **Plano:** `free-1-1gb` (1 CPU, 1 GB de RAM e 1 GB de armazenamento, custo zero).
- **Região:** `do-nyc` (DigitalOcean, Nova York).
- **Provisionamento:** Terraform, com o provider oficial `aiven/aiven`.

Arquivos em `terraform/`:

- `main.tf`: provider da Aiven e recurso do PostgreSQL.
- `variables.tf`: token (marcado como sensível), projeto, nome do serviço, plano e região.
- `outputs.tf`: host, porta, plano e URI de conexão (marcada como sensível).
- `terraform.tfvars.example`: modelo dos valores a preencher, sem credenciais.

**Região:** o plano gratuito da Aiven só está disponível nas nuvens DigitalOcean e UpCloud, sem regiões na América do Sul (São Paulo e AWS foram testadas e recusadas pela Aiven). Foi escolhida Nova York, a mais próxima. Os dados armazenados são públicos, anonimizados na origem e agregados no ETL, sem dados pessoais.

**Tecnologias empregadas:** Python 3 (pandas, dbfread, pyreaddbc, psycopg), Jupyter Notebook, PostgreSQL, Terraform e Git/GitHub.

---

## 5. Segurança das informações

Nenhuma credencial está no repositório. A estratégia adotada:

- **Token da API da Aiven:** fica em `terraform/terraform.tfvars`, apenas na máquina local, listado no `.gitignore` e declarado como variável `sensitive` no Terraform.
- **Senha e URI do banco:** ficam no `.env` na raiz, gerado a partir do output do Terraform, listado no `.gitignore`. O output é `sensitive` e não aparece no terminal.
- **Estado do Terraform:** os arquivos `terraform/*.tfstate`, que contêm a senha do banco, estão no `.gitignore`, assim como a pasta `terraform/.terraform/`.
- Os scripts leem a conexão do `.env` em tempo de execução; nenhum código contém senha.
- O repositório traz apenas o `terraform.tfvars.example`, com valores fictícios, mostrando o que preencher.
- O token foi criado só para o Terraform, com validade definida (expira se ficar sem uso).
- O `.env` é gerado sem exibir a senha na tela, com `terraform output -raw uri_conexao`.

---

## 6. Organização do repositório

```
├── dados/
│   ├── brutos/          # arquivos originais (fora do Git pelo tamanho; ver Execução)
│   └── tratados/        # base tratada: fatos, dimensões e controle em CSV
├── docs/                # relatório técnico da fase 2 e diagrama do modelo
├── etl/
│   ├── fase1/           # testes das APIs e extração dos municípios do IBGE
│   ├── fase2/           # notebook de exploração (05) e scripts do ETL (06 a 10)
│   └── sql/             # schema do banco (01_schema.sql)
├── terraform/           # infraestrutura como código
├── .gitignore           # credenciais, estado do Terraform e dados brutos
└── README.md
```

Scripts da pasta `etl/fase2/`:

- `comum.py`: caminhos, anos e regras compartilhadas pelos scripts.
- `05_exploracao_bases.ipynb`: perfil das bases, testes das regras e conversão DBC → CSV.
- `06_tratamento_sim.py`: seleção e classificação dos óbitos maternos.
- `07_tratamento_sinasc.py`: agregação dos nascidos vivos nas duas tabelas fato.
- `08_dimensoes.py`: 14 dimensões e checagem de integridade referencial.
- `09_carga_postgres.py`: criação do schema e carga no PostgreSQL.
- `10_validacao_carga.py`: indicadores recalculados em SQL e comparados com as fontes oficiais.

---

## 7. Execução

### Ferramentas e dependências

- Python 3.12 ou superior
- Terraform 1.5 ou superior
- Conta na Aiven, com um token de API
- No Windows, Microsoft C++ Build Tools (exigido pelo `pyreaddbc`)

```bash
pip install pandas requests jupyter dbfread pyreaddbc "psycopg[binary]"
```

### Sequência de execução

1. **Baixar os dados brutos** em `dados/brutos/`:
   - `sinasc_2022.csv`, `sinasc_2023.csv`, `sinasc_2024.csv` e `sim_2024.csv` (OpenDataSUS);
   - `DOBR2022.dbc` e `DOBR2023.dbc` (datasus.saude.gov.br/transferencia-de-arquivos → SIM → Declarações de Óbito → UF BR);
   - tabelas da CID-10 do DATASUS em `dados/brutos/cid10/`.
2. **Gerar a tabela de municípios:**
   ```bash
   python etl/fase1/04_extracao_municipios_ibge.py
   ```
3. **Converter os DBC para CSV:** executar `etl/fase2/05_exploracao_bases.ipynb` até a seção de conversão.
4. **Tratar os dados:**
   ```bash
   python etl/fase2/06_tratamento_sim.py
   python etl/fase2/07_tratamento_sinasc.py
   python etl/fase2/08_dimensoes.py
   ```
5. **Provisionar o banco:** copiar `terraform/terraform.tfvars.example` para `terraform/terraform.tfvars`, preencher o token e executar:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```
6. **Criar o `.env`** na raiz (PowerShell, dentro de `terraform/`):
   ```powershell
   "DATABASE_URL=$(terraform output -raw uri_conexao)" | Out-File -Encoding ascii ..\.env
   ```
7. **Carregar e validar:**
   ```bash
   python etl/fase2/09_carga_postgres.py
   python etl/fase2/10_validacao_carga.py
   ```

O script 09 recria as tabelas a cada execução, então o processo pode ser repetido do zero.