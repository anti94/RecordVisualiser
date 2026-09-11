"""Burst, kayıp ve sıra dışı paket simülatörü — `F5-036`.

Kabul: **Her senaryo seed ile tekrar üretilebilir.**

Tekrar üretilebilirlik burada "iki koşu aynı sonucu verdi" demekle
yetinilmeden sınanır: aynı seed'li iki koşunun **paket paket** aynı
diziyi ürettiği, farklı seed'in genelde farklı ürettiği ve araya başka
bir `random` kullanımı girse bile sonucun değişmediği gösterilir. Son
madde önemlidir; modül global rastgeleliği kullansaydı aynı seed farklı
sonuç verebilirdi ve "tekrar üretilebilir" sözü tutmazdı.

Ayrıca üç bozulma türünün gerçekten *o* bozulmayı ürettiği ayrı ayrı
doğrulanır: kayıp paketi yok eder, sıra dışı paketi geciktirir ama **yok
etmez**, tekrar aynı paketi iki kez verir.
"""

from __future__ import annotations

import random
from collections.abc import Iterator, Sequence

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.impairment import (
    DEFAULT_SEED,
    ImpairedSource,
    ImpairmentProfile,
)
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats

START_NS = 1_788_901_200_000_000_000
CHANNELS = (ChannelMetadata(id="ch0", path="/ch0", name="ch0", dtype="float32"),)


def _packet(window: int) -> LivePacket:
    at_ns = START_NS + window * RECORD_PERIOD_NS
    chunk = DataChunk(
        "ch0",
        np.array([at_ns], dtype=np.int64),
        np.array([float(window)], dtype=np.float64),
    )
    return LivePacket(sequence_no=window, received_ns=at_ns, chunks=[chunk])


class _CleanSource:
    """Bozulmamış referans akış."""

    def __init__(self, count: int) -> None:
        self._count = count
        self.state = ConnectionState.CONNECTED
        self._stats = LiveStats()
        self.connect_calls = 0
        self.disconnect_calls = 0

    def channels(self) -> Sequence[ChannelMetadata]:
        return CHANNELS

    def stats(self) -> LiveStats:
        return self._stats

    def connect(self) -> None:
        self.connect_calls += 1

    def disconnect(self) -> None:
        self.disconnect_calls += 1

    def packets(self) -> Iterator[LivePacket]:
        for window in range(self._count):
            yield _packet(window)


def _sequences(source: ImpairedSource) -> list[int]:
    return [packet.sequence_no for packet in source.packets()]


def _impaired(
    count: int,
    profile: ImpairmentProfile,
    *,
    seed: int = DEFAULT_SEED,
) -> ImpairedSource:
    return ImpairedSource(_CleanSource(count), profile, seed=seed, sleep=lambda _s: None)


# --------------------------------------------------------------------------- #
# HER SENARYO SEED ILE TEKRAR URETILEBILIR
# --------------------------------------------------------------------------- #


def test_the_same_seed_replays_the_same_stream_packet_for_packet() -> None:
    profile = ImpairmentProfile(loss_ratio=0.2, reorder_ratio=0.2, duplicate_ratio=0.1)
    first = _sequences(_impaired(200, profile, seed=7))
    second = _sequences(_impaired(200, profile, seed=7))

    assert first == second
    assert len(first) < 200  # senaryo gercekten bozdu


def test_the_same_seed_reproduces_the_same_counters() -> None:
    profile = ImpairmentProfile(loss_ratio=0.3, reorder_ratio=0.1)
    first = _impaired(300, profile, seed=11)
    second = _impaired(300, profile, seed=11)
    _sequences(first)
    _sequences(second)

    assert first.impairment_stats == second.impairment_stats
    assert first.impairment_stats.dropped > 0


def test_a_different_seed_gives_a_different_stream() -> None:
    profile = ImpairmentProfile(loss_ratio=0.3)
    assert _sequences(_impaired(300, profile, seed=1)) != _sequences(
        _impaired(300, profile, seed=2)
    )


def test_other_random_use_cannot_disturb_a_seeded_run() -> None:
    """Modül global `random`'a dokunmaz; dokunsaydı bu test kırılırdı."""
    profile = ImpairmentProfile(loss_ratio=0.25, reorder_ratio=0.25)
    expected = _sequences(_impaired(150, profile, seed=99))

    random.seed(12345)
    for _ in range(1000):
        random.random()  # global durum kaydirildi

    assert _sequences(_impaired(150, profile, seed=99)) == expected


def test_replaying_the_same_source_object_twice_is_reproducible() -> None:
    """Aynı nesne ikinci kez okunduğunda da seed baştan başlar."""
    source = ImpairedSource(
        _CleanSource(120),
        ImpairmentProfile(loss_ratio=0.2),
        seed=5,
        sleep=lambda _s: None,
    )
    assert list(source.impair(_CleanSource(120).packets())) == list(
        source.impair(_CleanSource(120).packets())
    )


# --------------------------------------------------------------------------- #
# her bozulma turu KENDI etkisini uretir
# --------------------------------------------------------------------------- #


def test_a_clean_profile_changes_nothing() -> None:
    source = _impaired(50, ImpairmentProfile())
    assert _sequences(source) == list(range(50))
    assert source.impairment_stats.dropped == 0
    assert source.impairment_stats.reordered == 0


def test_loss_removes_packets_entirely() -> None:
    source = _impaired(400, ImpairmentProfile(loss_ratio=0.5), seed=3)
    emitted = _sequences(source)
    stats = source.impairment_stats

    assert stats.consumed == 400
    assert len(emitted) == 400 - stats.dropped
    assert sorted(emitted) == emitted  # yalniz kayip: sira bozulmaz
    assert 0.35 < stats.loss_ratio < 0.65  # yaklasik istenen oran


