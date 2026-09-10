"""Büyük dosya koşusunu §11.1 hedeflerine karşı değerlendirir — `F4-065`.

`F4-064` ölçtü; bu araç ölçümü **karara** çevirir. Her §11.1 hedefi için
tek bir durum üretir:

* `gecti` — ölçülen değer hedefi karşılıyor.
* `sapti` — hedeften sapma var; sapmanın büyüklüğü yazılır.
* `yetersiz` — hedef bu koşuyla değerlendirilemez (örneğin bellek
  doğrusallığı tek boyutlu bir koşuyla ölçülemez).

Karar kuralları burada **açıkça** tanımlanır ki rapor okunduğunda
"geçti" ne demek tartışmalı olmasın. Ölçüm dosyası değişmez; bu araç
yalnız okur.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

PASSED = "gecti"
DEVIATED = "sapti"
INSUFFICIENT = "yetersiz"

#: "Çoğu durumda ≤ 150 ms" — sorguların bu oranı bütçeye uymalı.
QUERY_SHARE_REQUIRED = 0.5
#: Bellek doğrusallığı için gereken en küçük boyut oranı.
MIN_SIZE_RATIO = 2.0
#: Dosya bu kadar büyürken bayt başına tepe bellek en az yarıya inmeli;
#: inmiyorsa kullanım dosya boyutuyla (en az) doğrusal demektir.
LINEARITY_DECAY_LIMIT = 0.5


@dataclass(frozen=True)
class Verdict:
    """Tek bir §11.1 hedefinin sonucu."""

    target: str
    goal: str
    status: str
    measured: str
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == PASSED


def _files(report: dict[str, Any]) -> list[dict[str, Any]]:
    files = report.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Koşu raporunda `files` yok veya boş")
    return cast("list[dict[str, Any]]", files)


def _label(entry: dict[str, Any]) -> str:
    return Path(str(entry["path"])).stem


def evaluate_metadata(files: list[dict[str, Any]], limit: float) -> Verdict:
    """En kötü metadata süresi hedefin altında mı."""
    worst = max(files, key=lambda entry: float(entry["metadata"]["seconds"]))
    seconds = float(worst["metadata"]["seconds"])
    return Verdict(
        target="metadata_seconds",
        goal=f"<= {limit:g} s",
        status=PASSED if seconds <= limit else DEVIATED,
        measured=f"{seconds * 1000:.3f} ms ({_label(worst)})",
        detail=(
            f"En kötü durum {_label(worst)}; {len(files)} dosyanın hepsinde "
            f"aralık header'dan O(1) türetilir."
        ),
    )


def evaluate_queries(files: list[dict[str, Any]], limit_ms: float) -> Verdict:
    """Soğuk viewport sorgularının kaçta kaçı bütçeye uyuyor."""
    durations: list[tuple[str, float]] = [
        (f"{_label(entry)}/{item['label']}", float(item["duration_ms"]))
        for entry in files
        for item in entry["queries"]
    ]
    if not durations:
        raise ValueError("Koşuda hiç sorgu ölçümü yok")
    within = [name for name, value in durations if value <= limit_ms]
    share = len(within) / len(durations)
    worst_name, worst_ms = max(durations, key=lambda pair: pair[1])
    best_name, best_ms = min(durations, key=lambda pair: pair[1])
    return Verdict(
        target="query_ms",
        goal=f"çoğu durumda <= {limit_ms:g} ms",
        status=PASSED if share > QUERY_SHARE_REQUIRED else DEVIATED,
        measured=f"{len(within)}/{len(durations)} sorgu bütçede (%{share * 100:.0f})",
        detail=(
            f"En hızlı {best_name} {best_ms:.1f} ms; en yavaş {worst_name} "
            f"{worst_ms:.1f} ms ({worst_ms / limit_ms:.0f}x bütçe)."
        ),
    )


def evaluate_frame_rate(files: list[dict[str, Any]], minimum: float) -> Verdict:
    """En düşük ardışık düzen FPS'i hedefin üstünde mi."""
    worst = min(files, key=lambda entry: float(entry["frame_rate"]["pipeline_fps"]))
    fps = float(worst["frame_rate"]["pipeline_fps"])
    frame_rate = worst["frame_rate"]
    truncated = " (koşu bütçeyi aşıp kesildi)" if frame_rate.get("truncated") else ""
    return Verdict(
        target="pipeline_fps",
        goal=f">= {minimum:g} FPS",
        status=PASSED if fps >= minimum else DEVIATED,
        measured=f"{fps:.2f} FPS ({_label(worst)}){truncated}",
        detail=(
            f"{frame_rate['frames_completed']}/{frame_rate['frames_requested']} kare, "
            f"medyan {float(frame_rate['frame_ms_p50']):.1f} ms/kare. "
            f"Qt paint hariç; algılanan FPS bundan yüksek olamaz."
        ),
    )


