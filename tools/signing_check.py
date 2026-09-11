"""İmzalama denetimi ve yayın akışına bağlanması — `F6-012`.

Kabul: **Gerekliyse sertifika ile doğrulanır; değilse imzasız dağıtım
kararı kaydedilir.**

D-17 ("code signing gerekli mi") cevaplanmadı. Bu araç iki durumu da
karşılar ve **hangi durumda olduğumuzu ölçerek** söyler:

* sertifika yapılandırılmışsa artefaktların imzası doğrulanır,
* yapılandırılmamışsa artefaktların **gerçekten imzasız** olduğu
  kaydedilir ve kararın bedeli yazılır.

İkincisi "hiçbir şey yapma" demek değildir: imzasız bir Windows
çalıştırılabiliri SmartScreen uyarısı gösterir ve kullanıcı "yine de
çalıştır" demek zorunda kalır. Bu bilinen ve kabul edilen bir maliyettir;
kaydedilmezse bir gün sürpriz olur.

İmza durumu Windows'un kendi doğrulayıcısıyla (`Get-AuthenticodeSignature`)
okunur; tahmin edilmez.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIST = ROOT / "dist"
DEFAULT_REPORT = ROOT / "docs" / "packaging" / "results" / "signing-check.json"

#: Sertifika yolu bu ortam degiskeninden gelir. Tanimli degilse imzasiz
#: dagitim kararı gecerlidir.
CERT_ENV = "SONAR_SIGNING_CERT"

#: `Get-AuthenticodeSignature` durumlari.
STATUS_NOT_SIGNED = "NotSigned"
STATUS_VALID = "Valid"


@dataclass
class ArtifactSignature:
    """Tek bir artefaktın imza durumu."""

    name: str
    status: str
    signer: str = ""


@dataclass
class SigningReport:
    """Yayın akışının imza denetimi."""

    signing_required: bool = False
    certificate_configured: bool = False
    artifacts: list[ArtifactSignature] = field(default_factory=lambda: [])
    decision: str = ""
    consequences: list[str] = field(default_factory=lambda: [])

    @property
    def ok(self) -> bool:
        """Karar ile ölçülen durum tutarlı mı?

        İmza gerekiyorsa **hepsi** geçerli imzalı olmalı; gerekmiyorsa
        durum ne olursa olsun rapor geçerlidir ama artefaktların
        bulunmuş olması şarttır — hiçbir şey ölçmeden "tamam" denmez.
        """
        if not self.artifacts:
            return False
        if self.signing_required:
            return all(item.status == STATUS_VALID for item in self.artifacts)
        return True


def certificate_configured() -> bool:
    """Sertifika yapılandırılmış mı?"""
    return bool(os.environ.get(CERT_ENV, "").strip())


def signature_of(path: Path) -> ArtifactSignature:
    """Windows'un kendi doğrulayıcısıyla imza durumunu okur."""
    script = (
        f"$s = Get-AuthenticodeSignature -LiteralPath '{path}'; "
        "Write-Output $s.Status; "
        "if ($s.SignerCertificate) { Write-Output $s.SignerCertificate.Subject } "
        "else { Write-Output '' }"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return ArtifactSignature(name=path.name, status="Bilinmiyor")

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    status = lines[0] if lines else "Bilinmiyor"
    signer = lines[1] if len(lines) > 1 else ""
    return ArtifactSignature(name=path.name, status=status, signer=signer)


def find_artifacts(dist_root: Path) -> list[Path]:
    """İmzalanabilir artefaktlar: installer ve paket çalıştırılabiliri."""
    found = sorted(dist_root.glob("sonar-analyzer-*-setup.exe"))
    found += sorted(dist_root.glob("sonar-analyzer-*/sonar-analyzer.exe"))
    return found


def check(dist_root: Path = DEFAULT_DIST) -> SigningReport:
    """Artefaktların imza durumunu ölçer ve kararı kaydeder."""
    configured = certificate_configured()
    report = SigningReport(
        signing_required=configured,
        certificate_configured=configured,
        artifacts=[signature_of(path) for path in find_artifacts(dist_root)],
    )

    if configured:
        report.decision = "Sertifika yapilandirilmis; artefaktlar imzali olmali."
        report.consequences = [
            "Imzasiz artefakt yayinlanmaz.",
            "Sertifikanin suresi dolarsa yayin akisi durur.",
        ]
    else:
        report.decision = (
            "IMZASIZ DAGITIM. D-17 cevaplanmadi ve sertifika yapilandirilmadi; "
            "artefaktlar imzasiz yayinlanir."
        )
        report.consequences = [
            "SmartScreen bilinmeyen yayinci uyarisi gosterir; "
            "kullanici 'Yine de calistir' demek zorunda kalir.",
            "Bazi kurumsal ilkeler imzasiz calistirilabiliri engelleyebilir.",
            "Sertifika temini uzun surer; gerekliyse erken baslatilmali (plan D-17).",
        ]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Imzalama denetimi (F6-012)")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    report = check(args.dist)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    print(f"sertifika yapilandirildi mi: {'evet' if report.certificate_configured else 'hayir'}")
    print(f"karar: {report.decision}")
    for item in report.artifacts:
        signer = f" — {item.signer}" if item.signer else ""
        print(f"  {item.name}: {item.status}{signer}")
    for line in report.consequences:
        print(f"  * {line}")
    print("sonuc: " + ("TAMAM" if report.ok else "BASARISIZ"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
