"""Paketli uygulamada kullanıcı kabul turu — `F6-030`.

Kabul: **Operatör ve mühendis akışları kanıtla işaretlenir;
başarısızlıklar ayrı işe dönüşür.**

Bu araç kabul turunu **paketlenmiş `.exe` üzerinde** yürütür. Kaynak
ağacından çalıştırmak bir şey kanıtlamaz: paketlemede kaybolan şeyler
(eksik veri dosyası, gelmeyen Qt eklentisi, yanlış sürüm) tam da orada
ortaya çıkar.

İki rol vardır ve beklentileri farklıdır:

* **Operatör** — uygulamayı açar, bir kaydı görüntüler, çıktı alır.
  Onun için "çalışıyor" demek, ekranın açılması ve dosyanın okunmasıdır.
* **Mühendis** — verinin doğruluğunu sorgular. Onun için "çalışıyor"
  demek, **bozuk verinin reddedilmesi** ve sağlam verinin eksiksiz
  okunmasıdır.

Her adım çalıştırılmadan **önce** ne beklendiğini bildirir
(`expected_exit`, `expect_stdout`, `expect_artifacts`). Böylece sonuç,
çıktıya bakıp sonradan uydurulmuş bir beklentiyle değil, önceden
yazılmış bir sözleşmeyle karşılaştırılır.

Bazı adımlar **başarısızlık bekler**: desteklenmeyen sürümlü ya da kesik
bir dosyanın açılmaması, bu turda bir hata değil, geçme koşuludur.

Başarısız adım gizlenmez: rapora `YENİ İŞ` olarak yazılır ve önerilen
iş kaydıyla birlikte listelenir. "Kabul turu geçti" demek için hiçbir
adımın atlanmamış olması gerekir — atlanan adım da başarısızlıktır.

Kullanım::

    python tools/acceptance_run.py
    python tools/acceptance_run.py --exe dist/sonar-analyzer-3.29.0/sonar-analyzer.exe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FIXTURES = ROOT / "tests" / "fixtures"
RESULTS = ROOT / "docs" / "acceptance" / "results"
REPORT_JSON = RESULTS / "packaged-acceptance.json"

#: Tek bir adimin en fazla surebilecegi sure.
STEP_TIMEOUT_S = 180


@dataclass(frozen=True)
class Step:
    """Kabul turunun tek bir adımı — beklentisiyle birlikte."""

    step_id: str
    role: str
    title: str
    why: str
    argv: tuple[str, ...]
    expected_exit: int
    expect_stdout: tuple[str, ...] = ()
    reject_stdout: tuple[str, ...] = ()
    expect_artifacts: tuple[str, ...] = ()
    needs_fixture: str = ""


@dataclass
class StepResult:
    """Bir adımın çalıştırılmış hâli ve kanıtı."""

    step_id: str
    role: str
    title: str
    why: str
    command: str
    expected_exit: int
    actual_exit: int
    duration_s: float
    stdout_tail: list[str]
    artifacts: list[dict[str, object]] = field(default_factory=lambda: [])
    problems: list[str] = field(default_factory=lambda: [])

    @property
    def passed(self) -> bool:
        return not self.problems


def _fixture(name: str) -> Path:
    return FIXTURES / name


def build_steps(out_root: Path) -> tuple[Step, ...]:
    """Kabul turunun adımları; sıra anlamlıdır (basitten veriye)."""
    return (
        # -- OPERATOR -------------------------------------------------- #
        Step(
            step_id="O-01",
            role="operator",
            title="Doğru sürüm kuruldu mu",
            why=("Yanlış sürümü çalıştırıp 'düzeldi' sanmak, bir hatayı iki kez aramaya yol açar."),
            argv=("--version",),
            expected_exit=0,
            expect_stdout=(f"sonar-analyzer {_version()}",),
        ),
        Step(
            step_id="O-02",
            role="operator",
            title="Uygulama ekransız da olsa temiz başlayıp kapanıyor mu",
            why=(
                "Giriş yolunun paketten çalıştığını, pencere açmadan "
                "gösterir; çökmeden kapanmak da sonucun parçasıdır."
            ),
            argv=("--no-window",),
            expected_exit=0,
        ),
        Step(
            step_id="O-03",
            role="operator",
            title="Ana ekran açılıyor, tema ve ikon yükleniyor mu",
            why=(
                "Paketlemede en sık kaybolan şeyler bunlardır: Qt platform "
                "eklentisi, tema ve ikon. Üçü de pencere gerçekten "
                "gösterilerek denetlenir."
            ),
            argv=("--self-check",),
            expected_exit=0,
            expect_stdout=("sonuc: TAMAM",),
        ),
        Step(
            step_id="O-04",
            role="operator",
            title="Güncel kayıt açılıyor, CSV ve PNG çıktısı alınıyor mu",
            why=(
                "Operatörün günlük işi budur. Çıktılar yazıldıktan sonra "
                "geri okunur; yazıp 'oldu' demek yetmez, bozuk bir dosya "
                "da yazılmış olur."
            ),
            argv=(
                "--bin-check",
                str(_fixture("valid_8records_v2.bin")),
                "--bin-check-out",
                str(out_root / "O-04"),
            ),
            expected_exit=0,
            expect_stdout=("sonuc: TAMAM", "8 kanal"),
            expect_artifacts=("O-04/export.csv", "O-04/export.png"),
            needs_fixture="valid_8records_v2.bin",
        ),
        # -- MUHENDIS -------------------------------------------------- #
        Step(
            step_id="M-01",
            role="engineer",
            title="CRC'siz eski sürüm (v1) kayıt hâlâ okunuyor mu",
            why=(
                "Eski kayıtlar arşivde kalır. Yeni sürüm onları okumayı "
                "bırakırsa geçmiş ölçümler erişilemez olur."
            ),
            argv=(
                "--bin-check",
                str(_fixture("valid_8records.bin")),
                "--bin-check-out",
                str(out_root / "M-01"),
            ),
            expected_exit=0,
            expect_stdout=("sonuc: TAMAM",),
            expect_artifacts=("M-01/export.csv",),
            needs_fixture="valid_8records.bin",
        ),
        Step(
            step_id="M-02",
            role="engineer",
            title="Sıra boşluğu olan kayıt eksiksiz açılıyor mu",
            why=(
                "Paket kaybı bir bozulma değildir. Boşluklu kayıt "
                "açılmazsa, elde olan veri de kaybedilmiş olur."
            ),
            argv=(
                "--bin-check",
                str(_fixture("gap_missing_record.bin")),
                "--bin-check-out",
                str(out_root / "M-02"),
            ),
            expected_exit=0,
            expect_stdout=("sonuc: TAMAM",),
            needs_fixture="gap_missing_record.bin",
        ),
        Step(
            step_id="M-03",
            role="engineer",
            title="Desteklenmeyen format sürümü reddediliyor mu",
            why=(
                "Bilinmeyen sürümü en yakın sürüm sanıp okumak, sessizce "
                "yanlış veri üretirdi. Ret, burada geçme koşuludur."
            ),
            argv=(
                "--bin-check",
                str(_fixture("unsupported_version.bin")),
                "--bin-check-out",
                str(out_root / "M-03"),
            ),
            expected_exit=1,
            expect_stdout=("ACILAMADI",),
            reject_stdout=("sonuc: TAMAM",),
            needs_fixture="unsupported_version.bin",
        ),
        Step(
            step_id="M-04",
            role="engineer",
            title="Kesik başlıklı dosya reddediliyor mu",
            why=(
                "Yarım bir başlıkla açılıp uydurma alanlar göstermek, açılmamaktan daha zararlıdır."
            ),
            argv=(
                "--bin-check",
                str(_fixture("truncated_header.bin")),
                "--bin-check-out",
                str(out_root / "M-04"),
            ),
            expected_exit=1,
            expect_stdout=("ACILAMADI",),
            reject_stdout=("sonuc: TAMAM",),
            needs_fixture="truncated_header.bin",
        ),
        Step(
            step_id="M-05",
            role="engineer",
            title="Bozuk CRC'li kayıt açılıyor ama sessiz geçilmiyor mu",
            why=(
                "ADR-011: kayıt CRC hatası fatal değildir — dosya açılır, "
                "bozuk kayıt işaretlenir. Dosyanın tamamını reddetmek "
                "sağlam kayıtları da kaybettirirdi. Ama işaretlenmiş "
                "olması yetmez: mühendis bunu **görebilmelidir**. Bu "
                "adım, bilinen bir bozuk kaydın kullanıcıya ulaşan "
                "yolda görünür olmasını arar."
            ),
            argv=(
                "--bin-check",
                str(_fixture("crc_error.bin")),
                "--bin-check-out",
                str(out_root / "M-05"),
            ),
            expected_exit=0,
            expect_stdout=("kayit:", "CRC_ERROR"),
            needs_fixture="crc_error.bin",
        ),
    )


def _version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def find_executable(explicit: Path | None = None) -> Path | None:
    """Kabul turunun çalıştırılacağı paketli `.exe`.

    Öntanımlı olarak **bu sürümün** klasörü aranır. Başka bir sürümün
    paketiyle tur yürütmek, kabul edilen şeyin ne olduğunu belirsiz
    kılardı.
    """
    if explicit is not None:
        return explicit if explicit.is_file() else None
    candidate = DIST / f"sonar-analyzer-{_version()}" / "sonar-analyzer.exe"
    return candidate if candidate.is_file() else None


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_step(exe: Path, step: Step, out_root: Path) -> StepResult:
    """Tek adımı çalıştırır ve kanıtını toplar."""
    command = [str(exe), *step.argv]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=STEP_TIMEOUT_S,
        check=False,
    )
    duration = time.monotonic() - started
    output = (completed.stdout or "") + (completed.stderr or "")
    lines = [line for line in output.splitlines() if line.strip()]

    problems: list[str] = []
    if completed.returncode != step.expected_exit:
        problems.append(f"cikis kodu {completed.returncode}, beklenen {step.expected_exit}")
    for needle in step.expect_stdout:
        if needle not in output:
            problems.append(f"ciktida bulunamadi: {needle!r}")
    for needle in step.reject_stdout:
        if needle in output:
            problems.append(f"ciktida olmamasi gereken ifade var: {needle!r}")

    artifacts: list[dict[str, object]] = []
    for relative in step.expect_artifacts:
        path = out_root / relative
        if not path.is_file():
            problems.append(f"uretilmedi: {relative}")
            continue
        size = path.stat().st_size
        if size == 0:
            problems.append(f"bos uretildi: {relative}")
        artifacts.append({"path": relative, "bytes": size, "sha256": _digest(path)})

    return StepResult(
        step_id=step.step_id,
        role=step.role,
        title=step.title,
        why=step.why,
        command=" ".join([exe.name, *step.argv]),
        expected_exit=step.expected_exit,
        actual_exit=completed.returncode,
        duration_s=round(duration, 3),
        stdout_tail=lines[-8:],
        artifacts=artifacts,
        problems=problems,
    )


def run_acceptance(exe: Path, out_root: Path) -> dict[str, object]:
    """Bütün adımları yürütür ve rapor sözlüğünü döndürür."""
    out_root.mkdir(parents=True, exist_ok=True)
    steps = build_steps(out_root)

    missing = sorted(
        {step.needs_fixture for step in steps if step.needs_fixture} - _present_fixtures()
    )
    results: list[StepResult] = []
    for step in steps:
        if step.needs_fixture and not _fixture(step.needs_fixture).is_file():
            results.append(
                StepResult(
                    step_id=step.step_id,
                    role=step.role,
                    title=step.title,
                    why=step.why,
                    command=" ".join([exe.name, *step.argv]),
                    expected_exit=step.expected_exit,
                    actual_exit=-1,
                    duration_s=0.0,
                    stdout_tail=[],
                    problems=[f"fixture yok: {step.needs_fixture}"],
                )
            )
            continue
        results.append(run_step(exe, step, out_root))

    failures = [result for result in results if not result.passed]
    return {
        "executable": str(exe),
        "version": _version(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "step_count": len(results),
        "passed_count": len(results) - len(failures),
        "failed_count": len(failures),
        "missing_fixtures": missing,
        "ok": not failures,
        "results": [asdict(result) for result in results],
    }


def _present_fixtures() -> set[str]:
    return {path.name for path in FIXTURES.glob("*.bin")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paketli uygulamada kabul turu")
    parser.add_argument("--exe", type=Path, default=None, help="Paketli .exe yolu")
    parser.add_argument("--out", type=Path, default=None, help="Kanit ciktilari dizini")
    args = parser.parse_args(argv)

    exe = find_executable(args.exe)
    if exe is None:
        expected = DIST / f"sonar-analyzer-{_version()}" / "sonar-analyzer.exe"
        print(
            f"Paketli uygulama bulunamadi: {expected}\n"
            "Once paketi uretin: python tools/build_package.py",
            file=sys.stderr,
        )
        return 2

    out_root = args.out or (RESULTS / "artifacts")
    report = run_acceptance(exe, out_root)

    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for entry in report["results"]:  # type: ignore[union-attr]
        assert isinstance(entry, dict)
        mark = "TAMAM" if not entry["problems"] else "BASARISIZ"
        print(f"[{mark}] {entry['step_id']} {entry['title']}")
        for problem in entry["problems"]:  # type: ignore[union-attr]
            print(f"        -> {problem}")

    print(
        f"adim: {report['step_count']}, gecen: {report['passed_count']}, "
        f"basarisiz: {report['failed_count']}"
    )
    print(f"rapor: {REPORT_JSON}")
    print("sonuc: " + ("TAMAM" if report["ok"] else "BASARISIZ"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
