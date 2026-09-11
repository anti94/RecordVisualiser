"""Büyük Profil B dosyasında metadata, sorgu, FPS ve bellek ölçümü — `F4-064`.

Ölçülen dört aile `plan.md` Bölüm 11.1 hedeflerine birebir karşılık gelir:

* **metadata** — kullanıcı bir şey yapabilmeden önce görünmesi gereken
  bilgi (header, kanal listesi, kayıt aralığı). Hedef: ≤ 5 s.
* **sorgu** — soğuk viewport sorgusu, birkaç zoom genişliğinde. Hedef:
  çoğu durumda ≤ 150 ms.
* **FPS** — sıcak önbellekle kayıt boyunca pan; kare/saniye. Hedef: ≥ 30.
* **bellek** — tutulan `tracemalloc` baytı ve süreç tepe working set'i.
  Hedef: dosya boyutuyla doğrusal büyümemek, bu yüzden sonuç dosya
  baytına oranıyla birlikte yazılır (`retained_per_file_byte`).

Her sonuç **makine bilgisiyle** (`machine`) yazılır; farklı bilgisayarların
sayıları karıştırılamaz.

Ölçüm gerçek gösterim yığınını kullanır: `MappedSource` (F4-053) üzerinden
`query_acoustic_channel` (F4-013) okur, `DisplayQuery` (F4-058/F4-059)
özet + LRU önbelleğiyle sunar. Qt paint süresi **dahil değildir**; bu
yüzden alan adı `pipeline_fps`'tir — çizim öncesi ardışık düzenin üst
sınırıdır, algılanan FPS bundan yüksek olamaz.

Değerlendirme `F4-065`'in işidir; bu araç yalnız ölçer ve raporlar.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from sonar_analyzer.domain.data_chunk import DataChunk  # noqa: E402
from sonar_analyzer.domain.time_range import TimeRange  # noqa: E402
from sonar_analyzer.io.decoders.profile_b import (  # noqa: E402
    ProfileBHeader,
    acoustic_channel_ids,
    decode_file_header,
)
from sonar_analyzer.io.decoders.profile_b_query import (  # noqa: E402
    AcousticQuery,
    acoustic_recording_span,
)
from sonar_analyzer.io.profile_b_format import SAMPLES_PER_BLOCK  # noqa: E402
from sonar_analyzer.io.readers.mapped_source import MappedSource  # noqa: E402
from sonar_analyzer.repository.display_query import DisplayQuery  # noqa: E402

#: Tipik bir grafik genişliğinin piksel bütçesi.
DEFAULT_MAX_POINTS = 2_000
#: Pan koşusundaki kare sayısı ve kare başına viewport genişliği.
DEFAULT_FRAMES = 60
DEFAULT_FRAME_WINDOW_S = 1.0
#: Uzun koşu bir yerde durmalı; kesilen koşu `truncated` ile işaretlenir.
DEFAULT_FRAME_BUDGET_S = 60.0
#: Soğuk sorgu genişlikleri (saniye); `None` tüm kaydı temsil eder.
DEFAULT_VIEWPORT_SECONDS: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0)
#: Ölçüm sırasında gösterim önbelleğine verilen bütçe.
DEFAULT_CACHE_BYTES = 64 * 1024 * 1024

#: `plan.md` §11.1 hedefleri — burada yalnız rapora yazılır, karar `F4-065`.
TARGETS: dict[str, float] = {
    "metadata_seconds": 5.0,
    "query_ms": 150.0,
    "pipeline_fps": 30.0,
}


# --------------------------------------------------------------------------- #
# makine bilgisi
# --------------------------------------------------------------------------- #


def total_ram_bytes() -> int | None:
    """Fiziksel bellek; ölçülemezse `None` (uydurma değer üretilmez)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.ullTotalPhys)
    try:
        return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, ValueError, OSError):
        return None


