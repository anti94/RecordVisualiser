"""Oynatma durum makinesi — `F3-056`.

Saf Python: Qt / zamanlayıcı yoktur, bu yüzden geçişler **GUI olmadan**
doğrulanabilir. Üç durum:

* ``STOPPED`` — durdu, konum başlangıçta (`0`).
* ``PLAYING`` — ilerliyor.
* ``PAUSED`` — durakladı, konum korunuyor.

Kurallar:

* ``play()``  : STOPPED / PAUSED -> PLAYING; PLAYING iken etkisiz.
* ``pause()`` : PLAYING -> PAUSED; diğer durumlarda etkisiz.
* ``stop()``  : her durumdan -> STOPPED **ve konum başa döner**.
* ``advance(dt)`` : yalnız PLAYING iken konumu ilerletir; sona ulaşınca
  PAUSED'a geçer (oynatma başı sonda kalır).
* ``seek(t)`` : konumu `[0, duration]`'a kenetler; durum değişmez.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum


class PlaybackState(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackMachine:
    """Oynatma durumu + kayıt-zamanı konumu (saniye)."""

    def __init__(self, duration_s: float = 0.0) -> None:
        self._duration_s = max(0.0, duration_s)
        self._state = PlaybackState.STOPPED
        self._position_s = 0.0
        self._listeners: list[Callable[[], None]] = []

    # -- sorgular ----------------------------------------------------

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def position_s(self) -> float:
        return self._position_s

    @property
    def duration_s(self) -> float:
        return self._duration_s

    @property
    def is_playing(self) -> bool:
        return self._state is PlaybackState.PLAYING

    @property
    def at_end(self) -> bool:
        return self._duration_s > 0.0 and self._position_s >= self._duration_s

    # -- geçişler --------------------------------------------------

    def add_listener(self, callback: Callable[[], None]) -> None:
        """Durum ya da konum her değiştiğinde çağrılacak geri çağrı."""
        self._listeners.append(callback)

    def play(self) -> None:
        if self._state is PlaybackState.PLAYING:
            return
        # sondayken tekrar oynat: başa dönmeden değil, kullanıcı stop/seek yapmalı;
        # yine de sonda "play" bir şey yapmasın diye küçük bir kolaylık:
        if self.at_end:
            self._position_s = 0.0
        self._transition(PlaybackState.PLAYING)

    def pause(self) -> None:
        if self._state is PlaybackState.PLAYING:
            self._transition(PlaybackState.PAUSED)

    def stop(self) -> None:
        changed = self._state is not PlaybackState.STOPPED or self._position_s != 0.0
        self._state = PlaybackState.STOPPED
        self._position_s = 0.0
        if changed:
            self._notify()

    def toggle_play(self) -> None:
        if self._state is PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    def advance(self, dt_s: float) -> None:
        """PLAYING iken konumu `dt_s` saniye ilerletir (negatifse yok sayılır)."""
        if self._state is not PlaybackState.PLAYING or dt_s <= 0.0:
            return
        self._position_s = min(self._duration_s, self._position_s + dt_s)
        if self.at_end:
            self._state = PlaybackState.PAUSED
        self._notify()

    def seek(self, seconds: float) -> None:
        """Konumu `[0, duration]` aralığına kenetler; durum değişmez."""
        clamped = min(max(0.0, seconds), self._duration_s)
        if clamped != self._position_s:
            self._position_s = clamped
            self._notify()

    def set_duration(self, duration_s: float) -> None:
        self._duration_s = max(0.0, duration_s)
        if self._position_s > self._duration_s:
            self._position_s = self._duration_s
            self._notify()

    # -- ic yardimcilar ------------------------------------------

    def _transition(self, new_state: PlaybackState) -> None:
        if new_state is not self._state:
            self._state = new_state
            self._notify()

    def _notify(self) -> None:
        for callback in self._listeners:
            callback()
