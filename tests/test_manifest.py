"""Testes para manifest.py — controle de estado incremental."""
import json
import time
import pytest
from pathlib import Path
from rais_etl.manifest import Manifest, ManifestEntry


@pytest.fixture()
def manifest_path(tmp_path: Path) -> Path:
    return tmp_path / "_manifest.json"


class TestManifest:
    def test_empty_manifest_created(self, manifest_path):
        m = Manifest(manifest_path)
        assert m.count() == 0

    def test_mark_done_persists(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1000, size_bytes=72_000_000)
        m2 = Manifest(manifest_path)
        assert m2.count() == 1

    def test_is_done_true(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1000, size_bytes=72_000_000)
        assert m.is_done("vinculos", 2014, "AC2014ID.txt")

    def test_is_done_false_unknown(self, manifest_path):
        m = Manifest(manifest_path)
        assert not m.is_done("vinculos", 2014, "AC2014ID.txt")

    def test_is_done_false_different_year(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1, size_bytes=1)
        assert not m.is_done("vinculos", 2015, "AC2015ID.txt")

    def test_mark_done_idempotent(self, manifest_path):
        """Marcar o mesmo arquivo duas vezes não duplica."""
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1000, size_bytes=72_000_000)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1000, size_bytes=72_000_000)
        assert m.count() == 1

    def test_remove_entry(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1, size_bytes=1)
        m.remove("vinculos", 2014, "AC2014ID.txt")
        assert not m.is_done("vinculos", 2014, "AC2014ID.txt")

    def test_entry_stores_rows_and_size(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1234, size_bytes=999)
        entry = m.get_entry("vinculos", 2014, "AC2014ID.txt")
        assert entry.rows == 1234
        assert entry.size_bytes == 999

    def test_list_done_by_dataset(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1, size_bytes=1)
        m.mark_done("vinculos", 2015, "AC2015ID.txt", rows=1, size_bytes=1)
        m.mark_done("estabelecimentos", 2014, "Estb2014ID.txt", rows=1, size_bytes=1)
        done = m.list_done(dataset="vinculos")
        assert len(done) == 2

    def test_list_done_by_year(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1, size_bytes=1)
        m.mark_done("vinculos", 2014, "SP2014ID.txt", rows=1, size_bytes=1)
        m.mark_done("vinculos", 2015, "AC2015ID.txt", rows=1, size_bytes=1)
        done = m.list_done(ano=2014)
        assert len(done) == 2

    def test_json_is_human_readable(self, manifest_path):
        m = Manifest(manifest_path)
        m.mark_done("vinculos", 2014, "AC2014ID.txt", rows=1, size_bytes=1)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(raw, list)
        assert raw[0]["dataset"] == "vinculos"
