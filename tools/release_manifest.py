"""Artefakt checksum ve sürüm manifesti — `F6-009`.

Kabul: **Paket sürümü, dosya adı ve hash birbiriyle eşleşir.**

Bir sürüm artefaktının üç kimliği vardır ve üçü de ayrışabilir:

* **dosya adı** (`sonar-analyzer-3.8.0-setup.exe`),
* **uygulamanın bildirdiği sürüm** (`--version` çıktısı),
* **içerik** (baytların hash'i).

Manifest üçünü tek yerde toplar ve **tutarlılıklarını denetler**. Yalnız
hash yazan bir manifest, yanlış sürümü doğru hash'le imzalamayı
engellemez: dosya adı `3.8.0` derken içindeki uygulama `3.7.0` diyorsa
hash o yanlışlığı da sadakatle kaydeder.

Hash **SHA-256**'dır ve dosya parça parça okunur; 170 MB'lık bir paketi
belleğe almak gereksizdir.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
DEFAULT_DIST = ROOT / "dist"
DEFAULT_MANIFEST = DEFAULT_DIST / "release-manifest.json"

#: Hash okuma parcasi (1 MiB).
CHUNK_BYTES = 1024 * 1024


@dataclass
class Artifact:
    """Tek bir sürüm artefaktı."""

    name: str
    kind: str
    size_bytes: int
    sha256: str
    version_in_name: str = ""
    version_reported: str = ""
    consistent: bool = False
    note: str = ""


@dataclass
class ReleaseManifest:
    """Bir sürümün bütün artefaktları."""

    version: str
    created_utc: str
    artifacts: list[Artifact] = field(default_factory=lambda: [])

    @property
    def ok(self) -> bool:
        """Artefakt varsa ve hepsi tutarlıysa geçer."""
        return bool(self.artifacts) and all(item.consistent for item in self.artifacts)


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def sha256_of(path: Path) -> str:
    """Dosyanın SHA-256'sı; parça parça okunur."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(CHUNK_BYTES)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def version_in_filename(name: str) -> str:
    """Dosya ya da klasör adındaki sürüm; bulunamazsa boş.

    Ad `sonar-analyzer-<surum>[-setup][.exe]` düzenindedir.

    `Path.stem` KULLANILMAZ: klasör adı `sonar-analyzer-3.8.0` iken `.0`
    uzantı sanılır ve sürüm `3.8` okunurdu. (Bu hatayı manifestin kendi
    tutarlılık denetimi yakaladı.) Bu yüzden yalnız gerçek `.exe` uzantısı
    kırpılır.
    """
    label = name[: -len(".exe")] if name.lower().endswith(".exe") else name
    if not label.startswith("sonar-analyzer-"):
        return ""
    rest = label[len("sonar-analyzer-") :]
    return rest[: -len("-setup")] if rest.endswith("-setup") else rest


def reported_version(executable: Path) -> str:
    """Uygulamanın kendi bildirdiği sürüm; çalıştırılamazsa boş."""
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(executable.parent),
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    text = (completed.stdout + completed.stderr).strip()
    # "sonar-analyzer 3.8.0" -> "3.8.0"
    return text.split()[-1] if text else ""


def collect(dist_root: Path, version: str) -> list[Artifact]:
    """Sürümün artefaktlarını toplar ve tutarlılığını denetler."""
    artifacts: list[Artifact] = []

    installer = dist_root / f"sonar-analyzer-{version}-setup.exe"
    if installer.is_file():
        artifacts.append(_describe_installer(installer, version))

    package_exe = dist_root / f"sonar-analyzer-{version}" / "sonar-analyzer.exe"
    if package_exe.is_file():
        artifacts.append(_describe_package(package_exe, version))

    return artifacts


def _describe_installer(path: Path, version: str) -> Artifact:
    in_name = version_in_filename(path.name)
    consistent = in_name == version
    return Artifact(
        name=path.name,
        kind="installer",
        size_bytes=path.stat().st_size,
        sha256=sha256_of(path),
        version_in_name=in_name,
        # Installer'i calistirmak kurulum yapardi; surumu adindan dogrulanir
        # ve icerdigi uygulama `package` artefaktiyla ayrica denetlenir.
        version_reported="",
        consistent=consistent,
        note="" if consistent else f"ad surumu {in_name!r}, beklenen {version!r}",
    )


def _describe_package(executable: Path, version: str) -> Artifact:
    folder = executable.parent
    in_name = version_in_filename(folder.name)
    told = reported_version(executable)
    consistent = in_name == version and told == version
    problems: list[str] = []
    if in_name != version:
        problems.append(f"klasor surumu {in_name!r}")
    if told != version:
        problems.append(f"uygulama {told!r} diyor")
    return Artifact(
        name=f"{folder.name}/{executable.name}",
        kind="package",
        size_bytes=executable.stat().st_size,
        sha256=sha256_of(executable),
        version_in_name=in_name,
        version_reported=told,
        consistent=consistent,
        note="; ".join(problems),
    )


def build_manifest(dist_root: Path = DEFAULT_DIST) -> ReleaseManifest:
    version = read_version()
    return ReleaseManifest(
        version=version,
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        artifacts=collect(dist_root, version),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Surum manifesti ve checksum uretir (F6-009)")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--json", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    manifest = build_manifest(args.dist)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")

    print(f"surum: {manifest.version}")
    if not manifest.artifacts:
        print(f"artefakt bulunamadi: {args.dist}")
        print("sonuc: BASARISIZ")
        return 1

    for item in manifest.artifacts:
        mark = "TAMAM" if item.consistent else "TUTARSIZ"
        print(f"  [{mark}] {item.kind}: {item.name}")
        print(f"          {item.size_bytes} bayt  sha256={item.sha256}")
        if item.note:
            print(f"          {item.note}")
    print(f"manifest: {args.json}")
    print("sonuc: " + ("TAMAM" if manifest.ok else "BASARISIZ"))
    return 0 if manifest.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
