"""Testes para transform.py — transformações sobre DataFrames pandas."""
import datetime
import pytest
import pandas as pd
from rais_etl.config import VINCULOS_SCHEMA, ESTAB_SCHEMA
from rais_etl.transform import (
    derive_uf_from_municipio,
    select_and_rename,
    cast_column,
    NULL_DATE_VALUES,
)


# ─────────────────────────────────────────────────────────────────────────────
# derive_uf_from_municipio
# ─────────────────────────────────────────────────────────────────────────────

class TestDeriveUf:
    def test_normal_codigo_ibge(self):
        assert derive_uf_from_municipio("120040") == "12"

    def test_sp_capital(self):
        assert derive_uf_from_municipio("355030") == "35"

    def test_zero_filled(self):
        assert derive_uf_from_municipio("000000") == "00"

    def test_empty_string(self):
        assert derive_uf_from_municipio("") == "00"

    def test_single_zero(self):
        assert derive_uf_from_municipio("0") == "00"

    def test_strips_spaces(self):
        assert derive_uf_from_municipio("  120040  ") == "12"

    def test_short_code_two_digits(self):
        assert derive_uf_from_municipio("12") == "12"


# ─────────────────────────────────────────────────────────────────────────────
# cast_column — conversão de tipos por ColSpec.dtype
# ─────────────────────────────────────────────────────────────────────────────

class TestCastColumn:
    def test_str_trims_whitespace(self):
        s = pd.Series(["  LAERTE  ", "ANA"])
        result = cast_column(s, "str")
        assert result.iloc[0] == "LAERTE"

    def test_int_converts(self):
        s = pd.Series(["44", "08", ""])
        result = cast_column(s, "int")
        assert result.iloc[0] == 44
        assert pd.isna(result.iloc[2])

    def test_int_with_zeros(self):
        s = pd.Series(["000000007", "000000000"])
        result = cast_column(s, "int")
        assert result.iloc[0] == 7

    def test_double_comma_decimal(self):
        s = pd.Series(["0000001125,29", "0001125,29", ""])
        result = cast_column(s, "double")
        assert abs(result.iloc[0] - 1125.29) < 0.001
        assert abs(result.iloc[1] - 1125.29) < 0.001
        assert pd.isna(result.iloc[2])

    def test_double_dot_decimal_also_works(self):
        s = pd.Series(["1125.29"])
        result = cast_column(s, "double")
        assert abs(result.iloc[0] - 1125.29) < 0.001

    def test_date_ddmmyyyy(self):
        s = pd.Series(["02062014", "31051965"])
        result = cast_column(s, "date")
        assert result.iloc[0] == datetime.date(2014, 6, 2)
        assert result.iloc[1] == datetime.date(1965, 5, 31)

    def test_date_null_values(self):
        for null_val in NULL_DATE_VALUES:
            s = pd.Series([null_val])
            result = cast_column(s, "date")
            assert pd.isna(result.iloc[0]), f"Esperado NaT para '{null_val}'"

    def test_date_empty_becomes_null(self):
        s = pd.Series(["", "   "])
        result = cast_column(s, "date")
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

    def test_date_invalid_becomes_null(self):
        s = pd.Series(["99999999"])
        result = cast_column(s, "date")
        assert pd.isna(result.iloc[0])


# ─────────────────────────────────────────────────────────────────────────────
# select_and_rename — aplica schema a um DataFrame lido do CSV
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def df_vinculos_2014() -> pd.DataFrame:
    """DataFrame mínimo simulando saída de pd.read_csv no AC2014ID.txt."""
    return pd.DataFrame([{
        "Município":                "120040",
        "PIS":                      "12592585003",
        "CPF":                      "65543939272",
        "Nome Trabalhador":         "LAERTE BERNARDO SOBRINHO                               ",
        "Data de Nascimento":       "31051965",
        "CNPJ / CEI":               "02263250000140",
        "CNPJ Raiz":                "02263250",
        "CEI Vinculado":            "000000000000",
        "Sexo Trabalhador":         "01",
        "Idade":                    "049",
        "Raça Cor":                 "09",
        "Nacionalidade":            "10",
        "Escolaridade após 2005":   "01",
        "Ind Portador Defic":       "0",
        "Tipo Defic":               "00",
        "Vínculo Ativo 31/12":      " 0",
        "Tipo Vínculo":             "10",
        "Tipo Admissão":            "02",
        "Data Admissão Declarada":  "02062014",
        "Tempo Emprego":            "0005,9",
        "Motivo Desligamento":      "11",
        "Mês Desligamento":         "12",
        "Dia de Desligamento":      "01",
        "Qtd Hora Contr":           "44",
        "CBO Ocupação 2002":        "715110",
        "Natureza Jurídica":        "2062",
        "Tamanho Estabelecimento":  "04",
        "Tipo Estab":               "01",
        "CNAE 2.0 Classe":          "43134",
        "CNAE 2.0 Subclasse":       "4313400",
        "Vl Remun Média Nom":       "0000001125,29",
        "Vl Salário Contratual":    "0001125,29",
        "Vl Última Remuneração Ano":"0000037,51",
        "Causa Afastamento 1":      "99",
        "Dia Ini AF1":              "99",
        "Mês Ini AF1":              "99",
        "Dia Fim AF1":              "99",
        "Mês Fim AF1":              "99",
        "Causa Afastamento 2":      "99",
        "Dia Ini AF2":              "99",
        "Mês Ini AF2":              "99",
        "Dia Fim AF2":              "99",
        "Mês Fim AF2":              "99",
        "Causa Afastamento 3":      "99",
        "Dia Ini AF3":              "99",
        "Mês Ini AF3":              "99",
        "Dia Fim AF3":              "99",
        "Mês Fim AF3":              "99",
        "Qtd Dias Afastamento":     "000",
        # 2014 NÃO tem Razão Social
    }])


