# rais-etl-db

ETL incremental que converte os arquivos TXT da RAIS (Relação Anual de Informações
Sociais) para Parquet particionado, reduzindo drasticamente o tamanho em disco e
o tempo de consulta analítica.

---

## Objetivo

Os arquivos TXT originais da RAIS são grandes, codificados em latin-1, separados
por ponto-e-vírgula e contêm dezenas de colunas redundantes ou de uso legado.
Este projeto:

- Seleciona apenas as colunas analiticamente relevantes
- Converte para Parquet com compressão zstd
- Particiona por `ano` e `uf` para leitura seletiva eficiente
- Padroniza nomes de colunas para snake_case
- Converte tipos (datas, inteiros, decimais) corretamente

---

## Metodologia

### 1. Descoberta de arquivos (`rais_etl/discover.py`)

O ETL varre a árvore de diretórios e identifica dois conjuntos:

- **Vínculos:** pastas `RAIS Vínculos/RAIS <ano>/`, arquivos `<UF><ano>ID.txt`
- **Estabelecimentos:** pasta `RAIS Estabelecimentos/`, arquivos `Estb<ano>ID.txt`

Cada arquivo vira um `RaisJob` com metadados de dataset, ano e UF.

### 2. Validação de schema (`rais_etl/schema.py`)

Antes de processar, o cabeçalho do TXT é comparado com o schema canônico
(`rais_etl/config.py`). Colunas obrigatórias ausentes geram aviso; colunas
opcionais ausentes são preenchidas com `NULL`.

### 3. Leitura em chunks (`rais_etl/process.py`)

Cada TXT é lido com `pandas.read_csv` em chunks de 500.000 linhas, encoding
`latin-1`, separador `;`. Isso evita estouro de memória em arquivos de vários GB.

### 4. Transformação (`rais_etl/transform.py`)

Para cada chunk:
- Seleciona apenas as colunas do schema (descarta todas as outras)
- Renomeia para snake_case
- Converte tipos: `str`, `int` (Int64 nullable), `double`, `date` (DDMMYYYY)
- Injeta coluna `ano` (int32)
- Deriva coluna `uf` dos 2 primeiros dígitos do código IBGE do município

### 5. Escrita Parquet particionada (`rais_etl/process.py`)

Cada chunk é convertido para Arrow e gravado em:

```
<RAIS_OUTPUT_DIR>/
  vinculos/
    ano=2022/
      uf=35/
        SP2022ID.parquet
  estabelecimentos/
    ano=2022/
      uf=35/
        Estb2022ID.parquet
```

Compressão: **zstd**. Particionamento Hive permite leitura seletiva por ano e UF
sem varrer todos os arquivos.

### 6. Manifesto incremental (`rais_etl/manifest.py`)

Um arquivo `_manifest.json` registra quais TXTs já foram processados (dataset,
ano, nome do arquivo, linhas, tamanho, data). Execuções subsequentes pulam
arquivos já concluídos, permitindo retomada após interrupção.

---

## Estrutura do projeto

```
rais-etl-db/
├── cli.py                   # Ponto de entrada CLI
├── exemplo_consulta.py      # Exemplo de consulta com DuckDB
├── requirements.txt
├── .env.example             # Modelo de configuração
└── rais_etl/
    ├── config.py            # Schemas canônicos das colunas
    ├── discover.py          # Varredura de arquivos TXT
    ├── manifest.py          # Controle incremental
    ├── process.py           # ETL: TXT → Parquet
    ├── schema.py            # Validação de cabeçalhos
    └── transform.py         # Transformações de dados
```

---

## Configuração

```bash
# 1. Clonar o repositório
git clone https://github.com/<usuario>/rais-etl-db.git
cd rais-etl-db

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar caminhos
cp .env.example .env
# Editar .env e preencher RAIS_DATA_DIR e RAIS_OUTPUT_DIR
```

---

## Uso

```bash
# Verificar compatibilidade dos arquivos TXT com o schema
python cli.py verify-schema
python cli.py verify-schema --dataset vinculos

# Processar todos os arquivos pendentes
python cli.py process --all

# Processar dataset e ano específicos
python cli.py process --dataset vinculos --year 2022

# Processar uma UF específica
python cli.py process --dataset vinculos --year 2022 --uf RS

# Ver o que já foi processado
python cli.py status
python cli.py status --dataset estabelecimentos
```

### Consulta com DuckDB

```python
import duckdb

# Lê apenas RS, todos os anos disponíveis
df = duckdb.sql("""
    SELECT ano, COUNT(*) AS vinculos
    FROM read_parquet('caminho/vinculos/ano=*/uf=43/*.parquet',
                      hive_partitioning=true)
    GROUP BY ano ORDER BY ano
""").df()
```

---

## Resultados

### Vínculos — 50 colunas selecionadas (+ `ano` e `uf` derivadas)

