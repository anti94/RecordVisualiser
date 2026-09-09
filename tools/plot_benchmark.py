"""Pan/zoom ve cursor ölçüm koşucusu — `F1-042`.

`tools/spike_fixtures.py` (`F1-041`) ile üretilen 1 M ve 10 M noktalık
girdileri gerçek `PlotPanel` üzerinde çizip üç şeyi ölçer:

* **Sorgu süresi** — `set_channel()` çağrısının süresi (veri hazırlama + ilk
  çizim isteği). `docs/perf/budget.md` P-07 bütçesiyle karşılaştırılır.
* **Pan/zoom FPS** — art arda görünür aralık değişimlerinin ortalama karesi.
  P-04 bütçesiyle karşılaştırılır (algılanan >= 30 FPS).
* **Cursor gecikmesi** — ekran konumundan veri koordinatına eşlemenin süresi.
  P-05 bütçesiyle karşılaştırılır (<= 50 ms).

**Önemli sınırlama:** bu makinede fiziksel ekran yok; Qt `offscreen`
platformunda yazılım rasterlayıcısı kullanılır. Buradaki FPS sayıları gerçek
GPU hızlandırmalı bir ekrandaki performansı **temsil etmez** — yalnız veri
hazırlama ve PyQtGraph çağrı maliyetini yansıtır. `docs/perf/results/` içine
yazılan raporda bu açıkça belirtilir.

Kullanım:
    python tools/plot_benchmark.py
    python tools/plot_benchmark.py --out docs/perf/results/plot-benchmark.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SAMPLE_RATE_HZ = 100_000.0
SPIKE_SIZES: tuple[int, ...] = (1_000_000, 10_000_000)

#: Pan/zoom kosucusunun tekrar sayisi; kare suresi ortalanir.
PAN_ZOOM_ITERATIONS = 30
CURSOR_ITERATIONS = 200


def _prepare_qt() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "QT_QPA_FONTDIR" not in os.environ and Path("C:/Windows/Fonts").is_dir():
        os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"


def measure_query(panel: Any, sample_count: int) -> float:
    from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
    from sonar_analyzer.processing.signals import sine

    duration_s = sample_count / SAMPLE_RATE_HZ
    chunk = sine("spike", SAMPLE_RATE_HZ, duration_s, frequency_hz=440.0)
    channel = ChannelMetadata(
        id="spike",
        path="Bench/Spike",
        name="Spike",
        dtype="float32",
        source=ChannelSource.DERIVED,
        sample_rate_hz=SAMPLE_RATE_HZ,
    )

    start = time.perf_counter()
    panel.set_channel(channel, chunk)
    return time.perf_counter() - start


def measure_pan_zoom_fps(panel: Any, app: Any) -> float:
    """Görünür aralığı art arda kaydırıp yakınlaştırarak ortalama FPS ölçer."""
    view = panel.plot.getPlotItem().getViewBox()
    x_min, x_max = view.viewRange()[0]
    span = x_max - x_min or 1.0

    start = time.perf_counter()
    for i in range(PAN_ZOOM_ITERATIONS):
        offset = span * 0.01 * (i % 5)
        view.setXRange(x_min + offset, x_max + offset, padding=0)
        if i % 3 == 0:
            view.setYRange(-1.0 - 0.01 * i, 1.0 + 0.01 * i, padding=0)
        app.processEvents()
    elapsed = time.perf_counter() - start

    return PAN_ZOOM_ITERATIONS / elapsed if elapsed > 0 else float("inf")


def measure_cursor_latency_ms(panel: Any) -> float:
    """Ekran -> veri koordinat eşlemesinin ortalama süresi (ms)."""
    from PySide6.QtCore import QPointF

    view = panel.plot.getPlotItem().getViewBox()
    scene = panel.plot.scene()
    center = panel.plot.rect().center()
    scene_point = panel.plot.mapToScene(center)

    start = time.perf_counter()
    for _ in range(CURSOR_ITERATIONS):
        view.mapSceneToView(QPointF(scene_point))
    elapsed = time.perf_counter() - start
    del scene

    return (elapsed / CURSOR_ITERATIONS) * 1000.0


def run_for_size(sample_count: int) -> dict[str, Any]:
    from PySide6.QtWidgets import QApplication

    from sonar_analyzer.ui.plots.plot_panel import PlotPanel

    app = QApplication.instance() or QApplication([])
    panel = PlotPanel()
    panel.resize(1200, 600)
    panel.show()
    app.processEvents()

    query_seconds = measure_query(panel, sample_count)
    app.processEvents()
    fps = measure_pan_zoom_fps(panel, app)
    cursor_ms = measure_cursor_latency_ms(panel)

    panel.close()

    return {
        "sample_count": sample_count,
        "query_seconds": round(query_seconds, 6),
        "query_ms": round(query_seconds * 1000, 3),
        "pan_zoom_fps": round(fps, 2),
        "cursor_latency_ms": round(cursor_ms, 4),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "perf" / "results" / "plot-benchmark.json"),
        help="rapor JSON yolu",
    )
    args = parser.parse_args(argv)

    _prepare_qt()

    print(
        "UYARI: offscreen platform, yazilim rasterlayici kullanir; "
        "FPS sayilari gercek ekran performansini temsil etmez.\n",
        file=sys.stderr,
    )

    results = [run_for_size(size) for size in SPIKE_SIZES]

    for result in results:
        print(
            f"{result['sample_count']:>10,} nokta | "
            f"sorgu {result['query_ms']:>8.2f} ms | "
            f"pan/zoom {result['pan_zoom_fps']:>7.1f} FPS | "
            f"cursor {result['cursor_latency_ms']:>7.3f} ms"
        )

    report = {
        "environment": "offscreen (yazilim rasterlayici; ekran performansini TEMSIL ETMEZ)",
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "pan_zoom_iterations": PAN_ZOOM_ITERATIONS,
        "cursor_iterations": CURSOR_ITERATIONS,
        "results": results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"\n{out_path} yazildi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
