"""Profil B kayıt dizisi teşhisleri — plan Bölüm 8.3.12.

Bu üç kural tek bir kayda bakarak görülemez; ardışık kayıtlar
karşılaştırılınca ortaya çıkar. Testler beklenen değerleri **elle**
hesaplar: 125 ms = 125_000_000 ns; akustik fixture'in sayacı örnek
sayar (48 kHz × 0,125 s = 6000 tick), %1 toleransı 60 tick eder. Kodun
kendi hesabını referans almak, hatayı iki yerde birden yapmak olurdu.

Her kural için hem **tetiklenen** hem **tetiklenmeyen** durum sınanır.
Yalnız tetiklenen durumu sınamak, her girdide alarm veren bir denetimi
de geçirirdi.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.decoders.profile_b import DecodedRecord
from sonar_analyzer.io.decoders.profile_b_sequence import (
    SequenceLimits,
    check_record_sequence,
    issue_codes,
)
from sonar_analyzer.io.profile_b_format import RECORD_PERIOD_NS

PERIOD = RECORD_PERIOD_NS  # 125_000_000 ns

#: Akustik fixture'in sayaci ORNEK sayar: 48 kHz x 0,125 s = 6000 tick.
TICKS_PER_RECORD = 6_000
TOLERANCE_1PCT = TICKS_PER_RECORD // 100  # 60 tick

#: Jitter denetimi ancak tick frekansi verildiginde yapilir.
TICK_LIMITS = SequenceLimits(ticks_per_record=TICKS_PER_RECORD)


def _record(
    index: int,
    *,
    ticks: int | None = None,
    t_start: int | None = None,
) -> DecodedRecord:
    """İdeal bir kayıt; parametreler yalnız sapma sınanırken verilir."""
    return DecodedRecord(
        record_index=index,
        name=f"Data{index:05d}",
        t_start_offset_ns=index * PERIOD if t_start is None else t_start,
        byte_offset=512 + index * 48_160,
        blocks=(),
        device_ticks=index * TICKS_PER_RECORD if ticks is None else ticks,
    )


# --------------------------------------------------------------------------- #
# TEMIZ DIZI
# --------------------------------------------------------------------------- #


def test_a_clean_sequence_reports_nothing() -> None:
    """Karşı yön: her girdide alarm veren bir denetim işe yaramaz."""
    records = [_record(i) for i in range(8)]
    assert check_record_sequence(records) == []


def test_an_empty_sequence_reports_nothing() -> None:
    assert check_record_sequence([]) == []


def test_a_single_record_has_nothing_to_compare() -> None:
    """Tek kayıtta önceki yoktur; "sorun yok" demek denetim yapılmış izlenimi verirdi."""
    assert check_record_sequence([_record(0)]) == []


# --------------------------------------------------------------------------- #
# record_index MONOTONLUGU
# --------------------------------------------------------------------------- #


def test_a_skipped_index_is_reported_as_a_gap() -> None:
    records = [_record(0), _record(3)]
    issues = check_record_sequence(records)

    assert issue_codes(issues) == ["GAP_BEFORE"]
    assert issues[0].record_index == 3
    assert "2 kayit eksik" in issues[0].message


def test_the_gap_count_is_the_number_of_missing_records() -> None:
    """0 ile 1 arasında boşluk yok; 0 ile 5 arasında dört kayıt eksik."""
    issues = check_record_sequence([_record(0), _record(5)])
    assert "4 kayit eksik" in issues[0].message


def test_a_backward_index_is_not_called_a_gap() -> None:
    """Boşlukta veri kaybolur; geri gidişte dosyanın sırası bozulur."""
    issues = check_record_sequence([_record(5), _record(2)])

    assert issue_codes(issues) == ["INDEX_BACKWARD"]
    assert "geriye gitti" in issues[0].message


def test_a_repeated_index_is_reported_as_backward() -> None:
    """Aynı indeksin iki kez gelmesi de monotonluk ihlalidir."""
    issues = check_record_sequence([_record(4), _record(4)])
    assert issue_codes(issues) == ["INDEX_BACKWARD"]


def test_the_byte_offset_of_the_offending_record_is_reported() -> None:
    """ "Bir yerde bozulma var" demek, aranabilir bir teşhis değildir."""
    records = [_record(0), _record(3)]
    issues = check_record_sequence(records)
    assert issues[0].byte_offset == records[1].byte_offset


# --------------------------------------------------------------------------- #
# device_ticks JITTER
# --------------------------------------------------------------------------- #


def test_a_tick_step_inside_the_tolerance_is_accepted() -> None:
    """%1 tolerans = 60 tick; 50 tick sapma kabul edilmeli."""
    records = [_record(0, ticks=0), _record(1, ticks=TICKS_PER_RECORD + 50)]
    assert check_record_sequence(records, TICK_LIMITS) == []


def test_a_tick_step_outside_the_tolerance_is_reported() -> None:
    """61 tick sapma sınırın hemen dışıdır."""
    records = [_record(0, ticks=0), _record(1, ticks=TICKS_PER_RECORD + TOLERANCE_1PCT + 1)]
    issues = check_record_sequence(records, TICK_LIMITS)

    assert issue_codes(issues) == ["TICK_JITTER"]
    assert "sapma" in issues[0].message


def test_the_tolerance_boundary_itself_is_accepted() -> None:
    """Sınırın üstünde değil, dışında olan raporlanır."""
    records = [_record(0, ticks=0), _record(1, ticks=TICKS_PER_RECORD + TOLERANCE_1PCT)]
    assert check_record_sequence(records, TICK_LIMITS) == []


def test_a_slow_device_clock_is_reported_too() -> None:
    """Sapma iki yönlüdür; yalnız hızlanmayı aramak yarısını kaçırırdı."""
    records = [_record(0, ticks=0), _record(1, ticks=TICKS_PER_RECORD - TOLERANCE_1PCT - 1)]
    assert issue_codes(check_record_sequence(records, TICK_LIMITS)) == ["TICK_JITTER"]


def test_the_nominal_step_follows_the_index_gap() -> None:
    """Üç kayıt atlanmışsa beklenen adım da üç katıdır."""
    records = [_record(0, ticks=0), _record(3, ticks=3 * TICKS_PER_RECORD)]
    assert issue_codes(check_record_sequence(records, TICK_LIMITS)) == ["GAP_BEFORE"]


def test_a_missing_tick_counter_is_not_called_jitter() -> None:
    """Sayaç yoksa bilmediğimiz şeyi sapma diye raporlamayız."""
    records = [_record(0, ticks=0), _record(1, ticks=0)]
    assert check_record_sequence(records, TICK_LIMITS) == []


def test_the_tick_tolerance_is_configurable() -> None:
    """Farklı cihazın saat kalitesi farklıdır; sabit eşik ya çalar ya çalmaz."""
    records = [_record(0, ticks=0), _record(1, ticks=TICKS_PER_RECORD + 300)]

    assert issue_codes(check_record_sequence(records, TICK_LIMITS)) == ["TICK_JITTER"]
    loose = SequenceLimits(ticks_per_record=TICKS_PER_RECORD, tick_tolerance=0.10)
    assert check_record_sequence(records, loose) == []


def test_without_a_known_tick_rate_jitter_is_not_judged() -> None:
    """Tick frekansı bilinmiyor (`E-07`); varsayımla hüküm vermeyiz.

    Aynı veri, frekans verildiğinde jitter olarak raporlanır — yani
    denetim gerçekten atlanıyor, sessizce geçilmiyor.
    """
    records = [_record(0, ticks=0), _record(1, ticks=TICKS_PER_RECORD * 3)]

    assert check_record_sequence(records) == []  # ontanimli: tick frekansi yok
    assert issue_codes(check_record_sequence(records, TICK_LIMITS)) == ["TICK_JITTER"]


def test_ticks_are_not_checked_when_the_index_went_backward() -> None:
    """Sıra bozukken tick farkı anlamsızdır; iki kez şikâyet edilmez."""
    records = [_record(5, ticks=5 * TICKS_PER_RECORD), _record(2, ticks=0)]
    assert issue_codes(check_record_sequence(records, TICK_LIMITS)) == ["INDEX_BACKWARD"]


# --------------------------------------------------------------------------- #
# t_start_offset_ns IZGARA TUTARLILIGI
# --------------------------------------------------------------------------- #


def test_an_offset_on_the_grid_is_accepted() -> None:
    assert check_record_sequence([_record(4)]) == []


def test_an_offset_off_the_grid_is_reported() -> None:
    """1 ms tolerans; 2 ms sapma dışarıdadır."""
    issues = check_record_sequence([_record(4, t_start=4 * PERIOD + 2_000_000)])

    assert issue_codes(issues) == ["TIME_INCONSISTENT"]
    assert "izgara" in issues[0].message


def test_the_time_tolerance_boundary_is_accepted() -> None:
    assert check_record_sequence([_record(4, t_start=4 * PERIOD + 1_000_000)]) == []


def test_the_time_tolerance_is_configurable() -> None:
    records = [_record(4, t_start=4 * PERIOD + 2_000_000)]

    assert issue_codes(check_record_sequence(records)) == ["TIME_INCONSISTENT"]
    loose = SequenceLimits(time_tolerance_ns=5_000_000)
    assert check_record_sequence(records, loose) == []


def test_the_grid_check_runs_on_the_first_record_too() -> None:
    """İlk kaydın da ızgaraya oturması gerekir; önceki kayıt gerekmez."""
    issues = check_record_sequence([_record(0, t_start=9_000_000)])
    assert issue_codes(issues) == ["TIME_INCONSISTENT"]


# --------------------------------------------------------------------------- #
# BIRDEN FAZLA SORUN
# --------------------------------------------------------------------------- #


def test_several_problems_are_all_reported() -> None:
    """İlk sorunda durmak, kalan bozulmaları gizlerdi."""
    records = [
        _record(0),
        _record(3, t_start=3 * PERIOD + 9_000_000),  # bosluk + izgara sapmasi
    ]
    assert sorted(issue_codes(check_record_sequence(records))) == [
        "GAP_BEFORE",
        "TIME_INCONSISTENT",
    ]


def test_the_issue_renders_with_code_index_and_offset() -> None:
    issues = check_record_sequence([_record(0), _record(2)])
    text = str(issues[0])
    assert "GAP_BEFORE" in text
    assert "kayit 2" in text
    assert "offset" in text


# --------------------------------------------------------------------------- #
# SINIR DEGERLERI
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tick_tolerance": -0.01},
        {"time_tolerance_ns": -1},
        {"ticks_per_record": 0},
        {"record_period_ns": 0},
    ],
)
def test_invalid_limits_are_rejected(kwargs: dict[str, float]) -> None:
    """Geçersiz tolerans sessizce varsayılana düşmemeli."""
    with pytest.raises(ValueError):
        SequenceLimits(**kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# GERCEK FIXTURE
# --------------------------------------------------------------------------- #


def test_the_real_acoustic_fixture_passes_every_rule() -> None:
    """Sağlam bir dosyada alarm çalarsa, denetim kullanılamaz hâle gelir."""
    from pathlib import Path

    from sonar_analyzer.io.decoders.profile_b_sequence import check_buffer_sequence

    root = Path(__file__).resolve().parents[2]
    data = (root / "tests" / "fixtures" / "acoustic_8records.bin").read_bytes()

    assert check_buffer_sequence(data) == []
    assert check_buffer_sequence(data, TICK_LIMITS) == []


def test_the_real_fixture_records_carry_their_device_ticks() -> None:
    """`device_ticks` çözülmezse jitter denetimi sessizce hiçbir şey yapmaz."""
    from pathlib import Path

    from sonar_analyzer.io.decoders.profile_b import iter_records

    root = Path(__file__).resolve().parents[2]
    data = (root / "tests" / "fixtures" / "acoustic_8records.bin").read_bytes()

    records = list(iter_records(data))
    assert len(records) == 8
    assert [record.device_ticks for record in records] == [i * TICKS_PER_RECORD for i in range(8)]


def test_the_summary_states_when_nothing_is_wrong() -> None:
    """Sessizlik, denetimin hiç çalışmadığı anlamına da gelebilirdi."""
    from sonar_analyzer.io.decoders.profile_b_sequence import summarize

    assert summarize([], TICK_LIMITS) == "kayit dizisi: sorun yok"


def test_the_summary_counts_each_code() -> None:
    from sonar_analyzer.io.decoders.profile_b_sequence import summarize

    issues = check_record_sequence([_record(0), _record(3, t_start=3 * PERIOD + 9_000_000)])
    text = summarize(issues, TICK_LIMITS)
    assert "2 tesbit" in text
    assert "GAP_BEFORE=1" in text
    assert "TIME_INCONSISTENT=1" in text
