"""Testes para config.py — mapeamento canônico de colunas."""
import pytest
from rais_etl.config import (
    VINCULOS_SCHEMA,
    VINCULOS_ALT_ALIASES_2024,
    ESTAB_SCHEMA,
    ESTAB_ALT_ALIASES_2024,
    ColSpec,
    resolve_column,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def all_aliases(schema: dict[str, "ColSpec"]) -> list[str]:
    return list(schema.keys())


# ── VINCULOS_SCHEMA ───────────────────────────────────────────────────────────

class TestVinculosSchema:
    def test_contains_pis(self):
        assert "PIS" in VINCULOS_SCHEMA

    def test_contains_cpf(self):
        assert "CPF" in VINCULOS_SCHEMA

    def test_cpf_canonical_name(self):
        assert VINCULOS_SCHEMA["CPF"].name == "cpf"

    def test_pis_canonical_name(self):
        assert VINCULOS_SCHEMA["PIS"].name == "pis"

    def test_municipio_type_is_str(self):
        assert VINCULOS_SCHEMA["Município"].dtype == "str"

    def test_vl_remun_media_nom_type_is_double(self):
        assert VINCULOS_SCHEMA["Vl Remun Média Nom"].dtype == "double"

    def test_idade_type_is_int(self):
        assert VINCULOS_SCHEMA["Idade"].dtype == "int"

    def test_data_admissao_type_is_date(self):
        assert VINCULOS_SCHEMA["Data Admissão Declarada"].dtype == "date"

    def test_data_nascimento_type_is_date(self):
        assert VINCULOS_SCHEMA["Data de Nascimento"].dtype == "date"

    def test_razao_social_optional_in_2014(self):
        assert VINCULOS_SCHEMA["Razão Social"].optional is True

    def test_pis_not_optional(self):
        assert VINCULOS_SCHEMA["PIS"].optional is False

    def test_monthly_cc_suffixes_not_in_schema(self):
        """Remunerações mensais com sufixo CC/SC devem ser descartadas."""
        for alias in all_aliases(VINCULOS_SCHEMA):
            assert not alias.endswith(" CC"), f"Alias com CC encontrado: {alias}"
            assert not alias.endswith(" SC"), f"Alias com SC encontrado: {alias}"

    def test_50_columns_total(self):
        """Exatamente 50 colunas do layout historico (2014-2023), mais os aliases
        do layout alternativo de 2024+ que apontam para os mesmos nomes canonicos."""
        assert len(VINCULOS_SCHEMA) == 50 + len(VINCULOS_ALT_ALIASES_2024)

    def test_afastamento_cols_present(self):
        assert "Causa Afastamento 1" in VINCULOS_SCHEMA
        assert "Causa Afastamento 3" in VINCULOS_SCHEMA
        assert "Qtd Dias Afastamento" in VINCULOS_SCHEMA

    def test_cbo_2002_canonical_name(self):
        assert VINCULOS_SCHEMA["CBO Ocupação 2002"].name == "cbo_2002"

    def test_cnae20_subclasse_canonical_name(self):
        assert VINCULOS_SCHEMA["CNAE 2.0 Subclasse"].name == "cnae20_subclasse"

    def test_ind_trab_intermitente_not_in_schema(self):
        """Ind Trab Intermitente não foi selecionado pelo usuário."""
        assert "Ind Trab Intermitente" not in VINCULOS_SCHEMA


# ── ESTAB_SCHEMA ──────────────────────────────────────────────────────────────

class TestEstabSchema:
    def test_contains_cnpj_cei(self):
        assert "CNPJ / CEI" in ESTAB_SCHEMA

    def test_cnpj_cei_canonical_name(self):
        assert ESTAB_SCHEMA["CNPJ / CEI"].name == "cnpj_cei"

    def test_23_columns_total(self):
        """Exatamente 23 colunas do layout historico, mais os aliases do
        layout novo (extensão .COMT, a partir de 2024)."""
        assert len(ESTAB_SCHEMA) == 23 + len(ESTAB_ALT_ALIASES_2024)

    def test_removed_cols_absent(self):
        """Colunas removidas pelo usuário não devem constar no schema."""
        removed = [
            "Ind CEI Vinculado",
            "Número Telefone Empresa",
            "Email Estabelecimento",
            "CNAE 95 Classe",
            "Ind Atividade Ano",
            "Ind Estab Participa PAT",
        ]
        for col in removed:
            assert col not in ESTAB_SCHEMA, f"Coluna removida ainda presente: {col}"

    def test_qtd_vinculos_ativos_type_is_int(self):
        assert ESTAB_SCHEMA["Qtd Vínculos Ativos"].dtype == "int"

    def test_data_abertura_type_is_date(self):
        assert ESTAB_SCHEMA["Data Abertura"].dtype == "date"

    def test_razao_social_type_is_str(self):
        assert ESTAB_SCHEMA["Razão Social"].dtype == "str"

    def test_ind_simples_type_is_str(self):
        """Indicadores são códigos → mantidos como string."""
        assert ESTAB_SCHEMA["Ind Simples"].dtype == "str"


# ── resolve_column ─────────────────────────────────────────────────────────────

class TestResolveColumn:
    def test_exact_match_vinculos(self):
        spec = resolve_column("PIS", VINCULOS_SCHEMA)
        assert spec is not None
        assert spec.name == "pis"

    def test_trimmed_match(self):
        """Header pode ter espaços ao redor — deve resolver mesmo assim."""
        spec = resolve_column("  PIS  ", VINCULOS_SCHEMA)
        assert spec is not None

    def test_unknown_column_returns_none(self):
        spec = resolve_column("Coluna Inexistente XYZ", VINCULOS_SCHEMA)
        assert spec is None

    def test_exact_match_estab(self):
        spec = resolve_column("CNPJ / CEI", ESTAB_SCHEMA)
        assert spec is not None
        assert spec.name == "cnpj_cei"
