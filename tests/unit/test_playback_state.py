"""Oynatma durum makinesi — `F3-056`.

Kabul: geçişler GUI olmadan doğrulanır; stop başlangıca döner.
"""

from __future__ import annotations

from sonar_analyzer.application.playback_state import PlaybackMachine, PlaybackState


def _machine(duration: float = 10.0) -> PlaybackMachine:
    return PlaybackMachine(duration)


# -- baslangic durumu -----------------------------------


def test_starts_stopped_at_zero() -> None:
    m = _machine()
    assert m.state is PlaybackState.STOPPED
    assert m.position_s == 0.0
    assert not m.is_playing


# -- play / pause / stop geçişleri --------------------


def test_play_from_stopped_goes_to_playing() -> None:
    m = _machine()
    m.play()
    assert m.state is PlaybackState.PLAYING


def test_pause_from_playing_goes_to_paused_and_keeps_position() -> None:
    m = _machine()
    m.play()
    m.advance(3.0)

    m.pause()

    assert m.state is PlaybackState.PAUSED
    assert m.position_s == 3.0


def test_play_from_paused_resumes() -> None:
    m = _machine()
    m.play()
    m.advance(2.0)
    m.pause()

    m.play()

    assert m.state is PlaybackState.PLAYING
    assert m.position_s == 2.0


def _fresh_stopped() -> PlaybackMachine:
    return _machine()


def _mid_playing() -> PlaybackMachine:
    m = _machine()
    m.play()
    m.advance(4.0)
    return m


def _mid_paused() -> PlaybackMachine:
    m = _mid_playing()
    m.pause()
    return m


def test_stop_returns_to_the_start_from_any_state() -> None:
    for build in (_fresh_stopped, _mid_playing, _mid_paused):
        m = build()

        m.stop()

        assert m.state is PlaybackState.STOPPED
        assert m.position_s == 0.0


def test_pause_is_a_no_op_when_stopped() -> None:
    m = _machine()
    m.pause()
    assert m.state is PlaybackState.STOPPED


def test_play_is_idempotent() -> None:
    m = _machine()
    m.play()
    m.play()
    assert m.state is PlaybackState.PLAYING


def test_toggle_play_alternates() -> None:
    m = _machine()

    m.toggle_play()
    assert m.is_playing
    m.toggle_play()
    assert m.state is PlaybackState.PAUSED
    m.toggle_play()
    assert m.is_playing


# -- advance / seek --------------------------------


def test_advance_only_moves_while_playing() -> None:
    m = _machine()
    m.advance(5.0)
    assert m.position_s == 0.0

    m.play()
    m.advance(5.0)
    assert m.position_s == 5.0

    m.pause()
    m.advance(5.0)
    assert m.position_s == 5.0


def test_advance_past_the_end_pauses_at_the_end() -> None:
    m = _machine(10.0)
    m.play()

    m.advance(99.0)

    assert m.position_s == 10.0
    assert m.state is PlaybackState.PAUSED
    assert m.at_end


def test_play_from_the_end_rewinds_to_start() -> None:
    m = _machine(10.0)
    m.play()
    m.advance(99.0)  # sona -> PAUSED

    m.play()

    assert m.position_s == 0.0
    assert m.state is PlaybackState.PLAYING


def test_seek_clamps_without_changing_state() -> None:
    m = _machine(10.0)
    m.play()

    m.seek(20.0)
    assert m.position_s == 10.0
    assert m.state is PlaybackState.PLAYING

    m.seek(-5.0)
    assert m.position_s == 0.0
    assert m.state is PlaybackState.PLAYING


def test_negative_advance_is_ignored() -> None:
    m = _machine()
    m.play()
    m.advance(3.0)
    m.advance(-1.0)
    assert m.position_s == 3.0


def test_set_duration_clamps_the_position() -> None:
    m = _machine(10.0)
    m.play()
    m.advance(8.0)

    m.set_duration(5.0)

    assert m.position_s == 5.0
    assert m.duration_s == 5.0


# -- dinleyiciler --------------------------------


def test_listeners_fire_on_state_and_position_changes() -> None:
    m = _machine()
    ticks: list[int] = []
    m.add_listener(lambda: ticks.append(1))

    m.play()  # 1
    m.advance(2.0)  # 2
    m.pause()  # 3
    m.stop()  # 4

    assert len(ticks) == 4


def test_listener_does_not_fire_on_no_op() -> None:
    m = _machine()
    ticks: list[int] = []
    m.add_listener(lambda: ticks.append(1))

    m.pause()  # STOPPED iken etkisiz
    m.stop()  # zaten STOPPED@0

    assert ticks == []
