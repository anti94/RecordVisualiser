"""Çizim önbelleğinin tutulan payload ve tracemalloc kullanımını ölçer."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import numpy as np

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.display_query import DisplayQuery


def measure() -> dict[str, object]:
    def read(channel_id: str, span: TimeRange) -> DataChunk:
        times = np.arange(span.start_ns, span.end_ns, dtype=np.int64)
        return DataChunk(channel_id, times, np.sin(times * 0.1))

    query = DisplayQuery(read, max_bytes=512 * 1024)
    tracemalloc.start()
    started = perf_counter()
    try:
        for index in range(64):
            span = TimeRange(index * 4000, (index + 1) * 4000)
            query.query("a", span, 200)
            query.query("a", TimeRange(span.start_ns + 100, span.end_ns - 100), 100)
        gc.collect()
        retained, peak = tracemalloc.get_traced_memory()
        return {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "windows_visited": 64,
            "samples_per_window": 4000,
            "elapsed_seconds": perf_counter() - started,
            "cache": asdict(query.cache_stats()),
            "tracemalloc_retained_bytes": retained,
            "tracemalloc_peak_bytes": peak,
            "scope": (
                "Cache budget covers NumPy payload; "
                "Python overhead and temporary arrays are separate."
            ),
        }
    finally:
        tracemalloc.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    target = Path(args.output)
    result = measure()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
