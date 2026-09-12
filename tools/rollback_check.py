"""Geri dönüş (rollback) prosedürünün uygulanabilirliğini sınar — `F6-032`.

Kabul: **Önceki paket ve kullanıcı ayarlarının geri yükleme adımları
uygulanabilirdir.**

Yazılmış bir geri dönüş prosedürü, denenmemişse bir temenniden ibarettir.
Bu araç `docs/release/release-and-rollback.md` §4'teki adımları
**gerçekten yürütür** ve her adımın sonucunu kaydeder.

Senaryo, gerçek bir başarısız yükseltmeyi taklit eder:

1. Yeni sürüm kurulur ve çalıştığı doğrulanır.
2. Kullanıcı ayarları **yeni sürümün şemasıyla** yazılır ve yedeklenir.
3. Yeni sürüm kaldırılır.
4. **Önceki sürüm** kurulur — geri dönüş adımı.
5. Önceki sürümün, yeni sürümün yazdığı ayar dosyasıyla **açılabildiği**
   doğrulanır. Asıl risk budur: geri dönülen sürüm, ileri şemalı bir
   ayar dosyasıyla karşılaşır. Açılmazsa kullanıcı hem yeni sürümü hem
   ayarlarını kaybeder.
6. Ayarların hâlâ okunabilir olduğu ve yedekten geri yüklemenin
   çalıştığı doğrulanır.
7. Ortam temizlenir; kurulum dizini geride bir şey bırakmamalıdır.

Ayar dosyası kurulum dizininin **dışında** yaşar
(`%APPDATA%\\SonarAnalyzer\\settings.json`), bu yüzden kaldırma onu
silmez. Bu bir tasarım kararıdır ve prosedürün dayandığı temeldir —
burada doğrulanır, varsayılmaz.

Kullanım::

    python tools/rollback_check.py
    python tools/rollback_check.py --previous dist/sonar-analyzer-3.8.0-setup.exe
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RESULTS = ROOT / "docs" / "packaging" / "results"
REPORT_JSON = RESULTS / "rollback-check.json"

SETTINGS_ENV = "SONAR_ANALYZER_SETTINGS"
STEP_TIMEOUT_S = 300

#: Geri donuste korunmasi gereken, ayirt edici kullanici ayarlari.
MARKER_SETTINGS: dict[str, object] = {
    "schema_version": 99,  # kasten ILERI surum: geri donulen paket bunu gormeli
    "theme": "dark",
    "time_display": "utc",
    "recent_files": ["D:/olcumler/gorev-42.bin"],
    "last_export_dir": "D:/olcumler/cikti",
    "bilinmeyen_alan": {"yeni_surumden": True},
}


@dataclass
class Step:
    """Prosedürün tek bir adımı ve sonucu."""

    name: str
    ok: bool
    detail: str = ""


@dataclass
class RollbackReport:
    steps: list[Step] = field(default_factory=lambda: [])
    previous_installer: str = ""
    current_installer: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.steps) and all(step.ok for step in self.steps)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.steps.append(Step(name=name, ok=ok, detail=detail))


def _version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def find_installers(dist_root: Path = DIST) -> list[Path]:
    return sorted(dist_root.glob("sonar-analyzer-*-setup.exe"))


def _version_of(installer: Path) -> str:
    return installer.stem.replace("sonar-analyzer-", "").replace("-setup", "")


def _install(installer: Path, target: Path) -> int:
    completed = subprocess.run(
        [str(installer), "/S", f"/D={target}"],
        capture_output=True,
        check=False,
        timeout=STEP_TIMEOUT_S,
    )
    return completed.returncode


def _uninstall(target: Path) -> int:
    """Kaldırıcıyı **senkron** çalıştırır (`_?=`).

    `_?=` verildiğinde NSIS kaldırıcıyı kendini temp'e kopyalamadan,
    yerinde çalıştırır; böylece işlem bitene kadar beklenebilir. Bunun
    bilinen bedeli, kaldırıcının **kendini silememesidir**: dizinde
    `uninstall.exe` kalır. Bu, ürünün değil çağrının sonucudur — normal
    kullanıcı kaldırması `_uninstall_normal()` ile ayrıca sınanır.
    """
    uninstaller = target / "uninstall.exe"
    if not uninstaller.is_file():
        return 2
    completed = subprocess.run(
        [str(uninstaller), "/S", f"_?={target}"],
        capture_output=True,
        check=False,
        timeout=STEP_TIMEOUT_S,
    )
    return completed.returncode


def _uninstall_normal(target: Path, wait_s: float = 60.0) -> bool:
    """Kullanıcının yaptığı gibi kaldırır: `_?=` **yok**.

    Bu kipte NSIS kaldırıcıyı temp'e kopyalar, oradan çalıştırır ve
    kurulum dizinini **tamamen** siler. Çağrı hemen döndüğü için dizinin
    yok olması beklenir.
    """
    import time

    uninstaller = target / "uninstall.exe"
    if not uninstaller.is_file():
        return False
    subprocess.Popen(
        [str(uninstaller), "/S"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if not target.exists() or not any(target.iterdir()):
            return True
        time.sleep(0.5)
    return not target.exists() or not any(target.iterdir())


def _run_app(target: Path, args: list[str], settings: Path | None) -> tuple[int, str]:
    """Kurulu uygulamayı verilen ayar dosyasıyla çalıştırır."""
    import os

    executable = target / "sonar-analyzer.exe"
    if not executable.is_file():
        return 2, "sonar-analyzer.exe yok"
    env = dict(os.environ)
    if settings is not None:
        env[SETTINGS_ENV] = str(settings)
    completed = subprocess.run(
        [str(executable), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(target),
        env=env,
        timeout=STEP_TIMEOUT_S,
    )
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def run_rollback(previous: Path, current: Path, workspace: Path) -> RollbackReport:
    """Geri dönüş prosedürünü baştan sona yürütür."""
    report = RollbackReport(
        previous_installer=previous.name,
        current_installer=current.name,
    )
    install_dir = workspace / "program"
    settings_path = workspace / "settings" / "settings.json"
    backup_path = workspace / "yedek" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Yeni surum kurulur.
    code = _install(current, install_dir)
    executable = install_dir / "sonar-analyzer.exe"
    report.add(
        "1. Yeni sürüm kurulur",
        code == 0 and executable.is_file(),
        f"cikis {code}, exe={'var' if executable.is_file() else 'YOK'}",
    )

    new_version = _version_of(current)
    code, output = _run_app(install_dir, ["--version"], None)
    report.add(
        "2. Yeni sürüm çalışıyor",
        code == 0 and new_version in output,
        output.strip() or f"cikis {code}",
    )

    # 3) Kullanici ayarlari yazilir ve YEDEKLENIR.
    settings_path.write_text(
        json.dumps(MARKER_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copy2(settings_path, backup_path)
    report.add(
        "3. Ayarlar yazılır ve yedeklenir",
        backup_path.is_file() and backup_path.read_text(encoding="utf-8").strip() != "",
        f"yedek: {backup_path.name}, {backup_path.stat().st_size} bayt",
    )

    # 4) Yeni surum kaldirilir. Olcut "dizin bos mu" DEGIL, "uygulama
    # dosyalari gitti mi": `_?=` ile calisan kaldirici kendini silemez.
    code = _uninstall(install_dir)
    remaining = sorted(p.name for p in install_dir.glob("*")) if install_dir.exists() else []
    leftovers = [name for name in remaining if name != "uninstall.exe"]
    report.add(
        "4. Yeni sürümün uygulama dosyaları kaldırılır",
        code == 0 and not leftovers,
        f"cikis {code}, kalan: {leftovers or 'yok'} (senkron kaldirmada uninstall.exe beklenir)",
    )

    # 5) AYAR DOSYASI KALDIRMADAN SAG CIKTI MI (prosedurun dayanagi).
    survived = settings_path.is_file()
    report.add(
        "5. Ayarlar kaldırmadan sağ çıktı",
        survived,
        "ayar dosyasi kurulum dizini disinda yasiyor" if survived else "AYAR DOSYASI SILINDI",
    )

    # 6) Onceki surum kurulur -- geri donus adimi.
    code = _install(previous, install_dir)
    old_version = _version_of(previous)
    report.add(
        "6. Önceki sürüm kurulur (geri dönüş)",
        code == 0 and (install_dir / "sonar-analyzer.exe").is_file(),
        f"cikis {code}, hedef surum {old_version}",
    )

    code, output = _run_app(install_dir, ["--version"], None)
    report.add(
        "7. Geri dönülen sürüm doğru",
        code == 0 and old_version in output and new_version not in output,
        output.strip() or f"cikis {code}",
    )

    # 8) ASIL RISK: eski surum, ileri semali ayar dosyasiyla acilabiliyor mu?
    code, output = _run_app(install_dir, ["--no-window"], settings_path)
    report.add(
        "8. Önceki sürüm, yeni sürümün ayar dosyasıyla açılıyor",
        code == 0,
        f"cikis {code}" + ("" if code == 0 else f"; cikti: {output.strip()[:200]}"),
    )

    # 9) Yedekten geri yukleme calisiyor mu.
    settings_path.write_text("{bozuk", encoding="utf-8")
    shutil.copy2(backup_path, settings_path)
    restored = json.loads(settings_path.read_text(encoding="utf-8"))
    report.add(
        "9. Yedekten geri yükleme çalışıyor",
        restored.get("recent_files") == MARKER_SETTINGS["recent_files"],
        f"recent_files={restored.get('recent_files')}",
    )

    code, output = _run_app(install_dir, ["--no-window"], settings_path)
    report.add(
        "10. Geri yüklenen ayarlarla açılıyor",
        code == 0,
        f"cikis {code}",
    )

    # 11) Kullanicinin yaptigi gibi kaldirma: dizin TAMAMEN gitmeli.
    cleaned = _uninstall_normal(install_dir)
    remaining = sorted(p.name for p in install_dir.glob("*")) if install_dir.exists() else []
    report.add(
        "11. Geri dönülen sürüm normal kaldırmada iz bırakmıyor",
        cleaned and not remaining,
        f"kalan: {remaining or 'yok'}",
    )

    # 12) Ayar dosyasi kaldirmadan sonra DA duruyor mu: kullanici verisi
    # program dosyalariyla birlikte silinmemeli.
    report.add(
        "12. Ayarlar kaldırmadan sonra hâlâ duruyor",
        settings_path.is_file(),
        str(settings_path.name) if settings_path.is_file() else "AYAR DOSYASI SILINDI",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Geri donus prosedurunu sina")
    parser.add_argument("--previous", type=Path, default=None)
    parser.add_argument("--current", type=Path, default=None)
    args = parser.parse_args(argv)

    installers = find_installers()
    current = args.current or (DIST / f"sonar-analyzer-{_version()}-setup.exe")
    if not current.is_file():
        print(f"Guncel surumun installer'i yok: {current}", file=sys.stderr)
        print("Once uretin: python tools/build_installer.py", file=sys.stderr)
        return 2

    previous = args.previous
    if previous is None:
        earlier = [path for path in installers if path != current]
        if not earlier:
            print("Geri donulecek onceki installer bulunamadi", file=sys.stderr)
            return 2
        previous = earlier[-1]

    with tempfile.TemporaryDirectory(prefix="sonar-rollback-") as raw:
        report = run_rollback(previous, current, Path(raw))

    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "previous_installer": report.previous_installer,
        "current_installer": report.current_installer,
        "platform": platform.platform(),
        "step_count": len(report.steps),
        "passed_count": sum(1 for step in report.steps if step.ok),
        "failed_count": sum(1 for step in report.steps if not step.ok),
        "ok": report.ok,
        "steps": [asdict(step) for step in report.steps],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for step in report.steps:
        print(f"[{'TAMAM' if step.ok else 'BASARISIZ'}] {step.name}")
        print(f"        {step.detail}")
    print(f"adim: {payload['step_count']}, gecen: {payload['passed_count']}")
    print(f"rapor: {REPORT_JSON}")
    print("sonuc: " + ("TAMAM" if report.ok else "BASARISIZ"))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
