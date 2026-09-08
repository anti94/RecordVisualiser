"""plan.md'deki tüm işaretlenebilir maddeleri okuyup docs/notes/todo.md üretir.

plan.md tek doğruluk kaynağıdır. Bir iş tamamlandığında plan.md'de kutu [x] yapılır
ve bu betik yeniden çalıştırılır; todo.md her zaman plan.md ile aynı durumu gösterir.

İki tür madde toplanır:
  1. Bölüm 22 iş tabloları  -> "| [ ] | `F0-001` | `0.1.0` | 15 dk | çıktı | ..."
  2. Bölüm içi kontrol listeleri -> "- [ ] madde"

Kullanım:
    python tools/sync_todo.py            # todo.md üret
    python tools/sync_todo.py --check    # üretilecek içerik diskteki ile aynı mı (CI için)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan.md"
TODO = ROOT / "docs" / "notes" / "todo.md"

WORK_ROW = re.compile(
    r"^\|\s*\[(?P<done>[ x])\]\s*\|\s*`(?P<id>F\d-\d{3})`\s*\|\s*`(?P<version>[^`]+)`\s*"
    r"\|\s*(?P<duration>[^|]+?)\s*\|\s*(?P<output>[^|]+?)\s*\|"
)
BULLET = re.compile(r"^- \[(?P<done>[ x])\] (?P<text>.+?)\s*$")
HEADING = re.compile(r"^(?P<hashes>#{2,4})\s+(?P<title>.+?)\s*$")

PHASE_NAMES = {
    "F0": "Faz 0 — Keşif ve format sözleşmesi",
    "F1": "Faz 1 — Uygulama iskeleti ve domain modeli",
    "F2": "Faz 2 — Parser, indeks ve kayıtlı veri",
    "F3": "Faz 3 — MVP analiz arayüzü",
    "F4": "Faz 4 — Mockup analiz panosu ve büyük veri performansı",
    "F5": "Faz 5 — Canlı veri, bağlantı ve kayıt",
    "F6": "Faz 6 — Windows dağıtımı ve ürünleştirme",
}


@dataclass(frozen=True)
class Work:
    done: bool
    id: str
    version: str
    duration: str
    output: str


@dataclass(frozen=True)
class Item:
    done: bool
    text: str
    section: str
    line: int


def parse(plan_text: str) -> tuple[list[Work], list[Item]]:
    works: list[Work] = []
    items: list[Item] = []
    section = "(başlıksız)"

    for lineno, line in enumerate(plan_text.splitlines(), start=1):
        heading = HEADING.match(line)
        if heading:
            section = heading.group("title")
            continue

        work = WORK_ROW.match(line)
        if work:
            works.append(
                Work(
                    done=work.group("done") == "x",
                    id=work.group("id"),
                    version=work.group("version"),
                    duration=work.group("duration"),
                    output=work.group("output"),
                )
            )
            continue

        bullet = BULLET.match(line)
        if bullet:
            items.append(
                Item(
                    done=bullet.group("done") == "x",
                    text=bullet.group("text"),
                    section=section,
                    line=lineno,
                )
            )

    return works, items


def bar(done: int, total: int, width: int = 24) -> str:
    if total == 0:
        return "-" * width
    filled = round(width * done / total)
    return "#" * filled + "." * (width - filled)


def render(works: list[Work], items: list[Item]) -> str:
    total = len(works) + len(items)
    done = sum(w.done for w in works) + sum(i.done for i in items)

    out: list[str] = []
    out.append("# Todo — plan.md'den üretilmiştir")
    out.append("")
    out.append("> **Bu dosya elle düzenlenmez.** Kaynak `plan.md`'dir.")
    out.append("> Bir işi tamamlayınca `plan.md`'deki kutuyu `[x]` yap ve")
    out.append("> `python tools/sync_todo.py` çalıştır.")
    out.append("")
    out.append(f"**Toplam {total} madde · {done} tamamlandı · {total - done} kaldı**")
    out.append("")
    out.append(f"`[{bar(done, total)}]` %{100 * done / total:.1f}" if total else "")
    out.append("")

    out.append("## Özet")
    out.append("")
    out.append("| Grup | Tamam | Kalan | Toplam |")
    out.append("| --- | --- | --- | --- |")
    for prefix, name in PHASE_NAMES.items():
        phase = [w for w in works if w.id.startswith(prefix)]
        if phase:
            d = sum(w.done for w in phase)
            out.append(f"| {name} | {d} | {len(phase) - d} | {len(phase)} |")
    d_items = sum(i.done for i in items)
    out.append(f"| Bölüm içi kontrol listeleri | {d_items} | {len(items) - d_items} | {len(items)} |")
    out.append(f"| **Toplam** | **{done}** | **{total - done}** | **{total}** |")
    out.append("")

    out.append("## A. Bölüm 22 iş tabloları")
    out.append("")
    for prefix, name in PHASE_NAMES.items():
        phase = [w for w in works if w.id.startswith(prefix)]
        if not phase:
            continue
        d = sum(w.done for w in phase)
        out.append(f"### {name} ({d}/{len(phase)})")
        out.append("")
        out.append("| | İş | Sürüm | Süre | Çıktı |")
        out.append("| --- | --- | --- | --- | --- |")
        for w in phase:
            mark = "[x]" if w.done else "[ ]"
            out.append(f"| {mark} | `{w.id}` | `{w.version}` | {w.duration} | {w.output} |")
        out.append("")

    out.append("## B. Bölüm içi kontrol listeleri")
    out.append("")
    current = None
    for item in items:
        if item.section != current:
            current = item.section
            out.append("")
            out.append(f"### {current}")
            out.append("")
        mark = "x" if item.done else " "
        out.append(f"- [{mark}] {item.text}  <sub>plan.md:{item.line}</sub>")
    out.append("")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="yaz, sadece farkı bildir")
    args = parser.parse_args()

    plan_text = PLAN.read_text(encoding="utf-8")
    works, items = parse(plan_text)
    if not works:
        print("HATA: plan.md içinde iş satırı bulunamadı", file=sys.stderr)
        return 2

    content = render(works, items)

    if args.check:
        existing = TODO.read_text(encoding="utf-8") if TODO.exists() else ""
        if existing != content:
            print("todo.md guncel degil: python tools/sync_todo.py calistirin", file=sys.stderr)
            return 1
        print(f"todo.md guncel ({len(works)} is, {len(items)} kontrol maddesi)")
        return 0

    TODO.parent.mkdir(parents=True, exist_ok=True)
    with TODO.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    done = sum(w.done for w in works) + sum(i.done for i in items)
    print(f"{TODO.relative_to(ROOT)} yazildi: {len(works)} is + {len(items)} madde, {done} tamam")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
