"""Testes para schema.py — verificação de cabeçalhos dos arquivos TXT."""
import pytest
from pathlib import Path
from rais_etl.config import VINCULOS_SCHEMA, VINCULOS_ALT_ALIASES_2024, ESTAB_SCHEMA
from rais_etl.schema import check_file_schema, SchemaReport


@pytest.fixture()
def vinculos_header_2014() -> list[str]:
    return [
        "Município", "CNAE 95 Classe", "Vínculo Ativo 31/12", "Tipo Vínculo",
        "Motivo Desligamento", "Mês Desligamento", "Ind Vínculo Alvará",
        "Tipo Admissão", "Tipo Salário", "CBO 94 Ocupação",
        "Escolaridade após 2005", "Sexo Trabalhador", "Nacionalidade",
        "Raça Cor", "Ind Portador Defic", "Tamanho Estabelecimento",
        "Natureza Jurídica", "Ind CEI Vinculado", "Tipo Estab",
        "Ind Estab Participa PAT", "Ind Simples", "Data Admissão Declarada",
        "Vl Remun Média Nom", "Vl Remun Média (SM)", "Vl Remun Dezembro Nom",
        "Vl Remun Dezembro (SM)", "Tempo Emprego", "Qtd Hora Contr",
        "Vl Última Remuneração Ano", "Vl Salário Contratual", "PIS",
        "Data de Nascimento", "Número CTPS", "CPF", "CEI Vinculado",
        "CNPJ / CEI", "CNPJ Raiz", "Nome Trabalhador", "CBO Ocupação 2002",
        "CNAE 2.0 Classe", "CNAE 2.0 Subclasse", "Tipo Defic",
        "Causa Afastamento 1", "Dia Ini AF1", "Mês Ini AF1", "Dia Fim AF1", "Mês Fim AF1",
        "Causa Afastamento 2", "Dia Ini AF2", "Mês Ini AF2", "Dia Fim AF2", "Mês Fim AF2",
        "Causa Afastamento 3", "Dia Ini AF3", "Mês Ini AF3", "Dia Fim AF3", "Mês Fim AF3",
        "Qtd Dias Afastamento", "Idade", "Dia de Desligamento",
        # NÃO tem: Razão Social, IBGE Subsetor, CEP Estab, Mun Trab, Ano Chegada Brasil
    ]


@pytest.fixture()
def vinculos_header_2018(vinculos_header_2014) -> list[str]:
    return vinculos_header_2014 + [
        "IBGE Subsetor", "Ano Chegada Brasil", "CEP Estab", "Mun Trab",
        "Razão Social",
        "Vl Rem Janeiro CC", "Vl Rem Fevereiro CC",  # deve ser ignorado
        "Ind Trab Intermitente", "Ind Trab Parcial",
    ]


class TestCheckFileSchema:
    def test_returns_schema_report(self, vinculos_header_2014):
        report = check_file_schema(vinculos_header_2014, VINCULOS_SCHEMA)
        assert isinstance(report, SchemaReport)

    def test_missing_optional_cols_listed(self, vinculos_header_2014):
        """Razão Social é opcional e ausente em 2014 → deve aparecer em missing_optional."""
        report = check_file_schema(vinculos_header_2014, VINCULOS_SCHEMA)
        assert "Razão Social" in report.missing_optional

    def test_no_missing_required_in_2014(self, vinculos_header_2014):
        """Todas as colunas obrigatórias do schema estão em 2014."""
        report = check_file_schema(vinculos_header_2014, VINCULOS_SCHEMA)
        assert len(report.missing_required) == 0

    def test_unknown_cols_listed(self, vinculos_header_2014):
        """Colunas no arquivo que não estão no schema → unknown."""
        report = check_file_schema(vinculos_header_2014, VINCULOS_SCHEMA)
        # "CNAE 95 Classe" não está no VINCULOS_SCHEMA
        assert "CNAE 95 Classe" in report.unknown

    def test_monthly_cc_sc_in_unknown(self, vinculos_header_2018):
        """Colunas CC/SC devem aparecer em unknown (não fazem parte do schema)."""
        report = check_file_schema(vinculos_header_2018, VINCULOS_SCHEMA)
        assert "Vl Rem Janeiro CC" in report.unknown

    def test_ok_when_all_required_present(self, vinculos_header_2018):
        report = check_file_schema(vinculos_header_2018, VINCULOS_SCHEMA)
        assert len(report.missing_required) == 0

    def test_missing_required_detected(self):
        """Remove uma coluna obrigatória → deve aparecer em missing_required."""
        headers_sem_pis = ["CPF", "Município"]  # sem PIS
        report = check_file_schema(headers_sem_pis, VINCULOS_SCHEMA)
        assert "PIS" in report.missing_required

    def test_report_is_ok_when_no_issues(self):
        """is_ok só True quando não há missing_required."""
        report = check_file_schema(list(VINCULOS_SCHEMA.keys()), VINCULOS_SCHEMA)
        assert report.is_ok

    def test_report_not_ok_when_missing_required(self):
        report = check_file_schema(["PIS"], VINCULOS_SCHEMA)
        assert not report.is_ok


@pytest.fixture()
def vinculos_header_2024() -> list[str]:
    """Cabeçalho no layout alternativo (a partir de 2024): aliases com sufixo
    "- Código" para as colunas que têm forma alternativa, aliases originais
    para as demais (PIS, CPF, Idade, etc. não mudaram de nome)."""
    alt_by_name = {name: alias for alias, name in VINCULOS_ALT_ALIASES_2024.items()}
    header = []
    seen_names = set()
    for alias, spec in VINCULOS_SCHEMA.items():
        if spec.name in seen_names:
            continue
        seen_names.add(spec.name)
        header.append(alt_by_name.get(spec.name, alias))
    return header


class TestCheckFileSchema2024Layout:
    def test_no_missing_required_with_alt_aliases_only(self, vinculos_header_2024):
        """Um arquivo 2024/2025 que só tem os aliases alternativos não deve
        acusar colunas obrigatórias ausentes — os aliases históricos e os
        alternativos representam a mesma coluna canônica."""
        report = check_file_schema(vinculos_header_2024, VINCULOS_SCHEMA)
        assert report.missing_required == []
        assert report.is_ok

    def test_historic_file_not_missing_alt_only_columns(self, vinculos_header_2014):
        """Um arquivo histórico (2014) não deve acusar como ausentes as colunas
        que só existem sob o alias alternativo — pois o alias histórico já as
        cobre."""
        report = check_file_schema(vinculos_header_2014, VINCULOS_SCHEMA)
        alt_only_aliases = set(VINCULOS_ALT_ALIASES_2024.keys())
        assert not (set(report.missing_required) & alt_only_aliases)
