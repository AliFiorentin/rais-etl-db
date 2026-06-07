"""Testes para discover.py — varredura de arquivos TXT da RAIS."""
import os
import pytest
from pathlib import Path
from rais_etl.discover import discover_jobs, RaisJob


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_rais(tmp_path: Path) -> Path:
    """Cria uma árvore de pastas simulando a estrutura real da RAIS em D:\\."""
    estb = tmp_path / "RAIS Estabelecimentos"
    estb.mkdir()
    (estb / "Estb2014ID.txt").write_text("header\n", encoding="latin-1")
    (estb / "Estb2022ID.txt").write_text("header\n", encoding="latin-1")

    vinc = tmp_path / "RAIS Vínculos"
    # Formato por-UF (2014-2017)
    for ano in (2014, 2015):
        pasta = vinc / f"RAIS {ano}"
        pasta.mkdir(parents=True)
        for uf in ("AC", "SP"):
            (pasta / f"{uf}{ano}ID.txt").write_text("header\n", encoding="latin-1")

    # Formato por-região (2018+)
    pasta2018 = vinc / "RAIS 2018"
    pasta2018.mkdir(parents=True)
    for reg in ("NORTE", "SUL", "SP"):
        (pasta2018 / f"RAIS_VINC_ID_{reg}.txt").write_text("header\n", encoding="latin-1")

    return tmp_path


# ── testes de RaisJob ─────────────────────────────────────────────────────────

class TestRaisJob:
    def test_job_has_dataset_ano_source(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        j = jobs[0]
        assert hasattr(j, "dataset")   # "vinculos" | "estabelecimentos"
        assert hasattr(j, "ano")
        assert hasattr(j, "source")    # Path para o TXT
        assert hasattr(j, "uf_hint")   # UF de 2 letras ou None (para arquivos regionais)

    def test_job_source_is_path(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        for j in jobs:
            assert isinstance(j.source, Path)
            assert j.source.exists()


# ── testes de discover_jobs ───────────────────────────────────────────────────

class TestDiscoverJobs:
    def test_finds_estab_files(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        estb = [j for j in jobs if j.dataset == "estabelecimentos"]
        assert len(estb) == 2

    def test_estab_anos(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        estb_anos = {j.ano for j in jobs if j.dataset == "estabelecimentos"}
        assert estb_anos == {2014, 2022}

    def test_estab_uf_hint_is_none(self, fake_rais):
        """Estabelecimentos são nacionais — sem uf_hint."""
        jobs = discover_jobs(fake_rais)
        for j in jobs:
            if j.dataset == "estabelecimentos":
                assert j.uf_hint is None

    def test_finds_vinculos_per_uf(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        vinc = [j for j in jobs if j.dataset == "vinculos"]
        assert len(vinc) == 7  # 2 anos × 2 UFs + 3 regiões 2018

    def test_vinculos_uf_format(self, fake_rais):
        """Arquivos por-UF têm uf_hint de 2 letras maiúsculas."""
        jobs = discover_jobs(fake_rais)
        vinc_uf = [j for j in jobs if j.dataset == "vinculos" and j.uf_hint is not None]
        for j in vinc_uf:
            assert len(j.uf_hint) == 2
            assert j.uf_hint.isupper()

    def test_vinculos_regional_uf_hint_is_none(self, fake_rais):
        """Arquivos RAIS_VINC_ID_* não têm uf_hint (região, não UF)."""
        jobs = discover_jobs(fake_rais)
        vinc_reg = [
            j for j in jobs
            if j.dataset == "vinculos" and j.ano == 2018
        ]
        for j in vinc_reg:
            assert j.uf_hint is None

    def test_ano_parsed_correctly(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        anos = {j.ano for j in jobs}
        assert 2014 in anos
        assert 2018 in anos

    def test_no_duplicates(self, fake_rais):
        jobs = discover_jobs(fake_rais)
        keys = [(j.dataset, j.ano, j.source.name) for j in jobs]
        assert len(keys) == len(set(keys))

    def test_non_txt_ignored(self, fake_rais):
        """Arquivos XLS/DOC nas pastas não devem aparecer como jobs."""
        xls = fake_rais / "RAIS Vínculos" / "RAIS 2014" / "layout.xls"
        xls.write_bytes(b"dummy")
        jobs = discover_jobs(fake_rais)
        for j in jobs:
            assert j.source.suffix.lower() == ".txt"
