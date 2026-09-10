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
        # F3-057: kayıt sınırı zamanları (artan, saniye) ve o ana dek
        # geçilen son sınırın indeksi (-1 = hiçbiri).
        self._boundaries: tuple[float, ...] = ()
        self._last_boundary_index = -1
        self._boundary_listeners: list[Callable[[int, float], None]] = []

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

    # -- kayıt sınırları / ilerleme saati (F3-057) ------------

    def set_record_boundaries(self, times_s: tuple[float, ...]) -> None:
        """Kayıt sınırı zamanlarını (125 ms ızgara) belirler — `F3-057`."""
        self._boundaries = tuple(sorted(times_s))
        self._last_boundary_index = self._boundary_index_at(self._position_s)

    def add_record_listener(self, callback: Callable[[int, float], None]) -> None:
        """Bir kayıt sınırı **geçildiğinde** `(index, time_s)` ile çağrılır."""
        self._boundary_listeners.append(callback)

    @property
    def crossed_record_boundaries(self) -> int:
        """O ana dek ilerleme sırasında geçilen kayıt sınırı sayısı."""
        return self._last_boundary_index + 1

    def _boundary_index_at(self, position_s: float) -> int:
        """`position_s`'e kadar (dahil) geçilmiş son sınırın indeksi; yoksa -1."""
        index = -1
        for i, boundary in enumerate(self._boundaries):
            if boundary <= position_s + 1e-12:
                index = i
            else:
                break
        return index

    def _emit_boundary_crossings(self, new_position_s: float) -> None:
        target = self._boundary_index_at(new_position_s)
        while self._last_boundary_index < target:
            self._last_boundary_index += 1
            crossed = self._boundaries[self._last_boundary_index]
            for callback in self._boundary_listeners:
                callback(self._last_boundary_index, crossed)

    def play(self) -> None:
        if self._state is PlaybackState.PLAYING:
            return
        # sondayken tekrar oynat: başa dönmeden değil, kullanıcı stop/seek yapmalı;
        # yine de sonda "play" bir şey yapmasın diye küçük bir kolaylık:
        if self.at_end:
            self._position_s = 0.0
            self._last_boundary_index = self._boundary_index_at(0.0)
        self._transition(PlaybackState.PLAYING)

    def pause(self) -> None:
        if self._state is PlaybackState.PLAYING:
            self._transition(PlaybackState.PAUSED)

    def stop(self) -> None:
        changed = self._state is not PlaybackState.STOPPED or self._position_s != 0.0
        self._state = PlaybackState.STOPPED
        self._position_s = 0.0
        self._last_boundary_index = self._boundary_index_at(0.0)
        if changed:
            self._notify()

    def toggle_play(self) -> None:
        if self._state is PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    def advance(self, dt_s: float) -> None:
        """PLAYING iken konumu `dt_s` saniye ilerletir (negatifse yok sayılır).

        İlerleme sırasında aşılan her 125 ms kayıt sınırı, **artan sırayla
        ve bir kez** kayıt dinleyicilerine bildirilir — `F3-057`.
        """
        if self._state is not PlaybackState.PLAYING or dt_s <= 0.0:
            return
        self._position_s = min(self._duration_s, self._position_s + dt_s)
        self._emit_boundary_crossings(self._position_s)
        if self.at_end:
            self._state = PlaybackState.PAUSED
        self._notify()

    def seek(self, seconds: float) -> None:
        """Konumu `[0, duration]` aralığına kenetler; durum değişmez.

        Geri sarma sınır indeksini de geri alır; ileri arama, atlanan
        sınırlar için crossing bildirmez (bunlar "geçilmiş" sayılır).
        """
        clamped = min(max(0.0, seconds), self._duration_s)
        if clamped != self._position_s:
            self._position_s = clamped
            self._last_boundary_index = self._boundary_index_at(clamped)
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
