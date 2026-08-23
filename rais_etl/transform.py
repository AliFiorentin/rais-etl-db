"""
Transformações de dados para os arquivos TXT da RAIS.

Funções puras que operam sobre pandas DataFrames:
  - cast_column(series, dtype)  → converte uma Series para o tipo canônico
  - select_and_rename(df, schema, ano) → aplica schema, renomeia, injeta ano/uf
  - derive_uf_from_municipio(cod) → 2 primeiros dígitos do código IBGE
"""

from __future__ import annotations
import datetime
import pandas as pd
from rais_etl.config import ColSpec

# Valores de data que devem ser tratados como NULL
NULL_DATE_VALUES: frozenset[str] = frozenset({"00000000", "0", ""})


# ─────────────────────────────────────────────────────────────────────────────

def derive_uf_from_municipio(municipio: str) -> str:
    """Retorna os 2 primeiros dígitos do código IBGE, ou '00' para inválidos."""
    code = municipio.strip()
    if len(code) < 2 or all(c == "0" for c in code):
        return "00"
    return code[:2]


def cast_column(series: pd.Series, dtype: str) -> pd.Series:
    """
    Converte uma Series pandas para o dtype canônico.

    dtype : "str" | "int" | "double" | "date"
    """
    if dtype == "str":
        return series.astype(str).str.strip()

    if dtype == "int":
        cleaned = series.astype(str).str.strip().replace("", pd.NA)
        numeric = pd.to_numeric(cleaned, errors="coerce")
        # Descarta valores fora do range de int32 (saída Arrow) ou não-inteiros
        # — dado sujo na origem (ex.: "Num Logradouro" com "9.5e+108" ou "3.92")
        # vira NULL em vez de estourar exceção no cast final.
        is_valid = numeric.between(-2_147_483_648, 2_147_483_647) & (numeric == numeric.round())
        numeric = numeric.where(is_valid)
        return numeric.astype("Int64")

    if dtype == "double":
        # Suporta tanto vírgula como ponto como separador decimal
        cleaned = (
            series.astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
            .replace("", pd.NA)
        )
        return pd.to_numeric(cleaned, errors="coerce")

    if dtype == "date":
        def parse_date(val: str):
            v = str(val).strip()
            if v in NULL_DATE_VALUES or not v:
                return pd.NaT
            for fmt in ("%d%m%Y", "%d/%m/%Y"):
                try:
                    return datetime.datetime.strptime(v, fmt).date()
                except (ValueError, TypeError):
                    continue
            return pd.NaT

        return series.apply(parse_date)

    # fallback — retorna como está
    return series


def select_and_rename(
    df: pd.DataFrame,
    schema: dict[str, ColSpec],
    ano: int,
) -> pd.DataFrame:
    """
    Aplica o schema canônico a um DataFrame lido do CSV.

    - Seleciona apenas as colunas do schema (ignora extras/desconhecidas)
    - Colunas opcionais ausentes → preenchidas com None/NaT
    - Converte tipos via cast_column
    - Injeta coluna `ano` (int) e deriva coluna `uf` a partir de `municipio`
    - Retorna DataFrame com colunas na ordem do schema + ano + uf
    """
    output: dict[str, pd.Series] = {}
    output["ano"] = pd.Series([ano] * len(df), dtype="int32")

    # Vários aliases (layouts históricos e alternativos) podem apontar para o
    # mesmo nome canônico — resolve por nome uma única vez, priorizando o
    # primeiro alias presente no arquivo, para não sobrescrever com nulo.
    for name in dict.fromkeys(spec.name for spec in schema.values()):
        spec = next(s for s in schema.values() if s.name == name)
        alias = next(
            (a for a, s in schema.items() if s.name == name and a in df.columns),
            None,
        )
        if alias is not None:
            output[name] = cast_column(df[alias], spec.dtype)
        elif spec.dtype == "date":
            output[name] = pd.Series([pd.NaT] * len(df))
        elif spec.dtype == "int":
            output[name] = pd.Series([pd.NA] * len(df), dtype="Int64")
        else:
            output[name] = pd.Series([None] * len(df), dtype=object)

    result = pd.DataFrame(output)

    # Deriva uf a partir de municipio (se municipio existir no schema)
    if "municipio" in result.columns:
        result["uf"] = result["municipio"].fillna("").apply(derive_uf_from_municipio)

    return result
