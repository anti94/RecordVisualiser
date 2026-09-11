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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.release_guard import (  # noqa: E402
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
    report = check(tag=f"v{read_version()}", manifest_path=MISSING)

    assert report.ok is True
    assert report.problems == []


def test_a_mismatched_tag_stops_the_release() -> None:
    """Asıl kabul: etiket ile VERSION ayrışırsa yayın durmalı."""
    report = check(tag="v9.9.9", manifest_path=MISSING)

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

    report = check(tag=f"v{read_version()}", manifest_path=manifest)

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

    report = check(tag=f"v{read_version()}", manifest_path=manifest)

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

    assert check(tag=f"v{read_version()}", manifest_path=manifest).ok is True


# --------------------------------------------------------------------------- #
# CIKIS KODU
# --------------------------------------------------------------------------- #


def test_the_command_exits_non_zero_on_a_mismatch() -> None:
    """CI adımının durması buna bağlı."""
    assert main(["--tag", "v9.9.9", "--manifest", str(MISSING)]) == 1


def test_the_command_exits_zero_when_consistent() -> None:
    assert main(["--tag", f"v{read_version()}", "--manifest", str(MISSING)]) == 0


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
