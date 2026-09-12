"""Seçili kanal ve aralığı CSV olarak yazma — `F3-064`, `F3-066`.

Saf Python: Qt yok, `GUI olmadan` doğrulanır. Bir `DataChunk` (kanonik
`int64` ns zaman + değer) ve kanalın değişmez tanımını alır, isteğe
bağlı olarak kayıt metadata'sıyla birlikte bir CSV dosyasına yazar.

Dosya düzeni:

* İstenirse `# anahtar=değer` biçiminde **metadata yorum satırları**
  (kanal, birim, kaynak, örnekleme hızı, kayıt kimliği, dışa aktarılan
  aralık, satır sayısı).
* Bir başlık satırı: ``timestamp_ns,timestamp_utc,value`` — parça
  kalite bayrağı taşıyorsa sonuna ``quality`` sütunu eklenir.
* Her örnek için bir satır; zaman hem kanonik ns hem de UTC ISO-8601.

`F6-035`: bozuk CRC'li ya da boşluklu bir örnek, dosyada **işaretli**
görünür. Bunlar okuma katmanında zaten tespit ediliyordu ama dışa
aktarmada düşüyordu; bozuk bir değeri ortalamaya katmak, onu hiç
görmemekten daha zararlıdır. Bayrak bilgisi **olmayan** parçalarda
sütun hiç yazılmaz: "OK" yazmak, bilmediğimiz bir şeyi biliyormuş gibi
göstermek olurdu.

`F3-066`: yazma **atomiktir** — önce `<hedef>.part` geçici dosyasına
yazılır, tamamlanınca `os.replace` ile hedefe taşınır. Böylece iptal
edilen (ya da hata veren) bir dışa aktarma **yarım bir dosyayı
tamamlanmış gibi bırakmaz**: hedef ya tam ya hiç yoktur. `should_cancel`
her satırda yoklanır; iptal `ExportCancelled` fırlatır.

Kabul: satır sayısı, zaman, birim ve kaynak metadata doğru çıkar.
"""

from __future__ import annotations

import csv
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.export.text_format import Delimiter, TextFormat, resolve_format

#: Veri bölümünün sütun adları (kalite bilgisi olmayan parçalar için).
DATA_COLUMNS: tuple[str, ...] = ("timestamp_ns", "timestamp_utc", "value")

#: `F6-035`: parça kalite bayrağı taşıyorsa eklenen sütun.
QUALITY_COLUMN = "quality"

#: Kalite bilgisi olan parçalarda kullanılan sütun adları.
DATA_COLUMNS_WITH_QUALITY: tuple[str, ...] = (*DATA_COLUMNS, QUALITY_COLUMN)

#: Bayrağı olmayan örneğin `quality` sütununda yazan değer.
QUALITY_OK = "OK"

#: Bayrak adları `|` ile birleştirilir: `CRC_ERROR|GAP_BEFORE`.
QUALITY_SEPARATOR = "|"


def describe_quality(flags: int) -> str:
    """Kalite bayrağı maskesini okunabilir adlara çevirir — `F6-035`.

    Sayıyı olduğu gibi yazmak (``2``) kimseye bir şey söylemez; CSV'yi
    inceleyen kişi bayrak tablosunu ezbere bilmek zorunda kalırdı.
    Bilinmeyen bitler **atılmaz**, `BIT_n` olarak yazılır — sessizce
    kaybolan bir bayrak, hiç olmayan bir bayraktan kötüdür.
    """
    mask = int(flags)
    if mask == 0:
        return QUALITY_OK
    names: list[str] = []
    remaining = mask
    for flag in Quality:
        if flag is Quality.OK:
            continue
        if mask & int(flag):
            names.append(flag.name or f"BIT_{int(flag)}")
            remaining &= ~int(flag)
    bit = 0
    while remaining:
        if remaining & 1:
            names.append(f"BIT_{bit}")
        remaining >>= 1
        bit += 1
    return QUALITY_SEPARATOR.join(names)


def summarize_quality(chunk: DataChunk) -> str:
    """Metadata satırı: kaç örnek işaretli ve hangi bayraklardan.

    Kalite bilgisi **yoksa** "hepsi sağlam" denmez; bilgi olmadığı
    yazılır. Bilmediğini bilmek, yanlış bilmekten iyidir.
    """
    if chunk.quality is None:
        return "quality_flags=yok (kaynak kalite bilgisi vermedi)"
    total = len(chunk)
    counts: dict[str, int] = {}
    flagged = 0
    for raw in chunk.quality.tolist():
        mask = int(raw)
        if mask == 0:
            continue
        flagged += 1
        for name in describe_quality(mask).split(QUALITY_SEPARATOR):
            counts[name] = counts.get(name, 0) + 1
    if not flagged:
        return f"quality_flags=var, isaretli=0/{total}"
    detail = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    return f"quality_flags=var, isaretli={flagged}/{total} ({detail})"


#: Metadata yorum satırlarının öneki.
METADATA_PREFIX = "# "

#: Yazma sürerken kullanılan geçici dosya son eki.
PARTIAL_SUFFIX = ".part"

#: İlerleme geri çağrısı kaç satırda bir tetiklenir.
PROGRESS_INTERVAL = 2048

