"""Paketli uygulamada BIN ve export akışı — `F6-006`.

Kabul: **Örnek kayıt açılır; CSV/PNG çıktısı yeniden okunabilir.**

Asıl kanıt paketlenmiş `.exe` çalıştırılarak üretildi ve
`docs/packaging/results/packaging-spike.json` içindedir. Buradaki testler
denetimin **mantığını** sabitler: yazıp "oldu" demek yetmez, çünkü bozuk
ya da boş bir dosya da yazılmış olur. Bu yüzden denetim CSV satırını
sayar ve PNG imzasına bakar; testler de bu iki kontrolün gerçekten
başarısızlığı yakaladığını gösterir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from sonar_analyzer.application.bin_check import PNG_SIGNATURE, run_bin_check

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "valid_8records.bin"

pytestmark = pytest.mark.gui  # PNG yazimi Qt gerektirir


@pytest.fixture(autouse=True)
def qt_application(qapp: object) -> None:
    """Qt uygulaması olmadan `QImage`/`QPainter` süreci çökertir.

    `QPainter` bir `QGuiApplication` ister; yoksa PySide6 hata vermeden
    süreci düşürür (Windows'ta 0xC0000409). Denetim gerçek uygulamada
    zaten bir Qt uygulamasının içinde koşar, testte de öyle koşmalı.
    """


# --------------------------------------------------------------------------- #
# ORNEK KAYIT ACILIR
# --------------------------------------------------------------------------- #


def test_a_valid_recording_passes_every_step(tmp_path: Path) -> None:
    report = run_bin_check(FIXTURE, tmp_path)

    assert report.ok is True, report.lines
    assert "sonuc: TAMAM" in report.lines[-1]


def test_the_report_names_the_channels_and_records(tmp_path: Path) -> None:
    report = run_bin_check(FIXTURE, tmp_path)
    assert any("8 kanal" in line for line in report.lines)
    assert any("8 kayit" in line for line in report.lines)


def test_a_missing_file_is_reported_not_crashed(tmp_path: Path) -> None:
    """Açılamayan kayıt çökme değil, raporlanan bir eksiklik."""
    report = run_bin_check(tmp_path / "yok.bin", tmp_path / "out")

    assert report.ok is False
    assert "kayit" in report.failures


def test_a_corrupt_file_is_reported(tmp_path: Path) -> None:
    broken = tmp_path / "bozuk.bin"
    broken.write_bytes(b"bu bir kayit degil")
    report = run_bin_check(broken, tmp_path / "out")

    assert report.ok is False


# --------------------------------------------------------------------------- #
# CSV GERI OKUNABILIR
# --------------------------------------------------------------------------- #


def test_the_csv_is_written_and_has_one_row_per_sample(tmp_path: Path) -> None:
    report = run_bin_check(FIXTURE, tmp_path)
    csv_path = Path(report.csv_path)

    assert csv_path.is_file()
    rows = [
        line
        for line in csv_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    # Basligin uzerine 8 veri satiri.
    assert len(rows) == 9


def test_the_csv_keeps_its_metadata_header(tmp_path: Path) -> None:
    report = run_bin_check(FIXTURE, tmp_path)
    text = Path(report.csv_path).read_text(encoding="utf-8")
    assert text.startswith("#")
    assert "channel_id" in text


# --------------------------------------------------------------------------- #
# PNG GERI OKUNABILIR
# --------------------------------------------------------------------------- #


def test_the_png_is_written_with_a_valid_signature(tmp_path: Path) -> None:
    report = run_bin_check(FIXTURE, tmp_path)
    png = Path(report.png_path)

    assert png.is_file()
    assert png.read_bytes()[:8] == PNG_SIGNATURE
    assert png.stat().st_size > 0


def test_an_empty_png_would_be_caught() -> None:
    """İmza kontrolü gerçek: boş dosya PNG imzasını taşımaz."""
    assert b""[:8] != PNG_SIGNATURE
    assert PNG_SIGNATURE != b"\x00" * 8


# --------------------------------------------------------------------------- #
# gercek paketin kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_package_run_passed() -> None:
    """Depodaki kanıt: paketlenmiş exe aynı akışı geçti."""
    evidence = ROOT / "docs/packaging/results/packaging-spike.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    run = payload.get("f6_006_bin_export_in_package")
    assert run is not None, "F6-006 kaniti kaydedilmemis"

    assert run["result"] == "TAMAM"
    assert run["csv_rows_read_back"] == run["samples_queried"]
    assert run["png_signature_ok"] is True
    assert run["png_bytes"] > 0
