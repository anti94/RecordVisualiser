"""Bir ve on milyon noktalık spike girdilerini hazırlar — `F1-041`.

Faz 1 grafik spike'ının (plan Bölüm 11.3, `docs/perf/budget.md`) veri
tarafıdır: `PlotPanel`/PyQtGraph'ın büyük veri karşısındaki davranışını
ölçmeden önce **gerçekçi büyüklükte, deterministik** girdi üretir.

1 000 000 nokta ~= 1 Hz'de bir hidrofon kanalının ~11,6 günlük kaydı ya da
96 kHz'de ~10,4 saniyelik ham kaydı; 10 000 000 nokta bu ölçeğin üst ucunu
temsil eder (`docs/format/profile-a.md` §6, Profil B akustik veri).

Kullanım:
    python tools/spike_fixtures.py
    python tools/spike_fixtures.py --out docs/perf/results/spike-fixtures.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SPIKE_SIZES: tuple[int, ...] = (1_000_000, 10_000_000)
#: 1 000 000 nokta 100 kHz'de tam 10 s, 10 000 000 nokta tam 100 s eder.
SAMPLE_RATE_HZ = 100_000.0


def build_spike(sample_count: int) -> tuple[Any, float]:
    """Deterministik sinüs üretir; (DataChunk, üretim süresi saniye) döner."""
    from sonar_analyzer.processing.signals import sine

    duration_s = sample_count / SAMPLE_RATE_HZ
    start = time.perf_counter()
    chunk = sine(
        channel_id="spike",
        sample_rate_hz=SAMPLE_RATE_HZ,
        duration_s=duration_s,
        frequency_hz=440.0,
    )
    elapsed = time.perf_counter() - start
    return chunk, elapsed


def describe(chunk: Any, build_seconds: float) -> dict[str, Any]:
    timestamps_bytes = chunk.timestamps_ns.nbytes
    values_bytes = chunk.values.nbytes
    total_bytes = timestamps_bytes + values_bytes
    return {
        "sample_count": len(chunk),
        "timestamps_dtype": str(chunk.timestamps_ns.dtype),
        "values_dtype": str(chunk.values.dtype),
        "timestamps_bytes": timestamps_bytes,
        "values_bytes": values_bytes,
        "total_bytes": total_bytes,
        "total_mib": round(total_bytes / 1024**2, 3),
        "build_seconds": round(build_seconds, 6),
        "is_monotonic": bool(chunk.is_monotonic),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "perf" / "results" / "spike-fixtures.json"),
        help="rapor JSON yolu",
    )
    args = parser.parse_args(argv)

    report: dict[str, Any] = {"sample_rate_hz": SAMPLE_RATE_HZ, "sizes": []}

    for size in SPIKE_SIZES:
        chunk, build_seconds = build_spike(size)
        info = describe(chunk, build_seconds)
        report["sizes"].append(info)
        print(
            f"{info['sample_count']:>10,} nokta | "
            f"{info['total_mib']:>8.2f} MiB | "
            f"uretim {info['build_seconds'] * 1000:>7.2f} ms | "
            f"monoton: {info['is_monotonic']}"
        )
        assert info["sample_count"] == size, "uretilen ornek sayisi istenenle uyusmuyor"

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"\n{out_path} yazildi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
