"""İmzalama denetimi — `F6-012`.

Kabul: **Gerekliyse sertifika ile doğrulanır; değilse imzasız dağıtım
kararı kaydedilir.**

D-17 cevaplanmadı, sertifika yok. Bu durumda doğru davranış "imza
konusunu atlamak" değil, **imzasız olduğumuzu ölçüp kaydetmek**; kayıt
olmazsa bir gün SmartScreen uyarısı sürpriz olur.

Testler iki kipi de sınar. En önemlisi, sertifika yapılandırıldığında
denetimin gerçekten **sertleştiği**: imzasız artefakt o kipte raporu
düşürmeli, yoksa yapılandırma bir şey değiştirmiyor demektir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.signing_check import (  # noqa: E402
    CERT_ENV,
    STATUS_NOT_SIGNED,
    STATUS_VALID,
    ArtifactSignature,
    SigningReport,
    certificate_configured,
    check,
    find_artifacts,
)

EVIDENCE = ROOT / "docs/packaging/results/signing-check.json"
ADR = ROOT / "docs/adr/ADR-012-packaging.md"


def _unsigned() -> ArtifactSignature:
    return ArtifactSignature(name="a.exe", status=STATUS_NOT_SIGNED)


def _signed() -> ArtifactSignature:
    return ArtifactSignature(name="a.exe", status=STATUS_VALID, signer="CN=Ornek")


# --------------------------------------------------------------------------- #
# SERTIFIKA YOKKEN: imzasiz dagitim kabul edilir ama KAYDEDILIR
# --------------------------------------------------------------------------- #


def test_without_a_certificate_unsigned_artifacts_are_accepted() -> None:
    report = SigningReport(signing_required=False, artifacts=[_unsigned()])
    assert report.ok is True


def test_without_any_artifact_nothing_is_claimed() -> None:
    """Hiçbir şey ölçmeden "tamam" denmez."""
    assert SigningReport(signing_required=False).ok is False


def test_the_unsigned_decision_is_recorded_with_its_cost(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(CERT_ENV, raising=False)
    (tmp_path / "sonar-analyzer-1.0.0-setup.exe").write_bytes(b"MZ")

    report = check(tmp_path)

    assert report.certificate_configured is False
    assert "IMZASIZ DAGITIM" in report.decision
    assert any("SmartScreen" in line for line in report.consequences)


# --------------------------------------------------------------------------- #
# SERTIFIKA VARKEN: denetim SERTLESIR
# --------------------------------------------------------------------------- #


def test_with_a_certificate_an_unsigned_artifact_fails() -> None:
    """Yapılandırma bir şey değiştirmiyorsa yapılandırmanın anlamı yoktur."""
    report = SigningReport(signing_required=True, artifacts=[_unsigned()])
    assert report.ok is False


def test_with_a_certificate_a_signed_artifact_passes() -> None:
    report = SigningReport(signing_required=True, artifacts=[_signed()])
    assert report.ok is True


def test_with_a_certificate_one_unsigned_artifact_is_enough_to_fail() -> None:
    report = SigningReport(signing_required=True, artifacts=[_signed(), _unsigned()])
    assert report.ok is False


def test_configuring_the_certificate_switches_the_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(CERT_ENV, str(tmp_path / "cert.pfx"))
    (tmp_path / "sonar-analyzer-1.0.0-setup.exe").write_bytes(b"MZ")

    report = check(tmp_path)

    assert report.certificate_configured is True
    assert report.signing_required is True
    assert "imzali olmali" in report.decision


def test_an_empty_certificate_variable_is_not_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boş değişken "yapılandırıldı" sayılmamalı."""
    monkeypatch.setenv(CERT_ENV, "   ")
    assert certificate_configured() is False


# --------------------------------------------------------------------------- #
# ARTEFAKT BULMA
# --------------------------------------------------------------------------- #


def test_both_the_installer_and_the_package_executable_are_checked(tmp_path: Path) -> None:
    (tmp_path / "sonar-analyzer-1.0.0-setup.exe").write_bytes(b"MZ")
    package = tmp_path / "sonar-analyzer-1.0.0"
    package.mkdir()
    (package / "sonar-analyzer.exe").write_bytes(b"MZ")

    names = [path.name for path in find_artifacts(tmp_path)]
    assert names.count("sonar-analyzer.exe") == 1
    assert "sonar-analyzer-1.0.0-setup.exe" in names


def test_an_empty_dist_has_no_artifacts(tmp_path: Path) -> None:
    assert find_artifacts(tmp_path) == []


# --------------------------------------------------------------------------- #
# gercek olcumun kaydi ve ADR
# --------------------------------------------------------------------------- #


def test_the_recorded_check_measured_real_artifacts() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["artifacts"], "hicbir artefakt olculmemis"
    assert payload["certificate_configured"] is False


def test_the_recorded_artifacts_are_actually_unsigned() -> None:
    """Karar tahmin değil ölçüm: Windows doğrulayıcısı ne dedi."""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    statuses = {item["status"] for item in payload["artifacts"]}

    assert statuses == {STATUS_NOT_SIGNED}


def test_the_adr_records_the_unsigned_decision() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "Kod imzalama" in text
    assert "D-17" in text
    assert "imzasız dağıtım" in text


def test_the_adr_records_what_the_decision_costs_the_user() -> None:
    """Bedeli yazılmayan bir karar, bir gün sürpriz olur."""
    text = ADR.read_text(encoding="utf-8")

    assert "SmartScreen" in text
    assert "Sertifika temini uzun sürer" in text
