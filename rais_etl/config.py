"""
Schemas canônicos para os dois datasets da RAIS.

Cada entrada no dicionário mapeia o *alias de origem* (nome exato do cabeçalho
do TXT, sem espaços extras) para um ColSpec com:
  - name   : nome canônico snake_case na saída Parquet
  - dtype  : "str" | "int" | "double" | "date"
  - optional: True quando a coluna pode estar ausente em alguns anos
              (ex.: colunas que só existem a partir de 2015 ou 2017)
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ColSpec:
    name: str
    dtype: str          # "str" | "int" | "double" | "date"
    optional: bool = False


def resolve_column(alias: str, schema: dict[str, ColSpec]) -> ColSpec | None:
    """Retorna o ColSpec para o alias (com trim), ou None se desconhecido."""
    return schema.get(alias.strip())


# ─────────────────────────────────────────────────────────────────────────────
# VÍNCULOS — 50 colunas selecionadas
# ─────────────────────────────────────────────────────────────────────────────

# Aliases que aparecem em ALGUNS anos com sufixos CC (2015-2018) ou SC (2022)
# para remuneração mensal → descartados (não entram no schema).
VINCULOS_MONTHLY_CC_SC = {
    f"Vl Rem {mes} CC" for mes in [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro",
    ]
} | {
    f"Vl Rem {mes} SC" for mes in [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro",
    ]
}

VINCULOS_SCHEMA: dict[str, ColSpec] = {
    # ── Identificadores (8) ──────────────────────────────────────────────────
    "PIS":                      ColSpec("pis",               "str"),
    "CPF":                      ColSpec("cpf",               "str"),
    "Nome Trabalhador":         ColSpec("nome_trabalhador",  "str"),
    "Data de Nascimento":       ColSpec("data_nascimento",   "date"),
    "CNPJ / CEI":               ColSpec("cnpj_cei",          "str"),
    "CNPJ Raiz":                ColSpec("cnpj_raiz",         "str"),
    "CEI Vinculado":            ColSpec("cei_vinculado",     "str"),
    "Razão Social":             ColSpec("razao_social",      "str",  optional=True),

    # ── Atributos do trabalhador (7) ────────────────────────────────────────
    "Sexo Trabalhador":         ColSpec("sexo",              "str"),
    "Idade":                    ColSpec("idade",             "int"),
    "Raça Cor":                 ColSpec("raca_cor",          "str"),
    "Nacionalidade":            ColSpec("nacionalidade",     "str"),
    "Escolaridade após 2005":   ColSpec("escolaridade",      "str"),
    "Ind Portador Defic":       ColSpec("ind_portador_defic","str"),
    "Tipo Defic":               ColSpec("tipo_defic",        "str"),

    # ── Atributos do vínculo (10) ────────────────────────────────────────────
    "Vínculo Ativo 31/12":      ColSpec("vinculo_ativo_3112","str"),
    "Tipo Vínculo":             ColSpec("tipo_vinculo",      "str"),
    "Tipo Admissão":            ColSpec("tipo_admissao",     "str"),
    "Data Admissão Declarada":  ColSpec("data_admissao",     "date"),
    "Tempo Emprego":            ColSpec("tempo_emprego",     "double"),
    "Motivo Desligamento":      ColSpec("motivo_desligamento","str"),
    "Mês Desligamento":         ColSpec("mes_desligamento",  "str"),
    "Dia de Desligamento":      ColSpec("dia_desligamento",  "str"),
    "Qtd Hora Contr":           ColSpec("qtd_hora_contr",    "int"),
    "CBO Ocupação 2002":        ColSpec("cbo_2002",          "str"),

    # ── Atributos do estabelecimento no vínculo (6) ──────────────────────────
    "Município":                ColSpec("municipio",         "str"),
    "Natureza Jurídica":        ColSpec("natureza_juridica", "str"),
    "Tamanho Estabelecimento":  ColSpec("tamanho_estab",     "str"),
    "Tipo Estab":               ColSpec("tipo_estab",        "str"),
    "CNAE 2.0 Classe":          ColSpec("cnae20_classe",     "str"),
    "CNAE 2.0 Subclasse":       ColSpec("cnae20_subclasse",  "str"),

    # ── Remuneração (3) ──────────────────────────────────────────────────────
    "Vl Remun Média Nom":       ColSpec("vl_remun_media_nom",    "double"),
    "Vl Salário Contratual":    ColSpec("vl_salario_contratual", "double"),
    "Vl Última Remuneração Ano":ColSpec("vl_ultima_remun_ano",   "double"),

    # ── Afastamentos (16) ────────────────────────────────────────────────────
    "Causa Afastamento 1":      ColSpec("causa_afast_1",     "str"),
    "Dia Ini AF1":              ColSpec("dia_ini_af1",       "str"),
    "Mês Ini AF1":              ColSpec("mes_ini_af1",       "str"),
    "Dia Fim AF1":              ColSpec("dia_fim_af1",       "str"),
    "Mês Fim AF1":              ColSpec("mes_fim_af1",       "str"),
    "Causa Afastamento 2":      ColSpec("causa_afast_2",     "str"),
    "Dia Ini AF2":              ColSpec("dia_ini_af2",       "str"),
    "Mês Ini AF2":              ColSpec("mes_ini_af2",       "str"),
    "Dia Fim AF2":              ColSpec("dia_fim_af2",       "str"),
    "Mês Fim AF2":              ColSpec("mes_fim_af2",       "str"),
    "Causa Afastamento 3":      ColSpec("causa_afast_3",     "str"),
    "Dia Ini AF3":              ColSpec("dia_ini_af3",       "str"),
    "Mês Ini AF3":              ColSpec("mes_ini_af3",       "str"),
    "Dia Fim AF3":              ColSpec("dia_fim_af3",       "str"),
    "Mês Fim AF3":              ColSpec("mes_fim_af3",       "str"),
    "Qtd Dias Afastamento":     ColSpec("qtd_dias_afast",    "int"),

}

assert len(VINCULOS_SCHEMA) == 50, f"Esperado 50, obtido {len(VINCULOS_SCHEMA)}"


# ─────────────────────────────────────────────────────────────────────────────
# ESTABELECIMENTOS — 23 colunas selecionadas
# ─────────────────────────────────────────────────────────────────────────────

ESTAB_SCHEMA: dict[str, ColSpec] = {
    # ── Identificação (4) ────────────────────────────────────────────────────
    "CNPJ / CEI":               ColSpec("cnpj_cei",              "str"),
    "CNPJ Raiz":                ColSpec("cnpj_raiz",             "str"),
    "CEI Vinculado":            ColSpec("cei_vinculado",         "str"),
    "Razão Social":             ColSpec("razao_social",          "str"),

    # ── Localização (5) ──────────────────────────────────────────────────────
    "Município":                ColSpec("municipio",             "str"),
    "CEP Estab":                ColSpec("cep_estab",             "str"),
    "Nome Logradouro":          ColSpec("nome_logradouro",       "str"),
    "Número Logradouro":        ColSpec("numero_logradouro",     "int"),
    "Nome Bairro":              ColSpec("nome_bairro",           "str"),

    # ── Classificação (6) ────────────────────────────────────────────────────
    "CNAE 2.0 Classe":          ColSpec("cnae20_classe",         "str"),
    "CNAE 2.0 Subclasse":       ColSpec("cnae20_subclasse",      "str"),
    "IBGE Subsetor":            ColSpec("ibge_subsetor",         "str"),
    "Natureza Jurídica":        ColSpec("natureza_juridica",     "str"),
    "Tamanho Estabelecimento":  ColSpec("tamanho_estab",         "str"),
    "Tipo Estab":               ColSpec("tipo_estab",            "str"),

    # ── Datas / Situação (4) ─────────────────────────────────────────────────
    "Data Abertura":            ColSpec("data_abertura",         "date"),
    "Data Baixa":               ColSpec("data_baixa",            "date"),
    "Data Encerramento":        ColSpec("data_encerramento",     "date"),
    "Ind Rais Negativa":        ColSpec("ind_rais_negativa",     "str"),

    # ── Contagens de vínculos (3) ────────────────────────────────────────────
    "Qtd Vínculos Ativos":      ColSpec("qtd_vinculos_ativos",   "int"),
    "Qtd Vínculos CLT":         ColSpec("qtd_vinculos_clt",      "int"),
    "Qtd Vínculos Estatutários":ColSpec("qtd_vinculos_estat",    "int"),

    # ── Indicadores (1) ──────────────────────────────────────────────────────
    "Ind Simples":              ColSpec("ind_simples",           "str"),
}

assert len(ESTAB_SCHEMA) == 23, f"Esperado 23, obtido {len(ESTAB_SCHEMA)}"
