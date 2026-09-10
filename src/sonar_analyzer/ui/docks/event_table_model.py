"""Ortak olay tablosu modeli — `F3-042` (plan Bölüm 5.5).

Saf Python: bir `Event` alır, tablo sütunlarının metnini üretir. Qt'den
bağımsızdır; hem alt panelin `Events` sekmesi hem de testler aynı
biçimlendirmeyi kullanır.

`Time` sütunu kayıt başlangıcına **göre** (`+s`) ve **mutlak**
(`HH:MM:SS.mmm`) zamanı birlikte gösterir (Bölüm 5.5).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sonar_analyzer.domain.event import Event

#: Plan Bölüm 5.5 sütunları, mockup sırasıyla.
EVENT_COLUMNS: tuple[str, ...] = (
    "Time",
    "Severity",
    "Category",
    "Source",
    "Code",
    "State",
    "Message",
    "Value",
)

EMPTY_CELL = "—"


def _absolute_hms(timestamp_ns: int) -> str:
    seconds, remainder = divmod(timestamp_ns, 1_000_000_000)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return f"{moment.strftime('%H:%M:%S')}.{remainder // 1_000_000:03d}"


def format_event_time(timestamp_ns: int, start_ns: int) -> str:
    """`+1.234 s (12:00:01.234)` — göreli ve mutlak zaman birlikte."""
    relative_s = (timestamp_ns - start_ns) / 1_000_000_000
    return f"{relative_s:+.3f} s ({_absolute_hms(timestamp_ns)})"


def _format_value(event: Event) -> str:
    if event.value is None:
        return EMPTY_CELL
    text = f"{event.value:g}" if isinstance(event.value, float) else str(event.value)
    return f"{text} {event.unit}" if event.unit else text


def event_cell_text(event: Event, column: str, *, start_ns: int) -> str:
    """`Event`'in tek bir sütundaki metni — `F3-042`.

    Kabul kriteri: her sütun **doğru domain alanını** gösterir.
    """
    if column == "Time":
        return format_event_time(event.timestamp_ns, start_ns)
    if column == "Severity":
        return event.severity.value.capitalize()
    if column == "Category":
        return event.category
    if column == "Source":
        return event.source
    if column == "Code":
        return event.code
    if column == "State":
        return event.state or EMPTY_CELL
    if column == "Message":
        return event.message
    if column == "Value":
        return _format_value(event)
    raise KeyError(f"Tanimsiz olay sutunu: {column}")


def event_row(event: Event, *, start_ns: int) -> tuple[str, ...]:
    """Bir olayın tüm sütunlarını sırayla döndürür."""
    return tuple(event_cell_text(event, column, start_ns=start_ns) for column in EVENT_COLUMNS)
