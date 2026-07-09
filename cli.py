#!/usr/bin/env python
"""
CLI principal do ETL da RAIS.

Comandos:
  verify-schema   Verifica os cabeçalhos de todos os TXT contra o schema canônico
  process         Converte TXT -> Parquet (incremental por padrão)
  status          Exibe o estado do manifesto (o que já foi processado)

Exemplos:
  python cli.py verify-schema
  python cli.py verify-schema --dataset vinculos

  python cli.py process --all
  python cli.py process --dataset vinculos --year 2014
  python cli.py process --dataset vinculos --year 2014 --uf AC
  python cli.py process --all --force

  python cli.py status
  python cli.py status --dataset vinculos

Configuração:
  Crie um arquivo .env na raiz do projeto com:
    RAIS_DATA_DIR=/caminho/para/os/dados/brutos
    RAIS_OUTPUT_DIR=/caminho/para/saida/parquet
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from rais_etl.config import VINCULOS_SCHEMA, ESTAB_SCHEMA
from rais_etl.discover import discover_jobs, RaisJob
from rais_etl.manifest import Manifest
from rais_etl.process import process_job
from rais_etl.schema import check_file_schema

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# -- Paths via variáveis de ambiente ------------------------------------------

def _require_env(var: str) -> Path:
    val = os.environ.get(var, "").strip()
    if not val:
        print(f"Erro: variável de ambiente '{var}' não definida.")
        print("Crie um arquivo .env baseado em .env.example.")
        sys.exit(1)
    return Path(val)


# -----------------------------------------------------------------------------
# verify-schema
# -----------------------------------------------------------------------------

def cmd_verify_schema(args) -> int:
    base_data = _require_env("RAIS_DATA_DIR")
    jobs = _filter_jobs(discover_jobs(base_data), args)
    if not jobs:
        print("Nenhum arquivo encontrado com os filtros informados.")
        return 1

    schemas = {"vinculos": VINCULOS_SCHEMA, "estabelecimentos": ESTAB_SCHEMA}
    ok_count = error_count = warn_count = 0

    for job in sorted(jobs, key=lambda j: (j.dataset, j.ano, j.source.name)):
        with open(job.source, encoding="latin-1") as fh:
            raw_header = fh.readline().rstrip("\n\r")
        sep = ";" if ";" in raw_header else ","
        headers = next(csv.reader([raw_header], delimiter=sep))
        report = check_file_schema(headers, schemas[job.dataset])

        if not report.is_ok:
            print(f"\n[ERRO] [{job.dataset}] {job.ano} / {job.source.name}")
            print(f"    Colunas obrigatorias AUSENTES: {report.missing_required}")
            error_count += 1
        elif report.missing_optional:
            print(f"\n[AVISO] [{job.dataset}] {job.ano} / {job.source.name}")
            print(f"    Colunas opcionais ausentes (-> NULL): {report.missing_optional}")
            warn_count += 1
        else:
            print(f"[OK]  [{job.dataset}] {job.ano} / {job.source.name}  ({len(headers)} colunas)")
            ok_count += 1

        if report.unknown:
            extras = [c for c in report.unknown if c not in
                      {"CNAE 95 Classe", "CBO 94 Ocupação", "Número CTPS", "PIS",
                       "Vl Remun Média (SM)", "Vl Remun Dezembro Nom",
                       "Vl Remun Dezembro (SM)", "Ind Vínculo Alvará",
                       "Tipo Salário", "Ind CEI Vinculado",
                       "Ind Estab Participa PAT", "Ind Atividade Ano"}]
            if extras:
                print(f"    Colunas novas/desconhecidas: {extras[:10]}")

    print(f"\n-- Resumo: {ok_count} OK | {warn_count} aviso | {error_count} erro --")
    return 0 if error_count == 0 else 1


# -----------------------------------------------------------------------------
# process
# -----------------------------------------------------------------------------

def cmd_process(args) -> int:
    base_data  = _require_env("RAIS_DATA_DIR")
    output_dir = _require_env("RAIS_OUTPUT_DIR")
    manifest   = Manifest(output_dir / "_manifest.json")
    jobs       = _filter_jobs(discover_jobs(base_data), args)

    if not jobs:
        print("Nenhum arquivo encontrado com os filtros informados.")
        return 1

    pending = [
        j for j in jobs
        if args.force or not manifest.is_done(j.dataset, j.ano, j.source.name)
    ]

    if not pending:
        print(f"Tudo já processado ({len(jobs)} arquivos). Use --force para reprocessar.")
        return 0

    print(f"Processando {len(pending)} arquivo(s) de {len(jobs)} total...")
    total_rows = 0
    errors = []

    for i, job in enumerate(sorted(pending, key=lambda j: (j.dataset, j.ano, j.source.name)), 1):
        size_mb = job.source.stat().st_size / 1_000_000
        print(f"\n[{i}/{len(pending)}] {job.dataset} {job.ano} / {job.source.name} ({size_mb:.0f} MB)")
        try:
            rows = process_job(job, output_dir=output_dir, manifest=manifest, force=args.force)
            total_rows += rows
            if rows > 0:
                print(f"           -> {rows:,} linhas gravadas")
        except Exception as exc:
            logger.error("Erro em %s: %s", job.source.name, exc)
            errors.append((job, exc))

    print(f"\n-- Concluído: {total_rows:,} linhas totais | {len(errors)} erro(s) --")
    return 0 if not errors else 1


# -----------------------------------------------------------------------------
# status
# -----------------------------------------------------------------------------

def cmd_status(args) -> int:
    output_dir = _require_env("RAIS_OUTPUT_DIR")
    manifest   = Manifest(output_dir / "_manifest.json")
    entries    = manifest.list_done(
        dataset=getattr(args, "dataset", None) or None,
    )

    if not entries:
        print("Nenhum arquivo processado ainda.")
        return 0

    from collections import defaultdict
    groups: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        groups[e.dataset][e.ano].append(e)

    total_rows = total_bytes = 0
    for ds in sorted(groups):
        print(f"\n{'-'*60}")
        print(f"  {ds.upper()}")
        print(f"{'-'*60}")
        for ano in sorted(groups[ds]):
            year_entries = groups[ds][ano]
            year_rows  = sum(e.rows for e in year_entries)
            year_bytes = sum(e.size_bytes for e in year_entries)
            print(f"  {ano}  {len(year_entries):>3} arquivo(s)  "
                  f"{year_rows:>12,} linhas  {year_bytes/1e9:>6.1f} GB fonte")
            total_rows  += year_rows
            total_bytes += year_bytes

    parquet_size = (
        sum(f.stat().st_size for f in output_dir.rglob("*.parquet"))
        if output_dir.exists() else 0
    )

    print(f"\n{'-'*60}")
    print(f"  TOTAL  {len(entries)} arquivo(s)  {total_rows:,} linhas")
    print(f"  Fonte:   {total_bytes/1e9:.1f} GB")
    print(f"  Parquet: {parquet_size/1e9:.2f} GB")
    if total_bytes > 0:
        print(f"  Compressão: {parquet_size/total_bytes:.1%}")
    return 0


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------

def _filter_jobs(jobs: list[RaisJob], args) -> list[RaisJob]:
    dataset = getattr(args, "dataset", None)
    year    = getattr(args, "year", None)
    uf      = getattr(args, "uf", None)

    if dataset:
        jobs = [j for j in jobs if j.dataset == dataset]
    if year:
        jobs = [j for j in jobs if j.ano == int(year)]
    if uf:
        jobs = [j for j in jobs if j.uf_hint == uf.upper()]
    return jobs


# -----------------------------------------------------------------------------
# argparse
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rais-etl",
        description="ETL incremental da RAIS — TXT -> Parquet/DuckDB",
    )
    sub = p.add_subparsers(dest="command", required=True)

    vs = sub.add_parser("verify-schema", help="Verifica cabeçalhos dos TXT")
    vs.add_argument("--dataset", choices=["vinculos", "estabelecimentos"])
    vs.add_argument("--year", type=int)

    pr = sub.add_parser("process", help="Converte TXT -> Parquet (incremental)")
    pr.add_argument("--dataset", choices=["vinculos", "estabelecimentos"])
    pr.add_argument("--year", type=int)
    pr.add_argument("--uf", help="Sigla de UF (ex.: SP)")
    pr.add_argument("--all", action="store_true", dest="all",
                    help="Processa todos os arquivos pendentes")
    pr.add_argument("--force", action="store_true",
                    help="Reprocessa mesmo que já esteja no manifesto")

    st = sub.add_parser("status", help="Exibe estado do manifesto")
    st.add_argument("--dataset", choices=["vinculos", "estabelecimentos"])

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    dispatch = {
        "verify-schema": cmd_verify_schema,
        "process":        cmd_process,
        "status":         cmd_status,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
