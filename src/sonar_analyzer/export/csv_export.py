"""Seçili kanal ve aralığı CSV olarak yazma — `F3-064`.

Saf Python: Qt yok, `GUI olmadan` doğrulanır. Bir `DataChunk` (kanonik
`int64` ns zaman + değer) ve kanalın değişmez tanımını alır, isteğe
bağlı olarak kayıt metadata'sıyla birlikte bir CSV dosyasına yazar.

Dosya düzeni:

* İstenirse `# anahtar=değer` biçiminde **metadata yorum satırları**
  (kanal, birim, kaynak, örnekleme hızı, kayıt kimliği, dışa aktarılan
  aralık, satır sayısı).
* Bir başlık satırı: ``timestamp_ns,timestamp_utc,value``.
* Her örnek için bir satır; zaman hem kanonik ns hem de UTC ISO-8601.

Kabul: satır sayısı, zaman, birim ve kaynak metadata doğru çıkar.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange

#: Veri bölümünün sütun adları.
DATA_COLUMNS: tuple[str, ...] = ("timestamp_ns", "timestamp_utc", "value")

#: Metadata yorum satırlarının öneki.
METADATA_PREFIX = "# "

_NS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class CsvExportResult:
    """Yazma sonucu — çağıran (ve testler) için özet."""

    path: Path
    #: Yazılan veri satırı sayısı (başlık ve metadata yorumları hariç).
    row_count: int
    column_names: tuple[str, ...]
    #: Yazılan metadata satırları (önek olmadan, `anahtar=değer`).
    metadata_lines: tuple[str, ...]


def _utc_iso(timestamp_ns: int) -> str:
    """Kanonik ns'yi UTC ISO-8601'e çevirir (mikrosaniye çözünürlük)."""
    whole_s, rem_ns = divmod(timestamp_ns, _NS_PER_SECOND)
    moment = datetime.fromtimestamp(whole_s, tz=timezone.utc).replace(microsecond=rem_ns // 1000)
    return moment.isoformat()


def build_metadata_lines(
    channel: ChannelMetadata,
    chunk: DataChunk,
    *,
    recording: RecordingMetadata | None = None,
    exported_range: TimeRange | None = None,
    raw: bool = False,
) -> list[str]:
    """Dosya başına yazılacak `anahtar=değer` metadata satırlarını üretir."""
    lines = [
        f"channel_id={channel.id}",
        f"channel_name={channel.name}",
        f"channel_path={channel.path}",
        f"unit={'raw' if raw else (channel.unit or '')}",
        f"variant={'raw' if raw else 'processed'}",
        f"source={channel.source.value}",
        f"dtype={channel.dtype}",
    ]
    if raw:
        lines.append(f"calibration=value*{channel.gain:g}+{channel.offset:g}")
    if channel.sample_rate_hz is not None:
        lines.append(f"sample_rate_hz={channel.sample_rate_hz:g}")
    if recording is not None:
        lines.append(f"recording_id={recording.recording_id}")
        lines.append(f"recording_source={recording.source_path}")
        if recording.device_id:
            lines.append(f"device_id={recording.device_id}")
    if exported_range is not None:
        lines.append(f"range_ns=[{exported_range.start_ns},{exported_range.end_ns})")
    lines.append(f"row_count={len(chunk)}")
    return lines


def write_channel_csv(
    chunk: DataChunk,
    channel: ChannelMetadata,
    path: str | Path,
    *,
    recording: RecordingMetadata | None = None,
    exported_range: TimeRange | None = None,
    include_metadata: bool = True,
    raw: bool = False,
) -> CsvExportResult:
    """`chunk`'ı `path`'e CSV olarak yazar; özet döndürür.

    `raw=True` ise değerler ters kalibrasyonla (`(v - offset) / gain`) ham
    (kalibrasyonsuz) hâline döndürülür ve metadata `variant=raw` olur;
    aksi hâlde repository'den gelen işlenmiş (ölçekli) değerler yazılır.

    * `ValueError` — `chunk` başka bir kanala ait (`channel_id` uyuşmuyor)
      ya da `raw` istendi ama `channel.gain == 0` (ters çevrilemez).
    * `OSError` — dosya açılamadı / yazılamadı.

    Var olan dosyanın üzerine yazılır; üzerine yazma onayı `F3-065`'in
    işidir (bu katman saf yazıcıdır).
    """
    if chunk.channel_id != channel.id:
        raise ValueError(f"Parça kanalı ({chunk.channel_id}) hedef kanaldan ({channel.id}) farklı")
    if raw and channel.gain == 0:
        raise ValueError(f"{channel.id}: gain 0, ham degere ters cevrilemez")

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    metadata_lines = (
        build_metadata_lines(
            channel, chunk, recording=recording, exported_range=exported_range, raw=raw
        )
        if include_metadata
        else []
    )

    timestamps = chunk.timestamps_ns.tolist()
    values = chunk.values.tolist()
    assert len(timestamps) == len(values)  # DataChunk kurucusu garanti eder
    if raw:
        values = [(value - channel.offset) / channel.gain for value in values]

    with dest.open("w", encoding="utf-8", newline="") as handle:
        for line in metadata_lines:
            handle.write(f"{METADATA_PREFIX}{line}\n")
        writer = csv.writer(handle)
        writer.writerow(DATA_COLUMNS)
        for timestamp_ns, value in zip(timestamps, values):
            writer.writerow([int(timestamp_ns), _utc_iso(int(timestamp_ns)), value])

    return CsvExportResult(
        path=dest,
        row_count=len(chunk),
        column_names=DATA_COLUMNS,
        metadata_lines=tuple(metadata_lines),
    )
