"""Release ve geri dönüş prosedürü — `F6-032`.

Kabul: **Önceki paket ve kullanıcı ayarlarının geri yükleme adımları
uygulanabilirdir.**

"Uygulanabilir" ölçülebilir bir sözdür: adımlar gerçek installer'larla
yürütülmüş ve sonucu kaydedilmiş olmalıdır. Yazılıp denenmemiş bir geri
dönüş prosedürü, en kötü anda ilk kez denenir.

Testler üç şeye bakar:

1. Prosedürün dayandığı **ürün davranışı** gerçekten böyle mi — ayar
   dosyası kurulum dizininin dışında mı, uygulama ileri şemalı bir ayar
   dosyasını tolere ediyor mu,
2. Kayıtlı prova gerçek mi ve **her adımı** geçmiş mi,
3. Belge, provanın söylediğiyle aynı şeyi mi söylüyor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tools.rollback_check import MARKER_SETTINGS, find_installers

from sonar_analyzer.settings.store import (
    SCHEMA_VERSION,
    SETTINGS_PATH_ENV,
    default_settings_path,
    load_settings,
)

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "release" / "release-and-rollback.md"
REPORT = ROOT / "docs" / "packaging" / "results" / "rollback-check.json"


def _report() -> dict[str, Any]:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# PROSEDURUN DAYANDIGI URUN DAVRANISI
# --------------------------------------------------------------------------- #


def test_settings_live_outside_the_install_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Geri dönüşün tamamı buna dayanır; varsayım olarak bırakılamaz.

    Test takımı kullanıcı yollarını yalıtır, bu yüzden ortamdaki
    `APPDATA` denetlenmez; **kuralın kendisi** denetlenir: ayar dosyası
    `APPDATA` altındaki `SonarAnalyzer` klasöründe durur, kurulumun
    yapıldığı `Programs` ağacında değil.
    """
    monkeypatch.delenv(SETTINGS_PATH_ENV, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    path = default_settings_path()

    assert path == tmp_path / "Roaming" / "SonarAnalyzer" / "settings.json"
    assert "Programs" not in str(path)


def test_the_settings_path_can_be_redirected_for_checks() -> None:
    """Denetimin gerçek kullanıcı ayarlarını bozmaması gerekir."""
    assert SETTINGS_PATH_ENV == "SONAR_ANALYZER_SETTINGS"


def test_a_forward_schema_settings_file_is_tolerated(tmp_path: Path) -> None:
    """Geri dönülen sürüm, yeni sürümün yazdığı dosyayla açılabilmeli."""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(MARKER_SETTINGS, ensure_ascii=False), encoding="utf-8")

    result = load_settings(path)

    assert result.settings is not None
    assert any("daha yeni bir surumden" in warning for warning in result.warnings)


def test_the_forward_schema_marker_is_actually_ahead_of_the_current_schema() -> None:
    """İşaretçi geride kalırsa test hiçbir şeyi sınamaz olurdu."""
    assert int(str(MARKER_SETTINGS["schema_version"])) > SCHEMA_VERSION


def test_unknown_fields_do_not_prevent_loading(tmp_path: Path) -> None:
    """Yeni sürümün eklediği alan, eski sürümü durdurmamalı."""
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "bilinmeyen": {"a": 1}}),
        encoding="utf-8",
    )
    result = load_settings(path)
    assert result.settings is not None


def test_a_corrupt_settings_file_falls_back_to_defaults(tmp_path: Path) -> None:
    """§4.5: yedek yoksa dosya silinir; uygulama yine açılmalı."""
    path = tmp_path / "settings.json"
    path.write_text("{bozuk", encoding="utf-8")
    result = load_settings(path)
    assert result.settings is not None
    assert result.warnings


# --------------------------------------------------------------------------- #
# KAYITLI PROVA
# --------------------------------------------------------------------------- #


def test_the_rehearsal_was_recorded() -> None:
    assert REPORT.is_file()


def test_the_rehearsal_ran_every_step_and_passed() -> None:
    report = _report()
    assert report["step_count"] >= 12
    assert report["failed_count"] == 0
    assert report["ok"] is True


def test_the_rehearsal_used_two_different_real_installers() -> None:
    """Aynı paketten aynı pakete "geri dönmek" hiçbir şey kanıtlamaz."""
    report = _report()
    previous = str(report["previous_installer"])
    current = str(report["current_installer"])
    assert previous != current
    assert previous.endswith("-setup.exe")
    assert current.endswith("-setup.exe")


