"""Klasör tabanlı Profil C repository'si — `F7-036`…`F7-044`.

Bir kayıt klasörünü (tarih klasörü, `Tx/` ve `Rx/`, 1'er saniyelik
dosyalar) **tek mantıksal kayıt** gibi sunar. Arayüz bir klasörle bir
dosya arasındaki farkı görmez: `RecordingRepository` sözleşmesinin aynı
yedi metodu çalışır.

Kanal modeli: 2 akım × 32 sensör = 64 kanal. Her sensör ayrı bir kanaldır
çünkü kullanıcı tek bir sensörü çizmek, karşılaştırmak ve dışa aktarmak
ister. 32 sensörü tek kanalda toplamak, en çok istenen işlemi imkânsız
kılardı.

Dosya sınırları **görünmez**. Üç dosyaya yayılan bir aralık tek bir
`DataChunk` döner; kullanıcının 1 saniyelik dilimleri bilmesi gerekmez.

Eksik ve bozuk dosyalar sessizce atlanmaz. Eksik bir saniye zaman
ekseninde boşluk olarak kalır; bozuk CRC'li bir frame kalite bayrağıyla
işaretlenir ama veri atılmaz.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.domain.event import BitResult, Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval
from sonar_analyzer.io.decoders.profile_c import DecodedFile, decode_file
from sonar_analyzer.io.decoders.profile_c_folder import (
    RecordingFolder,
    Stream,
    StreamFile,
    discover,
)
from sonar_analyzer.io.index.profile_c_index import (
    FileEntry,
    FolderIndex,
    folder_fingerprint,
    is_current,
    read_index,
    write_index,
)
from sonar_analyzer.io.schema.model import Schema
from sonar_analyzer.io.schema.runtime import fingerprint
from sonar_analyzer.repository.protocol import EventFilter

#: Ayni anda bellekte tutulan cozulmus dosya sayisi. Her tam boyutlu
#: dosya 2 MiB; sekiz dosya 16 MiB eder ve surekli oynatmada dosya
#: sinirini gecerken yeniden okuma yapilmaz.
DEFAULT_CACHE_FILES = 8


def channel_id(stream: Stream, sensor: int) -> str:
    """Kanal kimliği: `rx-s07`. Sıfır dolgulu, sözlük sırası sayısal."""
    return f"{stream.value.lower()}-s{sensor:02d}"


def channel_path(stream: Stream, sensor: int) -> str:
    """Data Explorer ağacındaki yol: `Tx/Sensor 07`."""
    return f"{stream.value}/Sensor {sensor:02d}"


def parse_channel_id(value: str) -> tuple[Stream, int] | None:
    """Kanal kimliğini akım ve sensöre ayırır; tanınmazsa `None`."""
    parts = value.split("-s")
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    for stream in Stream:
        if stream.value.lower() == parts[0]:
            return stream, int(parts[1])
    return None


@dataclass
class _CacheEntry:
    counter: int
    decoded: DecodedFile


class FolderRecordingRepository:
    """Bir Profil C kayıt klasörünü `RecordingRepository` olarak sunar."""

    def __init__(self, *, cache_files: int = DEFAULT_CACHE_FILES) -> None:
        self._folder: RecordingFolder | None = None
        self._schema: Schema | None = None
        self._index: FolderIndex | None = None
        self._cache: dict[tuple[str, int], _CacheEntry] = {}
        self._cache_order: list[tuple[str, int]] = []
        self._cache_files = max(1, cache_files)
        self._warnings: list[str] = []

    # -- acma ------------------------------------------------------------

    def open(self, path: Path, schema: Schema) -> None:
        """Klasörü açar ve indeksi kurar ya da önbellekten yükler."""
        folder = discover(path)
        self._folder = folder
        self._schema = schema
        self._warnings = list(folder.warnings)

        schema_fp = fingerprint(schema)
        cached = read_index(folder)
        if cached is not None and is_current(cached, folder, schema_fp):
            self._index = cached
            return

        self._index = self._build_index(folder, schema, schema_fp)
        if write_index(folder, self._index) is None:
            self._warnings.append(
                "indeks yazilamadi (klasor salt okunur olabilir); her acilista yeniden kurulacak"
            )

    def _build_index(self, folder: RecordingFolder, schema: Schema, schema_fp: str) -> FolderIndex:
        entries: dict[str, tuple[FileEntry, ...]] = {}
        for stream in Stream:
            listing = folder.listing(stream)
            if not listing.present:
                continue
            items: list[FileEntry] = []
            for item in listing.files:
                decoded = self._decode(item, schema)
                start = decoded.frames[0].timestamp_ns if decoded.frames else None
                end = decoded.frames[-1].timestamp_ns if decoded.frames else None
                items.append(
                    FileEntry(
                        counter=item.counter,
                        name=item.path.name,
                        size_bytes=item.size_bytes,
                        frame_count=decoded.frame_count,
                        start_ns=start,
                        end_ns=end,
                    )
                )
                for issue in decoded.issues:
                    self._warnings.append(f"{item.path.name}: {issue.code} — {issue.detail}")
            entries[stream.value] = tuple(items)
        return FolderIndex(
            fingerprint=folder_fingerprint(folder),
            schema_fingerprint=schema_fp,
            entries=entries,
        )

    # -- sozlesme --------------------------------------------------------

    def metadata(self) -> RecordingMetadata:
        folder, index = self._require()
        span = index.time_range_ns
        if span is None:
            raise ValueError(f"{folder.path}: hicbir frame'de zaman damgasi yok")
        schema = self._require_schema()
        # Indeksteki `end_ns` SON FRAME'IN BASLANGICIDIR, sonu degil. O
        # frame'in ornekleri bir frame periyodu daha surer. Bitisi
        # uzatmadan `metadata().time_range` ile sorgu yapmak son frame'in
        # butun orneklerini disarida birakirdi — ve eksik veri sessizce
        # eksik gorunurdu, bir hata olarak degil.
        end_ns = span[1] + self._frame_period_ns()
        return RecordingMetadata(
            recording_id=folder.path.name,
            source_path=str(folder.path),
            time_range=TimeRange(start_ns=span[0], end_ns=end_ns),
            format_profile="C",
            format_version=schema.version,
            channel_count=len(self.channels()),
            record_count=index.frame_count,
            record_period_ns=self._frame_period_ns(),
            file_size_bytes=folder.total_bytes,
            diagnostics=list(self._warnings),
        )

    def channels(self) -> Sequence[ChannelMetadata]:
        """2 akım × 32 sensör. Bulunmayan akım için kanal üretilmez."""
        folder = self._require()[0]
        schema = self._require_schema()
        rate = float(schema.payload.frame_samples) / (self._frame_period_ns() / 1_000_000_000.0)
        result: list[ChannelMetadata] = []
        for stream in Stream:
            if not folder.listing(stream).present:
                continue
            for sensor in range(schema.payload.sensor_count):
                result.append(
                    ChannelMetadata(
                        id=channel_id(stream, sensor),
                        path=channel_path(stream, sensor),
                        name=f"{stream.value} Sensor {sensor:02d}",
                        dtype="complex64",
                        source=ChannelSource.ACOUSTIC,
                        # Birim BILINCLI OLARAK bos: ham sayilar Volt ya da
                        # Pascal degildir ve olcekleme sabitleri bilinmiyor
                        # (D-34, D-35). Bir birim yazmak uydurma olurdu.
                        unit=None,
                        sample_rate_hz=rate,
                    )
                )
        return tuple(result)

    def query(
        self,
        channel_id_value: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        """Bir sensörün verilen aralıktaki örnekleri — dosya sınırları görünmez."""
        parsed = parse_channel_id(channel_id_value)
        if parsed is None:
            return DataChunk.empty(channel_id_value, dtype="complex64")
        stream, sensor = parsed

        folder, index = self._require()
        schema = self._require_schema()
        if sensor >= schema.payload.sensor_count or not folder.listing(stream).present:
            return DataChunk.empty(channel_id_value, dtype="complex64")

        times: list[NDArray[np.int64]] = []
        values: list[NDArray[np.complex64]] = []
        flags: list[NDArray[np.uint8]] = []
        step = self._sample_step_ns()

        for item in folder.listing(stream).files:
            entry = self._entry(index, stream, item.counter)
            if entry is not None and not self._overlaps(entry, time_range):
                continue
            decoded = self._decode(item, schema)
            for frame in decoded.frames:
                base = frame.timestamp_ns
                count = frame.samples.shape[1]
                stamps = base + np.arange(count, dtype=np.int64) * step
                mask = (stamps >= time_range.start_ns) & (stamps < time_range.end_ns)
                if not mask.any():
                    continue
                times.append(stamps[mask])
                values.append(frame.samples[sensor][mask])
                quality = Quality.OK if frame.crc_ok else Quality.CRC_ERROR
                flags.append(np.full(int(mask.sum()), int(quality), dtype=np.uint8))

        if not times:
            return DataChunk.empty(channel_id_value, dtype="complex64")

        stamps_all = np.concatenate(times)
        values_all = np.concatenate(values).astype(np.complex64, copy=False)
        flags_all = np.concatenate(flags)
        if max_points is not None and stamps_all.size > max_points:
            stamps_all, values_all, flags_all = _decimate(
                stamps_all, values_all, flags_all, max_points
            )
        return DataChunk(
            channel_id=channel_id_value,
            timestamps_ns=stamps_all,
            values=values_all,
            quality=flags_all,
        )

    def events(self, time_range: TimeRange, filters: EventFilter | None = None) -> Sequence[Event]:
        """Profil C'de olay kaydı yok.

        Frame başlığındaki CIT, transmisyon ve platform blokları **opak**
        (`D-30`, `D-31`); içlerinden olay çıkarmak, alan yerleşimini
        uydurmak olurdu. Cevap gelince burası doldurulacak.
        """
        return ()

    def bit_results(self, time_range: TimeRange) -> Sequence[BitResult]:
        """Profil C'de BIT bloğu tanımlı değil."""
        return ()

    def transmissions(self, time_range: TimeRange) -> Sequence[TransmissionInterval]:
        """Transmisyon alanları opak (`D-31`); aralık çıkarılamaz.

        `tx_active` biti hangi frame'in yayın süresine denk geldiğini
        söyler ama PRI ve yayın süresi bilinmediğinden aralık sınırları
        çıkarılamaz. Yaklaşık bir aralık üretmek, ölçülmemiş bir sayıyı
        ölçülmüş göstermek olurdu.
        """
        return ()

    def close(self) -> None:
        self._cache.clear()
        self._cache_order.clear()
        self._folder = None
        self._schema = None
        self._index = None

    # -- yardimcilar -----------------------------------------------------

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(self._warnings)

    @property
    def cached_files(self) -> int:
        """Şu an bellekte tutulan çözülmüş dosya sayısı.

        Bellek bütçesi bir **davranıştır** ve dışarıdan ölçülebilmelidir.
        Testin iç alana uzanması gerekseydi, bütçe sözleşmenin parçası
        olmaz, bir uygulama ayrıntısı olurdu.
        """
        return len(self._cache)

    @property
    def cache_limit(self) -> int:
        """Bütçenin üst sınırı."""
        return self._cache_files

    def _require(self) -> tuple[RecordingFolder, FolderIndex]:
        if self._folder is None or self._index is None:
            raise ValueError("once open() cagrilmali")
        return self._folder, self._index

    def _require_schema(self) -> Schema:
        if self._schema is None:
            raise ValueError("once open() cagrilmali")
        return self._schema

    def _frame_period_ns(self) -> int:
        """Frame periyodu — indeksteki gerçek zaman damgalarından ölçülür.

        Nominal bir değer yazmak, 820/8192 kaynaklı kaymayı gizlerdi
        (`D-27`). Ölçülemiyorsa şemadan türetilen nominal değere düşülür.
        """
        _folder, index = self._require()
        schema = self._require_schema()
        for items in index.entries.values():
            for entry in items:
                if (
                    entry.start_ns is not None
                    and entry.end_ns is not None
                    and entry.frame_count > 1
                ):
                    return (entry.end_ns - entry.start_ns) // (entry.frame_count - 1)
        return round(schema.payload.frame_samples / 8192 * 1e9)

    def _sample_step_ns(self) -> int:
        schema = self._require_schema()
        return max(1, self._frame_period_ns() // schema.payload.frame_samples)

    @staticmethod
    def _entry(index: FolderIndex, stream: Stream, counter: int) -> FileEntry | None:
        for entry in index.stream(stream):
            if entry.counter == counter:
                return entry
        return None

    @staticmethod
    def _overlaps(entry: FileEntry, time_range: TimeRange) -> bool:
        if entry.start_ns is None or entry.end_ns is None:
            return True
        return entry.start_ns < time_range.end_ns and entry.end_ns >= time_range.start_ns

    def _decode(self, item: StreamFile, schema: Schema) -> DecodedFile:
        """Bir dosyayı çözer; son `cache_files` dosya bellekte tutulur.

        Önbellek olmadan sürekli oynatma, her saniye sınırında aynı
        dosyayı yeniden okurdu. Sınırsız önbellek ise 10 dakikalık bir
        kayıtta 1,17 GiB'i bellekte tutardı.
        """
        key = (item.stream.value, item.counter)
        hit = self._cache.get(key)
        if hit is not None:
            return hit.decoded

        decoded = decode_file(schema, item.path.read_bytes())
        self._cache[key] = _CacheEntry(counter=item.counter, decoded=decoded)
        self._cache_order.append(key)
        while len(self._cache_order) > self._cache_files:
            self._cache.pop(self._cache_order.pop(0), None)
        return decoded


def _decimate(
    stamps: NDArray[np.int64],
    values: NDArray[np.complex64],
    flags: NDArray[np.uint8],
    max_points: int,
) -> tuple[NDArray[np.int64], NDArray[np.complex64], NDArray[np.uint8]]:
    """Eşit aralıklı seyreltme — `F7-040`.

    Seyreltme **dosya sınırlarından bağımsız** yapılır: bütün aralık
    birleştirildikten sonra tek bir indeks dizisiyle örneklenir. Dosya
    başına seyreltme yapılsaydı, sınırlarda örnek yoğunluğu değişir ve
    grafikte görünür bir sıçrama oluşurdu.
    """
    if max_points < 1:
        max_points = 1
    picks = np.linspace(0, stamps.size - 1, num=max_points).astype(np.int64)
    picks = np.unique(picks)
    return stamps[picks], values[picks], flags[picks]
