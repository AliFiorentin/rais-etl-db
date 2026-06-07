"""
Testes para process.py — ETL ponta a ponta num arquivo TXT real (AC2014ID.txt).

Usa o arquivo menor da RAIS Vínculos 2014 (~72 MB) para validar o pipeline
completo: leitura Latin-1 → transformação → escrita Parquet → verificação.
"""
import pytest
import pandas as pd
import pyarrow.parquet as pq
import duckdb
from pathlib import Path
from rais_etl.config import VINCULOS_SCHEMA, ESTAB_SCHEMA
from rais_etl.process import process_job, CHUNKSIZE
from rais_etl.discover import RaisJob
from rais_etl.manifest import Manifest


VINCULOS_AC2014 = Path(r"D:\RAIS Vínculos\RAIS 2014\AC2014ID.txt")
ESTAB_2014 = Path(r"D:\RAIS Estabelecimentos\Estb2014ID.txt")


# ─────────────────────────────────────────────────────────────────────────────
# Testes usando arquivo real AC2014ID.txt (72 MB, ~370 k linhas)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not VINCULOS_AC2014.exists(),
    reason="Arquivo real não encontrado"
)
class TestProcessJobVinculos:
    @pytest.fixture()
    def output_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "rais_db"

    @pytest.fixture()
    def manifest(self, output_dir: Path) -> Manifest:
        return Manifest(output_dir / "_manifest.json")

    @pytest.fixture()
    def job(self) -> RaisJob:
        return RaisJob(
            dataset="vinculos",
            ano=2014,
            source=VINCULOS_AC2014,
            uf_hint="AC",
        )

    def test_process_creates_parquet_files(self, job, output_dir, manifest):
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets = list((output_dir / "vinculos").rglob("*.parquet"))
        assert len(parquets) >= 1

    def test_parquet_partitioned_by_ano_uf(self, job, output_dir, manifest):
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets = list((output_dir / "vinculos").rglob("*.parquet"))
        for p in parquets:
            # Caminho deve ter ano= e uf= no path
            assert "ano=" in str(p)
            assert "uf=" in str(p)

    def test_parquet_has_canonical_columns(self, job, output_dir, manifest):
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets = list((output_dir / "vinculos").rglob("*.parquet"))
        schema = pq.read_schema(parquets[0])
        col_names = schema.names
        assert "cpf" in col_names
        assert "municipio" in col_names
        assert "vl_remun_media_nom" in col_names
        assert "ano" in col_names
        assert "uf" in col_names

    def test_parquet_row_count_matches_txt(self, job, output_dir, manifest):
        """Número de linhas no Parquet deve ser igual ao TXT menos o header."""
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets = list((output_dir / "vinculos").rglob("*.parquet"))
        total_parquet = sum(pq.read_metadata(p).num_rows for p in parquets)
        # Conta linhas do TXT original (excluindo header)
        txt_lines = sum(1 for _ in open(VINCULOS_AC2014, encoding="latin-1")) - 1
        assert total_parquet == txt_lines

    def test_process_updates_manifest(self, job, output_dir, manifest):
        process_job(job, output_dir=output_dir, manifest=manifest)
        assert manifest.is_done("vinculos", 2014, VINCULOS_AC2014.name)

    def test_process_idempotent(self, job, output_dir, manifest):
        """Rodar duas vezes não duplica linhas nem cria arquivos extras."""
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets_1 = list((output_dir / "vinculos").rglob("*.parquet"))
        count_1 = sum(pq.read_metadata(p).num_rows for p in parquets_1)

        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets_2 = list((output_dir / "vinculos").rglob("*.parquet"))
        count_2 = sum(pq.read_metadata(p).num_rows for p in parquets_2)

        assert count_1 == count_2
        assert len(parquets_1) == len(parquets_2)

    def test_duckdb_can_query_output(self, job, output_dir, manifest):
        """DuckDB deve conseguir fazer SQL sobre os Parquets gerados."""
        process_job(job, output_dir=output_dir, manifest=manifest)
        pattern = str(output_dir / "vinculos" / "**" / "*.parquet").replace("\\", "/")
        con = duckdb.connect()
        result = con.execute(
            f"SELECT count(*), avg(vl_remun_media_nom) FROM read_parquet('{pattern}', hive_partitioning=true)"
        ).fetchone()
        assert result[0] > 0
        assert result[1] is None or result[1] > 0

    def test_decimals_are_float_not_string(self, job, output_dir, manifest):
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets = list((output_dir / "vinculos").rglob("*.parquet"))
        schema = pq.read_schema(parquets[0])
        idx = schema.get_field_index("vl_remun_media_nom")
        assert str(schema.field(idx).type) in ("double", "float64")

    def test_uf_column_is_string(self, job, output_dir, manifest):
        process_job(job, output_dir=output_dir, manifest=manifest)
        parquets = list((output_dir / "vinculos").rglob("*.parquet"))
        schema = pq.read_schema(parquets[0])
        idx = schema.get_field_index("uf")
        assert str(schema.field(idx).type) in ("string", "large_string", "utf8")

    def test_force_reprocesses(self, job, output_dir, manifest):
        """--force deve reprocessar mesmo que já esteja no manifesto."""
        process_job(job, output_dir=output_dir, manifest=manifest)
        entry1 = manifest.get_entry("vinculos", 2014, VINCULOS_AC2014.name)
        ts1 = entry1.processed_at

        import time; time.sleep(0.1)
        process_job(job, output_dir=output_dir, manifest=manifest, force=True)
        entry2 = manifest.get_entry("vinculos", 2014, VINCULOS_AC2014.name)
        ts2 = entry2.processed_at
        assert ts2 > ts1