def test_the_rehearsal_rolled_back_from_a_newer_package_to_an_older_one() -> None:
    """Prova ileri sürümden geriye dönmeli; tersi geri dönüş değildir.

    `VERSION` ile eşitlik yayın kapısının işidir
    (`tools/release_guard.py`); burada aranan, provanın yönüdür.
    """
    report = _report()
    new_version = (
        str(report["current_installer"]).replace("sonar-analyzer-", "").replace("-setup.exe", "")
    )
    old_version = (
        str(report["previous_installer"]).replace("sonar-analyzer-", "").replace("-setup.exe", "")
    )

    def parts(text: str) -> tuple[int, ...]:
        return tuple(int(piece) for piece in text.split("."))

    assert parts(new_version) > parts(old_version)


def test_the_rehearsal_covered_the_settings_survival_step() -> None:
    """Prosedürün dayanağı provada da sınanmış olmalı."""
    names = [str(step["name"]) for step in _report()["steps"]]
    assert any("sağ çıktı" in name for name in names)
    assert any("hâlâ duruyor" in name for name in names)


def test_the_rehearsal_covered_the_forward_schema_risk() -> None:
    names = [str(step["name"]) for step in _report()["steps"]]
    assert any("ayar dosyasıyla açılıyor" in name for name in names)


def test_the_rehearsal_covered_restore_from_backup() -> None:
    names = [str(step["name"]) for step in _report()["steps"]]
    assert any("Yedekten geri yükleme" in name for name in names)


def test_the_rehearsal_verified_a_clean_normal_uninstall() -> None:
    """`_?=` ile yapılan kaldırma iz bırakır; kullanıcının yaptığı bırakmamalı."""
    steps = {str(step["name"]): step for step in _report()["steps"]}
    matching = [name for name in steps if "normal kaldırmada" in name]
    assert matching, "normal kaldirma adimi yok"
    assert steps[matching[0]]["ok"] is True


def test_there_is_a_previous_installer_to_roll_back_to() -> None:
    """Elde önceki paket yoksa prosedürün geri kalanı işe yaramaz."""
    installers = find_installers()
    assert len(installers) >= 2


# --------------------------------------------------------------------------- #
# BELGE ile PROVA AYNI SEYI SOYLUYOR
# --------------------------------------------------------------------------- #


def test_the_document_exists_and_covers_both_procedures() -> None:
    text = _doc()
    assert "Yayın adımları" in text
    assert "Geri dönüş prosedürü" in text


def test_the_document_reports_the_recorded_step_count() -> None:
    report = _report()
    text = _doc()
    assert f"**{report['step_count']} adımın {report['step_count']}'si geçti**" in text or (
        f"{report['step_count']}'si geçti" in text
    )


def test_the_document_names_both_installers_of_the_rehearsal() -> None:
    report = _report()
    text = _doc()
    for installer in (report["previous_installer"], report["current_installer"]):
        version = str(installer).replace("sonar-analyzer-", "").replace("-setup.exe", "")
        assert version in text, version


def test_the_document_gives_concrete_commands_not_advice() -> None:
    """ "Ayarları yedekleyin" bir adım değildir; kopyalanabilir komut lazım."""
    text = _doc()
    assert "settings.json" in text
    assert "--version" in text
    assert "--self-check" in text
    assert "uninstall.exe" in text


def test_the_document_requires_keeping_the_previous_installer() -> None:
    text = _doc()
    assert "önceki sürümün kurulum dosyası saklanır" in text.lower()


def test_the_document_explains_the_forward_schema_risk() -> None:
    text = _doc()
    assert "schema_version" in text
    assert "yok sayar" in text


def test_the_document_states_what_rollback_cannot_undo() -> None:
    """Geri dönüşün veri biçimini geri almadığı yazılmalı."""
    text = _doc()
    assert "kapsamadıkları" in text.lower()
    assert "UnsupportedVersionError" in text


def test_the_document_links_the_raw_evidence() -> None:
    assert "rollback-check.json" in _doc()


def test_the_document_puts_the_rehearsal_before_release() -> None:
    """Geri dönüşü ilk kez gerçek olayda denemek, en kötü anda öğrenmektir."""
    text = _doc()
    assert "rollback_check.py" in text
    assert "yayından önce" in text.lower()
