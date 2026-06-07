"""
Varredura da árvore de diretórios da RAIS.

Retorna uma lista de RaisJob, um por arquivo TXT a processar.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RaisJob:
    dataset: str        # "vinculos" | "estabelecimentos"
    ano: int
    source: Path
    uf_hint: str | None  # 2 letras (UF) para arquivos por-estado; None para regionais/nacionais


# ── patterns ──────────────────────────────────────────────────────────────────

# Estabelecimentos: Estb2014ID.txt
_RE_ESTB = re.compile(r"^Estb(\d{4})ID\.txt$", re.IGNORECASE)

# Vínculos por UF: AC2014ID.txt  (2 letras + 4 dígitos + ID.txt)
_RE_VINC_UF = re.compile(r"^([A-Z]{2})(\d{4})ID\.txt$", re.IGNORECASE)

# Vínculos por região: RAIS_VINC_ID_NORTE.txt  /  RAIS_VINC_ID_SP.txt
_RE_VINC_REG = re.compile(r"^RAIS_VINC_ID_.+\.txt$", re.IGNORECASE)

# Pasta de vínculos por ano: "RAIS 2014"
_RE_VINC_DIR = re.compile(r"^RAIS\s+(\d{4})$", re.IGNORECASE)


def discover_jobs(base_dir: Path) -> list[RaisJob]:
    """Varre base_dir procurando os dois conjuntos da RAIS e retorna jobs."""
    jobs: list[RaisJob] = []
    jobs.extend(_scan_estabelecimentos(base_dir))
    jobs.extend(_scan_vinculos(base_dir))
    return jobs


def _scan_estabelecimentos(base_dir: Path) -> list[RaisJob]:
    estb_dir = base_dir / "RAIS Estabelecimentos"
    if not estb_dir.is_dir():
        return []
    result = []
    for f in estb_dir.iterdir():
        if f.suffix.lower() != ".txt":
            continue
        m = _RE_ESTB.match(f.name)
        if m:
            result.append(RaisJob(
                dataset="estabelecimentos",
                ano=int(m.group(1)),
                source=f,
                uf_hint=None,
            ))
    return result


def _scan_vinculos(base_dir: Path) -> list[RaisJob]:
    vinc_root = base_dir / "RAIS Vínculos"
    if not vinc_root.is_dir():
        return []
    result = []
    for pasta in vinc_root.iterdir():
        if not pasta.is_dir():
            continue
        m_dir = _RE_VINC_DIR.match(pasta.name)
        if not m_dir:
            continue
        ano = int(m_dir.group(1))
        for f in pasta.rglob("*.txt"):
            if _RE_VINC_UF.match(f.name):
                uf = _RE_VINC_UF.match(f.name).group(1).upper()
                result.append(RaisJob(dataset="vinculos", ano=ano, source=f, uf_hint=uf))
            elif _RE_VINC_REG.match(f.name):
                result.append(RaisJob(dataset="vinculos", ano=ano, source=f, uf_hint=None))
    return result
