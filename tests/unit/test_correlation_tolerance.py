"""Zaman korelasyonu toleransı — plan Bölüm 9.

Bir olayı bir örnekle eşlemek her zaman bir **yaklaştırmadır**: örnekler
125 ms ızgarasında, olaylar kendi anlarında üretilir. Sınır konmazsa "en
yakın örnek" araması her zaman bir sonuç döndürür — aradaki mesafe bir
saat bile olsa. Uzaktaki bir örneği olayla eşleştirmek, hiç
eşleştirmemekten daha zararlıdır: kullanıcı ilgisiz bir değere bakıp
olayı yorumlar.

Testler sınırı **iki yönden** sınar: tolerans içindeki eşleşme kabul
edilmeli, dışındaki ise reddedilmeden ama **işaretlenerek** dönmeli.
Sonucu atmak da bilgi kaybı olurdu; asıl mesele kararın görünmesidir.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.correlation import (
    DEFAULT_TOLERANCE_NS,
    CorrelationTolerance,
    nearest_within,
)

MS = 1_000_000
GRID = [0, 125 * MS, 250 * MS, 375 * MS]


# --------------------------------------------------------------------------- #
# TOLERANS NESNESI
# --------------------------------------------------------------------------- #


def test_the_default_is_one_record_period() -> None:
    """Bir olay kendi penceresindeki örnekle eşleşir; komşuya taşmaz."""
    assert DEFAULT_TOLERANCE_NS == 125 * MS
    assert CorrelationTolerance().value_ns == DEFAULT_TOLERANCE_NS


def test_a_negative_tolerance_is_rejected() -> None:
    """Geçersiz tolerans sessizce varsayılana düşmemeli."""
    with pytest.raises(ValueError, match="negatif olamaz"):
        CorrelationTolerance(value_ns=-1)


def test_the_boundary_is_inside_the_tolerance() -> None:
    tolerance = CorrelationTolerance(value_ns=100)
    assert tolerance.accepts(100)
    assert not tolerance.accepts(101)


def test_the_tolerance_is_symmetric() -> None:
    """Örnek olaydan önce de sonra da olabilir."""
    tolerance = CorrelationTolerance(value_ns=100)
    assert tolerance.accepts(-100)
    assert not tolerance.accepts(-101)


def test_a_zero_tolerance_demands_an_exact_match() -> None:
    tolerance = CorrelationTolerance(value_ns=0)
    assert tolerance.accepts(0)
    assert not tolerance.accepts(1)


def test_the_tolerance_describes_itself_in_milliseconds() -> None:
    """Nanosaniye kullanıcıya bir şey anlatmaz."""
    assert "125" in CorrelationTolerance().describe()
    assert "ms" in CorrelationTolerance().describe()


# --------------------------------------------------------------------------- #
# EN YAKIN ESLESME
# --------------------------------------------------------------------------- #


def test_an_exact_hit_has_zero_distance() -> None:
    match = nearest_within(GRID, 250 * MS)

    assert match is not None
    assert match.index == 2
    assert match.distance_ns == 0
    assert match.within_tolerance


def test_the_closer_neighbour_wins() -> None:
    """60 ms, 0'a değil 125 ms'e daha yakın değildir; 0 kazanmalı."""
    match = nearest_within(GRID, 60 * MS)

    assert match is not None
    assert match.index == 0
    assert match.distance_ns == -60 * MS


def test_the_later_neighbour_wins_when_it_is_closer() -> None:
    match = nearest_within(GRID, 70 * MS)

    assert match is not None
    assert match.index == 1
    assert match.distance_ns == 55 * MS


def test_a_target_before_the_first_sample_matches_the_first() -> None:
    match = nearest_within(GRID, -10 * MS)

    assert match is not None
    assert match.index == 0
    assert match.within_tolerance


def test_a_target_far_after_the_last_sample_is_flagged() -> None:
    """Asıl kabul: uzaktaki eşleşme sessizce doğru sayılmamalı."""
    match = nearest_within(GRID, 5_000 * MS)

    assert match is not None
    assert match.index == len(GRID) - 1
    assert not match.within_tolerance


def test_an_out_of_tolerance_match_is_still_returned() -> None:
    """Sonucu atmak da bilgi kaybıdır; karar `within_tolerance`'tadır."""
    match = nearest_within(GRID, 5_000 * MS)

    assert match is not None
    assert match.distance_ns != 0