| Grupo | Nome original no TXT | Nome no Parquet | Tipo |
|---|---|---|---|
| Identificadores | PIS | pis | str |
| Identificadores | CPF | cpf | str |
| Identificadores | Nome Trabalhador | nome_trabalhador | str |
| Identificadores | Data de Nascimento | data_nascimento | date |
| Identificadores | CNPJ / CEI | cnpj_cei | str |
| Identificadores | CNPJ Raiz | cnpj_raiz | str |
| Identificadores | CEI Vinculado | cei_vinculado | str |
| Identificadores | Razão Social | razao_social | str |
| Trabalhador | Sexo Trabalhador | sexo | str |
| Trabalhador | Idade | idade | int |
| Trabalhador | Raça Cor | raca_cor | str |
| Trabalhador | Nacionalidade | nacionalidade | str |
| Trabalhador | Escolaridade após 2005 | escolaridade | str |
| Trabalhador | Ind Portador Defic | ind_portador_defic | str |
| Trabalhador | Tipo Defic | tipo_defic | str |
| Vínculo | Vínculo Ativo 31/12 | vinculo_ativo_3112 | str |
| Vínculo | Tipo Vínculo | tipo_vinculo | str |
| Vínculo | Tipo Admissão | tipo_admissao | str |
| Vínculo | Data Admissão Declarada | data_admissao | date |
| Vínculo | Tempo Emprego | tempo_emprego | double |
| Vínculo | Motivo Desligamento | motivo_desligamento | str |
| Vínculo | Mês Desligamento | mes_desligamento | str |
| Vínculo | Dia de Desligamento | dia_desligamento | str |
| Vínculo | Qtd Hora Contr | qtd_hora_contr | int |
| Vínculo | CBO Ocupação 2002 | cbo_2002 | str |
| Estabelecimento | Município | municipio | str |
| Estabelecimento | Natureza Jurídica | natureza_juridica | str |
| Estabelecimento | Tamanho Estabelecimento | tamanho_estab | str |
| Estabelecimento | Tipo Estab | tipo_estab | str |
| Estabelecimento | CNAE 2.0 Classe | cnae20_classe | str |
| Estabelecimento | CNAE 2.0 Subclasse | cnae20_subclasse | str |
| Remuneração | Vl Remun Média Nom | vl_remun_media_nom | double |
| Remuneração | Vl Salário Contratual | vl_salario_contratual | double |
| Remuneração | Vl Última Remuneração Ano | vl_ultima_remun_ano | double |
| Afastamento | Causa Afastamento 1 | causa_afast_1 | str |
| Afastamento | Dia Ini AF1 | dia_ini_af1 | str |
| Afastamento | Mês Ini AF1 | mes_ini_af1 | str |
| Afastamento | Dia Fim AF1 | dia_fim_af1 | str |
| Afastamento | Mês Fim AF1 | mes_fim_af1 | str |
| Afastamento | Causa Afastamento 2 | causa_afast_2 | str |
| Afastamento | Dia Ini AF2 | dia_ini_af2 | str |
| Afastamento | Mês Ini AF2 | mes_ini_af2 | str |
| Afastamento | Dia Fim AF2 | dia_fim_af2 | str |
| Afastamento | Mês Fim AF2 | mes_fim_af2 | str |
| Afastamento | Causa Afastamento 3 | causa_afast_3 | str |
| Afastamento | Dia Ini AF3 | dia_ini_af3 | str |
| Afastamento | Mês Ini AF3 | mes_ini_af3 | str |
| Afastamento | Dia Fim AF3 | dia_fim_af3 | str |
| Afastamento | Mês Fim AF3 | mes_fim_af3 | str |
| Afastamento | Qtd Dias Afastamento | qtd_dias_afast | int |
| Derivada | — | ano | int |
| Derivada | — | uf | str |

---

### Estabelecimentos — 23 colunas selecionadas (+ `ano` e `uf` derivadas)

| Grupo | Nome original no TXT | Nome no Parquet | Tipo |
|---|---|---|---|
| Identificação | CNPJ / CEI | cnpj_cei | str |
| Identificação | CNPJ Raiz | cnpj_raiz | str |
| Identificação | CEI Vinculado | cei_vinculado | str |
| Identificação | Razão Social | razao_social | str |
| Localização | Município | municipio | str |
| Localização | CEP Estab | cep_estab | str |
| Localização | Nome Logradouro | nome_logradouro | str |
| Localização | Número Logradouro | numero_logradouro | int |
| Localização | Nome Bairro | nome_bairro | str |
| Classificação | CNAE 2.0 Classe | cnae20_classe | str |
| Classificação | CNAE 2.0 Subclasse | cnae20_subclasse | str |
| Classificação | IBGE Subsetor | ibge_subsetor | str |
| Classificação | Natureza Jurídica | natureza_juridica | str |
| Classificação | Tamanho Estabelecimento | tamanho_estab | str |
| Classificação | Tipo Estab | tipo_estab | str |
| Datas / Situação | Data Abertura | data_abertura | date |
| Datas / Situação | Data Baixa | data_baixa | date |
| Datas / Situação | Data Encerramento | data_encerramento | date |
| Datas / Situação | Ind Rais Negativa | ind_rais_negativa | str |
| Contagens | Qtd Vínculos Ativos | qtd_vinculos_ativos | int |
| Contagens | Qtd Vínculos CLT | qtd_vinculos_clt | int |
| Contagens | Qtd Vínculos Estatutários | qtd_vinculos_estat | int |
| Indicadores | Ind Simples | ind_simples | str |
| Derivada | — | ano | int |
| Derivada | — | uf | str |

---

## Observação

A base identificada da RAIS utilizada neste projeto foi obtida por meio da **Lei de Acesso à Informação (LAI)**. Nenhuma venda, cessão ou repasse dos dados a terceiros será realizado por parte do autor deste repositório.
