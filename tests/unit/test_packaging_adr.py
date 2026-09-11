"""Paketleme ADR'si ile spike kanıtı tutarlı mı — `F6-001`.

Kabul: **PyInstaller/Nuitka seçimi spike kanıtına ve hedef Windows
ortamına dayanır.**

Bir ADR'nin en sessiz bozulma biçimi, dayandığı ölçümle zamanla
ayrışmasıdır: sayılar depoda kalır, metin başka bir şey söylemeye başlar.
Bu testler ikisini birbirine bağlar — kanıt dosyası gerçekten iki aracı da
**çalıştırılmış** olarak kaydediyor mu, ADR bu ölçümlerin işaret ettiği
kararı mı veriyor, ve seçilen aracın ölçümü dosyada var mı.

Testler ADR'nin *doğru* kararı verdiğini iddia etmez (bu bir mühendislik
yargısıdır); kararın **kanıtsız** kalmadığını denetler.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
SPIKE = ROOT / "docs/packaging/results/packaging-spike.json"
ADR = ROOT / "docs/adr/ADR-012-packaging.md"


def _spike() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(SPIKE.read_text(encoding="utf-8")))


def _tool(name: str) -> dict[str, Any]:
    """Spike kaydindan tek bir aracin olcumleri."""
    entry = _spike()[name]
    assert isinstance(entry, dict), f"{name} olcumu sozluk degil"
    return cast("dict[str, Any]", entry)


def _adr() -> str:
    return ADR.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# spike kaniti gercekten var
# --------------------------------------------------------------------------- #


def test_the_spike_evidence_file_exists() -> None:
    """ADR bir ölçüme dayandığını söylüyorsa ölçüm depoda olmalı."""
    assert SPIKE.is_file(), f"spike kaniti yok: {SPIKE}"


def test_both_tools_were_actually_built_and_run() -> None:
    """İki araç da **koşturuldu**; biri sadece okunup elenmedi."""
    for name in ("pyinstaller", "nuitka"):
        entry = _tool(name)
        assert entry["runs"] is True, f"{name} calisan bir ikili uretmedi"
        assert entry["startup_ms"], f"{name} icin acilis olcumu yok"


def test_the_spike_records_the_measurements_the_adr_cites() -> None:
    """ADR'de geçen üç ölçüt kanıt dosyasında da var."""
    for name in ("pyinstaller", "nuitka"):
        entry = _tool(name)
        assert "dist_mb" in entry
        assert "startup_median_ms" in entry
        assert "version" in entry


def test_the_spike_records_the_environment_it_ran_in() -> None:
    """Hedef ortam bilinmiyorsa bile, ölçümün koştuğu ortam bilinmeli."""
    spike = _spike()
    assert "Windows" in str(spike["platform"])
    assert str(spike["python"]).startswith("3.")


# --------------------------------------------------------------------------- #
# ADR kanitla tutarli
# --------------------------------------------------------------------------- #


def test_the_adr_states_a_decision() -> None:
    text = _adr()
    assert "## Karar" in text
    assert "PyInstaller kullanılacak" in text


def test_the_adr_names_the_evidence_file() -> None:
    """Karar, okunabilir bir kanıta işaret etmeli."""
    assert "docs/packaging/results/packaging-spike.json" in _adr()


def test_the_adr_admits_where_the_rejected_tool_was_better() -> None:
    """Nuitka iki başlıkta daha iyiydi; ADR bunu gizlemiyor.

    Yalnız kazananın iyi göründüğü bir karşılaştırma, karar değil
    gerekçelendirmedir.
    """
    text = _adr()
    assert "Nuitka ölçülen iki başlıkta" in text
    assert "göz ardı edilmiyor" in text


def test_the_measured_numbers_in_the_adr_match_the_evidence() -> None:
    """ADR tablosundaki boyut ve açılış değerleri ölçümle aynı."""
    text = _adr()
    for name in ("pyinstaller", "nuitka"):
        entry = _tool(name)
        size_mb = float(str(entry["dist_mb"]))
        startup_ms = int(float(str(entry["startup_median_ms"])))
        assert f"{size_mb:.1f}".replace(".", ",") in text.replace(".", ",")
        assert f"{startup_ms} ms" in text


def test_the_adr_records_the_unknown_target_environment() -> None:
    """Kabul kriteri hedef ortama dayanmayı ister; ortam bilinmiyorsa yazılır."""
    text = _adr()
    assert "E-10" in text
    assert "bilinmiyor" in text.lower()


def test_the_adr_records_the_version_defect_the_spike_found() -> None:
    """Spike gerçek bir kusur buldu; ADR onu takibe bağlıyor."""
    text = _adr()
    assert "0.0.0" in text and "0.21.0" in text
    assert "F6-002" in text


def test_the_spike_shows_the_packaged_version_was_wrong() -> None:
    """Kanıt dosyası da kusuru taşıyor: bildirilen sürüm gerçeğinden farklı."""
    actual = str(_spike()["actual_version"])
    for name in ("pyinstaller", "nuitka"):
        assert str(_tool(name)["reported_version"]) != actual


def test_the_adr_is_registered_in_the_index() -> None:
    index = (ROOT / "docs/adr/README.md").read_text(encoding="utf-8")
    assert "ADR-012-packaging.md" in index
    assert "| ADR-012 | Paketleme aracı ve dağıtım biçimi | **YAZILDI**" in index
