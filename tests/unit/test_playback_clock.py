"""Kayıt zamanına göre ilerleme saati — `F3-057`.

Kabul: 125 ms kayıt sınırları doğru sırayla geçilir.
"""

from __future__ import annotations

from sonar_analyzer.application.playback_state import PlaybackMachine

PERIOD = 0.125
BOUNDARIES = tuple(i * PERIOD for i in range(9))  # 0 .. 1.0 s, 125 ms ızgara


def _machine() -> tuple[PlaybackMachine, list[tuple[int, float]]]:
    m = PlaybackMachine(1.0)
    m.set_record_boundaries(BOUNDARIES)
    crossed: list[tuple[int, float]] = []
    m.add_record_listener(lambda i, t: crossed.append((i, t)))
    return m, crossed


def test_advancing_crosses_boundaries_in_strict_order() -> None:
    m, crossed = _machine()
    m.play()

    m.advance(0.30)  # 0 -> 0.30 s: 0.125 ve 0.25 sınırlarını geçer

    assert [i for i, _t in crossed] == [1, 2]
    assert [round(t, 3) for _i, t in crossed] == [0.125, 0.250]
    assert m.crossed_record_boundaries == 3  # 0, 1, 2 kayıtları girildi


def test_each_boundary_is_crossed_exactly_once() -> None:
    m, crossed = _machine()
    m.play()

    for _ in range(20):
        m.advance(0.05)  # küçük adımlarla sona kadar

    indices = [i for i, _t in crossed]
    assert indices == sorted(indices)
    assert indices == list(range(1, 9))  # her sınır bir kez, sırayla
    assert len(indices) == len(set(indices))


def test_one_big_jump_crosses_all_intermediate_boundaries_in_order() -> None:
    m, crossed = _machine()
    m.play()

    m.advance(10.0)  # tek hamlede sona

    assert [i for i, _t in crossed] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_no_boundary_crossing_while_paused_or_stopped() -> None:
    m, crossed = _machine()

    m.advance(0.5)  # STOPPED
    m.play()
    m.advance(0.2)  # 0.125 geçilir
    m.pause()
    m.advance(0.5)  # PAUSED — hareket yok

    assert [i for i, _t in crossed] == [1]


def test_seeking_backward_then_forward_re_crosses_boundaries() -> None:
    m, crossed = _machine()
    m.play()
    m.advance(0.45)  # 0.125, 0.25, 0.375 geçilir -> [1, 2, 3]
    assert [i for i, _t in crossed] == [1, 2, 3]

    m.seek(0.20)  # geri: son geçilen sınır 1 (0.125)
    m.advance(0.15)  # 0.20 -> 0.35: 0.25 tekrar geçilir

    assert [i for i, _t in crossed] == [1, 2, 3, 2]


def test_stop_resets_boundary_progress() -> None:
    m, crossed = _machine()
    m.play()
    m.advance(0.6)
    assert m.crossed_record_boundaries > 1

    m.stop()

    assert m.crossed_record_boundaries == 1  # yalnız t=0 sınırı "girilmiş"
    crossed.clear()
    m.play()
    m.advance(0.3)
    assert [i for i, _t in crossed] == [1, 2]


def test_reaching_the_end_pauses_after_the_last_boundary() -> None:
    m, crossed = _machine()
    m.play()

    m.advance(5.0)

    assert crossed[-1][0] == 8
    assert m.at_end
    assert not m.is_playing