class TestSelectAndRename:
    def test_returns_dataframe(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        assert isinstance(result, pd.DataFrame)

    def test_canonical_column_names(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        assert "cpf" in result.columns
        assert "municipio" in result.columns
        assert "vl_remun_media_nom" in result.columns
        # Nomes originais não devem aparecer
        assert "CPF" not in result.columns
        assert "Município" not in result.columns

    def test_ano_column_injected(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        assert "ano" in result.columns
        assert result["ano"].iloc[0] == 2014

    def test_uf_derived(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        assert "uf" in result.columns
        assert result["uf"].iloc[0] == "12"

    def test_optional_missing_col_is_null(self, df_vinculos_2014):
        """Razão Social ausente em 2014 → coluna razao_social com NaN."""
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        assert "razao_social" in result.columns
        assert pd.isna(result["razao_social"].iloc[0])

    def test_decimal_comma_converted(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        val = result["vl_remun_media_nom"].iloc[0]
        assert abs(val - 1125.29) < 0.01

    def test_date_parsed(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        val = result["data_admissao"].iloc[0]
        assert val == datetime.date(2014, 6, 2)

    def test_nome_trabalhador_stripped(self, df_vinculos_2014):
        result = select_and_rename(df_vinculos_2014, VINCULOS_SCHEMA, ano=2014)
        nome = result["nome_trabalhador"].iloc[0]
        assert nome == "LAERTE BERNARDO SOBRINHO"

    def test_monthly_cc_sc_columns_not_in_output(self):
        """Colunas CC/SC extras no arquivo não devem aparecer na saída."""
        df = pd.DataFrame([{"Município": "120040", "PIS": "123", "CPF": "456",
                             "Vl Rem Janeiro CC": "1000,00",
                             "Vl Rem Janeiro SC": "1000,00"}])
        result = select_and_rename(df, VINCULOS_SCHEMA, ano=2018)
        for col in result.columns:
            assert "CC" not in col
            assert "SC" not in col

    def test_unknown_columns_dropped(self, df_vinculos_2014):
        """Colunas extras desconhecidas não entram na saída."""
        df = df_vinculos_2014.copy()
        df["Coluna Desconhecida XYZ"] = "lixo"
        result = select_and_rename(df, VINCULOS_SCHEMA, ano=2014)
        assert "Coluna Desconhecida XYZ" not in result.columns
        assert "coluna_desconhecida_xyz" not in result.columns

    def test_optional_present_in_2018(self):
        """Razão Social presente em 2018 → mapeada como string normal."""
        df = pd.DataFrame([{
            "Município": "120040", "PIS": "123", "CPF": "456",
            "Nome Trabalhador": "JOAO", "Data de Nascimento": "01011980",
            "CNPJ / CEI": "123", "CNPJ Raiz": "123", "CEI Vinculado": "123",
            "Razão Social": "EMPRESA TESTE LTDA",
            "Sexo Trabalhador": "01", "Idade": "040", "Raça Cor": "01",
            "Nacionalidade": "10", "Escolaridade após 2005": "07",
            "Ind Portador Defic": "0", "Tipo Defic": "00",
            "Vínculo Ativo 31/12": "1", "Tipo Vínculo": "10",
            "Tipo Admissão": "01", "Data Admissão Declarada": "01012018",
            "Tempo Emprego": "012,0", "Motivo Desligamento": "00",
            "Mês Desligamento": "00", "Dia de Desligamento": "00",
            "Qtd Hora Contr": "40", "CBO Ocupação 2002": "252105",
            "Natureza Jurídica": "2062", "Tamanho Estabelecimento": "03",
            "Tipo Estab": "01", "CNAE 2.0 Classe": "62020",
            "CNAE 2.0 Subclasse": "6201301",
            "Vl Remun Média Nom": "0005000,00",
            "Vl Salário Contratual": "0005000,00",
            "Vl Última Remuneração Ano": "0005000,00",
            "Causa Afastamento 1": "99", "Dia Ini AF1": "99",
            "Mês Ini AF1": "99", "Dia Fim AF1": "99", "Mês Fim AF1": "99",
            "Causa Afastamento 2": "99", "Dia Ini AF2": "99",
            "Mês Ini AF2": "99", "Dia Fim AF2": "99", "Mês Fim AF2": "99",
            "Causa Afastamento 3": "99", "Dia Ini AF3": "99",
            "Mês Ini AF3": "99", "Dia Fim AF3": "99", "Mês Fim AF3": "99",
            "Qtd Dias Afastamento": "000",
        }])
        result = select_and_rename(df, VINCULOS_SCHEMA, ano=2018)
        assert result["razao_social"].iloc[0] == "EMPRESA TESTE LTDA"
