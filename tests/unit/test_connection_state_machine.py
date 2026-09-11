"""Bağlantı durum makinesi geçişleri — `F5-002`.

Kabul: `disconnected`, `connecting`, `connected`, `degraded` (`RECONNECTING`)
ve `error` (`FAILED`) geçişleri doğrulanır.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.live.connection_state_machine import ConnectionStateMachine
from sonar_analyzer.io.live.protocol import ConnectionState

D = ConnectionState.DISCONNECTED
CG = ConnectionState.CONNECTING
CD = ConnectionState.CONNECTED
R = ConnectionState.RECONNECTING  # plan.md Bölüm 13: "degraded"
F = ConnectionState.FAILED  # plan.md Bölüm 13: "error"

#: Her hedef duruma **yalnız genel API üzerinden** ulaşan geçiş dizisi.
_PATH_TO: dict[ConnectionState, tuple[str, ...]] = {
    D: (),
    CG: ("request_connect",),
    CD: ("request_connect", "established"),
    R: ("request_connect", "established", "connection_lost"),
    F: ("request_connect", "established", "connection_lost", "retries_exhausted"),
}


def _reach(state: ConnectionState) -> ConnectionStateMachine:
    machine = ConnectionStateMachine()
    for method in _PATH_TO[state]:
        getattr(machine, method)()
    assert machine.state is state
    return machine


def test_starts_disconnected() -> None:
    machine = ConnectionStateMachine()
    assert machine.state is D
    assert machine.history == (D,)


# --------------------------------------------------------------------------- #
# gecerli gecisler
# --------------------------------------------------------------------------- #


def test_disconnected_to_connecting() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    assert machine.state is CG


def test_connecting_to_connected() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.established()
    assert machine.state is CD


def test_connected_to_degraded_on_connection_lost() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.established()
    machine.connection_lost()
    assert machine.state is R


def test_degraded_recovers_to_connected() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.established()
    machine.connection_lost()
    machine.established()
    assert machine.state is CD


def test_degraded_to_error_when_retries_exhausted() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.established()
    machine.connection_lost()
    machine.retries_exhausted()
    assert machine.state is F


def test_connecting_to_error_when_initial_attempt_fails() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.retries_exhausted()
    assert machine.state is F


def test_error_allows_a_manual_retry() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.retries_exhausted()
    machine.request_connect()
    assert machine.state is CG


@pytest.mark.parametrize("source", [CG, CD, R, F])
def test_disconnect_reaches_disconnected_from_any_active_state(source: ConnectionState) -> None:
    machine = _reach(source)
    machine.disconnect()
    assert machine.state is D


# --------------------------------------------------------------------------- #
# idempotentlik (F1-017 LiveSource.connect/disconnect sozlesmesiyle tutarli)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("source", [CG, CD, R])
def test_request_connect_is_a_no_op_when_already_connecting_or_better(
    source: ConnectionState,
) -> None:
    machine = _reach(source)
    before = machine.history
    machine.request_connect()
    assert machine.state is source
    assert machine.history == before  # gecis kaydedilmedi


def test_disconnect_is_a_no_op_when_already_disconnected() -> None:
    machine = ConnectionStateMachine()
    machine.disconnect()
    assert machine.state is D
    assert machine.history == (D,)


# --------------------------------------------------------------------------- #
# izinsiz gecisler durumu degistirmez
# --------------------------------------------------------------------------- #


def test_established_from_disconnected_is_rejected() -> None:
    machine = ConnectionStateMachine()
    with pytest.raises(ValueError, match="İzinsiz geçiş"):
        machine.established()
    assert machine.state is D  # durum degismedi


def test_connection_lost_requires_being_connected() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    with pytest.raises(ValueError, match="İzinsiz geçiş"):
        machine.connection_lost()
    assert machine.state is CG


def test_retries_exhausted_requires_connecting_or_degraded() -> None:
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.established()
    with pytest.raises(ValueError, match="İzinsiz geçiş"):
        machine.retries_exhausted()
    assert machine.state is CD


def test_a_rejected_transition_is_not_recorded_in_history() -> None:
    machine = ConnectionStateMachine()
    with pytest.raises(ValueError):
        machine.established()
    assert machine.history == (D,)


# --------------------------------------------------------------------------- #
# tarihce ve butun senaryo
# --------------------------------------------------------------------------- #


def test_full_lifecycle_is_recorded_in_order() -> None:
    """Bağlan → kopar (degraded) → toparlan → tekrar kopar → tükenir (error) → dene → kapat."""
    machine = ConnectionStateMachine()
    machine.request_connect()  # -> CONNECTING
    machine.established()  # -> CONNECTED
    machine.connection_lost()  # -> RECONNECTING (degraded)
    machine.established()  # -> CONNECTED
    machine.connection_lost()  # -> RECONNECTING (degraded)
    machine.retries_exhausted()  # -> FAILED (error)
    machine.request_connect()  # -> CONNECTING
    machine.established()  # -> CONNECTED
    machine.disconnect()  # -> DISCONNECTED

    assert machine.history == (D, CG, CD, R, CD, R, F, CG, CD, D)


@pytest.mark.parametrize("state", [D, CG, CD, R, F])
def test_every_planned_state_is_reachable(state: ConnectionState) -> None:
    """plan.md Bölüm 13'ün beş durumu (disconnected/connecting/connected/degraded/error)."""
    machine = ConnectionStateMachine()
    machine.request_connect()
    machine.established()
    machine.connection_lost()
    machine.retries_exhausted()
    machine.request_connect()
    machine.established()
    machine.disconnect()
    assert state in machine.history
