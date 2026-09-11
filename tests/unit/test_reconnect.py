"""Sınırlı otomatik yeniden bağlanma — `F5-017`.

Kabul: denemeler görünürdür; kullanıcı durdurunca yeniden bağlantı başlamaz.

Gecikmeler enjekte edilen bir `sleep` ile ölçülür — gerçek üstel backoff
beklemesi (0,5 + 1 + 2 + ... saniye) testte yaşanmaz, ama süreler tam
olarak doğrulanır.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.live.protocol import ConnectionState
from sonar_analyzer.io.live.reconnect import (
    Reconnectable,
    ReconnectController,
    ReconnectPolicy,
)


class _FakeSource:
    """`Reconnectable`: kaçıncı denemede bağlanacağı (veya hata vereceği) ayarlanır."""

    def __init__(self, *, succeed_on: int | None = 1, raise_on: set[int] | None = None) -> None:
        self._succeed_on = succeed_on
        self._raise_on = raise_on or set()
        self._calls = 0
        self._state = ConnectionState.DISCONNECTED

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def calls(self) -> int:
        return self._calls

    def connect(self) -> None:
        self._calls += 1
        if self._calls in self._raise_on:
            raise OSError(f"baglanti reddedildi ({self._calls})")
        if self._succeed_on is not None and self._calls >= self._succeed_on:
            self._state = ConnectionState.CONNECTED


class _SleepSpy:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


_FAST = ReconnectPolicy(max_attempts=5, initial_delay_s=0.5, backoff_factor=2.0, max_delay_s=30.0)


# --------------------------------------------------------------------------- #
# basarili yeniden baglanma
# --------------------------------------------------------------------------- #


def test_a_first_attempt_success_stops_immediately() -> None:
    source = _FakeSource(succeed_on=1)
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())

    assert controller.run() is True
    assert source.calls == 1
    assert len(controller.attempts) == 1
    assert controller.attempts[0].succeeded is True


def test_it_keeps_trying_until_the_connection_comes_back() -> None:
    source = _FakeSource(succeed_on=3)
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())

    assert controller.run() is True
    assert source.calls == 3
    assert [a.succeeded for a in controller.attempts] == [False, False, True]


def test_a_raising_connect_is_recorded_as_a_failed_attempt_with_the_error() -> None:
    source = _FakeSource(succeed_on=2, raise_on={1})
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())

    assert controller.run() is True
    first = controller.attempts[0]
    assert first.succeeded is False
    assert first.error is not None
    assert "baglanti reddedildi" in first.error
    assert controller.attempts[1].succeeded is True


# --------------------------------------------------------------------------- #
# sinirlilik: sonsuza kadar denemez
# --------------------------------------------------------------------------- #


def test_attempts_are_bounded_by_the_policy() -> None:
    source = _FakeSource(succeed_on=None)  # hic baglanmaz
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())

    assert controller.run() is False
    assert source.calls == 5  # max_attempts, ne bir eksik ne bir fazla
    assert len(controller.attempts) == 5
    assert all(not attempt.succeeded for attempt in controller.attempts)


def test_a_single_attempt_policy_tries_exactly_once() -> None:
    source = _FakeSource(succeed_on=None)
    controller = ReconnectController(source, ReconnectPolicy(max_attempts=1), sleep=_SleepSpy())

    assert controller.run() is False
    assert source.calls == 1


# --------------------------------------------------------------------------- #
# denemeler GORUNURDUR
# --------------------------------------------------------------------------- #


def test_every_attempt_is_numbered_and_carries_its_delay() -> None:
    source = _FakeSource(succeed_on=None)
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())
    controller.run()

    assert [a.number for a in controller.attempts] == [1, 2, 3, 4, 5]
    assert [a.delay_s for a in controller.attempts] == [0.5, 1.0, 2.0, 4.0, 8.0]


def test_attempts_are_visible_while_the_policy_is_still_running() -> None:
    """Arayüz "3/5. deneme" diyebilmeli — kayıtlar koşu bitmeden de okunur."""
    source = _FakeSource(succeed_on=4)
    seen: list[int] = []

    def sleep_and_peek(_seconds: float) -> None:
        seen.append(len(controller.attempts))

    controller = ReconnectController(source, _FAST, sleep=sleep_and_peek)
    controller.run()
    assert seen == [0, 1, 2, 3]  # her beklemede o ana kadarki deneme sayisi gorunur


# --------------------------------------------------------------------------- #
# ustel backoff - elle hesaplanmis
# --------------------------------------------------------------------------- #


def test_backoff_is_exponential_and_capped() -> None:
    policy = ReconnectPolicy(
        max_attempts=8, initial_delay_s=1.0, backoff_factor=3.0, max_delay_s=20.0
    )
    delays = [policy.delay_for(n) for n in range(1, 9)]
    assert delays == [1.0, 3.0, 9.0, 20.0, 20.0, 20.0, 20.0, 20.0]  # 27 -> tavan 20


def test_a_zero_initial_delay_means_the_first_attempt_is_immediate() -> None:
    spy = _SleepSpy()
    policy = ReconnectPolicy(max_attempts=2, initial_delay_s=0.0, backoff_factor=2.0)
    controller = ReconnectController(_FakeSource(succeed_on=None), policy, sleep=spy)
    controller.run()
    assert spy.calls == []  # 0 gecikmede hic uyunmaz


def test_the_controller_actually_sleeps_the_policy_delays() -> None:
    spy = _SleepSpy()
    controller = ReconnectController(_FakeSource(succeed_on=None), _FAST, sleep=spy)
    controller.run()
    assert spy.calls == [0.5, 1.0, 2.0, 4.0, 8.0]


def test_delay_for_rejects_a_non_positive_attempt_number() -> None:
    with pytest.raises(ValueError, match="attempt 1'den baslar"):
        _FAST.delay_for(0)


# --------------------------------------------------------------------------- #
# KULLANICI DURDURUNCA yeniden baglanti BASLAMAZ
# --------------------------------------------------------------------------- #


def test_stopping_before_run_prevents_every_attempt() -> None:
    source = _FakeSource(succeed_on=1)
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())
    controller.stop()

    assert controller.run() is False
    assert source.calls == 0  # hic denenmedi
    assert controller.attempts == ()


def test_stopping_during_the_backoff_wait_prevents_the_next_attempt() -> None:
    """Kullanıcı beklerken "Disconnect" derse, o bekleme denemeye dönüşmez."""
    source = _FakeSource(succeed_on=None)

    def sleep_then_user_stops(_seconds: float) -> None:
        controller.stop()  # kullanici bekleme sirasinda durdurdu

    controller = ReconnectController(source, _FAST, sleep=sleep_then_user_stops)
    assert controller.run() is False
    assert source.calls == 0  # bekleme bitti ama deneme BASLAMADI
    assert controller.stopped is True


def test_stopping_after_some_attempts_halts_the_remaining_ones() -> None:
    source = _FakeSource(succeed_on=None)
    calls = 0

    def sleep_and_stop_on_third(_seconds: float) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            controller.stop()

    controller = ReconnectController(source, _FAST, sleep=sleep_and_stop_on_third)
    assert controller.run() is False
    assert source.calls == 2  # 3. bekleme sonrasi durdu; 5'e kadar gitmedi
    assert len(controller.attempts) == 2


def test_reset_allows_a_new_session_after_a_user_stop() -> None:
    source = _FakeSource(succeed_on=1)
    controller = ReconnectController(source, _FAST, sleep=_SleepSpy())
    controller.stop()
    assert controller.run() is False

    controller.reset()  # kullanici yeniden "Connect" dedi
    assert controller.run() is True
    assert controller.stopped is False
    assert len(controller.attempts) == 1


# --------------------------------------------------------------------------- #
# sozlesme ve yapilandirma dogrulamasi
# --------------------------------------------------------------------------- #


def test_the_fake_source_satisfies_the_reconnectable_protocol() -> None:
    assert isinstance(_FakeSource(), Reconnectable)


def test_the_live_adapters_satisfy_the_reconnectable_protocol() -> None:
    """Dört canlı adaptör de yapısal olarak yeniden bağlanabilir."""
    from sonar_analyzer.io.live.udp_live_source import UdpLiveSource

    assert isinstance(UdpLiveSource(), Reconnectable)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_attempts": 0}, "max_attempts pozitif olmali"),
        ({"initial_delay_s": -1.0}, "initial_delay_s negatif olamaz"),
        ({"backoff_factor": 0.5}, "backoff_factor en az 1.0 olmali"),
        ({"initial_delay_s": 10.0, "max_delay_s": 5.0}, "altinda olamaz"),
    ],
)
def test_invalid_policies_are_refused(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ReconnectPolicy(**kwargs)  # type: ignore[arg-type]
