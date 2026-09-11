"""Bilinen sorunlar ve veri sınırlamaları — `F6-029`.

Kabul: **Her açık sorun etki, iş kimliği ve hedef düzeltme içerir.**

Bu kabul, belgenin *biçimine* dair bir söz değil, içeriğine dair bir
disiplindir: hedef düzeltmesi yazılamayan bir madde henüz anlaşılmamış
demektir, etkisi yazılamayan bir madde ise kullanıcı için anlamsızdır.

Testler bu yüzden üç alanın **her madde için** var olduğunu ve boş
olmadığını denetler; ayrıca maddelerin gerçekten açık olduğunu, yani
iddia ettikleri sınırlamanın kodda hâlâ geçerli olduğunu örnekleyerek
doğrular. Kapanmış bir sorunu listede tutmak, listeyi güvenilmez kılar.
"""

from __future__ import annotations

import re
from pathlib import Path

from sonar_analyzer.ui.actions import MENU_SPECS
from sonar_analyzer.ui.shortcuts import SHORTCUTS

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "release" / "known-issues.md"
OPEN_DECISIONS = ROOT / "docs" / "notes" / "open-decisions.md"
PLAN = ROOT / "plan.md"

REQUIRED_FIELDS = ("**Etki:**", "**İş kimliği:**", "**Hedef düzeltme:**")

