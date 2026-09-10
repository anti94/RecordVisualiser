"""MVP etkileşim bütçesi ölçüm koşucusu — `F3-077`.

Plan Bölüm 11.1 / `docs/perf/budget.md` §3'ün etkileşim hedeflerini
gerçek `MainWindow` üzerinde ölçer ve karşılaştırır:

* **Cursor geri bildirimi** (P-05, ≤ 50 ms) — `set_cursor` + değer
  etiketi metninin üretilmesi.
* **Play/pause tepkisi** (P-08, ≤ 100 ms) — oynat düğmesinin durum
  makinesini sürmesi + etiket tazelenmesi.
* **Event'e gitme** (P-06, ≤ 200 ms) — playback imlecinin bir sonraki
  olaya atlaması.
* **Kanal ağacı sonucu** (MVP hedefi, ≤ 100 ms) — arama kutusuna metin
  girildikten sonra ağacın filtrelenmesi.

**Önemli sınırlama:** bu makinede fiziksel ekran yok; Qt `offscreen`
platformunda yazılım rasterlayıcısı kullanılır. Sayılar gerçek GPU
hızlandırmalı bir ekranı temsil etmez, yalnız Python + Qt çağrı
maliyetini yansıtır.

Kullanım:
    python tools/mvp_interaction_benchmark.py
    python tools/mvp_interaction_benchmark.py --out docs/perf/results/mvp-interaction.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REPS = 25
DURATION_S = 30.0

#: (anahtar, açıklama, bütçe ms, budget.md kodu)
BUDGETS: tuple[tuple[str, str, float, str], ...] = (
    ("cursor", "Cursor geri bildirimi", 50.0, "P-05"),
    ("play_pause", "Play/pause tepkisi", 100.0, "P-08"),
    ("event_nav", "Event'e gitme", 200.0, "P-06"),
    ("tree_filter", "Kanal ağacı sonucu", 100.0, "MVP"),
)


def _prepare_qt() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "QT_QPA_FONTDIR" not in os.environ and Path("C:/Windows/Fonts").is_dir():
        os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"


def _median_ms(action: Callable[[], None], reps: int = REPS) -> float:
    samples: list[float] = []
    for _ in range(reps):
        start = time.perf_counter()
        action()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def measure(reps: int = REPS) -> dict[str, float]:
    """Dört etkileşimin medyan gecikmesini ms cinsinden döndürür."""
    _prepare_qt()
    from PySide6.QtWidgets import QApplication

    from sonar_analyzer.repository.mock_repository import MockRecordingRepository
    from sonar_analyzer.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)

    repo = MockRecordingRepository(duration_s=DURATION_S)
    win = MainWindow()
    win.set_repository(repo)
    win.open_channel("ch0")
    time_range = repo.metadata().time_range
    win.bottom_dock.set_events(repo.events(time_range), start_ns=time_range.start_ns)

    x_min, x_max = win.plot_panel.visible_x_range()
    x_span = x_max - x_min
    cursor_toggle = [x_min + x_span * 0.25, x_min + x_span * 0.75]

    def _cursor() -> None:
        target = cursor_toggle[0]
        cursor_toggle.reverse()
        win.plot_panel.set_cursor(target)
        win.plot_panel.cursor_readout_text()

    def _play_pause() -> None:
        win.playback_dock.buttons["button_play"].toggle()

    def _event_nav() -> None:
        if not win.playback_dock.goto_next_event():
            win.playback_dock.set_position(0.0)

    filters = ["Pres", "", "Accel", ""]

    def _tree_filter() -> None:
        win.left_dock.search.setText(filters[0])
        filters.append(filters.pop(0))
        app.processEvents()

    results = {
        "cursor": _median_ms(_cursor, reps),
        "play_pause": _median_ms(_play_pause, reps),
        "event_nav": _median_ms(_event_nav, reps),
        "tree_filter": _median_ms(_tree_filter, reps),
    }
    win.close()
    return results


def build_report(measured: dict[str, float]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    all_pass = True
    for key, label, budget_ms, code in BUDGETS:
        value = measured[key]
        passed = value <= budget_ms
        all_pass = all_pass and passed
        rows.append(
            {
                "key": key,
                "label": label,
                "budget_code": code,
                "budget_ms": budget_ms,
                "median_ms": round(value, 4),
                "pass": passed,
            }
        )
    return {
        "environment": "offscreen (yazilim rasterlayici; ekran performansini TEMSIL ETMEZ)",
        "reps": REPS,
        "duration_s": DURATION_S,
        "all_pass": all_pass,
        "measurements": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None, help="JSON rapor yolu")
    parser.add_argument("--reps", type=int, default=REPS)
    args = parser.parse_args()

    report = build_report(measure(args.reps))

    def _emit(line: str) -> None:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))

    _emit(f"{'Interaction':<26} {'median ms':>10} {'budget ms':>10}  result")
    _emit("-" * 60)
    for row in report["measurements"]:
        mark = "OK" if row["pass"] else "OVER"
        _emit(
            f"{row['key']:<26} {row['median_ms']:>10.3f} {row['budget_ms']:>10.1f}  "
            f"{mark} ({row['budget_code']})"
        )

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        _emit(f"\nRapor yazildi: {args.out}")

    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
