"""
ETL principal: lê um arquivo TXT da RAIS em chunks → transforma → grava Parquet.

Usa pandas para leitura (suporte nativo a latin-1 e chunked I/O) e
pyarrow para escrita Parquet particionada (compressão zstd).
"""

from __future__ import annotations
import csv
import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from rais_etl.config import VINCULOS_SCHEMA, ESTAB_SCHEMA, ColSpec
from rais_etl.discover import RaisJob
from rais_etl.manifest import Manifest
from rais_etl.schema import check_file_schema
from rais_etl.transform import select_and_rename

logger = logging.getLogger(__name__)

CHUNKSIZE = 500_000  # linhas por chunk

# Mapeamento dtype canônico → tipo PyArrow
_ARROW_TYPES: dict[str, pa.DataType] = {
    "str":    pa.string(),
    "int":    pa.int32(),
    "double": pa.float64(),
    "date":   pa.date32(),
}


def _get_schema(dataset: str) -> dict[str, ColSpec]:
    if dataset == "vinculos":
        return VINCULOS_SCHEMA
    if dataset == "estabelecimentos":
        return ESTAB_SCHEMA
    raise ValueError(f"Dataset desconhecido: {dataset}")


def _build_arrow_schema(col_schema: dict[str, ColSpec]) -> pa.Schema:
    """Constrói o schema PyArrow canônico (colunas na ordem do config + ano + uf).

    Vários aliases (layouts históricos e alternativos) podem apontar para o
    mesmo nome canônico — cada nome entra uma única vez no schema de saída.
    """
    fields = [pa.field("ano", pa.int32())]
    seen_names: set[str] = set()
    for spec in col_schema.values():
        if spec.name in seen_names:
            continue
        seen_names.add(spec.name)
        fields.append(pa.field(spec.name, _ARROW_TYPES.get(spec.dtype, pa.string())))
    fields.append(pa.field("uf", pa.string()))
    return pa.schema(fields)


def process_job(
    job: RaisJob,
    output_dir: Path,
    manifest: Manifest,
    force: bool = False,
) -> int:
    """
    Processa um RaisJob: lê o TXT, transforma, grava Parquet particionado.

    Retorna o número de linhas gravadas.
    Se já estiver no manifesto e force=False, pula sem processar.
    """
    output_dir = Path(output_dir)
    filename = job.source.name

    if not force and manifest.is_done(job.dataset, job.ano, filename):
        logger.info("Pulando (já processado): %s", filename)
        return 0

    if job.source.stat().st_size == 0:
        logger.info("Pulando arquivo vazio: %s", filename)
        manifest.mark_done(job.dataset, job.ano, filename, rows=0, size_bytes=0)
        return 0

    col_schema = _get_schema(job.dataset)
    arrow_schema = _build_arrow_schema(col_schema)

    # Destino dos Parquets
    dataset_dir = output_dir / job.dataset
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # Se reprocessando, remove partições antigas deste arquivo
    if force and manifest.is_done(job.dataset, job.ano, filename):
        manifest.remove(job.dataset, job.ano, filename)

    # ── Lê o cabeçalho para verificar o schema ────────────────────────────
    # Layout histórico (2014-2023): separador ";", sem aspas.
    # Layout novo (a partir de 2024): CSV padrão com aspas, separador ",".
    with open(job.source, encoding="latin-1") as fh:
        raw_header = fh.readline().rstrip("\n").rstrip("\r")
    sep = ";" if ";" in raw_header else ","
    file_headers = next(csv.reader([raw_header], delimiter=sep))

    report = check_file_schema(file_headers, col_schema)
    if report.missing_optional:
        logger.info("%s: colunas opcionais ausentes (serão NULL): %s",
                    filename, report.missing_optional)
    if not report.is_ok:
        logger.warning("%s: colunas obrigatórias ausentes: %s",
                       filename, report.missing_required)

    # ── Lê em chunks e grava Parquet particionado por ano/uf ─────────────
    total_rows = 0
    writer_map: dict[str, pq.ParquetWriter] = {}

    try:
        chunks = pd.read_csv(
            job.source,
            sep=sep,
            encoding="latin-1",
            dtype=str,
            chunksize=CHUNKSIZE,
            on_bad_lines="skip",
        )

        for chunk in chunks:
            df = select_and_rename(chunk, col_schema, job.ano)
            if df.empty:
                continue

            # Converte para Arrow
            table = _df_to_arrow(df, arrow_schema)
            total_rows += len(table)

            # Agrupa por uf e grava em arquivo separado por partição
            uf_col = table.column("uf")
            for uf_val in uf_col.unique().to_pylist():
                uf_str = str(uf_val) if uf_val is not None else "00"
                mask = pa.compute.equal(uf_col, pa.scalar(uf_val))
                partition_table = table.filter(mask)

                part_dir = dataset_dir / f"ano={job.ano}" / f"uf={uf_str}"
                part_dir.mkdir(parents=True, exist_ok=True)
                part_file = part_dir / f"{Path(filename).stem}.parquet"

                if part_file not in writer_map:
                    writer_map[part_file] = pq.ParquetWriter(
                        part_file, arrow_schema, compression="zstd"
                    )
                writer_map[part_file].write_table(partition_table)

    finally:
        for writer in writer_map.values():
            writer.close()

    manifest.mark_done(job.dataset, job.ano, filename,
                       rows=total_rows, size_bytes=job.source.stat().st_size)
    logger.info("Concluido: %s -> %d linhas", filename, total_rows)
    return total_rows


def _df_to_arrow(df: pd.DataFrame, arrow_schema: pa.Schema) -> pa.Table:
    """Converte DataFrame para Arrow, alinhando com o schema canônico."""
    arrays = []
    for field in arrow_schema:
        if field.name in df.columns:
            col = df[field.name]
            try:
                arrays.append(pa.array(col.tolist(), type=field.type, from_pandas=True))
            except (pa.ArrowInvalid, pa.ArrowTypeError):
                # Fallback: converte como string para não perder dados
                arrays.append(pa.array(col.astype(str).tolist(), type=pa.string()))
        else:
            arrays.append(pa.nulls(len(df), type=field.type))

    return pa.table(arrays, schema=arrow_schema)
