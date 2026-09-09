"""İndeks dosyasını atomik kaydetme — `F2-031`.

Kabul: yarım geçici dosya geçerli indeksin üzerine alınmaz.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sonar_analyzer.io.index.storage import load_index_json, save_index_atomic


def test_save_and_load_round_trips_payload(tmp_path: Path) -> None:
    target = tmp_path / "index.json"
    payload = {"version": 1, "records": [1, 2, 3]}

    save_index_atomic(target, payload)

    assert target.exists()
    assert load_index_json(target) == payload


def test_save_leaves_no_temp_file_behind_on_success(tmp_path: Path) -> None:
    target = tmp_path / "index.json"
    save_index_atomic(target, {"a": 1})

    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == []


def test_stray_incomplete_temp_file_is_never_adopted(tmp_path: Path) -> None:
    """Kabul kriteri birebir: yarım geçici dosya geçerli indeksin üzerine alınmaz."""
    target = tmp_path / "index.json"
    good_payload = {"version": 1, "status": "gecerli"}
    save_index_atomic(target, good_payload)

    # Bir onceki (basarisiz) yazma girisiminden kalmis gibi, yarim/bozuk
    # icerikli bir .tmp dosyasi ayni dizine birakilir.
    stray_temp = tmp_path / (target.name + ".stray123.tmp")
    stray_temp.write_text('{"version": 1, "status": "YARIM VE BOZUK', encoding="utf-8")

    # target hala eski gecerli icerigi taşımali; stray .tmp hicbir zaman
    # okunmaz/benimsenmez.
    assert load_index_json(target) == good_payload


def test_interrupted_write_does_not_replace_existing_valid_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rename adimindan hemen once cokme simulasyonu: eski gecerli indeks korunur."""
    target = tmp_path / "index.json"
    original_payload = {"version": 1, "status": "orijinal"}
    save_index_atomic(target, original_payload)

    def _boom(self: Path, other: object) -> None:
        raise OSError("simulated crash before rename completes")

    monkeypatch.setattr(Path, "replace", _boom)

    with pytest.raises(OSError, match="simulated crash"):
        save_index_atomic(target, {"version": 2, "status": "yarim"})

    # Path.replace mock'landigi icin gercek dosya okumak icin patch'i kaldir.
    monkeypatch.undo()
    assert load_index_json(target) == original_payload


def test_interrupted_write_cleans_up_its_own_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "index.json"

    def _boom(self: Path, other: object) -> None:
        raise OSError("simulated crash before rename completes")

    monkeypatch.setattr(Path, "replace", _boom)

    with pytest.raises(OSError):
        save_index_atomic(target, {"version": 1})

    monkeypatch.undo()
    assert list(tmp_path.glob("*.tmp")) == []
    assert not target.exists()


# -- load_index_json'un bozuk/eksik dosyalarda zarif davranisi -------------


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    assert load_index_json(tmp_path / "yok.json") is None


def test_load_corrupt_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "bozuk.json"
    path.write_text("{ bu gecerli json degil", encoding="utf-8")
    assert load_index_json(path) is None


def test_load_non_object_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "liste.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_index_json(path) is None


def test_load_invalid_utf8_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_bytes(b"\xff\xfe\x00")
    assert load_index_json(path) is None


def test_flush_failure_preserves_previous_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "index.json"
    save_index_atomic(target, {"version": 1})

    def fail_sync(fd: int) -> None:
        raise OSError("disk flush failed")

    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(OSError, match="disk flush"):
        save_index_atomic(target, {"version": 2})
    assert load_index_json(target) == {"version": 1}
    assert list(tmp_path.glob("*.tmp")) == []
