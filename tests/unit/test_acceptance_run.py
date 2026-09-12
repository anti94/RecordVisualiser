"""Paketli uygulamada kullanıcı kabul turu — `F6-030`.

Kabul: **Operatör ve mühendis akışları kanıtla işaretlenir;
başarısızlıklar ayrı işe dönüşür.**

Kabul turu kendisi de denetlenmelidir: her zaman "geçti" diyen bir tur,
hiç tur yapmamaktan daha kötüdür — geçtiğine dair yanlış bir güven
verir. Bu yüzden testler üç şeye bakar:

1. **Sözleşme önce yazılıyor mu** — her adım beklentisini (çıkış kodu,
   çıktı ifadeleri, üretilecek dosyalar) çalışmadan önce bildiriyor mu,
2. **Başarısızlık yolu gerçekten çalışıyor mu** — uydurma bir sonuçla
   beslendiğinde tur başarısız olabiliyor mu, atlanan adımı geçmiş
   saymıyor mu,
3. **Turun raporu gerçeğe uyuyor mu** — belgedeki sayılar ve başarısız
   adım, kaydedilmiş ham kanıtla aynı mı ve başarısızlık gerçekten ayrı
   bir işe dönüşmüş mü.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from tools.acceptance_run import Step, StepResult, build_steps, run_acceptance, run_step

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "acceptance" / "results" / "packaged-acceptance.json"
DOC = ROOT / "docs" / "acceptance" / "packaged-acceptance.md"
PLAN = ROOT / "plan.md"

#: Ilk turda dusen, ayri ise donusen ve `F6-035` ile kapatilan adim.
ONCE_FAILED_STEP = "M-05"
FOLLOW_UP = "F6-035"


def _report() -> dict[str, object]:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _results() -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", _report()["results"])


# --------------------------------------------------------------------------- #
# ADIMLAR SOZLESMELERINI ONCEDEN BILDIRIYOR
# --------------------------------------------------------------------------- #


def test_both_roles_are_covered() -> None:
    """Tek rolle yürütülen bir tur, diğer rolün beklentisini test etmez."""
    roles = {step.role for step in build_steps(Path("out"))}
    assert roles == {"operator", "engineer"}


def test_each_role_has_more_than_one_step() -> None:
    steps = build_steps(Path("out"))
    for role in ("operator", "engineer"):
        assert len([s for s in steps if s.role == role]) >= 4


def test_every_step_declares_an_expected_exit_code() -> None:
    """Beklentisi olmayan adım, sonucu sonradan uydurmaya açıktır."""
    for step in build_steps(Path("out")):
        assert step.expected_exit in (0, 1), step.step_id


def test_every_step_explains_why_it_matters() -> None:
    """Gerekçesiz bir adım, ilk zorlandığında silinir."""
    for step in build_steps(Path("out")):
        assert len(step.why) >= 60, step.step_id


def test_step_ids_are_unique() -> None:
    ids = [step.step_id for step in build_steps(Path("out"))]
    assert len(ids) == len(set(ids))


def test_some_steps_expect_rejection() -> None:
    """Bozuk verinin reddi bu turda geçme koşuludur; en az bir adım aramalı."""
    rejecting = [step for step in build_steps(Path("out")) if step.expected_exit != 0]
    assert len(rejecting) >= 2
    for step in rejecting:
        assert step.reject_stdout, f"{step.step_id}: ret adimi 'TAMAM' cikitisini dislamali"


def test_steps_that_need_data_declare_their_fixture() -> None:
    for step in build_steps(Path("out")):
        if "--bin-check" in step.argv:
            assert step.needs_fixture, step.step_id
            assert (ROOT / "tests" / "fixtures" / step.needs_fixture).is_file()


# --------------------------------------------------------------------------- #
# BASARISIZLIK YOLU CALISIYOR
# --------------------------------------------------------------------------- #


def test_a_wrong_exit_code_is_reported_as_a_problem(tmp_path: Path) -> None:
    """Beklenen ile gerçek çıkış kodu ayrışırsa adım geçmemeli."""
    step = Step(
        step_id="T-01",
        role="operator",
        title="kasten yanlis beklenti",
        why="x" * 60,
        argv=("--version",),
        expected_exit=99,
    )
    result = run_step(_python_stub(), step, tmp_path)
    assert not result.passed
    assert any("cikis kodu" in problem for problem in result.problems)


def test_a_missing_expected_phrase_is_reported(tmp_path: Path) -> None:
    step = Step(
        step_id="T-02",
        role="operator",
        title="olmayan ifade",
        why="x" * 60,
        argv=("--version",),
        expected_exit=0,
        expect_stdout=("bu ifade asla yazilmaz",),
    )
    result = run_step(_python_stub(), step, tmp_path)
    assert not result.passed


def test_a_missing_artifact_is_reported(tmp_path: Path) -> None:
    """Üretilmeyen dosya sessizce geçilmemeli."""
    step = Step(
        step_id="T-03",
        role="engineer",
        title="uretilmeyen dosya",
        why="x" * 60,
        argv=("--version",),
        expected_exit=0,
        expect_artifacts=("yok/olmayan.csv",),
    )
    result = run_step(_python_stub(), step, tmp_path)
    assert not result.passed
    assert any("uretilmedi" in problem for problem in result.problems)


def test_a_skipped_step_is_not_counted_as_passed() -> None:
    """Atlanan adım da başarısızlıktır; aksi hâlde tur kendini kandırır."""
    skipped = StepResult(
        step_id="T-04",
        role="engineer",
        title="atlandi",
        why="x" * 60,
        command="-",
        expected_exit=0,
        actual_exit=-1,
        duration_s=0.0,
        stdout_tail=[],
        problems=["fixture yok: olmayan.bin"],
    )
    assert not skipped.passed


def test_a_result_with_no_problems_passes() -> None:
    """Karşı yön: sorunsuz adım geçmeli, yoksa test her şeyi reddederdi."""
    clean = StepResult(
        step_id="T-05",
        role="operator",
        title="temiz",
        why="x" * 60,
        command="-",
        expected_exit=0,
        actual_exit=0,
        duration_s=0.1,
        stdout_tail=["sonuc: TAMAM"],
    )
    assert clean.passed


def test_the_runner_reports_not_ok_when_any_step_fails(tmp_path: Path) -> None:
    """Tur, tek bir adım düşse bile 'TAMAM' dememeli."""
    report = run_acceptance(_python_stub(), tmp_path / "out")
    assert report["ok"] is False  # stub gercek uygulama degil; adimlar duser
    assert cast("int", report["failed_count"]) > 0


def _python_stub() -> Path:
    """Gerçek `.exe` yerine kullanılan yorumlayıcı.

    `--version` argümanını kabul eder ve 0 döner; böylece koşucunun
    hata yolları paketli uygulamaya ihtiyaç duymadan sınanabilir.
    """
    import sys

    return Path(sys.executable)


# --------------------------------------------------------------------------- #
# KAYITLI TUR GERCEGE UYUYOR
# --------------------------------------------------------------------------- #


def test_the_recorded_run_exists_and_covers_every_step() -> None:
    assert REPORT.is_file()
    report = _report()
    assert report["step_count"] == len(build_steps(Path("out")))
    assert len(_results()) == report["step_count"]


def test_the_recorded_run_was_made_against_the_packaged_executable() -> None:
    """Kaynak ağacından yürütülen bir tur, paketi kanıtlamaz."""
    executable = str(_report()["executable"])
    assert executable.endswith(".exe")
    assert "dist" in executable


def test_the_recorded_run_is_internally_consistent() -> None:
    """Turun bildirdiği sürüm, çalıştırdığı paketin sürümü olmalı.

    `VERSION` ile eşitlik burada **aranmaz**: geliştirme sırasında sürüm
    kanıtın önüne geçer ve her küçük değişiklikte paketi yeniden üretmek
    boşa iş olurdu. Katı eşitlik yayın anında `tools/release_guard.py`
    tarafından denetlenir — eski bir sürümün kanıtıyla yayın yapmak orada
    durdurulur.
    """
    report = _report()
    version = str(report["version"])
    assert version
    assert f"sonar-analyzer-{version}" in str(report["executable"])


def test_every_recorded_step_carries_its_command_and_expectation() -> None:
    for entry in _results():
        assert entry["command"]
        assert entry["why"]
        assert "expected_exit" in entry and "actual_exit" in entry


def test_successful_data_steps_recorded_artifact_evidence() -> None:
    """ "Yazıldı" demek yetmez; boyut ve özet kaydedilmiş olmalı."""
    seen = 0
    for entry in _results():
        artifacts = cast("list[dict[str, object]]", entry["artifacts"])
        for artifact in artifacts:
            seen += 1
            assert int(cast("int", artifact["bytes"])) > 0
            assert len(str(artifact["sha256"])) == 64
    assert seen, "hicbir adim dosya kaniti birakmamis"


def test_the_recorded_run_has_no_failing_step() -> None:
    """`F6-035` kapandıktan sonra tur tekrarlandı; dokuz adım da geçmeli."""
    failed = [entry["step_id"] for entry in _results() if entry["problems"]]
    assert failed == [], f"dusen adim: {failed}"
    assert _report()["ok"] is True


def test_the_once_failing_step_now_shows_the_flag_it_was_looking_for() -> None:
    """`M-05` "geçti" demesi yetmez; aradığı kanıtı bulmuş olmalı."""
    entry = next(item for item in _results() if item["step_id"] == ONCE_FAILED_STEP)
    joined = "\n".join(cast("list[str]", entry["stdout_tail"]))
    assert "CRC_ERROR" in joined
    assert "isaretli" in joined


def test_the_failure_became_a_separate_work_item() -> None:
    """Kabul kriteri: başarısızlıklar ayrı işe dönüşür.

    İş kapandı ama **kaydı silinmedi**: turun bir kusur bulup
    kapattırdığı, sonradan izlenebilir olmalı.
    """
    plan = PLAN.read_text(encoding="utf-8")
    assert f"`{FOLLOW_UP}`" in plan
    assert "Kalite bayraklarını dışa aktarmaya" in plan
    assert f"`{ONCE_FAILED_STEP}`" in plan  # isin nereden dogdugu yaziyor


def test_the_report_document_keeps_the_history_of_the_finding() -> None:
    """Bulgu kapandı diye silinmemeli; turun ne işe yaradığının kanıtı."""
    text = DOC.read_text(encoding="utf-8")
    assert "İlk koşuda ne oldu" in text
    assert "Kök neden" in text
    assert "K-21" in text


def test_the_report_document_agrees_with_the_recorded_evidence() -> None:
    """Belge ile ham kanıt ayrışırsa hangisinin doğru olduğu belirsizleşir."""
    text = DOC.read_text(encoding="utf-8")
    report = _report()
    assert f"**{report['step_count']}**" in text
    assert f"**{report['passed_count']}**" in text
    assert f"**{report['failed_count']}**" in text
    assert ONCE_FAILED_STEP in text
    assert FOLLOW_UP in text


def test_the_document_states_why_the_defect_was_not_fixed_in_place() -> None:
    """Turun işi kusuru bulmaktır; aynı iş içinde kapatmak yolu denetimsiz bırakırdı."""
    text = DOC.read_text(encoding="utf-8")
    assert "düzeltilmedi" in text
    assert "kök neden" in text.lower()


def test_the_document_records_the_rejection_messages_with_their_offsets() -> None:
    """Ret mesajı nedenini ve konumunu vermeli; 'açılamadı' tek başına yetmez."""
    text = DOC.read_text(encoding="utf-8")
    assert "offset 8" in text
    assert "offset 0" in text
