"""Profil C oturumu — `F7-045`…`F7-052` (Qt'siz bölüm).

Kabuller: klasör seçicisi kayıt klasörü ayırt eder; şema yolu ayarlarda
saklanır; geçersiz şema hangi alanın sorunlu olduğunu söyler; şema
uyuşmazsa kayıt açılmaz ama arayüz çökmez.

Bu katmanın sessiz hatası **tek bir hata mesajıdır**. Şema seçilmemiş,
dosya yok, şema bozuk ve şema kayıtla uyuşmuyor — dördü de "kayıt
açılamadı" diye gösterilseydi kullanıcı neyi düzelteceğini bilemezdi.
Testlerin çoğunluğu bu dört durumun **ayrı ayrı** adlandırıldığını
doğrular.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.profile_c_writer import WriteSpec, write_recording

from sonar_analyzer.application.profile_c_session import (
    OpenFailure,
    load_configured_schema,
    open_recording,
    schema_summary,
    warning_report,
)
from sonar_analyzer.io.schema.loader import load_text
from sonar_analyzer.settings.store import SCHEMA_VERSION, AppSettings, load_settings

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"

SENSORS = 4
SAMPLES = 8


def _small_schema_text() -> str:
    return (
        EXAMPLE.read_text(encoding="utf-8")
        .replace("sensor_count = 32", f"sensor_count = {SENSORS}")
        .replace("frame_samples = 820", f"frame_samples = {SAMPLES}")
    )


@pytest.fixture
def schema_file(tmp_path: Path) -> Path:
    path = tmp_path / "sema.toml"
    path.write_text(_small_schema_text(), encoding="utf-8")
    return path


@pytest.fixture
def recording(tmp_path: Path) -> Path:
    return write_recording(
        tmp_path / "kayitlar", WriteSpec(seconds=2, sensors=SENSORS, samples=SAMPLES)
    )


# --------------------------------------------------------------------------- #
# F7-048 — SEMA AYARDA SAKLANIYOR
# --------------------------------------------------------------------------- #


def test_the_schema_path_defaults_to_empty() -> None:
    """Uygulamaya gömülü bir şema yok; kullanıcı seçmeli."""
    assert AppSettings().profile_c_schema_path == ""


def test_the_schema_path_survives_a_round_trip(tmp_path: Path) -> None:
    import json

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {"schema_version": SCHEMA_VERSION, "profile_c_schema_path": "C:/sema/profil-c.toml"}
        ),
        encoding="utf-8",
    )

    result = load_settings(path)

    assert result.settings.profile_c_schema_path == "C:/sema/profil-c.toml"


def test_recent_folders_are_kept_apart_from_recent_files(tmp_path: Path) -> None:
    """Asıl kabul: klasör yolu eklemek dosya geçmişini bozmamalı.

    İkisi farklı açma yollarına gider; tek listede tutulsalardı bir
    klasör dosya olarak açılmaya çalışılırdı.
    """
    import json

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "recent_files": ["C:/a.bin", "C:/b.bin"],
                "recent_folders": ["C:/kayitlar/2026-09-12T14-30-00Z"],
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(path).settings

    assert settings.recent_files == ["C:/a.bin", "C:/b.bin"]
    assert settings.recent_folders == ["C:/kayitlar/2026-09-12T14-30-00Z"]


def test_a_broken_recent_folders_list_falls_back_with_a_warning(tmp_path: Path) -> None:
    import json

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "recent_folders": "liste degil"}),
        encoding="utf-8",
    )

    result = load_settings(path)

    assert result.settings.recent_folders == []
    assert result.warnings


# --------------------------------------------------------------------------- #
# DORT AYRI BASARISIZLIK
# --------------------------------------------------------------------------- #


def test_no_schema_configured_says_so(recording: Path) -> None:
    """Asıl kabul: "kayıt açılamadı" demek yetmez."""
    result = open_recording(recording, "")

    assert result.ok is False
    assert result.failure is OpenFailure.NO_SCHEMA_CONFIGURED
    assert result.report is not None
    assert "Settings" in result.report.action


def test_the_missing_schema_message_explains_why_it_is_needed(recording: Path) -> None:
    """Şemanın neden gerektiği yazılmazsa, ayar keyfî bir engel gibi görünür."""
    report = open_recording(recording, "").report

    assert report is not None
    assert "C++" in report.detail
    assert "gömülü değildir" in report.detail


def test_a_missing_schema_file_is_named_separately(recording: Path, tmp_path: Path) -> None:
    result = open_recording(recording, str(tmp_path / "hicyok.toml"))

    assert result.failure is OpenFailure.SCHEMA_FILE_MISSING
    assert result.report is not None
    assert "hicyok.toml" in result.report.detail


def test_an_invalid_schema_names_the_field(recording: Path, tmp_path: Path) -> None:
    """Asıl kabul: hangi alanın hangi offsette sorunlu olduğu görünmeli."""
    broken = tmp_path / "bozuk.toml"
    broken.write_text(
        _small_schema_text().replace(
            'name = "frame_index"\ntype = "uint32_t"\noffset = 4',
            'name = "frame_index"\ntype = "widget_t"\noffset = 4',
        ),
        encoding="utf-8",
    )

    result = open_recording(recording, str(broken))

    assert result.failure is OpenFailure.SCHEMA_INVALID
    assert result.report is not None
    assert "frame_index" in result.report.detail
    assert "widget_t" in result.report.detail


def test_a_layout_error_points_at_the_contract(recording: Path, tmp_path: Path) -> None:
    broken = tmp_path / "cakisma.toml"
    broken.write_text(
        _small_schema_text().replace(
            'name = "sensor_count"\ntype = "uint16_t"\noffset = 18',
            'name = "sensor_count"\ntype = "uint16_t"\noffset = 17',
        ),
        encoding="utf-8",
    )

    result = open_recording(recording, str(broken))

    assert result.failure is OpenFailure.SCHEMA_INVALID
    assert result.report is not None
    assert "toml-schema.md" in result.report.action


def test_a_folder_that_is_not_a_recording_is_named_separately(
    tmp_path: Path, schema_file: Path
) -> None:
    empty = tmp_path / "bos"
    empty.mkdir()

    result = open_recording(empty, str(schema_file))

    assert result.failure is OpenFailure.FOLDER_INVALID
    assert result.report is not None
    assert "Tx/" in result.report.detail


def test_the_folder_error_tells_the_user_what_to_pick(tmp_path: Path, schema_file: Path) -> None:
    """Kullanıcı çoğu zaman üst klasörü seçer; mesaj bunu söylemeli."""
    parent = tmp_path / "ust"
    parent.mkdir()
    write_recording(parent, WriteSpec(seconds=1, sensors=SENSORS, samples=SAMPLES))

    result = open_recording(parent, str(schema_file))

    assert result.failure is OpenFailure.FOLDER_INVALID
    assert result.report is not None
    assert "üst klasörünü değil" in result.report.action


def test_a_mismatched_schema_stops_the_open(recording: Path, tmp_path: Path) -> None:
    """Asıl kabul: şema kayıtla uyuşmuyorsa kayıt **açılmaz** (§7)."""
    wrong = tmp_path / "yanlis.toml"
    wrong.write_text(
        _small_schema_text().replace(f"sensor_count = {SENSORS}", "sensor_count = 9"),
        encoding="utf-8",
    )

    result = open_recording(recording, str(wrong))

    assert result.ok is False
    assert result.failure is OpenFailure.SCHEMA_MISMATCH
    assert result.report is not None
    assert "hatasız görünürdü" in result.report.detail


def test_the_four_failures_are_distinct(recording: Path, tmp_path: Path) -> None:
    """Dördü aynı koda düşseydi, ayrı mesaj yazmanın anlamı kalmazdı."""
    broken = tmp_path / "b.toml"
    broken.write_text("bu gecerli toml degil [[", encoding="utf-8")
    wrong = tmp_path / "w.toml"
    wrong.write_text(
        _small_schema_text().replace(f"sensor_count = {SENSORS}", "sensor_count = 9"),
        encoding="utf-8",
    )

    failures = {
        open_recording(recording, "").failure,
        open_recording(recording, str(tmp_path / "yok.toml")).failure,
        open_recording(recording, str(broken)).failure,
        open_recording(recording, str(wrong)).failure,
    }

    assert len(failures) == 4


# --------------------------------------------------------------------------- #
# BASARILI ACMA
# --------------------------------------------------------------------------- #


def test_a_matching_schema_opens_the_recording(recording: Path, schema_file: Path) -> None:
    """Karşı yön: doğru şemayla kayıt açılmalı."""
    result = open_recording(recording, str(schema_file))

    assert result.ok is True
    assert result.failure is None
    assert result.repository is not None
    assert len(result.repository.channels()) == 2 * SENSORS
    result.repository.close()


def test_opening_reports_folder_warnings(tmp_path: Path, schema_file: Path) -> None:
    folder = write_recording(tmp_path / "k", WriteSpec(seconds=3, sensors=SENSORS, samples=SAMPLES))
    (folder / "Rx" / "RxData00001.bin").unlink()

    result = open_recording(folder, str(schema_file))

    assert result.ok is True
    assert any("bosluk" in warning for warning in result.warnings)
    assert result.repository is not None
    result.repository.close()


def test_warnings_become_a_recoverable_report() -> None:
    report = warning_report(("S: 4..8 arasinda bildirilmemis 4 bayt bosluk",))

    assert report is not None
    assert report.recoverable is True


def test_no_warnings_produces_no_report() -> None:
    assert warning_report(()) is None


# --------------------------------------------------------------------------- #
# F7-052 — KAYIT KARTI OZETI
# --------------------------------------------------------------------------- #


def test_the_summary_shows_the_schema_identity(recording: Path) -> None:
    """Asıl kabul: aynı klasör iki şemayla iki farklı sonuç verir.

    Hangisinin kullanıldığı ekranda görünmezse, yanlış olan fark edilmez.
    """
    schema = load_text(_small_schema_text())

    summary = schema_summary(schema, recording)

    assert summary["Şema"] == "sonar-profile-c v1"
    assert summary["Sensör"] == str(SENSORS)
    assert summary["Frame örneği"] == str(SAMPLES)
    assert summary["Klasör"] == recording.name


def test_the_summary_names_the_sample_type_and_layout(recording: Path) -> None:
    """Yerleşim yanlışsa sensörler karışır ve hiçbir boyut denetimi düşmez."""
    summary = schema_summary(load_text(_small_schema_text()), recording)

    assert summary["Örnek tipi"] == "std::complex<float>"
    assert summary["Yerleşim"] == "sensor_major"


# --------------------------------------------------------------------------- #
# SEMA YUKLEME AYRI TEST EDILEBILIR
# --------------------------------------------------------------------------- #


def test_load_configured_schema_returns_the_schema(schema_file: Path) -> None:
    schema, failure = load_configured_schema(str(schema_file))

    assert failure is None
    assert schema is not None
    assert schema.id == "sonar-profile-c"


def test_load_configured_schema_reports_an_empty_path() -> None:
    schema, failure = load_configured_schema("   ")

    assert schema is None
    assert failure is not None
    assert failure.failure is OpenFailure.NO_SCHEMA_CONFIGURED
