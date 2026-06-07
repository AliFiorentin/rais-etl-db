"""
Exemplo de consulta DuckDB sobre a base RAIS convertida para Parquet.

Mostra vínculos, ativos em 31/12 e remuneração média por setor econômico
para um município e anos selecionados.

Configure RAIS_OUTPUT_DIR no arquivo .env antes de executar.
Ajuste o código de município e os anos conforme necessário.
"""

import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

_output_dir = os.environ.get("RAIS_OUTPUT_DIR", "").strip()
if not _output_dir:
    print("Erro: variável de ambiente 'RAIS_OUTPUT_DIR' não definida.")
    print("Crie um arquivo .env baseado em .env.example.")
    raise SystemExit(1)

PARQUET_PATH = str(Path(_output_dir) / "vinculos" / "ano=*" / "uf=43" / "*.parquet")

result = duckdb.sql(f"""
SELECT
    ano,
    CASE
        WHEN cnae20_subclasse[1:2] BETWEEN '01' AND '03' THEN 'Agropecuaria'
        WHEN cnae20_subclasse[1:2] BETWEEN '05' AND '09' THEN 'Ind. Extrativa'
        WHEN cnae20_subclasse[1:2] BETWEEN '10' AND '33' THEN 'Ind. Transformacao'
        WHEN cnae20_subclasse[1:2] IN ('35','36','37','38','39') THEN 'Energia/Saneamento'
        WHEN cnae20_subclasse[1:2] BETWEEN '41' AND '43' THEN 'Construcao'
        WHEN cnae20_subclasse[1:2] BETWEEN '45' AND '47' THEN 'Comercio'
        WHEN cnae20_subclasse[1:2] BETWEEN '49' AND '53' THEN 'Transporte'
        WHEN cnae20_subclasse[1:2] BETWEEN '55' AND '56' THEN 'Alojamento/Alimentacao'
        WHEN cnae20_subclasse[1:2] BETWEEN '58' AND '63' THEN 'Info/Comunicacao'
        WHEN cnae20_subclasse[1:2] BETWEEN '64' AND '66' THEN 'Financeiro'
        WHEN cnae20_subclasse[1:2] = '68'               THEN 'Imobiliario'
        WHEN cnae20_subclasse[1:2] BETWEEN '69' AND '75' THEN 'Prof/Tecnico/Cientifico'
        WHEN cnae20_subclasse[1:2] BETWEEN '77' AND '82' THEN 'Adm. e Servicos'
        WHEN cnae20_subclasse[1:2] = '84'               THEN 'Adm. Publica'
        WHEN cnae20_subclasse[1:2] = '85'               THEN 'Educacao'
        WHEN cnae20_subclasse[1:2] BETWEEN '86' AND '88' THEN 'Saude'
        WHEN cnae20_subclasse[1:2] BETWEEN '90' AND '93' THEN 'Arte/Cultura/Esporte'
        WHEN cnae20_subclasse[1:2] BETWEEN '94' AND '96' THEN 'Outros Servicos'
        ELSE 'Outros'
    END AS setor,
    COUNT(*) AS vinculos,
    SUM(CASE WHEN vinculo_ativo_3112 = '1' THEN 1 ELSE 0 END) AS ativos_31dez,
    ROUND(AVG(TRY_CAST(vl_remun_media_nom AS DOUBLE)), 2) AS remun_media
FROM read_parquet('{PARQUET_PATH}', hive_partitioning=true)
WHERE municipio = '430543'
  AND ano IN (2021, 2022, 2023)
GROUP BY ano, setor
ORDER BY ano, vinculos DESC
""").df()

for ano in [2021, 2022, 2023]:
    print(f"\n=== {ano} ===")
    print(result[result.ano == ano][['setor', 'vinculos', 'ativos_31dez', 'remun_media']].to_string(index=False))
