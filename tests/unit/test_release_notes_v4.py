"""Major sürüm notları ve milestone özeti — `F6-033`.

Kabul: **Kapsam, kontroller, bilinen sorunlar ve artefaktlar
tutarlıdır.**

Sürüm notlarının tehlikesi yanlış olmaları değil, **eskimeleridir**:
kapsam büyür, bir kontrol kaldırılır, bir sorun kapanır — belge yerinde
kalır. Okuyan kişi bunu anlayamaz, çünkü belgeye bakarak doğrulayacağı
bir şey yoktur.

Bu yüzden testler dört tutarlılığı ayrı ayrı denetler:

1. **Kapsam** — notlarda anılan her iş `plan.md`'de var ve tamamlanmış,
2. **Kontroller** — anılan her araç dosya olarak var, her kanıt dosyası
   gerçekten üretilmiş,
3. **Bilinen sorunlar** — anılan her `K-xx` maddesi
   `known-issues.md`'de var ve sayılar uyuşuyor,
4. **Artefaktlar** — manifestteki dosyalar gerçekten üretilmiş ve
   sürümleri belgeyle aynı.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "docs" / "release" / "release-notes-v4.0.0.md"
MILESTONE = ROOT / "docs" / "release" / "ms-07-distribution.md"
KNOWN_ISSUES = ROOT / "docs" / "release" / "known-issues.md"
PLAN = ROOT / "plan.md"
RESULTS = ROOT / "docs" / "packaging" / "results"


def _notes() -> str:
    return NOTES.read_text(encoding="utf-8")


def _milestone() -> str:
    return MILESTONE.read_text(encoding="utf-8")


def _both() -> str:
    return _notes() + "\n" + _milestone()


def _json(name: str) -> dict[str, Any]:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# BELGELER VAR
# --------------------------------------------------------------------------- #


def test_both_documents_exist() -> None:
    assert NOTES.is_file()
    assert MILESTONE.is_file()


def test_the_notes_declare_the_major_version_and_its_reason() -> None:
    """Major sürüm bir şeyin kırıldığını ima eder; nedeni yazılmalı."""
    text = _notes()
    assert "v4.0.0" in text
    assert "dağıtım biçimi değişti" in text


# --------------------------------------------------------------------------- #
# 1. KAPSAM TUTARLILIGI
# --------------------------------------------------------------------------- #


def test_every_cited_work_item_exists_in_the_plan() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    cited = set(re.findall(r"`(F\d-\d{3})`", _both()))
    assert cited, "hic is kimligi anilmamis"
    for work_id in sorted(cited):
        assert f"`{work_id}`" in plan, f"{work_id} plan.md'de yok"


def test_every_cited_phase6_item_except_the_open_ones_is_done() -> None:
    """Tamamlanmamış bir işi başarı olarak saymak, notları yanlış yapar."""
    plan = PLAN.read_text(encoding="utf-8")
    done: set[str] = set()
    for line in plan.splitlines():
        match = re.match(r"^\| \[x\] \| `(F6-\d{3})`", line.strip())
        if match:
            done.add(match.group(1))

    cited = {item for item in re.findall(r"`(F6-\d{3})`", _both())}
    # F6-034 (milestone kapanisi) ve F6-035 (kabul turundan dogan is) acik.
    still_open = {"F6-034", "F6-035"}
    for work_id in sorted(cited - still_open):
        assert work_id in done, f"{work_id} tamamlanmamis ama basari olarak aniliyor"


def test_the_open_items_are_described_as_open_not_delivered() -> None:
    text = _both()
    assert "F6-035" in text
    assert "açık iştir" in text or "ayrı işe dönüştürüldü" in text


def test_the_declared_work_count_matches_the_plan() -> None:
    """34 iş iddiası sayılabilir olmalı."""
    plan = PLAN.read_text(encoding="utf-8")
    numbered = {
        match.group(1)
        for line in plan.splitlines()
        if (match := re.match(r"^\| \[[ x]\] \| `(F6-0(?:0\d|1\d|2\d|3[0-4]))`", line.strip()))
    }
    assert len(numbered) == 34
    assert "34" in _both()


# --------------------------------------------------------------------------- #
# 2. KONTROL TUTARLILIGI
# --------------------------------------------------------------------------- #


def test_every_cited_tool_exists() -> None:
    """Var olmayan bir aracı anmak, yapılmamış bir kontrolü ima eder."""
    cited = set(re.findall(r"`(tools/[a-z_]+\.py)`", _both()))
    assert len(cited) >= 8
    for tool in sorted(cited):
        assert (ROOT / tool).is_file(), f"{tool} yok"


def test_every_cited_evidence_file_exists() -> None:
    cited = set(re.findall(r"`(docs/[a-z0-9/_\-]+\.(?:json|md))`", _both()))
    assert len(cited) >= 8
    for evidence in sorted(cited):
        assert (ROOT / evidence).is_file(), f"{evidence} yok"


def test_the_packaged_checks_are_described_as_running_on_the_package() -> None:
    """Kaynak ağacından çalıştırmak paketi kanıtlamaz; bu ayrım yazılmalı."""
    text = _notes()
    assert "paketli `.exe` üzerinde" in text
    assert "Kaynak ağacından çalıştırmak paketi kanıtlamaz" in text


def test_the_coverage_numbers_match_the_recorded_gate() -> None:
    data = _json("coverage-gate.json")
    overall = data["overall"]
    text = _milestone()
    assert f"%{overall['percent']:.1f}".replace(".", ",") in text
    assert overall["percent"] >= overall["threshold"]


def test_the_reproducibility_claim_matches_the_recorded_comparison() -> None:
    """ "291 dosyanın 289'u aynı" iddiası rapordan gelmeli."""
    data = _json("build-reproducibility.json")
    text = _milestone()
    assert str(data["total_files"]) in text
    assert str(data["identical_files"]) in text
    for difference in data["differences"]:
        assert difference["expected"] is True, difference["path"]


def test_the_dependency_scan_claim_matches_the_recorded_findings() -> None:
    data = _json("dependency-scan.json")
    assert f"{len(data['findings'])} bulgu" in _milestone()


def test_the_acceptance_result_matches_the_recorded_run() -> None:
    report = json.loads(
        (ROOT / "docs" / "acceptance" / "results" / "packaged-acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    text = _both()
    assert f"{report['passed_count']}/{report['step_count']}" in text or (
        f"{report['step_count']} adımdan {report['passed_count']}'ini geçti" in text
    )
    assert report["failed_count"] == 1
    assert "M-05" in text


def test_the_mockup_result_matches_the_recorded_comparison() -> None:
    report = json.loads(
        (ROOT / "docs" / "ui" / "results" / "packaged-mockup-comparison.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["failed_count"] == 0
    assert f"{report['passed_count']}/{report['check_count']}" in _milestone()


def test_the_rollback_result_matches_the_recorded_rehearsal() -> None:
    data = _json("rollback-check.json")
    text = _both()
    assert data["failed_count"] == 0
    assert f"{data['step_count']}/{data['step_count']}" in text or (
        f"{data['step_count']} adımın tamamı" in text
    )


# --------------------------------------------------------------------------- #
# 3. BILINEN SORUN TUTARLILIGI
# --------------------------------------------------------------------------- #


def test_every_cited_known_issue_exists() -> None:
    issues = KNOWN_ISSUES.read_text(encoding="utf-8")
    cited = set(re.findall(r"`(K-\d{2})`", _both()))
    assert len(cited) >= 6
    for issue in sorted(cited):
        assert f"### {issue} —" in issues, f"{issue} known-issues.md'de yok"


def test_the_declared_issue_count_matches_the_issue_document() -> None:
    issues = KNOWN_ISSUES.read_text(encoding="utf-8")
    count = len(re.findall(r"^### K-\d{2} —", issues, re.MULTILINE))
    assert f"**{count} açık madde**" in _notes()
    assert f"{count} açık madde" in _milestone()


def test_the_unsigned_distribution_is_stated_in_the_notes() -> None:
    """Kullanıcı SmartScreen uyarısıyla karşılaşacak; sürpriz olmamalı."""
    text = _notes()
    assert "SmartScreen" in text
    assert "K-16" in text


def test_the_failed_acceptance_step_is_not_hidden_in_the_notes() -> None:
    text = _notes()
    assert "M-05" in text
    assert "gizlenmedi" in text


# --------------------------------------------------------------------------- #
# 4. ARTEFAKT TUTARLILIGI
# --------------------------------------------------------------------------- #


def test_the_release_manifest_matches_the_current_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifest = _json("release-manifest.json")
    assert manifest["version"] == version


def test_every_manifest_artifact_was_actually_produced() -> None:
    """Manifest, üretilmemiş bir artefaktı listelememeli."""
    manifest = _json("release-manifest.json")
    entries = manifest["artifacts"]
    assert entries, "manifest bos"
    version = str(manifest["version"])
    for entry in entries:
        assert int(entry["size_bytes"]) > 0, entry["name"]
        assert len(str(entry["sha256"])) == 64, entry["name"]
        # Ad ile icerikteki surum ayrisirsa yanlis paket yayinlanabilir.
        assert entry["consistent"] is True, entry["name"]
        assert entry["version_in_name"] == version, entry["name"]


def test_the_manifest_covers_both_the_installer_and_the_package() -> None:
    kinds = {str(entry["kind"]) for entry in _json("release-manifest.json")["artifacts"]}
    assert {"installer", "package"} <= kinds


def test_the_notes_name_the_installer_artifact() -> None:
    assert "sonar-analyzer-4.0.0-setup.exe" in _notes()


# --------------------------------------------------------------------------- #
# MILESTONE TUTANAGININ DURUSTLUGU
# --------------------------------------------------------------------------- #


def test_the_milestone_lists_what_was_not_verified() -> None:
    """Bir milestone'un en tehlikeli yanı, doğrulanmamışı doğrulanmış saymaktır."""
    text = _milestone()
    assert "doğrulanmayan maddeler" in text
    rows = re.findall(r"^\| \d+ \| ", text, re.MULTILINE)
    assert len(rows) >= 8, "kapsam disi listesi fazla kisa"


def test_the_milestone_states_synthetic_data_is_not_hardware_proof() -> None:
    text = _milestone()
    assert "Sentetik veri gerçek donanım doğrulaması sayılmaz" in text


def test_the_milestone_covers_all_four_acceptance_headings() -> None:
    text = _milestone()
    for heading in ("Kurulum", "Mockup kabulü", "Kalite kapıları", "Yayın belgeleri"):
        assert heading in text, heading


def test_the_milestone_marks_partial_results_as_partial() -> None:
    """Yeniden üretilebilirlik tam değil; "TAMAM" demek yanlış olurdu."""
    text = _milestone()
    assert "KISMİ" in text
    assert "YAPILMADI" in text