def test_full_loss_emits_nothing() -> None:
    source = _impaired(40, ImpairmentProfile(loss_ratio=1.0))
    assert _sequences(source) == []
    assert source.impairment_stats.dropped == 40


def test_reordering_delays_a_packet_without_losing_it() -> None:
    """Sıra dışı paket geç gelir ama **gelir**."""
    source = _impaired(100, ImpairmentProfile(reorder_ratio=0.3, reorder_depth=3), seed=4)
    emitted = _sequences(source)
    stats = source.impairment_stats

    assert stats.dropped == 0
    assert sorted(emitted) == list(range(100))  # hicbiri kaybolmadi
    assert emitted != list(range(100))  # ama sira bozuldu
    assert stats.reordered > 0


def test_every_reordered_packet_is_released_even_at_the_very_end() -> None:
    """Akışın son paketleri bekletilmiş olsa bile salınır."""
    source = _impaired(30, ImpairmentProfile(reorder_ratio=1.0, reorder_depth=50), seed=8)
    emitted = _sequences(source)

    assert sorted(emitted) == list(range(30))
    assert source.impairment_stats.reordered == 30


def test_duplicates_repeat_the_same_packet() -> None:
    source = _impaired(200, ImpairmentProfile(duplicate_ratio=0.5), seed=6)
    emitted = _sequences(source)
    stats = source.impairment_stats

    assert stats.duplicated > 0
    assert len(emitted) == 200 + stats.duplicated
    assert len(set(emitted)) == 200  # tekrarlar yeni paket uretmez


def test_loss_does_not_strand_the_reordered_packets() -> None:
    """Kayıp ve sıra dışı birlikteyken bekleyenler kilitlenmez."""
    source = _impaired(
        300, ImpairmentProfile(loss_ratio=0.3, reorder_ratio=0.3, reorder_depth=2), seed=13
    )
    emitted = _sequences(source)
    stats = source.impairment_stats

    # Gonderilen + dusen = tuketilen (tekrarlar haric).
    assert len(emitted) - stats.duplicated == stats.consumed - stats.dropped


# --------------------------------------------------------------------------- #
# burst: paketler obekler halinde, arada duraklama
# --------------------------------------------------------------------------- #


def test_a_burst_pauses_once_per_group() -> None:
    pauses: list[float] = []
    source = ImpairedSource(
        _CleanSource(20),
        ImpairmentProfile(burst_size=5, burst_pause_s=0.25),
        sleep=pauses.append,
    )
    assert _sequences(source) == list(range(20))
    assert pauses == [0.25] * 4  # 20 paket / 5 = 4 obek


def test_a_burst_size_of_one_is_a_flat_stream() -> None:
    pauses: list[float] = []
    source = ImpairedSource(
        _CleanSource(6),
        ImpairmentProfile(burst_size=1, burst_pause_s=0.1),
        sleep=pauses.append,
    )
    _sequences(source)
    assert pauses == [0.1] * 6


def test_no_pause_is_requested_when_none_is_configured() -> None:
    pauses: list[float] = []
    source = ImpairedSource(_CleanSource(10), ImpairmentProfile(burst_size=3), sleep=pauses.append)
    _sequences(source)
    assert pauses == []


# --------------------------------------------------------------------------- #
# sozlesme ve dogrulama
# --------------------------------------------------------------------------- #


def test_the_impaired_source_forwards_the_live_source_contract() -> None:
    upstream = _CleanSource(3)
    source = ImpairedSource(upstream, ImpairmentProfile())

    assert source.channels() == CHANNELS
    assert source.state is ConnectionState.CONNECTED
    source.connect()
    source.disconnect()
    assert (upstream.connect_calls, upstream.disconnect_calls) == (1, 1)


@pytest.mark.parametrize("value", [-0.1, 1.5])
def test_a_loss_ratio_outside_zero_to_one_is_refused(value: float) -> None:
    with pytest.raises(ValueError, match="loss_ratio \\[0, 1\\]"):
        ImpairmentProfile(loss_ratio=value)


@pytest.mark.parametrize("value", [-0.1, 1.5])
def test_a_reorder_ratio_outside_zero_to_one_is_refused(value: float) -> None:
    with pytest.raises(ValueError, match="reorder_ratio \\[0, 1\\]"):
        ImpairmentProfile(reorder_ratio=value)


@pytest.mark.parametrize("value", [-0.1, 1.5])
def test_a_duplicate_ratio_outside_zero_to_one_is_refused(value: float) -> None:
    with pytest.raises(ValueError, match="duplicate_ratio \\[0, 1\\]"):
        ImpairmentProfile(duplicate_ratio=value)


def test_a_non_positive_burst_size_is_refused() -> None:
    with pytest.raises(ValueError, match="burst_size pozitif olmali"):
        ImpairmentProfile(burst_size=0)


def test_a_non_positive_reorder_depth_is_refused() -> None:
    with pytest.raises(ValueError, match="reorder_depth pozitif olmali"):
        ImpairmentProfile(reorder_depth=0)


def test_a_negative_pause_is_refused() -> None:
    with pytest.raises(ValueError, match="burst_pause_s negatif olamaz"):
        ImpairmentProfile(burst_pause_s=-1.0)


def test_a_clean_profile_reports_itself_as_clean() -> None:
    assert ImpairmentProfile().is_clean is True
    assert ImpairmentProfile(burst_size=4).is_clean is True  # burst veri bozmaz
    assert ImpairmentProfile(loss_ratio=0.1).is_clean is False
