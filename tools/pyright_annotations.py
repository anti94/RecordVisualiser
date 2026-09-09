"""Pyright JSON çıktısını GitHub Actions annotation'larına çevirir.

Pyright'ın `--output-format=github` seçeneği yoktur; hatalar yalnız adım
günlüğünde görünür. Günlüğü okumak kimlik doğrulaması gerektirdiğinden,
bulgular burada `::error file=...` komutlarına çevrilir. Böylece hatalar hem
değişiklik satırlarının yanında hem de annotations API'sinde görünür.

Kullanım:
    python -m pyright --outputjson > pyright.json
    python tools/pyright_annotations.py pyright.json

Çıkış kodu: hata varsa 1, yoksa 0.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

LEVELS = {"error": "error", "warning": "warning", "information": "notice"}


def escape(text: str) -> str:
    """Annotation komutlarında özel anlamı olan karakterleri kaçırır."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def emit(diagnostic: dict[str, Any]) -> str:
    severity = str(diagnostic.get("severity", "error"))
    level = LEVELS.get(severity, "error")

    path = str(diagnostic.get("file", ""))
    with contextlib.suppress(ValueError, OSError):
        path = str(Path(path).resolve().relative_to(Path.cwd()))

    start = diagnostic.get("range", {}).get("start", {})
    line = int(start.get("line", 0)) + 1
    column = int(start.get("character", 0)) + 1

    rule = diagnostic.get("rule")
    message = str(diagnostic.get("message", "")).strip()
    if rule:
        message = f"{message} ({rule})"

    return f"::{level} file={path},line={line},col={column}::{escape(message)}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("kullanim: pyright_annotations.py <pyright.json>", file=sys.stderr)
        return 2

    raw = Path(argv[1]).read_text(encoding="utf-8")
    try:
        report: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"::error::pyright ciktisi ayristirilamadi: {exc}")
        print(raw[:2000], file=sys.stderr)
        return 1

    diagnostics: list[dict[str, Any]] = report.get("generalDiagnostics", [])
    for diagnostic in diagnostics:
        print(emit(diagnostic))

    summary = report.get("summary", {})
    error_count = int(summary.get("errorCount", 0))
    warning_count = int(summary.get("warningCount", 0))
    print(f"pyright: {error_count} hata, {warning_count} uyari, {len(diagnostics)} bulgu")

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
