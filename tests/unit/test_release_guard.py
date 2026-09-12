"""Yayın sürüm kapısı — `F6-017`.

Kabul: **Sürüm etiketiyle VERSION uyuşmazsa yayın adımı durur.**

Bir sürüm yayınlanırken etiket, `VERSION` ve artefaktlar aynı sürümü
söylemelidir. Ayrıştıklarında en kötü biçimde ayrışırlar: `v3.17.0`
etiketiyle yayınlanan paketin içinden `3.16.0` çıkar, kullanıcı yanlış
sürümü kurar ve hata raporu yanlış sürüme yazılır.

Testler kapının **gerçekten durdurduğunu** gösterir. Bir kapının en
tehlikeli hâli her şeyi geçirmesidir; bu yüzden buradaki testlerin çoğu
uyuşmazlık kurup çıkışın sıfırdan farklı olduğunu doğrular.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.release_guard import (  # noqa: E402
    PACKAGED_EVIDENCE,
    check,
    main,
    read_version,
    version_from_tag,
)

WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
MISSING = ROOT / "dist" / "kesinlikle-yok.json"


# --------------------------------------------------------------------------- #
# ETIKET -> SURUM
# --------------------------------------------------------------------------- #


def test_a_v_prefixed_tag_yields_its_version() -> None:
    assert version_from_tag("v3.17.0") == "3.17.0"


def test_a_tag_without_the_prefix_is_used_as_is() -> None:
    assert version_from_tag("3.17.0") == "3.17.0"


def test_surrounding_whitespace_is_ignored() -> None:
    assert version_from_tag("  v3.17.0\n") == "3.17.0"


# --------------------------------------------------------------------------- #
# KAPI DURDURUR
# --------------------------------------------------------------------------- #


def test_a_matching_tag_passes() -> None:
    report = check(tag=f"v{read_version()}", manifest_path=MISSING, evidence=())

    assert report.ok is True
    assert report.problems == []


def test_a_mismatched_tag_stops_the_release() -> None:
    """Asıl kabul: etiket ile VERSION ayrışırsa yayın durmalı."""
    report = check(tag="v9.9.9", manifest_path=MISSING, evidence=())

    assert report.ok is False
    assert any("ayni degil" in problem for problem in report.problems)


def test_a_release_without_a_tag_stops() -> None:
    """Etiketsiz bir commit'ten sürüm yayınlanmaz."""
    report = check(tag="", manifest_path=MISSING)

    # HEAD'de etiket olabilir; yoksa problem bildirilmeli.
    if not report.tag:
        assert report.ok is False
        assert any("etiketi yok" in problem for problem in report.problems)


def test_a_mismatched_manifest_stops_the_release(tmp_path: Path) -> None:
    """Etiket doğru olsa bile üretilen paket başka sürümse durmalı."""
    manifest = tmp_path / "release-manifest.json"
    manifest.write_text(json.dumps({"version": "1.2.3", "artifacts": []}), encoding="utf-8")

    report = check(tag=f"v{read_version()}", manifest_path=manifest, evidence=())

    assert report.ok is False
    assert any("Manifest surumu" in problem for problem in report.problems)


def test_an_inconsistent_artifact_stops_the_release(tmp_path: Path) -> None:
    """`F6-009`'un tutarsız bulduğu artefakt yayınlanmamalı."""
    manifest = tmp_path / "release-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": read_version(),
                "artifacts": [{"name": "kotu.exe", "consistent": False}],
            }
        ),
        encoding="utf-8",
    )

    report = check(tag=f"v{read_version()}", manifest_path=manifest, evidence=())

    assert report.ok is False
    assert any("Tutarsiz artefakt" in problem for problem in report.problems)


def test_a_fully_consistent_release_passes(tmp_path: Path) -> None:
    manifest = tmp_path / "release-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": read_version(),
                "artifacts": [{"name": "iyi.exe", "consistent": True}],
            }
        ),
        encoding="utf-8",
    )

    assert check(tag=f"v{read_version()}", manifest_path=manifest, evidence=()).ok is True


# --------------------------------------------------------------------------- #
# CIKIS KODU
# --------------------------------------------------------------------------- #


def test_the_command_exits_non_zero_on_a_mismatch() -> None:
    """CI adımının durması buna bağlı."""
    assert main(["--tag", "v9.9.9", "--manifest", str(MISSING)]) == 1