_NS_PER_SECOND = 1_000_000_000

#: `should_cancel() -> bool` — True dönerse yazma iptal edilir.
ShouldCancel = Callable[[], bool]
#: `on_progress(written, total)` — yazılan / toplam satır.
OnProgress = Callable[[int, int], None]


class ExportCancelled(RuntimeError):
    """Dışa aktarma iptal edildi. Geçici dosya silinir; hedef oluşmaz."""


@dataclass(frozen=True)
class CsvExportResult:
    """Yazma sonucu — çağıran (ve testler) için özet."""

    path: Path
    #: Yazılan veri satırı sayısı (başlık ve metadata yorumları hariç).
    row_count: int
    column_names: tuple[str, ...]
    #: Yazılan metadata satırları (önek olmadan, `anahtar=değer`).
    metadata_lines: tuple[str, ...]
    #: `F4-085` — kullanılan ayırıcı ve ondalık ayıracı.
    text_format: TextFormat = field(default_factory=resolve_format)


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
    text_format: TextFormat | None = None,
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
    if text_format is not None:
        # F4-085: okuyucu ayırıcıyı ve ondalık biçimini dosyadan öğrensin.
        lines.append(text_format.describe())
    lines.append(f"row_count={len(chunk)}")
    # F6-035: bozuk ya da bosluklu ornekler dosyada gorunmeliydi; ozet
    # satiri, sutunlara bakmadan once durumu soyler.
    lines.append(summarize_quality(chunk))
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
    delimiter: Delimiter = Delimiter.COMMA,
    decimal_separator: str | None = None,
    should_cancel: ShouldCancel | None = None,
    on_progress: OnProgress | None = None,
) -> CsvExportResult:
    """`chunk`'ı `path`'e CSV olarak yazar; özet döndürür.

    `raw=True` ise değerler ters kalibrasyonla (`(v - offset) / gain`) ham
    (kalibrasyonsuz) hâline döndürülür ve metadata `variant=raw` olur;
    aksi hâlde repository'den gelen işlenmiş (ölçekli) değerler yazılır.

    Yazma atomiktir (`F3-066`): `<path>.part`'a yazılıp `os.replace` ile
    taşınır. `should_cancel` her satırda yoklanır; ``True`` dönerse
    `ExportCancelled` fırlatılır, geçici dosya silinir ve **hedef
    oluşmaz**. `on_progress(written, total)` ilerlemeyi bildirir.

    * `ValueError` — `chunk` başka bir kanala ait (`channel_id` uyuşmuyor)
      ya da `raw` istendi ama `channel.gain == 0` (ters çevrilemez).
    * `ExportCancelled` — `should_cancel` iptal istedi.
    * `OSError` — dosya açılamadı / yazılamadı.
    """
    text_format = resolve_format(delimiter, decimal_separator)
    if chunk.channel_id != channel.id:
        raise ValueError(f"Parça kanalı ({chunk.channel_id}) hedef kanaldan ({channel.id}) farklı")
    if raw and channel.gain == 0:
        raise ValueError(f"{channel.id}: gain 0, ham degere ters cevrilemez")

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + PARTIAL_SUFFIX)

    metadata_lines = (
        build_metadata_lines(
            channel,
            chunk,
            recording=recording,
            exported_range=exported_range,
            raw=raw,
            text_format=text_format,
        )
        if include_metadata
        else []
    )

    timestamps = chunk.timestamps_ns.tolist()
    values = chunk.values.tolist()
    assert len(timestamps) == len(values)  # DataChunk kurucusu garanti eder
    if raw:
        values = [(value - channel.offset) / channel.gain for value in values]

    # F6-035: kalite sutunu yalniz parca bayrak TASIYORSA yazilir. Bayrak
    # yokken "OK" yazmak, bilmedigimiz bir seyi biliyormus gibi
    # gostermek olurdu.
    quality = chunk.quality.tolist() if chunk.quality is not None else None
    columns = DATA_COLUMNS_WITH_QUALITY if quality is not None else DATA_COLUMNS

    total = len(timestamps)
    try:
        with partial.open("w", encoding="utf-8", newline="") as handle:
            for line in metadata_lines:
                handle.write(f"{METADATA_PREFIX}{line}\n")
            writer = csv.writer(handle, delimiter=text_format.delimiter.value)
            writer.writerow(columns)
            for index, (timestamp_ns, value) in enumerate(zip(timestamps, values)):
                if should_cancel is not None and should_cancel():
                    raise ExportCancelled(f"{dest.name}: dışa aktarma iptal edildi")
                row = [
                    int(timestamp_ns),
                    _utc_iso(int(timestamp_ns)),
                    text_format.format_value(float(value)),
                ]
                if quality is not None:
                    row.append(describe_quality(int(quality[index])))
                writer.writerow(row)
                if on_progress is not None and index % PROGRESS_INTERVAL == 0:
                    on_progress(index + 1, total)
        os.replace(partial, dest)  # atomik: hedef ya tam ya hiç
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    if on_progress is not None:
        on_progress(total, total)

    return CsvExportResult(
        path=dest,
        row_count=total,
        column_names=columns,
        metadata_lines=tuple(metadata_lines),
        text_format=text_format,
    )
