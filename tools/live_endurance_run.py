"""Uzun süreli canlı kayıt koşusu — `F5-038`.

Kabul: **En az 2 saatlik otomatik koşu bellek, kayıp ve dosya boyutunu
kaydeder.**

Koşu *simüle edilmiş zamanda* ilerler: 2 saatlik akış, 2 saat beklenerek
değil, 2 saatlik **veri** (57 600 adet 125 ms penceresi) üretilerek
sınanır. Gerçek saat beklenseydi ölçüm hiç koşturulamaz ve "hazırlandı"
demekten öteye gidilemezdi; burada ölçülen şey — bellek büyüyor mu,
kayıp ne kadar, dosya ne kadar oluyor — süreye değil paket sayısına
bağlıdır.

Üç şey kaydedilir:

* **bellek** — koşu boyunca düzenli aralıklarla `tracemalloc` ile tutulan
  bayt. Önemli olan son değer değil, **eğilimdir**: canlı katman sabit
  kapasiteli tamponlar kullandığı için bellek yatay kalmalıdır. Bu yüzden
  ilk ve son çeyreğin ortalaması ayrı ayrı yazılır.
* **kayıp** — bozucunun (`F5-036`) ürettiği gerçek kayıp, kuyruğun
  düşürdüğü paket ve yazıcının düşürdüğü kayıt; üçü ayrı kalemdir çünkü
  üçü ayrı nedenlerdir.
* **dosya boyutu** — üretilen her dosyanın baytı ve toplam. Beklenen
  boyut kayıt sayısından hesaplanıp yanına yazılır; ikisi tutmazsa
  dosyada eksik ya da fazla var demektir.

Değerlendirme `F5-039`'un işidir; bu araç yalnız ölçer ve raporlar.
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
import tracemalloc
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from sonar_analyzer.domain.channel import ChannelMetadata  # noqa: E402
from sonar_analyzer.domain.data_chunk import DataChunk  # noqa: E402
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS  # noqa: E402
from sonar_analyzer.io.live.impairment import (  # noqa: E402
    ImpairedSource,
    ImpairmentProfile,
)
from sonar_analyzer.io.live.protocol import (  # noqa: E402
    ConnectionState,
    LivePacket,
    LiveStats,
)
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer  # noqa: E402
from sonar_analyzer.io.live.sequence_tracker import SequenceTracker  # noqa: E402
from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1  # noqa: E402
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2  # noqa: E402
from sonar_analyzer.io.readers.recording_reader import read_validated_header  # noqa: E402
from sonar_analyzer.recording.header_writer import (  # noqa: E402
    header_size_for,
    record_size_for,
)
from sonar_analyzer.recording.rotation import RotatingRecorder, RotationPolicy  # noqa: E402
from sonar_analyzer.recording.session import RecordingSession  # noqa: E402
from sonar_analyzer.repository.live_repository import LiveRepository  # noqa: E402

#: 2 saat = 7200 s / 0.125 s. Kabul kriterinin alt sınırı.
WINDOWS_PER_HOUR = 3600 * 1_000_000_000 // RECORD_PERIOD_NS
DEFAULT_HOURS = 2.0

#: Profil A sabit 8 kanal.
CHANNEL_IDS = [f"ch{index}" for index in range(8)]
CHANNELS = tuple(
    ChannelMetadata(id=channel_id, path=f"/{channel_id}", name=channel_id, dtype="float32")
    for channel_id in CHANNEL_IDS
)

START_NS = 1_788_901_200_000_000_000

#: Bellek kaç pencerede bir örneklenir. Her pencerede ölçmek koşuyu
#: yavaşlatır ve eğilimi göstermek için gereksizdir.
MEMORY_SAMPLE_EVERY = 500


@dataclass
class MemoryTrend:
    """Bellek eğilimi — son değer değil, ilk ve son çeyreğin ortalaması."""

    samples: int = 0
    first_quarter_bytes: float = 0.0
    last_quarter_bytes: float = 0.0
    peak_bytes: int = 0

    @property
    def growth_ratio(self) -> float:
        """Son çeyrek / ilk çeyrek. `1.0` yatay, `>1` büyüyor demektir."""
        if self.first_quarter_bytes <= 0:
            return 0.0
        return self.last_quarter_bytes / self.first_quarter_bytes


@dataclass
class LossBreakdown:
    """Kayıp üç ayrı kalemdir; üçü ayrı nedendir."""

    produced_windows: int = 0
    #: Ağda düşen (bozucunun ürettiği).
    network_dropped: int = 0
    #: Kuyruk dolduğu için düşen.
    queue_dropped: int = 0
    #: Disk yetişemediği için düşen kayıt.
    disk_dropped: int = 0
    #: Sıra izleyicinin gözleyebildiği eksik.
    observed_missing: int = 0
    recorded_windows: int = 0


@dataclass
class FileSizes:
    """Üretilen dosyalar ve beklenen boyut."""

    files: int = 0
    total_bytes: int = 0
    expected_bytes: int = 0
    per_file_bytes: list[int] = field(default_factory=lambda: [])

    @property
    def matches_expected(self) -> bool:
        return self.total_bytes == self.expected_bytes


@dataclass
class IntegrityCheck:
    """Yazılan dosyaların **geri okunarak** doğrulanması — `F5-039` kanıtı.

    Kayıt bütünlüğü, yazıcının sayacına bakarak iddia edilemez: dosyanın
    gerçekten okunabildiği ancak okunarak bilinir. Bu yüzden koşu bittikten
    sonra her dosya baştan sona çözülür.
    """

    files_checked: int = 0
    records_read: int = 0
    crc_mismatches: int = 0
    header_failures: int = 0
    trailing_bytes: int = 0
    non_monotonic_records: int = 0

    @property
    def is_intact(self) -> bool:
        """Tek bir kusur bile bütünlüğü bozar."""
        return (
            self.crc_mismatches == 0
            and self.header_failures == 0
            and self.trailing_bytes == 0
            and self.non_monotonic_records == 0
        )


@dataclass
class EnduranceResult:
    """Bir koşunun bütün sonucu.

    Rapora yazılan sözlük `to_json_dict()` ile üretilir; türetilen
    değerler (büyüme oranı, boyut tutuyor mu) orada açıkça yer alır çünkü
    raporu okuyanın onları yeniden hesaplaması gerekmemeli.
    """

    hours: float
    windows: int
    seed: int
    profile: dict[str, float]
    wall_seconds: float
    memory: MemoryTrend
    loss: LossBreakdown
    files: FileSizes
    integrity: IntegrityCheck
    machine: dict[str, str]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "hours": self.hours,
            "windows": self.windows,
            "seed": self.seed,
            "profile": self.profile,
            "wall_seconds": self.wall_seconds,
            "memory": {
                **asdict(self.memory),
                "growth_ratio": round(self.memory.growth_ratio, 4),
            },
            "loss": asdict(self.loss),
            "files": {
                **asdict(self.files),
                "matches_expected": self.files.matches_expected,
            },
            "integrity": {
                **asdict(self.integrity),
                "is_intact": self.integrity.is_intact,
            },
            "machine": self.machine,
        }


class _SyntheticSource:
    """Belirtilen sayıda 125 ms penceresi üreten kaynak.

    Paketler **üretildikçe** verilir (liste biriktirilmez): 2 saatlik akışı
    listede tutmak koşunun ölçtüğü belleği anlamsız kılardı.
    """

    def __init__(self, windows: int) -> None:
        self._windows = windows
        self.state = ConnectionState.CONNECTED
        self._stats = LiveStats()

    def channels(self) -> tuple[ChannelMetadata, ...]:
        return CHANNELS

    def stats(self) -> LiveStats:
        return self._stats

    def connect(self) -> None:
        self.state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self.state = ConnectionState.DISCONNECTED

    def packets(self):  # type: ignore[no-untyped-def]
        for window in range(self._windows):
            at_ns = START_NS + window * RECORD_PERIOD_NS
            stamps = np.array([at_ns], dtype=np.int64)
            yield LivePacket(
                sequence_no=window,
                received_ns=at_ns,
                chunks=[
                    DataChunk(
                        channel_id,
                        stamps,
                        np.array([float(window % 1000) + index], dtype=np.float64),
                    )
                    for index, channel_id in enumerate(CHANNEL_IDS)
                ],
            )


def run_endurance(
    output_dir: Path,
    *,
    hours: float = DEFAULT_HOURS,
    seed: int = 20260911,
    loss_ratio: float = 0.01,
    buffer_capacity: int = 240_000,
    max_file_bytes: int = 64 * 1024 * 1024,
) -> EnduranceResult:
    """Koşuyu yürütür ve ölçümleri döner. Gerçek saat **beklenmez**."""
    windows = round(hours * WINDOWS_PER_HOUR)
    profile = ImpairmentProfile(loss_ratio=loss_ratio)
    source = ImpairedSource(_SyntheticSource(windows), profile, seed=seed, sleep=lambda _s: None)

    repository = LiveRepository(LiveRingBuffer(capacity_samples=buffer_capacity), channels=CHANNELS)
    tracker = SequenceTracker()

    def session_factory(path: Path) -> RecordingSession:
        return RecordingSession(path, free_space=lambda _p: 1 << 40)

    output_dir.mkdir(parents=True, exist_ok=True)
    recorder = RotatingRecorder(
        output_dir,
        "Endurance",
        CHANNEL_IDS,
        policy=RotationPolicy(max_bytes=max_file_bytes),
        session_factory=session_factory,
    )

    gc.collect()
    tracemalloc.start()
    started = perf_counter()
    memory_samples: list[int] = []
    peak_seen = 0
    delivered = 0

    for delivered, packet in enumerate(source.packets(), start=1):
        tracker.observe(packet.sequence_no)
        repository.ingest(packet)
        recorder.accept(packet)

        if delivered % MEMORY_SAMPLE_EVERY == 0:
            current, peak = tracemalloc.get_traced_memory()
            memory_samples.append(current)
            peak_seen = max(peak_seen, peak)

    outcomes = recorder.stop()
    wall_seconds = perf_counter() - started
    current, peak = tracemalloc.get_traced_memory()
    memory_samples.append(current)
    peak_seen = max(peak_seen, peak)
    tracemalloc.stop()

    trend = _summarise_memory(memory_samples, peak_seen)
    loss = LossBreakdown(
        produced_windows=windows,
        network_dropped=source.impairment_stats.dropped,
        queue_dropped=0,  # bu kosuda kuyruk yok; akis dogrudan tuketiliyor
        disk_dropped=sum(outcome.dropped_records for outcome in outcomes),
        observed_missing=tracker.stats.missing_total,
        recorded_windows=recorder.total_record_count,
    )
    files = _summarise_files(recorder.paths, recorder.total_record_count)
    # Butunluk KOSUDAN SONRA, dosyalar kapaninca olculur (F5-029 garantisi
    # ancak kapanmis dosya icin gecerlidir).
    integrity = verify_recording(recorder.paths)

    return EnduranceResult(
        hours=hours,
        windows=windows,
        seed=seed,
        profile={
            "loss_ratio": profile.loss_ratio,
            "reorder_ratio": profile.reorder_ratio,
            "duplicate_ratio": profile.duplicate_ratio,
        },
        wall_seconds=round(wall_seconds, 3),
        memory=trend,
        loss=loss,
        files=files,
        integrity=integrity,
        machine={
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
    )


def _summarise_memory(samples: list[int], peak: int) -> MemoryTrend:
    """İlk ve son çeyreğin ortalamasını alır — tek bir örnek yanıltıcıdır."""
    if not samples:
        return MemoryTrend()
    quarter = max(1, len(samples) // 4)
    first = samples[:quarter]
    last = samples[-quarter:]
    return MemoryTrend(
        samples=len(samples),
        first_quarter_bytes=sum(first) / len(first),
        last_quarter_bytes=sum(last) / len(last),
        peak_bytes=peak,
    )


def verify_recording(paths: list[Path]) -> IntegrityCheck:
    """Yazılan her dosyayı **geri okuyarak** doğrular — `F5-039`.

    Üç şey aranır ve üçü de bağımsız kanıttır:

    * başlık üretim doğrulayıcısından geçiyor mu (`read_validated_header`),
    * her kaydın CRC'si tutuyor mu — ADR-011 §2.2'ye göre kendi alanı
      hariç, `zlib.crc32` ile **yeniden hesaplanarak**,
    * dosya tam bir kayıt sınırında bitiyor ve sıra numaraları artıyor mu.
    """
    check = IntegrityCheck()
    header_bytes = header_size_for(2)
    record_bytes = record_size_for(2)

    for path in paths:
        if not path.exists():
            continue
        check.files_checked += 1
        raw = path.read_bytes()
        try:
            read_validated_header(raw)
        except Exception:
            check.header_failures += 1
            continue

        body = len(raw) - header_bytes
        check.trailing_bytes += body % record_bytes
        previous = -1
        for index in range(body // record_bytes):
            offset = header_bytes + index * record_bytes
            record = read_data_record_v2(raw, offset)
            expected = zlib.crc32(raw[offset : offset + DATA_RECORD_V1.size]) & 0xFFFF_FFFF
            if record.record_crc32 != expected:
                check.crc_mismatches += 1
            if record.sequence_no <= previous:
                check.non_monotonic_records += 1
            previous = record.sequence_no
            check.records_read += 1

    return check


def _summarise_files(paths: list[Path], records: int) -> FileSizes:
    """Gerçek boyutları okur ve kayıt sayısından beklenen boyutla karşılaştırır."""
    sizes = [path.stat().st_size for path in paths if path.exists()]
    header = header_size_for(2)
    record = record_size_for(2)
    return FileSizes(
        files=len(sizes),
        total_bytes=sum(sizes),
        expected_bytes=len(sizes) * header + records * record,
        per_file_bytes=sizes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uzun sureli canli kayit kosusu (F5-038)")
    parser.add_argument("--hours", type=float, default=DEFAULT_HOURS)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--loss-ratio", type=float, default=0.01)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "build" / "endurance")
    parser.add_argument("--json", type=Path, default=ROOT / "docs/live/results/endurance.json")
    args = parser.parse_args(argv)

    if args.hours < DEFAULT_HOURS:
        parser.error(f"Kabul kriteri en az {DEFAULT_HOURS} saat ister: {args.hours}")

    result = run_endurance(
        args.work_dir,
        hours=args.hours,
        seed=args.seed,
        loss_ratio=args.loss_ratio,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result.to_json_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"Kosu tamamlandi: {result.windows} pencere, {result.wall_seconds} s")
    print(f"Bellek buyume orani: {result.memory.growth_ratio:.4f}")
    print(f"Dosya: {result.files.files} adet, {result.files.total_bytes} bayt")
    print(
        f"Butunluk: {result.integrity.records_read} kayit okundu, "
        f"saglam={result.integrity.is_intact}"
    )
    print(f"Rapor: {args.json}")
    return 0


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
