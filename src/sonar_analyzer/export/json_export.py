"""Event ve BIT metadata'sını JSON olarak dışa aktarma — `F4-084`.

CSV kanal örneklerini taşır (`F4-084` öncesi `F3-063`); olaylar ve BIT
sonuçları ise **yapılı** kayıtlardır: iç içe alanlar, isteğe bağlı
değerler ve farklı tipler taşırlar. Bunları CSV'ye sıkıştırmak `value`
alanının sayı mı metin mi olduğunu, `state`'in boş mu yoksa `"None"`
dizgesi mi olduğunu kaybettirir. JSON bu ayrımları korur.

**Kayıpsızlık sözleşmesi.** Dışa aktarılan belge, domain nesnelerinin
her alanını taşır ve `None` olanlar **atlanmaz**, açıkça `null` yazılır —
"alan yoktu" ile "alan boştu" karışmasın. `int64` zaman damgaları tam
sayı kalır; okunabilirlik için ayrıca UTC ISO-8601 karşılığı yazılır ama
kanonik değer `timestamp_ns`'tir.

**Seçili aralık.** Belge hangi aralığın dışa aktarıldığını `range` altında
yazar. Kayıtlar o aralığa göre süzülür: yarı-açık `[start, end)`.

Saf Python — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sonar_analyzer.domain.event import BitResult, Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange

#: Belgenin şema sürümü; okuyucular buna bakar.
EXPORT_SCHEMA_VERSION = 1
NS_PER_SECOND = 1_000_000_000


class JsonExportError(ValueError):
    """Dışa aktarma yapılamıyor (geçersiz hedef vb.)."""


@dataclass(frozen=True)
class JsonExportResult:
    """Yazma sonucu — çağıran ve testler için özet."""

    path: Path
    event_count: int
    bit_count: int
    exported_range: TimeRange | None


def utc_iso(timestamp_ns: int) -> str:
    """Kanonik ns'yi UTC ISO-8601'e çevirir (mikrosaniye çözünürlük).

    Yalnız **okunabilirlik** içindir; kanonik değer `timestamp_ns` alanıdır
    ve mikrosaniye altı kısım burada kaybolur.
    """
    whole_s, rem_ns = divmod(timestamp_ns, NS_PER_SECOND)
    moment = datetime.fromtimestamp(whole_s, tz=timezone.utc).replace(microsecond=rem_ns // 1000)
    return moment.isoformat()


def event_to_dict(event: Event) -> dict[str, Any]:
    """Bir olayın **tüm** alanları; boş olanlar `null` olarak yazılır."""
    return {
        "timestamp_ns": event.timestamp_ns,
        "timestamp_utc": utc_iso(event.timestamp_ns),
        "source": event.source,
        "category": event.category,
        "severity": event.severity.value,
        "code": event.code,
        "message": event.message,
        "state": event.state,
        "value": event.value,
        "unit": event.unit,
        "source_offset": event.source_offset,
    }


def bit_result_to_dict(result: BitResult) -> dict[str, Any]:
    """Bir BIT sonucunun **tüm** alanları; boş olanlar `null`."""
    return {
        "timestamp_ns": result.timestamp_ns,
        "timestamp_utc": utc_iso(result.timestamp_ns),
        "test_id": result.test_id,
        "component": result.component,
        "state": result.state.value,
        "severity": result.severity.value,
        "code": result.code,
        "measured": result.measured,
        "unit": result.unit,
        "detail": result.detail,
    }


def _in_range(timestamp_ns: int, span: TimeRange | None) -> bool:
    return span is None or span.start_ns <= timestamp_ns < span.end_ns


def build_document(
    events: Iterable[Event],
    bit_results: Iterable[BitResult],
    *,
    recording: RecordingMetadata | None = None,
    exported_range: TimeRange | None = None,
) -> dict[str, Any]:
    """Dışa aktarılacak belgeyi kurar (dosyaya yazmadan).

    Kayıtlar `exported_range`'e göre yarı-açık süzülür ve zamana göre
    sıralanır; aralık verilmezse hepsi çıkar.
    """
    selected_events = sorted(
        (item for item in events if _in_range(item.timestamp_ns, exported_range)),
        key=lambda item: item.timestamp_ns,
    )
    selected_bits = sorted(
        (item for item in bit_results if _in_range(item.timestamp_ns, exported_range)),
        key=lambda item: item.timestamp_ns,
    )

    document: dict[str, Any] = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "kind": "event-bit-metadata",
        "range": _range_dict(exported_range),
        "recording": _recording_dict(recording),
        "counts": {"events": len(selected_events), "bit_results": len(selected_bits)},
        "events": [event_to_dict(item) for item in selected_events],
        "bit_results": [bit_result_to_dict(item) for item in selected_bits],
    }
    return document


def _range_dict(span: TimeRange | None) -> dict[str, Any] | None:
    if span is None:
        return None
    return {
        "start_ns": span.start_ns,
        "end_ns": span.end_ns,
        "start_utc": utc_iso(span.start_ns),
        "end_utc": utc_iso(span.end_ns),
        "duration_ns": span.duration_ns,
    }


def _recording_dict(recording: RecordingMetadata | None) -> dict[str, Any] | None:
    if recording is None:
        return None
    return {
        "recording_id": recording.recording_id,
        "source_path": recording.source_path,
        "device_id": recording.device_id or None,
        "firmware_version": recording.firmware_version or None,
        "format_profile": recording.format_profile,
        "format_version": recording.format_version,
        "channel_count": recording.channel_count,
        "record_count": recording.record_count,
        "record_period_ns": recording.record_period_ns,
        "file_size_bytes": recording.file_size_bytes,
        "start_ns": recording.time_range.start_ns,
        "end_ns": recording.time_range.end_ns,
        "diagnostics": list(recording.diagnostics),
    }


def write_metadata_json(
    events: Sequence[Event],
    bit_results: Sequence[BitResult],
    path: str | Path,
    *,
    recording: RecordingMetadata | None = None,
    exported_range: TimeRange | None = None,
    indent: int | None = 2,
) -> JsonExportResult:
    """Belgeyi `path`'e yazar ve özetini döndürür.

    Yazma **atomiktir**: önce geçici bir dosyaya yazılır, sonra hedefin
    üstüne taşınır. Yarım bir dosya geçerli çıktı yerine geçmez.
    """
    target = Path(path)
    if target.is_dir():
        raise JsonExportError(f"Hedef bir dizin: {target}")
    document = build_document(
        events, bit_results, recording=recording, exported_range=exported_range
    )
    text = json.dumps(document, indent=indent, ensure_ascii=False, allow_nan=False) + "\n"

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".partial")
    try:
        # `Path.write_text` Python 3.9'da `newline` almaz; satır sonu
        # platformdan bağımsız LF kalsın diye dosya açıkça açılır.
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise JsonExportError(f"JSON yazılamadı: {target} ({exc})") from exc

    counts = document["counts"]
    return JsonExportResult(
        path=target,
        event_count=int(counts["events"]),
        bit_count=int(counts["bit_results"]),
        exported_range=exported_range,
    )
