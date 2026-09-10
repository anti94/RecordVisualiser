"""Scrubbing sorgu debouncer'ı — `F3-060`.

Kabul: hızlı sürüklemede son konum çizilir; eski sorgu görünümü ezmez.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.application.scrub_debounce import ScrubDebouncer

QUIET = 0.1


def _deb() -> ScrubDebouncer[int]:
    return ScrubDebouncer(QUIET)


# -- kurulum ------------------------------------------------------


def test_negative_quiet_period_is_rejected() -> None:
    with pytest.raises(ValueError, match="negatif"):
        ScrubDebouncer(-0.01)


# -- leading edge -----------------------------------------------


def test_first_submit_while_idle_runs_immediately() -> None:
    deb = _deb()
    assert deb.submit(10, now=0.0) == 10
    assert not deb.has_pending


def test_a_lone_submit_after_a_long_idle_also_runs_immediately() -> None:
    deb = _deb()
    assert deb.submit(1, now=0.0) == 1
    # çok sonra tekrar: yine boşta sayılır
    assert deb.submit(2, now=5.0) == 2


# -- trailing edge (coalesce) ---------------------------------


def test_burst_submits_are_coalesced_to_the_last_one() -> None:
    deb = _deb()
    assert deb.submit(1, now=0.0) == 1  # leading
    assert deb.submit(2, now=0.01) is None  # seri içinde
    assert deb.submit(3, now=0.02) is None
    assert deb.submit(4, now=0.03) is None
    assert deb.has_pending

    # sessizlik dolmadan poll bir şey vermez
    assert deb.poll(0.05) is None
    # sessizlik dolunca yalnız SON konum döner
    assert deb.poll(0.03 + QUIET) == 4
    assert not deb.has_pending
    # ikinci poll tekrar vermez
    assert deb.poll(1.0) is None


def test_only_two_runs_for_a_whole_drag() -> None:
    """Leading + tek trailing = sürükleme başına iki sorgu."""
    deb = _deb()
    runs: list[int] = []

    for i, t in enumerate([0.0, 0.005, 0.01, 0.015, 0.02, 0.025]):
        out = deb.submit(i, now=t)
        if out is not None:
            runs.append(out)
    # sürükleme bitti; zamanlayıcı tikleri
    pending = deb.poll(0.025 + QUIET)
    if pending is not None:
        runs.append(pending)

    assert runs == [0, 5]  # ilk konum + son konum


def test_flush_returns_the_pending_payload_without_waiting() -> None:
    deb = _deb()
    deb.submit(1, now=0.0)
    deb.submit(2, now=0.01)
    assert deb.flush(0.02) == 2
    assert not deb.has_pending
    assert deb.flush(0.03) is None


def test_cancel_drops_the_pending_payload() -> None:
    deb = _deb()
    deb.submit(1, now=0.0)
    deb.submit(2, now=0.01)
    deb.cancel()
    assert not deb.has_pending
    assert deb.poll(1.0) is None


def test_after_a_trailing_run_a_new_submit_is_a_fresh_leading_edge() -> None:
    deb = _deb()
    deb.submit(1, now=0.0)
    deb.submit(2, now=0.01)
    assert deb.poll(0.01 + QUIET) == 2
    # yeni sürükleme hemen ama sessizlik penceresinden sonra başlarsa leading
    assert deb.submit(3, now=0.01 + QUIET + QUIET) == 3


# -- stale sorgu koruması ------------------------------------


def test_a_query_is_current_until_a_newer_one_begins() -> None:
    deb = _deb()
    first = deb.begin_query()
    assert deb.is_current(first)

    second = deb.begin_query()
    assert deb.is_current(second)
    assert not deb.is_current(first)  # eski sorgu artık geçersiz


def test_late_stale_result_is_detectable_after_a_new_scrub() -> None:
    deb = _deb()
    # 1. scrub sorgusu başladı ama sonucu henüz gelmedi
    stale_token = deb.begin_query()
    # kullanıcı yeniden sürükledi -> 2. sorgu başladı
    fresh_token = deb.begin_query()
    # şimdi 1. sorgunun sonucu geç geldi:
    assert not deb.is_current(stale_token)  # görünümü ezmemeli
    # 2. sorgunun sonucu:
    assert deb.is_current(fresh_token)


def test_tokens_are_strictly_increasing() -> None:
    deb = _deb()
    tokens = [deb.begin_query() for _ in range(5)]
    assert tokens == sorted(tokens)
    assert len(set(tokens)) == 5
