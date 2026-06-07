"""
Manifesto incremental — registra quais arquivos TXT já foram processados.

Armazenado como JSON em <RAIS_OUTPUT_DIR>/_manifest.json.
Chave lógica: (dataset, ano, filename).
"""

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ManifestEntry:
    dataset: str
    ano: int
    filename: str
    rows: int
    size_bytes: int
    processed_at: str = ""

    def key(self) -> tuple[str, int, str]:
        return (self.dataset, self.ano, self.filename)


class Manifest:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._entries: dict[tuple, ManifestEntry] = {}
        if self._path.exists():
            self._load()

    # ── public API ────────────────────────────────────────────────────────────

    def is_done(self, dataset: str, ano: int, filename: str) -> bool:
        return (dataset, ano, filename) in self._entries

    def mark_done(
        self, dataset: str, ano: int, filename: str, rows: int, size_bytes: int
    ) -> None:
        key = (dataset, ano, filename)
        self._entries[key] = ManifestEntry(
            dataset=dataset,
            ano=ano,
            filename=filename,
            rows=rows,
            size_bytes=size_bytes,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save()

    def remove(self, dataset: str, ano: int, filename: str) -> None:
        self._entries.pop((dataset, ano, filename), None)
        self._save()

    def get_entry(self, dataset: str, ano: int, filename: str) -> ManifestEntry | None:
        return self._entries.get((dataset, ano, filename))

    def count(self) -> int:
        return len(self._entries)

    def list_done(
        self,
        dataset: str | None = None,
        ano: int | None = None,
    ) -> list[ManifestEntry]:
        result = list(self._entries.values())
        if dataset is not None:
            result = [e for e in result if e.dataset == dataset]
        if ano is not None:
            result = [e for e in result if e.ano == ano]
        return result

    # ── private ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for item in raw:
            entry = ManifestEntry(**item)
            self._entries[entry.key()] = entry

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self._entries.values()]
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