def evaluate_memory(files: list[dict[str, Any]]) -> Verdict:
    """Tepe bellek dosya boyutuyla doğrusal büyüyor mu.

    Tek boyutlu koşu bu soruyu **yanıtlayamaz**. En küçük ve en büyük
    dosyanın bayt başına tepe belleği karşılaştırılır: kullanım sabit
    olsaydı oran boyut kadar düşerdi, doğrusalsa aynı kalır.
    """
    goal = "dosya boyutuyla doğrusal büyümemeli"
    ordered = sorted(files, key=lambda entry: int(entry["file_bytes"]))
    small, large = ordered[0], ordered[-1]
    size_ratio = int(large["file_bytes"]) / int(small["file_bytes"])
    if len(ordered) < 2 or size_ratio < MIN_SIZE_RATIO:
        return Verdict(
            target="memory_scaling",
            goal=goal,
            status=INSUFFICIENT,
            measured=f"{len(ordered)} dosya, boyut oranı {size_ratio:.1f}x",
            detail=(
                f"Doğrusallık en az {MIN_SIZE_RATIO:g}x boyut farkı olan iki koşu ister; "
                f"benchmark'a birden çok `--input` verin."
            ),
        )
    small_ratio = float(small["memory"]["peak_per_file_byte"])
    large_ratio = float(large["memory"]["peak_per_file_byte"])
    decay = large_ratio / small_ratio if small_ratio else float("inf")
    return Verdict(
        target="memory_scaling",
        goal=goal,
        status=PASSED if decay < LINEARITY_DECAY_LIMIT else DEVIATED,
        measured=f"bayt başına tepe {small_ratio:.2f} -> {large_ratio:.2f} ({decay:.2f}x)",
        detail=(
            f"{_label(small)} ({int(small['file_bytes']) / 1e6:.0f} MB) ile "
            f"{_label(large)} ({int(large['file_bytes']) / 1e6:.0f} MB) arasında dosya "
            f"{size_ratio:.1f}x büyüdü. Kullanım sabit olsaydı oran ~{1 / size_ratio:.2f}x'e "
            f"inerdi; {decay:.2f}x kalması kullanımın boyutla ölçeklendiğini gösterir."
        ),
    )


def evaluate(report: dict[str, Any]) -> dict[str, Any]:
    """Koşu raporunu §11.1 kararlarına çevirir."""
    files = _files(report)
    targets = cast("dict[str, float]", report.get("targets") or {})
    verdicts = [
        evaluate_metadata(files, float(targets.get("metadata_seconds", 5.0))),
        evaluate_queries(files, float(targets.get("query_ms", 150.0))),
        evaluate_frame_rate(files, float(targets.get("pipeline_fps", 30.0))),
        evaluate_memory(files),
    ]
    deviated = [item.target for item in verdicts if item.status == DEVIATED]
    insufficient = [item.target for item in verdicts if item.status == INSUFFICIENT]
    return {
        "task": "F4-065",
        "source": report.get("benchmark", "large-file"),
        "machine": report.get("machine"),
        "files_measured": [_label(entry) for entry in files],
        "verdicts": [asdict(item) for item in verdicts],
        "passed": [item.target for item in verdicts if item.passed],
        "deviated": deviated,
        "insufficient": insufficient,
        "status": PASSED if not deviated and not insufficient else DEVIATED,
    }


def to_markdown(result: dict[str, Any]) -> str:
    """Kararı okunur bir tabloya çevirir."""
    symbol = {PASSED: "geçti", DEVIATED: "saptı", INSUFFICIENT: "yetersiz"}
    lines = ["| Hedef | §11.1 | Ölçülen | Durum |", "| --- | --- | --- | --- |"]
    for item in result["verdicts"]:
        lines.append(
            f"| `{item['target']}` | {item['goal']} | {item['measured']} | "
            f"**{symbol[item['status']]}** |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(report)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Windows konsolu cp1252 olabilir; karar metni Türkçe karakter taşır.
    # Yakalanmış/yönlendirilmiş bir stdout `reconfigure` taşımayabilir.
    with contextlib.suppress(AttributeError):
        cast("io.TextIOWrapper", sys.stdout).reconfigure(encoding="utf-8", errors="replace")
    print(to_markdown(result))
    print(f"\ndurum: {result['status']}; sapan: {result['deviated'] or '-'}")


if __name__ == "__main__":
    main()
