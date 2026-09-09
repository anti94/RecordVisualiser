"""Olay indeksini oluşturma — `F2-029`.

Bir dosyanın açılışında toplanan `Event` listesini (`F2-024`
dönüştürücüleriyle üretilir) `severity`'ye göre özetler — "kaç tane
ERROR/WARNING/... var" sorusu tüm listeyi yeniden taramadan cevaplanır
(plan Bölüm 8.5: "Event offsetleri ve severity özeti").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from sonar_analyzer.domain.event import Event, Severity


def _empty_severity_counts() -> dict[Severity, int]:
    return {}


@dataclass(frozen=True)
class EventIndex:
    """Bir dosyadaki tüm olayların özeti."""

    total_count: int
    severity_counts: dict[Severity, int] = field(default_factory=_empty_severity_counts)

    def count_for(self, severity: Severity) -> int:
        """Verilen severity için olay sayısı; hiç yoksa `0`."""
        return self.severity_counts.get(severity, 0)


def build_event_index(events: Sequence[Event]) -> EventIndex:
    """Olay listesinden severity'ye göre referans sayıları üretir."""
    counts: dict[Severity, int] = {}
    for event in events:
        counts[event.severity] = counts.get(event.severity, 0) + 1
    return EventIndex(total_count=len(events), severity_counts=counts)
