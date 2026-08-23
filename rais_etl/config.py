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
# Layout alternativo (a partir de 2024): CSV com aspas, cabeçalhos com sufixo
# "- Código" e nomes reformulados (ex.: "Sexo - Código" em vez de
# "Sexo Trabalhador"). Mapeia alias alternativo -> nome canônico já definido
# em VINCULOS_SCHEMA acima, reaproveitando o ColSpec (mesmo dtype/optional).
# ─────────────────────────────────────────────────────────────────────────────

VINCULOS_ALT_ALIASES_2024: dict[str, str] = {
    'Município - Código': 'municipio',
    'Ind Vínculo Ativo 31/12 - Código': 'vinculo_ativo_3112',
    'Tipo Vínculo - Código': 'tipo_vinculo',
    'Motivo Desligamento - Código': 'motivo_desligamento',
    'Mês Desligamento - Código': 'mes_desligamento',
    'Tipo Admissão Trabalhador - Código': 'tipo_admissao',
    'Escolaridade Após 2005 - Código': 'escolaridade',
    'Sexo - Código': 'sexo',
    'Nacionalidade - Código': 'nacionalidade',
    'Raça Cor - Código': 'raca_cor',
    'Ind Portador Defic - Código': 'ind_portador_defic',
    'Tamanho Estabelecimento - Código': 'tamanho_estab',
    'Natureza Jurídica - Código': 'natureza_juridica',
    'Tipo Estabelecimento - Código': 'tipo_estab',
    'Data Admissão': 'data_admissao',
    'Vl Rem Média Nom': 'vl_remun_media_nom',
    'Vl Últ Rem Ano': 'vl_ultima_remun_ano',
    'Data Nascimento': 'data_nascimento',
    'CBO 2002 Ocupação - Código': 'cbo_2002',
    'CNAE 2.0 Classe - Código': 'cnae20_classe',
    'CNAE 2.0 Subclasse - Codigo': 'cnae20_subclasse',
    'Tipo Deficiência - Código': 'tipo_defic',
    'Causa Afastamento 1 - Código': 'causa_afast_1',
    'Dia Início Afastamento 1 - Código': 'dia_ini_af1',
    'Mês Início Afastamento 1 - Código': 'mes_ini_af1',
    'Dia Fim Afastamento 1 - Código': 'dia_fim_af1',
    'Mês Fim Afastamento 1 - Código': 'mes_fim_af1',
    'Causa Afastamento 2 - Código': 'causa_afast_2',
    'Dia Início Afastamento 2 - Código': 'dia_ini_af2',
    'Mês Início Afastamento 2 - Código': 'mes_ini_af2',
    'Dia Fim Afastamento 2 - Código': 'dia_fim_af2',
    'Mês Fim Afastamento 2 - Código': 'mes_fim_af2',
    'Causa Afastamento 3 - Código': 'causa_afast_3',
    'Dia Início Afastamento 3 - Código': 'dia_ini_af3',
    'Mês Início Afastamento 3 - Código': 'mes_ini_af3',
    'Dia Fim Afastamento 3 - Código': 'dia_fim_af3',
    'Mês Fim Afastamento 3 - Código': 'mes_fim_af3',
    'Dia Desligamento - Código': 'dia_desligamento',
}

_name_to_spec = {spec.name: spec for spec in VINCULOS_SCHEMA.values()}
for _alt_alias, _canonical_name in VINCULOS_ALT_ALIASES_2024.items():
    VINCULOS_SCHEMA[_alt_alias] = _name_to_spec[_canonical_name]

assert len(VINCULOS_SCHEMA) == 50 + len(VINCULOS_ALT_ALIASES_2024), (
    f"Esperado {50 + len(VINCULOS_ALT_ALIASES_2024)}, obtido {len(VINCULOS_SCHEMA)}"
)


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

# ─────────────────────────────────────────────────────────────────────────────
# Layout alternativo (a partir de 2024, extensão .COMT): mesma convenção usada
# em VINCULOS_ALT_ALIASES_2024 (sufixo "- Código"), mas para estabelecimentos
# três campos também trocam de nome por completo (não é só sufixo):
# "Logradouro do Estab", "Num Logradouro" e "Bairros - Nome".
# ─────────────────────────────────────────────────────────────────────────────

ESTAB_ALT_ALIASES_2024: dict[str, str] = {
    'Município - Código': 'municipio',
    'Natureza Jurídica - Código': 'natureza_juridica',
    'Tamanho Estabelecimento - Código': 'tamanho_estab',
    'Tipo Estabelecimento - Código': 'tipo_estab',
    'IBGE Subsetor - Código': 'ibge_subsetor',
    'CNAE 2.0 Classe - Código': 'cnae20_classe',
    'CNAE 2.0 Subclasse - Codigo': 'cnae20_subclasse',
    'Ind RAIS Negativa - Código': 'ind_rais_negativa',
    'Ind Estab Participante SIMPLES - Código': 'ind_simples',
    'Logradouro do Estab': 'nome_logradouro',
    'Num Logradouro': 'numero_logradouro',
    'Bairros - Nome': 'nome_bairro',
}

_estab_name_to_spec = {spec.name: spec for spec in ESTAB_SCHEMA.values()}
for _estab_alt_alias, _estab_canonical_name in ESTAB_ALT_ALIASES_2024.items():
    ESTAB_SCHEMA[_estab_alt_alias] = _estab_name_to_spec[_estab_canonical_name]

assert len(ESTAB_SCHEMA) == 23 + len(ESTAB_ALT_ALIASES_2024), (
    f"Esperado {23 + len(ESTAB_ALT_ALIASES_2024)}, obtido {len(ESTAB_SCHEMA)}"
)