def test_the_command_exit_code_follows_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    """Çıkış kodu raporun kararını izlemeli; CI adımı buna bakar.

    Komut, depo içindeki **gerçek** kanıt dosyalarını okur. Geliştirme
    sırasında `VERSION` kanıtın önüne geçmiş olabilir; o durumda kapı
    doğru davranıp durur. Bu yüzden test sabit bir çıkış kodu beklemez,
    rapor ile çıkış kodunun **aynı şeyi söylediğini** doğrular.
    """
    expected_ok = check(tag=f"v{read_version()}", manifest_path=MISSING).ok
    code = main(["--tag", f"v{read_version()}", "--manifest", str(MISSING)])

    assert code == (0 if expected_ok else 1)
    if not expected_ok:
        # Durduran kapi NEDENINI yazmali; sessiz bir 1 is gormez.
        assert "HATA:" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# YAYIN IS AKISI
# --------------------------------------------------------------------------- #


def test_the_release_workflow_exists() -> None:
    assert WORKFLOW.is_file()


def test_the_release_workflow_is_triggered_by_version_tags() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'tags: ["v*"]' in text


def test_the_guard_runs_before_anything_is_built() -> None:
    """Kapı üretimden önce koşmalı; yoksa yanlış sürüm zaten üretilmiş olur."""
    text = WORKFLOW.read_text(encoding="utf-8")
    guard_index = text.index("release_guard.py")
    build_index = text.index("build_package.py")

    assert guard_index < build_index


def test_the_guard_runs_again_after_the_artifacts_exist() -> None:
    """İkinci geçiş üretilen paketin gerçekten o sürüm olduğunu doğrular."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count("release_guard.py") >= 2
    assert "dist/release-manifest.json" in text


def test_the_release_workflow_checks_signing() -> None:
    assert "signing_check.py" in WORKFLOW.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# PAKETLI DENETIM KANITI YAYINLANAN SURUMLE AYNI MI
# --------------------------------------------------------------------------- #


def _evidence(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_evidence_from_the_released_version_passes(tmp_path: Path) -> None:
    """Karşı yön: güncel kanıtla yayın durdurulmamalı."""
    version = read_version()
    evidence = (
        ("kabul turu", _evidence(tmp_path, "a.json", {"version": version, "ok": True})),
        ("mockup", _evidence(tmp_path, "m.json", {"version": version, "ok": True})),
    )

    report = check(tag=f"v{version}", manifest_path=MISSING, evidence=evidence)

    assert report.ok is True


def test_stale_evidence_stops_the_release(tmp_path: Path) -> None:
    """Asıl kabul: eski sürümün kanıtıyla yayın yapılamaz.

    Kabul edilen şeyin ne olduğu belirsizleşir: kullanıcı 4.1.0 kurar,
    kabul turu 4.0.0'da koşmuştur.
    """
    version = read_version()
    evidence = (("kabul turu", _evidence(tmp_path, "a.json", {"version": "0.0.1", "ok": True})),)

    report = check(tag=f"v{version}", manifest_path=MISSING, evidence=evidence)

    assert report.ok is False
    assert any("0.0.1" in problem and "kabul turu" in problem for problem in report.problems)


def test_a_failed_check_stops_the_release(tmp_path: Path) -> None:
    """Kanıt güncel ama denetim düşmüşse de yayın durmalı."""
    version = read_version()
    evidence = (("kabul turu", _evidence(tmp_path, "a.json", {"version": version, "ok": False})),)

    report = check(tag=f"v{version}", manifest_path=MISSING, evidence=evidence)

    assert report.ok is False
    assert any("basarisiz" in problem for problem in report.problems)


def test_missing_evidence_stops_the_release(tmp_path: Path) -> None:
    """Kanıt dosyası yoksa "denetim geçti" sayılamaz."""
    evidence = (("kabul turu", tmp_path / "hic-yok.json"),)

    report = check(tag=f"v{read_version()}", manifest_path=MISSING, evidence=evidence)

    assert report.ok is False
    assert any("kaniti yok" in problem for problem in report.problems)


def test_the_rollback_evidence_version_comes_from_the_installer_name(tmp_path: Path) -> None:
    """Geri dönüş provası sürümü doğrudan yazmaz; installer adından okunur."""
    version = read_version()
    payload: dict[str, object] = {
        "current_installer": f"sonar-analyzer-{version}-setup.exe",
        "previous_installer": "sonar-analyzer-3.8.0-setup.exe",
        "ok": True,
    }
    evidence = (("geri donus provasi", _evidence(tmp_path, "r.json", payload)),)

    report = check(tag=f"v{version}", manifest_path=MISSING, evidence=evidence)

    assert report.ok is True


def test_the_guard_watches_all_three_packaged_checks() -> None:
    """Biri unutulursa, o denetim eskimiş kanıtla yayına girebilirdi."""
    labels = [label for label, _path in PACKAGED_EVIDENCE]

    assert len(PACKAGED_EVIDENCE) == 3
    assert any("kabul" in label for label in labels)
    assert any("mockup" in label for label in labels)
    assert any("geri donus" in label for label in labels)