def peak_working_set_bytes() -> int | None:
    """Sürecin tepe working set'i; ölçülemezse `None`.

    `tracemalloc` yalnız Python ayırmalarını görür; eşlenmiş dosya
    sayfaları working set'te görünür. İkisi birlikte "dosya RAM'e
    kopyalanıyor mu" sorusunu yanıtlar.
    """
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        kernel32 = ctypes.windll.kernel32
        # HANDLE 64 bit; öntanımlı `c_int` restype pseudo-handle'ı kırpar.
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.argtypes = []
        get_info = kernel32.K32GetProcessMemoryInfo
        get_info.restype = wintypes.BOOL
        get_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        if not get_info(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return int(counters.PeakWorkingSetSize)
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows disi olmayan ortam
        return None
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux kibibayt, macOS bayt raporlar.
    return raw if sys.platform == "darwin" else raw * 1024


def machine_info() -> dict[str, object]:
    """Sonucun hangi bilgisayarda üretildiğini kaydeder."""
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "total_ram_bytes": total_ram_bytes(),
        "numpy": np.__version__,
    }


# --------------------------------------------------------------------------- #
# ölçüm birimleri
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MetadataResult:
    """Kullanıcı bir şey yapabilmeden önce hazır olması gereken bilgi."""

    seconds: float
    record_count: int
    channel_count: int
    channel_ids: list[int]
    record_period_ns: int
    start_ns: int
    end_ns: int
    duration_s: float
    span_source: str
    span_verified: bool


@dataclass(frozen=True)
class QueryResult:
    """Tek bir soğuk viewport sorgusu."""

    label: str
    span_ns: int
    max_points: int
    returned_points: int
    duration_ms: float


@dataclass(frozen=True)
class FrameRateResult:
    """Sıcak önbellekle pan koşusu; Qt paint hariç ardışık düzen hızı."""

    frames_requested: int
    frames_completed: int
    window_ns: int
    max_points: int
    elapsed_s: float
    pipeline_fps: float
    frame_ms_p50: float
    frame_ms_p95: float
    frame_ms_max: float
    truncated: bool


@dataclass(frozen=True)
class MemoryResult:
    """Ölçüm boyunca tutulan ve tepe bellek."""

    tracemalloc_retained_bytes: int
    tracemalloc_peak_bytes: int
    peak_working_set_bytes: int | None
    retained_per_file_byte: float
    peak_per_file_byte: float


def span_at(span: TimeRange, width_ns: int, position: float = 0.4) -> TimeRange:
    """Kaydın `position` oranındaki `width_ns` genişliğinde bir pencere.

    Uçlardan kaçınılır: baştaki/sondaki kısmi bloklar ölçümü kolaylaştırır,
    ortadaki bir pencere tipik kullanımı temsil eder.
    """
    total = span.end_ns - span.start_ns
    width = max(1, min(width_ns, total))
    start = span.start_ns + int((total - width) * position)
    return TimeRange(start, start + width)


def measure_metadata(buffer: memoryview, *, verify_span: bool) -> MetadataResult:
    """Header + kanal listesi + kayıt aralığı süresini ölçer.

    Aralık header'dan `O(1)` türetilir (uygulamanın açılışta yapacağı şey).
    `verify_span` verilirse tüm dosya taranıp aralık **doğrulanır**; bu
    tarama süreye dahil edilmez, yalnız header'ın doğruluğunu kanıtlar.
    """
    started = perf_counter()
    header: ProfileBHeader = decode_file_header(buffer)
    channel_ids = acoustic_channel_ids(buffer)
    start_ns = header.t0_utc_ns
    end_ns = start_ns + header.record_count * header.record_period_ns
    seconds = perf_counter() - started

    verified = False
    if verify_span:
        scanned = acoustic_recording_span(buffer, channel_ids[0]) if channel_ids else None
        if scanned is None:
            raise ValueError("Doğrulama istendi ama kayıtta akustik örnek yok")
        # Taranan aralık son örnekten bir örnek periyodu sonra biter;
        # header aralığı blok sınırına yuvarlar. Bir blok payı beklenir.
        block_ns = header.record_period_ns
        if scanned.start_ns != start_ns or not 0 < end_ns - scanned.end_ns < block_ns:
            raise ValueError(
                f"Header aralığı taramayla uyuşmuyor: header={start_ns}..{end_ns} "
                f"tarama={scanned.start_ns}..{scanned.end_ns}"
            )
        verified = True

    return MetadataResult(
        seconds=seconds,
        record_count=header.record_count,
        channel_count=header.channel_count,
        channel_ids=channel_ids,
        record_period_ns=header.record_period_ns,
        start_ns=start_ns,
        end_ns=end_ns,
        duration_s=(end_ns - start_ns) / 1e9,
        span_source="header",
        span_verified=verified,
    )


