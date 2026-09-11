"""Sıra numarasından paket kaybı hesabı — `F5-012`.

Kabul: atlanan, tekrarlı ve sıra dışı paketler ayrı sayaç üretir.

Her senaryo elle hesaplanmış beklenen sayaçlarla karşılaştırılır.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.live.sequence_tracker import (
    SEQUENCE_MODULUS,
    SequenceTracker,
)

MAX_UINT32 = SEQUENCE_MODULUS - 1


def _observe_all(tracker: SequenceTracker, sequence: list[int]) -> list[str]:
    return [tracker.observe(seq).kind for seq in sequence]


# --------------------------------------------------------------------------- #
# temel siralar
# --------------------------------------------------------------------------- #


def test_a_clean_ascending_sequence_is_all_in_order() -> None:
    tracker = SequenceTracker()
    kinds = _observe_all(tracker, [0, 1, 2, 3, 4])
    assert kinds == ["in_order"] * 5
    assert tracker.stats.in_order == 5
    assert tracker.stats.gaps == 0
    assert tracker.stats.duplicates == 0
    assert tracker.stats.out_of_order == 0
    assert tracker.stats.resets == 0
    assert tracker.stats.total_observed == 5


def test_the_first_observation_is_always_in_order() -> None:
    tracker = SequenceTracker()
    assert tracker.observe(500).kind == "in_order"


# --------------------------------------------------------------------------- #
# atlanan paketler (gap)
# --------------------------------------------------------------------------- #


def test_a_forward_gap_reports_the_exact_missing_count() -> None:
    tracker = SequenceTracker()
    tracker.observe(0)
    tracker.observe(1)
    observation = tracker.observe(5)  # 2,3,4 atlandi
    assert observation.kind == "gap"
    assert observation.gap_size == 3
    assert tracker.stats.gaps == 1
    assert tracker.stats.missing_total == 3


def test_multiple_gaps_accumulate_the_missing_total() -> None:
    tracker = SequenceTracker()
    tracker.observe(0)
    tracker.observe(3)  # 1,2 atlandi -> gap_size 2
    tracker.observe(10)  # 4..9 atlandi -> gap_size 6
    assert tracker.stats.gaps == 2
    assert tracker.stats.missing_total == 8  # 2 + 6


def test_a_single_missing_packet_has_gap_size_one() -> None:
    tracker = SequenceTracker()
    tracker.observe(0)
    observation = tracker.observe(2)  # yalniz 1 atlandi
    assert observation.gap_size == 1


# --------------------------------------------------------------------------- #
# tekrarli paketler (duplicate)
# --------------------------------------------------------------------------- #


def test_an_exact_repeat_is_a_duplicate() -> None:
    tracker = SequenceTracker()
    kinds = _observe_all(tracker, [0, 1, 1, 2])
    assert kinds == ["in_order", "in_order", "duplicate", "in_order"]
    assert tracker.stats.duplicates == 1
    assert tracker.stats.in_order == 3


def test_the_first_observation_repeated_is_also_a_duplicate() -> None:
    tracker = SequenceTracker()
    tracker.observe(7)
    assert tracker.observe(7).kind == "duplicate"


def test_a_gapped_value_seen_again_is_a_duplicate_not_another_gap() -> None:
    tracker = SequenceTracker()
    tracker.observe(0)
    tracker.observe(5)  # gap, 1..4 atlandi; 5 artik "gorulmus"
    observation = tracker.observe(5)  # tekrar
    assert observation.kind == "duplicate"
    assert tracker.stats.gaps == 1  # ikinci kez gap sayilmadi
    assert tracker.stats.duplicates == 1


# --------------------------------------------------------------------------- #
# sira disi (out of order) - gec gelen paket
# --------------------------------------------------------------------------- #


def test_a_late_arrival_after_a_gap_is_out_of_order_not_duplicate() -> None:
    """0 -> 2 (gap, 1 atlandi) -> 1 (gec gelen, daha once GORULMEMIS) -> 3 (in_order)."""
    tracker = SequenceTracker()
    kinds = _observe_all(tracker, [0, 2, 1, 3])
    assert kinds == ["in_order", "gap", "out_of_order", "in_order"]
    assert tracker.stats.in_order == 2
    assert tracker.stats.gaps == 1
    assert tracker.stats.missing_total == 1
    assert tracker.stats.out_of_order == 1
    assert tracker.stats.duplicates == 0


def test_out_of_order_does_not_move_the_last_seen_pointer() -> None:
    """Geç gelen bir paket "son görülen"i geri almaz — sonraki beklenti değişmez."""
    tracker = SequenceTracker()
    tracker.observe(0)
    tracker.observe(5)  # last=5
    tracker.observe(4)  # gec gelen, out_of_order
    observation = tracker.observe(6)  # last+1 hala 6 olmali (5'ten devam)
    assert observation.kind == "in_order"


# --------------------------------------------------------------------------- #
# sarma (wraparound) - ADR-003 SS2.4 ile ayni desen
# --------------------------------------------------------------------------- #


def test_wraparound_by_exactly_one_step_is_in_order() -> None:
    tracker = SequenceTracker()
    tracker.observe(MAX_UINT32)  # 4294967295
    observation = tracker.observe(0)  # sardi
    assert observation.kind == "in_order"


def test_wraparound_with_missing_packets_is_a_gap_with_the_right_size() -> None:
    tracker = SequenceTracker()
    tracker.observe(MAX_UINT32 - 1)  # 4294967294
    # 4294967295, 0, 1 atlandi -> gap_size 3
    observation = tracker.observe(2)
    assert observation.kind == "gap"
    assert observation.gap_size == 3
    assert tracker.stats.missing_total == 3


def test_sequence_no_outside_uint32_range_is_refused() -> None:
    tracker = SequenceTracker()
    with pytest.raises(ValueError, match="uint32"):
        tracker.observe(-1)
    with pytest.raises(ValueError, match="uint32"):
        tracker.observe(SEQUENCE_MODULUS)


# --------------------------------------------------------------------------- #
# reset - makul hicbir aciklamaya uymayan buyuk geri sicrama
# --------------------------------------------------------------------------- #


def test_a_large_backward_jump_beyond_tolerance_is_a_reset() -> None:
    """Küçük bir tolerans (10) ile: 995'lik bir geri sıçrama ne sarma ne OOO'dur."""
    tracker = SequenceTracker(max_plausible_gap=10)
    tracker.observe(1000)
    observation = tracker.observe(5)  # ne sarma (uzak), ne OOO (tolerans disi)
    assert observation.kind == "reset"
    assert tracker.stats.resets == 1


def test_a_reset_starts_a_fresh_expectation() -> None:
    tracker = SequenceTracker(max_plausible_gap=10)
    tracker.observe(1000)
    tracker.observe(5)  # reset, last simdi 5
    observation = tracker.observe(6)  # yeni oturumun ikinci paketi
    assert observation.kind == "in_order"


def test_a_reset_clears_the_duplicate_window() -> None:
    """Reset sonrası eski oturumun değerleri "tekrar" gibi görünmemeli."""
    tracker = SequenceTracker(max_plausible_gap=10)
    tracker.observe(1000)
    tracker.observe(5)  # reset
    # Eski oturumdan '1000' degeri simdi tekrar gelse bile ilk kez goruluyor sayilir.
    observation = tracker.observe(1000)
    assert observation.kind != "duplicate"


def test_a_backward_jump_within_tolerance_is_out_of_order_not_reset() -> None:
    tracker = SequenceTracker(max_plausible_gap=10)
    tracker.observe(1000)
    observation = tracker.observe(995)  # tam sinirin altinda (fark 5 <= 10)
    assert observation.kind == "out_of_order"


# --------------------------------------------------------------------------- #
# bellek sinirlamasi - tekrar penceresi sinirsiz buyumez
# --------------------------------------------------------------------------- #


def test_the_duplicate_window_is_bounded() -> None:
    """Pencere dolduğunda çok eski bir değer artık "tekrar" olarak tanınmaz."""
    tracker = SequenceTracker(duplicate_window=4)
    for seq in range(10):  # pencereyi asan uzunlukta ardisik dizi
        tracker.observe(seq)
    # 0 artik pencerede degil (yalniz son 4 deger: 6,7,8,9 tutuluyor).
    observation = tracker.observe(0)
    assert observation.kind != "duplicate"


def test_a_value_still_inside_the_window_is_recognized_as_duplicate() -> None:
    tracker = SequenceTracker(duplicate_window=4)
    for seq in range(5):
        tracker.observe(seq)  # pencerede kalanlar: 1,2,3,4
    assert tracker.observe(4).kind == "duplicate"


# --------------------------------------------------------------------------- #
# yapilandirma dogrulamasi
# --------------------------------------------------------------------------- #


def test_max_plausible_gap_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_plausible_gap pozitif olmali"):
        SequenceTracker(max_plausible_gap=0)


def test_duplicate_window_must_be_positive() -> None:
    with pytest.raises(ValueError, match="duplicate_window pozitif olmali"):
        SequenceTracker(duplicate_window=0)