#: `### K-01 — Baslik` bicimindeki madde basliklari.
_HEADING = re.compile(r"^### (K-\d{2}) — (.+)$", re.MULTILINE)


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def _issue_blocks() -> dict[str, str]:
    """Her madde kimliği için o maddenin gövdesi."""
    text = _text()
    matches = list(_HEADING.finditer(text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.end() : end]
    return blocks


def _flat() -> str:
    return " ".join(_text().split())


# --------------------------------------------------------------------------- #
# BELGE VAR ve MADDELER AYRISTIRILABILIYOR
# --------------------------------------------------------------------------- #


def test_the_document_exists() -> None:
    assert DOC.is_file()


def test_there_are_issues_to_check() -> None:
    """Boş bir belge her kuralı kâğıt üzerinde geçerdi."""
    assert len(_issue_blocks()) >= 15


def test_issue_ids_are_sequential_and_unique() -> None:
    ids = [match.group(1) for match in _HEADING.finditer(_text())]
    assert len(ids) == len(set(ids)), "tekrarli madde kimligi"
    assert ids == [f"K-{n:02d}" for n in range(1, len(ids) + 1)]


# --------------------------------------------------------------------------- #
# KABUL KRITERI: UC ALAN, HER MADDEDE
# --------------------------------------------------------------------------- #


def test_every_issue_has_all_three_required_fields() -> None:
    missing: list[str] = []
    for issue_id, body in _issue_blocks().items():
        for field in REQUIRED_FIELDS:
            if field not in body:
                missing.append(f"{issue_id}: {field}")
    assert not missing, f"eksik alanlar: {missing}"


def _field(body: str, label: str) -> str:
    """Bir maddedeki `**Etiket:**` alanının içeriği.

    Alan, bir sonraki alan etiketine (satır başındaki `**...:**`) ya da
    gövdenin sonuna kadar uzanır. İçerikteki kalın/kod işaretlemesi
    kesmez — `**Analysis**` ile başlayan bir "Etki" boş sayılmamalı.
    """
    pattern = re.compile(
        re.escape(label) + r"(.*?)(?=\n\*\*(?:Etki|İş kimliği|Hedef düzeltme):\*\*|\Z)",
        re.DOTALL,
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def test_no_required_field_is_left_empty() -> None:
    """Başlığı olup gövdesi olmayan alan, alan sayılmaz.

    Alanların anlamlı uzunluğu farklıdır: "Etki" ve "Hedef düzeltme"
    düzyazıdır ve bir cümleden kısa olamaz; "İş kimliği" tek bir kayıt
    kimliği olabilir (`D-25` gibi) — onun içeriğini ayrıca
    `test_every_issue_cites_at_least_one_tracked_identifier` denetler.
    """
    minimums = {"**Etki:**": 60, "**İş kimliği:**": 4, "**Hedef düzeltme:**": 40}
    too_short: list[str] = []
    for issue_id, body in _issue_blocks().items():
        for field in REQUIRED_FIELDS:
            content = _field(body, field)
            if len(content) < minimums[field]:
                too_short.append(f"{issue_id}: {field} -> {content!r}")
    assert not too_short, f"bos ya da fazla kisa alanlar: {too_short}"


def test_every_issue_cites_at_least_one_tracked_identifier() -> None:
    """ "İş kimliği" satırı gerçek bir iş ya da karar kaydı göstermeli."""
    pattern = re.compile(r"`(F\d-\d{3}|D-\d{2}|E-\d{2}|ADR-\d{3})`")
    for issue_id, body in _issue_blocks().items():
        content = _field(body, "**İş kimliği:**")
        assert pattern.search(content), f"{issue_id}: izlenebilir kimlik yok ({content!r})"


def test_every_cited_decision_id_exists_in_the_decision_log() -> None:
    """Var olmayan bir karar kimliğine atıf, izlenebilirlik yanılsamasıdır."""
    decisions = OPEN_DECISIONS.read_text(encoding="utf-8")
    cited = set(re.findall(r"`(D-\d{2})`", _text()))
    assert cited, "hic karar kimligi anilmamis"
    for decision in sorted(cited):
        assert f"| {decision} |" in decisions, f"{decision} open-decisions.md'de yok"


def test_every_cited_work_id_exists_in_the_plan() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    cited = set(re.findall(r"`(F\d-\d{3})`", _text()))
    assert cited
    for work_id in sorted(cited):
        assert f"`{work_id}`" in plan, f"{work_id} plan.md'de yok"


def test_every_issue_is_listed_in_the_summary_table() -> None:
    """Özet tablo ile gövde ayrışırsa okuyucu maddeyi kaçırır."""
    text = _text()
    for issue_id in _issue_blocks():
        assert f"| `{issue_id}` |" in text, f"{issue_id} ozet tabloda yok"


def test_the_declared_total_matches_the_actual_count() -> None:
    count = len(_issue_blocks())
    assert f"Toplam açık madde: **{count}**" in _text()


# --------------------------------------------------------------------------- #
# MADDELER GERCEKTEN ACIK MI
# --------------------------------------------------------------------------- #


def test_k08_the_analysis_menu_really_is_permanently_disabled() -> None:
    """Menü eylemleri gerçekten pasif ve hiçbir yerde etkinleştirilmiyor."""
    analysis = next(menu for menu in MENU_SPECS if menu.name == "menu_analysis")
    names = {spec.name for spec in analysis.actions}
    assert names == {"action_fft", "action_spectrogram", "action_filter", "action_statistics"}
    assert all(not spec.enabled for spec in analysis.actions)

    sources = (ROOT / "src" / "sonar_analyzer").rglob("*.py")
    referenced = [
        path.name
        for path in sources
        if path.name != "actions.py" and "action_fft" in path.read_text(encoding="utf-8")
    ]
    assert not referenced, f"action_fft baska yerde kullaniliyor: {referenced}"


def test_k09_the_diagnostics_action_really_is_unwired() -> None:
    """Tanılama paketi kodu var ama menüden erişilemiyor."""
    assert (ROOT / "src" / "sonar_analyzer" / "application" / "diagnostics_export.py").is_file()
    tools = next(menu for menu in MENU_SPECS if menu.name == "menu_tools")
    diagnostics = next(spec for spec in tools.actions if spec.name == "action_diagnostics")
    assert not diagnostics.enabled

    ui_files = (ROOT / "src" / "sonar_analyzer" / "ui").rglob("*.py")
    referenced = [
        path.name
        for path in ui_files
        if path.name != "actions.py" and "action_diagnostics" in path.read_text(encoding="utf-8")
    ]
    assert not referenced, f"action_diagnostics baglanmis: {referenced}"


def test_k10_the_command_palette_shortcut_really_is_absent() -> None:
    bound = {spec.shortcut for menu in MENU_SPECS for spec in menu.actions if spec.shortcut}
    bound |= {spec.key for spec in SHORTCUTS}
    assert "Ctrl+K" not in bound


def test_k16_the_distribution_really_is_unsigned() -> None:
    """İmzasız dağıtım kararı kayıtlı olmalı; iddia dosyaya dayanmalı."""
    import json

    report = ROOT / "docs" / "packaging" / "results" / "signing-check.json"
    assert report.is_file()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["signing_required"] is False
    assert data["certificate_configured"] is False
    assert "SmartScreen" in _text()


def test_k19_the_repository_really_targets_python_39() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.9"' in pyproject
    assert "3.9" in _text()


def test_k20_the_dependency_findings_are_reported_with_their_real_counts() -> None:
    """Sayılar rapordan gelmeli; "birkaç bulgu" denmesi denetlenemezdi."""
    import json

    from tools.dependency_scan import SHIPPED_PACKAGES

    report = ROOT / "docs" / "packaging" / "results" / "dependency-scan.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    findings = data["findings"]

    flat = _flat()
    assert f"{data['packages_scanned']} pakette" in flat
    assert f"**{len(findings)} bulgu**" in flat

    # Iddianin kendisi: hicbiri kullaniciya sevk edilen pakette degil.
    shipped = [f["package"] for f in findings if f["package"].strip().lower() in SHIPPED_PACKAGES]
    assert not shipped, f"sevk edilen pakette bulgu var: {shipped}"
    assert "sevk edilen pakette 0 bulgu" in flat


# --------------------------------------------------------------------------- #
# BELGENIN KENDI DISIPLINI
# --------------------------------------------------------------------------- #


def test_the_document_states_why_each_field_is_required() -> None:
    flat = _flat()
    assert "Etki" in flat and "İş kimliği" in flat and "Hedef düzeltme" in flat
    assert "hata sanmasına" in flat


def test_the_update_rule_is_stated() -> None:
    """Kapanan maddenin çıkarılacağı yazılmazsa liste zamanla çürür."""
    flat = _flat()
    assert "Güncelleme kuralı" in flat
    assert "çıkarılır" in flat


def test_the_document_points_at_the_full_decision_log() -> None:
    text = _text()
    assert "open-decisions.md" in text
    assert "inventory.md" in text


def test_the_severity_column_uses_only_known_levels() -> None:
    severities = set(re.findall(r"\| `K-\d{2}` \| [^|]+ \| \*{0,2}([^|*]+?)\*{0,2} \|", _text()))
    assert severities <= {"Yüksek", "Orta", "Düşük"}, severities
