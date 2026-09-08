"""İş sürelerini git geçmişinden üretir ve worklog'a yazar.

Gerçek süre = bu işin commit'i ile bir önceki commit arasındaki fark. Bir işin
commit'i o işin bitişidir; dolayısıyla fark, önceki iş bittikten sonra bu işe
harcanan süredir. Ölçüm otomatiktir, tahmin değildir.

Kullanım:
    python tools/worklog_stats.py             # tabloyu ekrana yaz
    python tools/worklog_stats.py --update    # worklog.md icindeki bolumu guncelle
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan.md"
WORKLOG = ROOT / "docs" / "notes" / "worklog.md"

BEGIN_MARKER = "<!-- SURELER:BASLANGIC -->"
END_MARKER = "<!-- SURELER:BITIS -->"

WORK_ID = re.compile(r"\b(F\d-\d{3})\b")
PLAN_ROW = re.compile(
    r"^\|\s*\[[ x]\]\s*\|\s*`(?P<id>F\d-\d{3})`\s*\|\s*`[^`]+`\s*\|\s*(?P<duration>[^|]+?)\s*\|"
)


@dataclass(frozen=True)
class Entry:
    work_id: str
    commit: str
    seconds: int | None
    subject: str


def planned_durations() -> dict[str, str]:
    """plan.md'deki hedef süreleri iş kimliğine göre döndürür."""
    result: dict[str, str] = {}
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        match = PLAN_ROW.match(line)
        if match:
            result.setdefault(match.group("id"), match.group("duration"))
    return result


def git_log() -> list[tuple[str, int, str]]:
    output = subprocess.run(
        ["git", "log", "--reverse", "--format=%h%x1f%ct%x1f%s"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
        check=True,
    ).stdout
    rows: list[tuple[str, int, str]] = []
    for line in output.strip().splitlines():
        commit, timestamp, subject = line.split("\x1f", 2)
        rows.append((commit, int(timestamp), subject))
    return rows


def collect() -> list[Entry]:
    entries: list[Entry] = []
    previous: int | None = None
    for commit, timestamp, subject in git_log():
        match = WORK_ID.search(subject)
        work_id = match.group(1) if match else "-"
        seconds = None if previous is None else timestamp - previous
        entries.append(Entry(work_id, commit, seconds, subject))
        previous = timestamp
    return entries


def human(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds} sn"
    return f"{seconds // 60} dk {seconds % 60} sn"


def render(entries: list[Entry]) -> str:
    planned = planned_durations()
    lines = [
        "| İş ID | Hedef | Gerçek | Commit | Konu |",
        "| --- | --- | --- | --- | --- |",
    ]
    total = 0
    for entry in entries:
        target = planned.get(entry.work_id, "—")
        subject = entry.subject.split(":", 1)[-1].strip()
        if entry.work_id != "-":
            subject = subject.replace(entry.work_id, "").strip()
        lines.append(
            f"| `{entry.work_id}` | {target} | {human(entry.seconds)} | "
            f"`{entry.commit}` | {subject} |"
        )
        if entry.seconds:
            total += entry.seconds

    lines.append("")
    lines.append(
        f"**{len(entries)} commit · olculen toplam {human(total)} · olculemeyen 1 (ilk commit)**"
    )
    return "\n".join(lines)


def update_worklog(table: str) -> bool:
    text = WORKLOG.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        print(
            f"HATA: worklog icinde {BEGIN_MARKER} / {END_MARKER} isaretleri yok",
            file=sys.stderr,
        )
        return False
    start = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = text.index(END_MARKER)
    updated = text[:start] + "\n\n" + table + "\n\n" + text[end:]
    if updated == text:
        return True
    with WORKLOG.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    return True


def main() -> int:
    # Windows konsolu varsayilan olarak cp1252 kullanir ve Turkce karakterlerde
    # patlar; ciktiyi UTF-8'e cevir.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="worklog.md dosyasini guncelle")
    args = parser.parse_args()

    table = render(collect())
    if not args.update:
        print(table)
        return 0

    if not update_worklog(table):
        return 1
    print(f"{WORKLOG.relative_to(ROOT)} guncellendi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
