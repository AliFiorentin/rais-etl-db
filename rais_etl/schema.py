"""
Verificação de schema: compara o cabeçalho real de um TXT contra o schema canônico.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from rais_etl.config import ColSpec


@dataclass
class SchemaReport:
    missing_required: list[str] = field(default_factory=list)  # no schema, obrigatório, ausente no arquivo
    missing_optional: list[str] = field(default_factory=list)  # no schema, opcional, ausente no arquivo
    unknown: list[str] = field(default_factory=list)           # no arquivo, não reconhecido pelo schema

    @property
    def is_ok(self) -> bool:
        """True quando não há colunas obrigatórias faltando."""
        return len(self.missing_required) == 0


def check_file_schema(
    file_headers: list[str],
    schema: dict[str, ColSpec],
) -> SchemaReport:
    """
    Compara os cabeçalhos de um arquivo TXT com o schema canônico.

    Parâmetros
    ----------
    file_headers : lista de nomes de colunas lidos do cabeçalho (sem trim)
    schema       : VINCULOS_SCHEMA ou ESTAB_SCHEMA
    """
    file_set = {h.strip() for h in file_headers}
    schema_set = set(schema.keys())

    # Múltiplos aliases (layouts históricos e alternativos) podem apontar para o
    # mesmo nome canônico (ColSpec.name) — uma coluna só está "ausente" se
    # NENHUM dos seus aliases aparecer no arquivo.
    aliases_by_name: dict[str, list[str]] = {}
    for alias, spec in schema.items():
        aliases_by_name.setdefault(spec.name, []).append(alias)

    missing_required = []
    missing_optional = []
    for name, aliases in aliases_by_name.items():
        if any(alias in file_set for alias in aliases):
            continue
        spec = schema[aliases[0]]
        primary_alias = aliases[0]
        if spec.optional:
            missing_optional.append(primary_alias)
        else:
            missing_required.append(primary_alias)

    unknown = [
        h.strip() for h in file_headers
        if h.strip() not in schema_set
    ]

    return SchemaReport(
        missing_required=missing_required,
        missing_optional=missing_optional,
        unknown=unknown,
    )
