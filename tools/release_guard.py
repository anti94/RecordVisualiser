"""Yayın öncesi sürüm tutarlılık kapısı — `F6-017`.

Kabul: **Sürüm etiketiyle VERSION uyuşmazsa yayın adımı durur.**

Bir sürüm yayınlanırken üç şeyin aynı sürümü söylemesi gerekir:

* git **etiketi** (`v3.17.0`),
* depo kökündeki **VERSION** dosyası,
* üretilen **artefaktların** adı ve içindeki uygulamanın bildirdiği sürüm.

Üçü ayrışabilir ve ayrıştığında en kötü biçimde ayrışır: `v3.17.0`
etiketiyle yayınlanan bir paketin içinden `3.16.0` çıkar. Kullanıcı
yanlış sürümü kurar, hata raporu yanlış sürüme yazılır ve iz sürülemez.

Bu araç yayın adımından **önce** koşar ve uyuşmazlıkta durur. Artefakt
denetimi `F6-009`'un manifestine devredilir; burada asıl soru etiket ile
`VERSION`'ın aynı olup olmadığıdır.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

#: Etiket oneki: `v3.17.0` -> `3.17.0`.
TAG_PREFIX = "v"


@dataclass
class ReleaseGuardReport:
    """Yayın kapısının kararı."""

    version_file: str = ""
    tag: str = ""
    tag_version: str = ""
    manifest_version: str = ""
    problems: list[str] = field(default_factory=lambda: [])

    @property
    def ok(self) -> bool:
        return not self.problems


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def version_from_tag(tag: str) -> str:
    """Etiketten sürümü çıkarır; `v` öneki kaldırılır."""
    cleaned = tag.strip()
    return cleaned[len(TAG_PREFIX) :] if cleaned.startswith(TAG_PREFIX) else cleaned


def current_tag() -> str:
    """`HEAD`'i işaret eden sürüm etiketi; yoksa boş.

    Yayın akışı etiketi ortam değişkeninden de verebilir; bu yüzden
    bulunamaması bir hata değil, "etiketli yayın değil" demektir.
    """
    try:
        completed = subprocess.run(
            ["git", "tag", "--points-at", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    tags = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    versions = [tag for tag in tags if tag.startswith(TAG_PREFIX)]
    return versions[0] if versions else ""


def check(tag: str = "", manifest_path: Path | None = None) -> ReleaseGuardReport:
    """Etiket, `VERSION` ve (varsa) manifest sürümünü karşılaştırır."""
    version = read_version()
    effective_tag = tag or current_tag()
    report = ReleaseGuardReport(
        version_file=version,
        tag=effective_tag,
        tag_version=version_from_tag(effective_tag) if effective_tag else "",
    )

    if not effective_tag:
        report.problems.append("Surum etiketi yok; yayin adimi etiketli bir commit'te kosmali.")
        return report

    if report.tag_version != version:
        report.problems.append(
            f"Etiket ({report.tag_version!r}) ile VERSION ({version!r}) ayni degil."
        )

    if manifest_path is not None and manifest_path.is_file():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        report.manifest_version = str(payload.get("version", ""))
        if report.manifest_version != version:
            report.problems.append(
                f"Manifest surumu ({report.manifest_version!r}) ile VERSION ({version!r}) "
                "ayni degil."
            )
        inconsistent = [
            item.get("name", "?")
            for item in payload.get("artifacts", [])
            if not item.get("consistent", False)
        ]
        if inconsistent:
            report.problems.append(f"Tutarsiz artefakt: {', '.join(map(str, inconsistent))}")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yayin surum kapisi (F6-017)")
    parser.add_argument("--tag", default="", help="etiket (bos ise HEAD'den okunur)")
    parser.add_argument("--manifest", type=Path, default=ROOT / "dist" / "release-manifest.json")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    report = check(args.tag, args.manifest)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    print(f"VERSION: {report.version_file}")
    print(f"etiket:  {report.tag or '(yok)'}")
    if report.manifest_version:
        print(f"manifest: {report.manifest_version}")
    for problem in report.problems:
        print(f"  HATA: {problem}", file=sys.stderr)
    print("sonuc: " + ("TAMAM" if report.ok else "YAYIN DURDURULDU"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
