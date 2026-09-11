"""Tekrarlı aç/kapat ve playback koşusu — `F6-022`.

Kabul: **Otomatik döngü bellek, handle ve kapanış hatalarını kaydeder.**

Uzun bir oturumda kullanıcı aynı pencereyi defalarca açar, kayıt yükler,
kanal çizer ve kapatır. Her turda geride küçük bir şey kalırsa (bir
widget, bir dosya tanıtıcısı, bir sinyal bağlantısı) bu, yüzüncü turda
görünür hâle gelir. Tek bir açılışı sınayan test bunu **hiç** görmez.

Koşu her turda üç şeyi ölçer ve kaydeder:

* **bellek** — ölçüm ısınmadan sonra alınan iki `tracemalloc` anlık
  görüntüsünün farkıdır ve **yalnız uygulamanın kendi kaynak
  dosyalarına** bakar (`app_bytes_per_cycle`). Bu üç gürültü kaynağını
  birden eler: ısınma maliyeti (ölçüm öncesi kalır), `tracemalloc`'un
  kendi defterleri ve standart kütüphane. Ölçüt tur başına eğimdir,
  çünkü kalıcı bir sızıntı doğrusal artar; sabit bir maliyet tur sayısı
  büyüdükçe sıfıra yaklaşır,
* **handle** — süreç tanıtıcı sayısı (Windows). Kapanmayan bir dosya ya
  da soket burada birikir ve bellekte görünmeyebilir,
* **kapanış hataları** — kapanırken atılan istisnalar sayılır ve
  **yutulmaz**; sessizce yakalanan bir kapanış hatası, kullanıcıda
  "uygulama kapanmıyor" olarak geri döner.

Değerlendirme `F6-023`'ün işidir; bu araç yalnız ölçer ve raporlar.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "valid_8records.bin"
DEFAULT_REPORT = ROOT / "docs" / "perf" / "results" / "open-close-endurance.json"

#: Ontanimli tur sayisi. Sizinti bir turda gorunmez; yuzlerce turda
#: gorunur, ama CI'da makul surede bitmeli.
DEFAULT_CYCLES = 120

#: Bellek ve handle kac turda bir orneklenir.
SAMPLE_EVERY = 10

#: Olcum baslamadan once kosan isinma turu. Ilk turlar onbellek doldurur
#: ve modul yukler; bu sabit maliyeti sizintiya saymak yanlis alarmdir.
WARMUP_CYCLES = 40


@dataclass
class CycleSample:
    """Bir örnekleme anındaki durum."""

    cycle: int
    traced_bytes: int
    handles: int


@dataclass
class EnduranceResult:
    """Aç/kapat koşusunun sonucu."""

    cycles: int = 0
    wall_seconds: float = 0.0
    samples: list[CycleSample] = field(default_factory=lambda: [])
    close_errors: list[str] = field(default_factory=lambda: [])
    peak_traced_bytes: int = 0
    app_bytes_grown: int = 0
    machine: dict[str, str] = field(default_factory=lambda: {})

    warmup_cycles: int = 0

    @property
    def memory_growth_ratio(self) -> float:
        """Son çeyrek / ilk çeyrek. `1.0` yatay demektir."""
        return _quarter_ratio([item.traced_bytes for item in self.samples])

    @property
    def app_bytes_per_cycle(self) -> float:
        """Tur başına **uygulama** belleği artışı — sızıntının asıl ölçüsü.

        Kalıcı bir sızıntı doğrusal artar ve bu değer tur sayısından
        bağımsız kalır; sabit bir maliyet ise tur sayısı büyüdükçe
        sıfıra yaklaşır. İkisini ayıran ölçü budur.
        """
        return 0.0 if self.cycles <= 0 else round(self.app_bytes_grown / self.cycles, 2)

    @property
    def handle_growth(self) -> int:
        """Son örnek ile ilk örnek arasındaki handle farkı."""
        if len(self.samples) < 2:
            return 0
        return self.samples[-1].handles - self.samples[0].handles


def _quarter_ratio(values: list[int]) -> float:
    """İlk ve son çeyreğin ortalamasını oranlar; tek örnek yanıltıcıdır."""
    if len(values) < 2:
        return 0.0
    quarter = max(1, len(values) // 4)
    first = values[:quarter]
    last = values[-quarter:]
    head = sum(first) / len(first)
    return 0.0 if head <= 0 else round((sum(last) / len(last)) / head, 4)


def process_handles() -> int:
    """Süreç tanıtıcı sayısı; okunamazsa `0`.

    Windows'ta `GetProcessHandleCount` kullanılır. Bellekte görünmeyen
    bir sızıntı (kapanmayan dosya, soket) burada görünür.
    """
    if sys.platform != "win32":  # pragma: no cover - hedef platform Windows
        return 0
    import ctypes
    from ctypes import wintypes

    # argtypes/restype BILDIRILMELI: bildirilmezse ctypes HANDLE'i int
    # sanip 64-bit degeri kirpiyor, cagri sessizce basarisiz oluyor ve
    # sayac hep 0 donuyordu. Sifir donen bir sayac "sizinti yok" gibi
    # okunur; oysa hicbir sey olculmemis olur.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetProcessHandleCount.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.GetProcessHandleCount.restype = wintypes.BOOL

    count = wintypes.DWORD(0)
    ok = kernel32.GetProcessHandleCount(kernel32.GetCurrentProcess(), ctypes.byref(count))
    return int(count.value) if ok else 0


def run_cycles(
    fixture: Path,
    work_dir: Path,
    *,
    cycles: int = DEFAULT_CYCLES,
    sample_every: int = SAMPLE_EVERY,
    warmup: int = WARMUP_CYCLES,
) -> EnduranceResult:
    """Kaydı `cycles` kez açar, sorgular ve kapatır."""
    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    work_dir.mkdir(parents=True, exist_ok=True)
    result = EnduranceResult(
        cycles=cycles,
        warmup_cycles=warmup,
        machine={"platform": platform.platform(), "python": platform.python_version()},
    )

    def one_cycle(index: int) -> None:
        repository = FileRecordingRepository()
        try:
            repository.open(fixture, cache_path=work_dir / "endurance.sidx")
            span = repository.metadata().time_range
            channel = next(iter(repository.channels()))
            # Playback'in yaptigi is: pencereyi tekrar tekrar sorgulamak.
            repository.query(channel.id, span)
            repository.events(span)
        finally:
            # Kapanis hatalari YUTULMAZ; sayilir ve raporlanir.
            try:
                repository.close()
            except Exception as exc:
                result.close_errors.append(f"tur {index}: {exc}")

    # Izleme ISINMADAN ONCE baslar: `tracemalloc` kendi defterlerini de
    # tahsis eder ve bu tahsisler olcume karisirsa uygulamaya ait
    # olmayan bir "sizinti" gorunur. Isinma sirasinda izleyici de isinir;
    # temel cizgi ondan SONRA alinir.
    gc.collect()
    tracemalloc.start()

    # ISINMA: olcum disinda. Onbellek dolar, moduller yuklenir.
    for index in range(1, warmup + 1):
        one_cycle(-index)
    gc.collect()

    started = perf_counter()
    baseline = tracemalloc.take_snapshot()

    for index in range(1, cycles + 1):
        one_cycle(index)

        if index % sample_every == 0:
            gc.collect()
            current, peak = tracemalloc.get_traced_memory()
            result.peak_traced_bytes = max(result.peak_traced_bytes, peak)
            result.samples.append(
                CycleSample(cycle=index, traced_bytes=current, handles=process_handles())
            )

    result.wall_seconds = round(perf_counter() - started, 2)
    gc.collect()
    final = tracemalloc.take_snapshot()
    result.app_bytes_grown = _app_growth(baseline, final)

    current, peak = tracemalloc.get_traced_memory()
    result.peak_traced_bytes = max(result.peak_traced_bytes, peak)
    tracemalloc.stop()
    return result


def _app_growth(before: tracemalloc.Snapshot, after: tracemalloc.Snapshot) -> int:
    """İki anlık görüntü arasında **uygulama kodunun** tuttuğu bayt farkı.

    Yalnız `src/sonar_analyzer` altındaki dosyalar sayılır; `tracemalloc`'un
    kendi defterleri ve standart kütüphane dışarıda kalır. Onlar sayılsaydı
    ölçüm, uygulamaya ait olmayan bir artışı sızıntı gibi gösterirdi.
    """
    app_root = str(ROOT / "src" / "sonar_analyzer").lower()
    total = 0
    for stat in after.compare_to(before, "filename"):
        traceback = stat.traceback
        if not traceback:
            continue
        # `resolve()` KULLANILMAZ: bazi kareler "<frozen importlib...>"
        # gibi dosya olmayan adlar tasir ve Windows'ta OSError verir.
        name = traceback[0].filename.replace("/", os.sep).lower()
        if app_root in name:
            total += stat.size_diff
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tekrarli ac/kapat kosusu (F6-022)")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--work", type=Path, default=ROOT / "build" / "open-close")
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    if not args.fixture.is_file():
        print(f"Fixture yok: {args.fixture}", file=sys.stderr)
        return 2

    result = run_cycles(args.fixture, args.work, cycles=args.cycles)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")

    print(f"tur: {result.cycles} ({result.wall_seconds} s, {result.warmup_cycles} isinma)")
    print(f"tur basina uygulama bellegi: {result.app_bytes_per_cycle} bayt")
    print(f"bellek buyume orani: {result.memory_growth_ratio}")
    print(f"handle farki: {result.handle_growth}")
    print(f"kapanis hatasi: {len(result.close_errors)}")
    for line in result.close_errors[:5]:
        print(f"  {line}")
    print(f"rapor: {args.json}")
    return 0


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