def measure_queries(
    query: DisplayQuery,
    channel_id: str,
    span: TimeRange,
    *,
    viewport_seconds: tuple[float, ...],
    max_points: int,
) -> list[QueryResult]:
    """Her genişlik için **soğuk** bir sorgu ölçer.

    Önbellek her ölçümden önce boşaltılır: hedef (§11.1 ≤ 150 ms) bir
    kullanıcının yeni bir pencereye ilk gidişini tanımlar, önbellekten
    dönen ikinci gidişi değil.
    """
    results: list[QueryResult] = []
    for seconds in (*viewport_seconds, None):
        width_ns = span.end_ns - span.start_ns if seconds is None else int(seconds * 1e9)
        window = span_at(span, width_ns)
        query.clear()
        started = perf_counter()
        chunk = query.query(channel_id, window, max_points)
        duration_ms = (perf_counter() - started) * 1000
        results.append(
            QueryResult(
                label="full" if seconds is None else f"{seconds:g}s",
                span_ns=window.end_ns - window.start_ns,
                max_points=max_points,
                returned_points=len(chunk),
                duration_ms=duration_ms,
            )
        )
    return results


def measure_frame_rate(
    query: DisplayQuery,
    channel_id: str,
    span: TimeRange,
    *,
    frames: int,
    window_s: float,
    max_points: int,
    budget_s: float,
) -> FrameRateResult:
    """Kayıt boyunca pan ederek kare/saniye ölçer.

    Önbellek koşunun **başında** bir kez boşaltılır: ölçüm kendi
    ısınmasını içerir, ama önceki sorgu ölçümünden kalan tam-kapsam
    penceresini miras almaz — o pencere her kareyi isabete çevirip FPS'i
    ölçüm sırasının yan etkisiyle şişirirdi. Koşu içinde önbellek
    korunur, çünkü gerçek pan'de kullanıcı sıcak önbellekle gezinir.

    Koşu `budget_s`'yi aşarsa erken durur ve `truncated` olur;
    tamamlanan kareler üzerinden hesaplanan FPS yine gerçektir.
    """
    if frames < 1:
        raise ValueError(f"frames en az 1 olmalı: {frames}")
    total = span.end_ns - span.start_ns
    window_ns = max(1, min(int(window_s * 1e9), total))
    step = max(1, (total - window_ns) // frames) if frames else 1

    query.clear()
    durations: list[float] = []
    started = perf_counter()
    for index in range(frames):
        start = span.start_ns + index * step
        frame_started = perf_counter()
        query.query(channel_id, TimeRange(start, start + window_ns), max_points)
        durations.append((perf_counter() - frame_started) * 1000)
        if perf_counter() - started > budget_s:
            break
    elapsed = perf_counter() - started

    samples = np.array(durations, dtype=np.float64)
    return FrameRateResult(
        frames_requested=frames,
        frames_completed=len(durations),
        window_ns=window_ns,
        max_points=max_points,
        elapsed_s=elapsed,
        pipeline_fps=len(durations) / elapsed if elapsed > 0 else 0.0,
        frame_ms_p50=float(np.percentile(samples, 50)),
        frame_ms_p95=float(np.percentile(samples, 95)),
        frame_ms_max=float(samples.max()),
        truncated=len(durations) < frames,
    )


# --------------------------------------------------------------------------- #
# tek dosya koşusu
# --------------------------------------------------------------------------- #


def benchmark_file(
    path: Path,
    *,
    max_points: int = DEFAULT_MAX_POINTS,
    frames: int = DEFAULT_FRAMES,
    frame_window_s: float = DEFAULT_FRAME_WINDOW_S,
    frame_budget_s: float = DEFAULT_FRAME_BUDGET_S,
    viewport_seconds: tuple[float, ...] = DEFAULT_VIEWPORT_SECONDS,
    cache_bytes: int = DEFAULT_CACHE_BYTES,
    verify_span: bool = False,
) -> dict[str, object]:
    """Bir Profil B dosyasını ölçer ve dört sonuç ailesini döndürür."""
    file_bytes = path.stat().st_size
    gc.collect()
    tracemalloc.start()
    try:
        with MappedSource(path) as source:
            buffer = source.data()
            metadata = measure_metadata(buffer, verify_span=verify_span)
            if not metadata.channel_ids:
                raise ValueError(f"Kayıtta akustik kanal yok: {path}")
            channel = metadata.channel_ids[0]
            span = TimeRange(metadata.start_ns, metadata.end_ns)
            index_started = perf_counter()
            reader = AcousticQuery(buffer)
            index_seconds = perf_counter() - index_started

            def read(_channel_id: str, window: TimeRange) -> DataChunk:
                return reader.query(channel, window)

            query = DisplayQuery(read, max_bytes=cache_bytes)
            queries = measure_queries(
                query,
                str(channel),
                span,
                viewport_seconds=viewport_seconds,
                max_points=max_points,
            )
            frame_rate = measure_frame_rate(
                query,
                str(channel),
                span,
                frames=frames,
                window_s=frame_window_s,
                max_points=max_points,
                budget_s=frame_budget_s,
            )
            cache = asdict(query.cache_stats())
            # Eşlemeyi kapatmadan ölç: tutulan bellek burada görünür.
            gc.collect()
            retained, peak = tracemalloc.get_traced_memory()
            working_set = peak_working_set_bytes()
            del query
    finally:
        tracemalloc.stop()

    memory = MemoryResult(
        tracemalloc_retained_bytes=retained,
        tracemalloc_peak_bytes=peak,
        peak_working_set_bytes=working_set,
        retained_per_file_byte=retained / file_bytes,
        peak_per_file_byte=peak / file_bytes,
    )
    return {
        "path": str(path),
        "file_bytes": file_bytes,
        "samples_per_block": SAMPLES_PER_BLOCK,
        "channel_measured": channel,
        "index_seconds": index_seconds,
        "metadata": asdict(metadata),
        "queries": [asdict(item) for item in queries],
        "frame_rate": asdict(frame_rate),
        "cache": cache,
        "memory": asdict(memory),
    }


def run(paths: list[Path], **options: object) -> dict[str, object]:
    """Bir veya daha çok dosyayı aynı makine bilgisiyle ölçer.

    Birden çok boyut verilirse §11.1'in "bellek dosya boyutuyla doğrusal
    büyümemeli" hedefi `retained_per_file_byte` oranları karşılaştırılarak
    değerlendirilebilir.
    """
    if not paths:
        raise ValueError("En az bir dosya verilmeli")
    started = perf_counter()
    files = [benchmark_file(path, **options) for path in paths]  # type: ignore[arg-type]
    return {
        "benchmark": "large-file",
        "task": "F4-064",
        "machine": machine_info(),
        "targets": TARGETS,
        "scope": (
            "pipeline_fps excludes Qt paint; it is the upper bound of the "
            "query+downsample stage. Memory covers Python allocations "
            "(tracemalloc) and process peak working set separately."
        ),
        "total_seconds": perf_counter() - started,
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, dest="inputs")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-points", type=int, default=DEFAULT_MAX_POINTS)
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    parser.add_argument("--frame-window-seconds", type=float, default=DEFAULT_FRAME_WINDOW_S)
    parser.add_argument("--frame-budget-seconds", type=float, default=DEFAULT_FRAME_BUDGET_S)
    parser.add_argument("--cache-bytes", type=int, default=DEFAULT_CACHE_BYTES)
    parser.add_argument("--verify-span", action="store_true")
    args = parser.parse_args()

    result = run(
        list(args.inputs),
        max_points=args.max_points,
        frames=args.frames,
        frame_window_s=args.frame_window_seconds,
        frame_budget_s=args.frame_budget_seconds,
        cache_bytes=args.cache_bytes,
        verify_span=args.verify_span,
    )
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
