"""BIT durum süresi ve değişim trendi — `F4-080`.

Kabul: bilinen PASS/FAIL aralıkları doğru süre ve değişim sayısı verir.

"Bilinen" burada birebir: koşu dizileri elle yazılır, beklenen aralıklar,
süreler ve değişim sayıları da elle hesaplanır. Hiçbir beklenen değer
koda sorularak üretilmez.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.analysis.bit_trend import (
    BitInterval,
    BitTrendError,
    build_trend,
    build_trends,
)
from sonar_analyzer.domain.event import BitResult, BitState, Severity
from sonar_analyzer.domain.time_range import TimeRange

S = 1_000_000_000
COMPONENT = "Thermal Management"
TEST_ID = 3


def _runs(states: str, *, test_id: int = TEST_ID, component: str = COMPONENT) -> list[BitResult]:
    """`"PPFFP"` gibi bir dizgeyi saniyede bir koşan BIT sonuçlarına çevirir."""
    mapping = {
        "P": BitState.PASS,
        "F": BitState.FAIL,
        "W": BitState.WARN,
        "N": BitState.NOT_RUN,
        "U": BitState.UNKNOWN,
    }
    return [
        BitResult(
            timestamp_ns=index * S,
            test_id=test_id,
            component=component,
            state=mapping[letter],
            severity=Severity.ERROR if letter == "F" else Severity.INFO,
        )
        for index, letter in enumerate(states)
    ]


# --------------------------------------------------------------------------- #
# araliklar
# --------------------------------------------------------------------------- #


def test_a_single_run_becomes_one_interval() -> None:
    trend = build_trend(_runs("P"), end_ns=5 * S)
    assert len(trend.intervals) == 1
    interval = trend.intervals[0]
    assert interval.state is BitState.PASS
    assert (interval.start_ns, interval.end_ns) == (0, 5 * S)
    assert interval.run_count == 1


def test_repeated_identical_runs_collapse_into_one_interval() -> None:
    """Beş kez PASS tek bir aralıktır, beş değil."""
    trend = build_trend(_runs("PPPPP"), end_ns=10 * S)
    assert len(trend.intervals) == 1
    assert trend.intervals[0].run_count == 5
    assert trend.intervals[0].duration_seconds == 10.0


def test_a_known_pass_fail_pass_sequence_has_the_expected_intervals() -> None:
    """`PPFFFP` — 0..2 PASS, 2..5 FAIL, 5..8 PASS (kayıt 8 s'de biter)."""
    trend = build_trend(_runs("PPFFFP"), end_ns=8 * S)

    assert [(item.state, item.start_ns // S, item.end_ns // S) for item in trend.intervals] == [
        (BitState.PASS, 0, 2),
        (BitState.FAIL, 2, 5),
        (BitState.PASS, 5, 8),
    ]
    assert [item.run_count for item in trend.intervals] == [2, 3, 1]


def test_an_interval_ends_where_the_next_one_starts() -> None:
    """Aralıklar boşluksuz zincirlenir; arada kayıp zaman kalmaz."""
    trend = build_trend(_runs("PFPF"), end_ns=10 * S)
    for earlier, later in zip(trend.intervals, trend.intervals[1:]):
        assert earlier.end_ns == later.start_ns
    assert trend.intervals[-1].end_ns == 10 * S


def test_the_intervals_cover_the_whole_recording() -> None:
    trend = build_trend(_runs("PPF"), end_ns=12 * S)
    assert trend.intervals[0].start_ns == 0
    assert trend.total_ns == 12 * S


def test_runs_are_sorted_before_grouping() -> None:
    """Sıralanmamış girdi de doğru aralıkları vermeli."""
    runs = _runs("PPFFFP")
    shuffled = [runs[4], runs[0], runs[3], runs[5], runs[1], runs[2]]
    assert (
        build_trend(shuffled, end_ns=8 * S).intervals == build_trend(runs, end_ns=8 * S).intervals
    )


# --------------------------------------------------------------------------- #
# sure
# --------------------------------------------------------------------------- #


def test_the_time_in_each_state_is_summed() -> None:
    """`PPFFFP`: PASS 2 + 3 = 5 s, FAIL 3 s."""
    trend = build_trend(_runs("PPFFFP"), end_ns=8 * S)
    assert trend.duration_for(BitState.PASS) == 5 * S
    assert trend.duration_for(BitState.FAIL) == 3 * S
    assert trend.duration_for(BitState.WARN) == 0


def test_separate_failure_stretches_are_added_together() -> None:
    """`FPFPF`: 0..1, 2..3, 4..9 -> 1 + 1 + 5 = 7 s."""
    trend = build_trend(_runs("FPFPF"), end_ns=9 * S)
    assert trend.failure_ns() == 7 * S
    assert trend.duration_for(BitState.PASS) == 2 * S


def test_warn_counts_as_a_failure_state() -> None:
    """`BitState.is_failure` WARN'ı da kapsar; süre ona göre toplanır."""
    trend = build_trend(_runs("PWWP"), end_ns=6 * S)
    assert trend.duration_for(BitState.WARN) == 2 * S
    assert trend.failure_ns() == 2 * S


def test_the_failure_ratio_is_the_failing_share_of_the_recording() -> None:
    trend = build_trend(_runs("PPFFFP"), end_ns=8 * S)
    assert abs(trend.failure_ratio() - 3 / 8) < 1e-12


def test_a_clean_recording_has_no_failure_time() -> None:
    trend = build_trend(_runs("PPPP"), end_ns=10 * S)
    assert trend.failure_ns() == 0
    assert trend.failure_ratio() == 0.0
    assert trend.first_failure() is None


def test_without_a_closing_time_the_last_interval_has_no_duration() -> None:
    """Son koşudan sonrası bilinmiyor; uydurma süre üretilmez."""
    trend = build_trend(_runs("PPF"))
    assert trend.intervals[-1].duration_ns == 0
    assert trend.total_ns == 2 * S


def test_a_closing_time_before_the_last_run_is_refused() -> None:
    with pytest.raises(BitTrendError, match="kapanış zamanı"):
        build_trend(_runs("PPF"), end_ns=S)


def test_a_closing_time_exactly_at_the_last_run_is_accepted() -> None:
    trend = build_trend(_runs("PPF"), end_ns=2 * S)
    assert trend.intervals[-1].duration_ns == 0


# --------------------------------------------------------------------------- #
# degisim sayisi
# --------------------------------------------------------------------------- #


def test_a_steady_state_has_no_changes() -> None:
    assert build_trend(_runs("PPPPP"), end_ns=9 * S).change_count == 0


def test_the_known_sequence_has_two_changes() -> None:
    """`PPFFFP` -> PASS→FAIL ve FAIL→PASS: iki değişim."""
    trend = build_trend(_runs("PPFFFP"), end_ns=8 * S)
    assert trend.change_count == 2
    assert [(t.previous, t.current, t.timestamp_ns // S) for t in trend.transitions] == [
        (BitState.PASS, BitState.FAIL, 2),
        (BitState.FAIL, BitState.PASS, 5),
    ]


def test_every_flip_is_counted() -> None:
    """`PFPFPF` — beş değişim."""
    assert build_trend(_runs("PFPFPF"), end_ns=9 * S).change_count == 5


def test_a_transition_between_two_failure_states_still_counts() -> None:
    """WARN'dan FAIL'e geçiş de bir durum değişimidir."""
    trend = build_trend(_runs("WF"), end_ns=4 * S)
    assert trend.change_count == 1
    transition = trend.transitions[0]
    assert not transition.became_failure  # ikisi de ariza
    assert not transition.recovered


def test_becoming_a_failure_and_recovering_are_distinguished() -> None:
    trend = build_trend(_runs("PFP"), end_ns=5 * S)
    assert trend.transitions[0].became_failure
    assert not trend.transitions[0].recovered
    assert trend.transitions[1].recovered
    assert not trend.transitions[1].became_failure


def test_a_transition_is_timestamped_where_the_new_state_starts() -> None:
    trend = build_trend(_runs("PPPF"), end_ns=6 * S)
    assert trend.transitions[0].timestamp_ns == 3 * S


# --------------------------------------------------------------------------- #
# ozetler
# --------------------------------------------------------------------------- #


def test_the_trend_reports_its_first_and_last_state() -> None:
    trend = build_trend(_runs("PPFFFP"), end_ns=8 * S)
    assert trend.first_state is BitState.PASS
    assert trend.last_state is BitState.PASS
    assert trend.run_count == 6


def test_the_first_failure_is_the_earliest_failing_interval() -> None:
    trend = build_trend(_runs("PPFPF"), end_ns=8 * S)
    first = trend.first_failure()
    assert first is not None
    assert first.start_ns == 2 * S
    assert first.state is BitState.FAIL


def test_intervals_can_be_filtered_by_window() -> None:
    trend = build_trend(_runs("PPFFFP"), end_ns=8 * S)
    window = TimeRange(3 * S, 6 * S)
    assert [item.state for item in trend.intervals_in(window)] == [BitState.FAIL, BitState.PASS]


def test_a_window_outside_the_recording_selects_nothing() -> None:
    trend = build_trend(_runs("PPF"), end_ns=5 * S)
    assert trend.intervals_in(TimeRange(20 * S, 30 * S)) == ()


def test_an_empty_run_list_gives_an_empty_trend() -> None:
    trend = build_trend([])
    assert trend.intervals == ()
    assert trend.transitions == ()
    assert trend.change_count == 0
    assert trend.first_state is None
    assert trend.failure_ratio() == 0.0


# --------------------------------------------------------------------------- #
# birden cok bilesen
# --------------------------------------------------------------------------- #


def test_mixing_two_tests_in_one_trend_is_refused() -> None:
    """Sessizce birleştirmek anlamsız bir trend üretirdi."""
    mixed = [*_runs("PP"), *_runs("FF", test_id=9, component="Power")]
    with pytest.raises(BitTrendError, match="tek bir BIT testi"):
        build_trend(mixed)


def test_build_trends_splits_by_component() -> None:
    mixed = [*_runs("PPF"), *_runs("FFP", test_id=9, component="Power")]
    trends = build_trends(mixed, end_ns=5 * S)

    assert [trend.component for trend in trends] == [COMPONENT, "Power"]
    assert trends[0].change_count == 1
    assert trends[1].change_count == 1
    assert trends[0].duration_for(BitState.FAIL) == 3 * S
    assert trends[1].duration_for(BitState.FAIL) == 2 * S


def test_build_trends_keeps_first_appearance_order() -> None:
    mixed = [*_runs("P", test_id=9, component="Power"), *_runs("P")]
    assert [trend.component for trend in build_trends(mixed)] == ["Power", COMPONENT]


def test_build_trends_on_an_empty_input_gives_nothing() -> None:
    assert build_trends([]) == ()


# --------------------------------------------------------------------------- #
# aralik gecerliligi
# --------------------------------------------------------------------------- #


def test_a_backwards_interval_is_refused() -> None:
    with pytest.raises(BitTrendError, match="küçük olamaz"):
        BitInterval(COMPONENT, TEST_ID, BitState.PASS, start_ns=5 * S, end_ns=S)


def test_an_interval_needs_at_least_one_run() -> None:
    with pytest.raises(BitTrendError, match="koşu sayısı"):
        BitInterval(COMPONENT, TEST_ID, BitState.PASS, 0, S, run_count=0)


def test_an_interval_reports_its_span_and_failure_flag() -> None:
    interval = BitInterval(COMPONENT, TEST_ID, BitState.FAIL, 2 * S, 5 * S)
    assert interval.span == TimeRange(2 * S, 5 * S)
    assert interval.is_failure
    assert interval.duration_seconds == 3.0
