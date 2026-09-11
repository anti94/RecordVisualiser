"""Kurulum, yükseltme ve kaldırma denetimi — `F6-008`.

Kabul: **Sürüm geçişi kullanıcı workspace ve kaynak kayıtlarını silmez.**

Bir kurulumun en pahalı hatası veri kaybettirmesidir ve bu, ancak
gerçekten kurup yükseltip kaldırarak bilinebilir. Bu araç tam turu
yürütür:

1. eski sürüm kurulur,
2. **kullanıcı verisi** oluşturulur (workspace/ayar dosyası ve bir
   kaynak `.bin` kaydı),
3. yeni sürüm aynı dizine kurulur (yükseltme),
4. uygulamanın sürümü değişti mi ve **kullanıcı verisi duruyor mu**
   denetlenir,
5. kaldırılır ve kullanıcı verisinin **hâlâ** durduğu denetlenir.

Beşinci adım ayrı bir sorudur: yükseltmede korunan veri, kaldırmada
silinebilir. İkisi de denetlenmezse kullanıcı verisi bir adımda kaybolur.

Kurulum geçici bir dizine, sessiz kipte yapılır; tur sonunda makinede iz
kalmaz.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIST = ROOT / "dist"
DEFAULT_REPORT = ROOT / "docs" / "packaging" / "results" / "installer-lifecycle.json"

#: Kullanici verisini temsil eden dosyalar (kurulum dizininin DISINDA).
WORKSPACE_NAME = "workspace.json"
RECORDING_NAME = "kayit.bin"


@dataclass
class LifecycleStep:
    """Turun tek bir adımının sonucu."""

    name: str
    ok: bool
    detail: str = ""


@dataclass
class LifecycleReport:
    """Kurulum/yükseltme/kaldırma turunun kaydı."""

    from_version: str = ""
    to_version: str = ""
    steps: list[LifecycleStep] = field(default_factory=lambda: [])

    @property
    def ok(self) -> bool:
        return bool(self.steps) and all(step.ok for step in self.steps)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.steps.append(LifecycleStep(name=name, ok=ok, detail=detail))


def find_installers(dist_root: Path) -> list[Path]:
    """Üretilmiş installer'ları sürüm sırasıyla döner."""
    return sorted(dist_root.glob("sonar-analyzer-*-setup.exe"))


def _version_of(installer: Path) -> str:
    name = installer.stem  # sonar-analyzer-<surum>-setup
    return name.replace("sonar-analyzer-", "").replace("-setup", "")


def _run_installer(installer: Path, target: Path) -> int:
    completed = subprocess.run(
        [str(installer), "/S", f"/D={target}"],
        capture_output=True,
        check=False,
    )
    return completed.returncode


def _run_uninstaller(target: Path) -> int:
    uninstaller = target / "uninstall.exe"
    if not uninstaller.is_file():
        return 2
    # Kaldirici kendini kopyalayip calistirir; bitmesini beklemek icin
    # _? parametresi gerekir, aksi halde islem hemen doner.
    completed = subprocess.run(
        [str(uninstaller), "/S", f"_?={target}"],
        capture_output=True,
        check=False,
    )
    return completed.returncode


def _reported_version(target: Path) -> str:
    executable = target / "sonar-analyzer.exe"
    if not executable.is_file():
        return ""
    completed = subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(target),
    )
    return (completed.stdout + completed.stderr).strip()


def run_lifecycle(older: Path, newer: Path) -> LifecycleReport:
    """Kurulum → kullanıcı verisi → yükseltme → kaldırma turunu yürütür."""
    report = LifecycleReport(from_version=_version_of(older), to_version=_version_of(newer))

    with tempfile.TemporaryDirectory(prefix="sonar-lifecycle-") as raw_root:
        root = Path(raw_root)
        install_dir = root / "program"
        user_dir = root / "kullanici"  # kurulum dizininin DISINDA
        user_dir.mkdir(parents=True)

        workspace = user_dir / WORKSPACE_NAME
        recording = user_dir / RECORDING_NAME

        # 1) Eski surum kurulur.
        code = _run_installer(older, install_dir)
        installed = (install_dir / "sonar-analyzer.exe").is_file()
        report.add("eski surum kuruldu", code == 0 and installed, f"cikis kodu {code}")
        if not installed:
            return report

        first_version = _reported_version(install_dir)
        report.add("eski surum calisiyor", bool(first_version), first_version)

        # 2) Kullanici verisi olusturulur.
        workspace.write_text(json.dumps({"acik_kanal": "ch0"}), encoding="utf-8")
        recording.write_bytes(b"SONARBIN" + bytes(range(64)))
        workspace_before = workspace.read_bytes()
        recording_before = recording.read_bytes()
        report.add("kullanici verisi olusturuldu", True, f"{workspace.name}, {recording.name}")

        # 3) Yeni surum AYNI dizine kurulur (yukseltme).
        code = _run_installer(newer, install_dir)
        second_version = _reported_version(install_dir)
        report.add("yukseltme yapildi", code == 0, f"cikis kodu {code}")
        report.add(
            "surum degisti",
            bool(second_version) and second_version != first_version,
            f"{first_version} -> {second_version}",
        )

        # 4) Kullanici verisi YUKSELTMEDEN sonra duruyor mu?
        report.add(
            "yukseltme workspace'i silmedi",
            workspace.is_file() and workspace.read_bytes() == workspace_before,
            str(workspace),
        )
        report.add(
            "yukseltme kaydi silmedi",
            recording.is_file() and recording.read_bytes() == recording_before,
            str(recording),
        )

        # 5) Kaldirma sonrasi kullanici verisi HALA duruyor mu?
        code = _run_uninstaller(install_dir)
        report.add("kaldirma calisti", code == 0, f"cikis kodu {code}")
        report.add(
            "kaldirma workspace'i silmedi",
            workspace.is_file() and workspace.read_bytes() == workspace_before,
            str(workspace),
        )
        report.add(
            "kaldirma kaydi silmedi",
            recording.is_file() and recording.read_bytes() == recording_before,
            str(recording),
        )
        report.add(
            "uygulama dosyalari kaldirildi",
            not (install_dir / "sonar-analyzer.exe").is_file(),
            str(install_dir),
        )

        # Ortaligi topla: kalan kurulum dizini varsa sil.
        shutil.rmtree(install_dir, ignore_errors=True)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kurulum/yukseltme/kaldirma denetimi (F6-008)")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    installers = find_installers(args.dist)
    if len(installers) < 2:
        print(
            "Yukseltme icin iki installer gerekli. Bulunan: "
            f"{[p.name for p in installers]}\n"
            "Farkli iki surumde uretin: python tools/build_installer.py",
        )
        return 2

    report = run_lifecycle(installers[-2], installers[-1])
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    print(f"yukseltme: {report.from_version} -> {report.to_version}")
    for step in report.steps:
        mark = "TAMAM" if step.ok else "BASARISIZ"
        print(f"  [{mark}] {step.name} — {step.detail}")
    print("sonuc: " + ("TAMAM" if report.ok else "BASARISIZ"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