def test_an_empty_series_has_no_match() -> None:
    """Örnek yokken bir şey uydurmak, en kötü eşleşmedir."""
    assert nearest_within([], 0) is None


def test_the_tolerance_can_be_tightened() -> None:
    """Yapılandırılabilirlik: aynı veri, farklı toleransla farklı karar."""
    strict = CorrelationTolerance(value_ns=10 * MS)

    loose_match = nearest_within(GRID, 60 * MS)
    strict_match = nearest_within(GRID, 60 * MS, strict)

    assert loose_match is not None and loose_match.within_tolerance
    assert strict_match is not None and not strict_match.within_tolerance


# --------------------------------------------------------------------------- #
# AYARLARDAN YAPILANDIRILABILIR
# --------------------------------------------------------------------------- #


def test_the_setting_defaults_to_the_record_period() -> None:
    from sonar_analyzer.settings.store import AppSettings

    assert AppSettings().correlation_tolerance_ns == DEFAULT_TOLERANCE_NS


def test_a_custom_tolerance_survives_a_round_trip(tmp_path: object) -> None:
    """Kullanıcının verdiği değer kaydedilip geri okunmalı."""
    import json
    from pathlib import Path

    from sonar_analyzer.settings.store import SCHEMA_VERSION, load_settings

    path = Path(str(tmp_path)) / "settings.json"
    path.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "correlation_tolerance_ns": 42 * MS}),
        encoding="utf-8",
    )

    result = load_settings(path)

    assert result.settings.correlation_tolerance_ns == 42 * MS


def test_an_invalid_tolerance_falls_back_with_a_warning(tmp_path: object) -> None:
    """Bozuk ayar sessizce varsayılana düşmemeli; uyarı görünmeli."""
    import json
    from pathlib import Path

    from sonar_analyzer.settings.store import SCHEMA_VERSION, load_settings

    path = Path(str(tmp_path)) / "settings.json"
    path.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "correlation_tolerance_ns": -5}),
        encoding="utf-8",
    )

    result = load_settings(path)

    assert result.settings.correlation_tolerance_ns == DEFAULT_TOLERANCE_NS
    assert any("korelasyon toleransi" in warning for warning in result.warnings)


# --------------------------------------------------------------------------- #
# DEPODA KULLANILIYOR
# --------------------------------------------------------------------------- #


def test_the_repository_reports_the_distance_of_the_matched_sample(
    tmp_path: object,
) -> None:
    """`inspect_sample` artık uzaklığı ve tolerans kararını taşımalı."""
    from pathlib import Path

    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    root = Path(__file__).resolve().parents[2]
    repository = FileRecordingRepository()
    repository.open(
        root / "tests" / "fixtures" / "valid_8records.bin",
        cache_path=Path(str(tmp_path)) / "i.sidx",
    )
    start = repository.metadata().time_range.start_ns

    exact = repository.inspect_sample("ch0", start)
    assert exact.distance_ns == 0
    assert exact.within_tolerance

    far = repository.inspect_sample("ch0", start + 60_000 * MS)
    assert not far.within_tolerance, "uzaktaki ornek 'bu ana ait' sayilmamali"
    assert far.distance_ns != 0


def test_a_tighter_tolerance_changes_the_repository_verdict(tmp_path: object) -> None:
    """Aynı örnek, dar toleransta tolerans dışı sayılmalı."""
    from pathlib import Path

    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    root = Path(__file__).resolve().parents[2]
    repository = FileRecordingRepository()
    repository.open(
        root / "tests" / "fixtures" / "valid_8records.bin",
        cache_path=Path(str(tmp_path)) / "j.sidx",
    )
    start = repository.metadata().time_range.start_ns

    default = repository.inspect_sample("ch0", start + 60 * MS)
    strict = repository.inspect_sample("ch0", start + 60 * MS, CorrelationTolerance(10 * MS))

    assert default.within_tolerance
    assert not strict.within_tolerance
