"""CI iş akışının kapıları — `F6-016`.

Kabul: **Build ve paketli açılış sonucu workflow artefaktına yazılır.**

Bir iş akışı dosyası sessizce bozulabilir: bir adım silinir, bir koşul
`if: always()` olmaktan çıkar, artefakt yolu yanlış yazılır. Hiçbiri
testi kırmaz ama kapı çalışmaz hâle gelir. Bu testler akışın **sözünü**
sabitler.

En önemlisi artefaktın **başarısız koşuda da** yüklenmesidir: "neden
bozuldu" sorusu ancak build logu ve raporlarla cevaplanabilir ve bunlar
tam da işin kaldığı koşuda gerekir.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _package_job() -> str:
    """Paket smoke işinin gövdesi."""
    text = _text()
    start = text.index("  package-smoke:")
    end = text.index("  todo-sync:")
    return text[start:end]


# --------------------------------------------------------------------------- #
# PAKET SMOKE ISI
# --------------------------------------------------------------------------- #


def test_the_workflow_exists() -> None:
    assert WORKFLOW.is_file()


def test_a_package_smoke_job_exists() -> None:
    assert "package-smoke:" in _text()


def test_the_package_is_actually_built() -> None:
    assert "tools/build_package.py" in _package_job()


def test_the_packaged_application_is_actually_opened() -> None:
    """Üretmek yetmez; paketin açıldığı görülmeli (`F6-005`)."""
    assert "tools/clean_env_check.py" in _package_job()


def test_the_release_manifest_is_produced() -> None:
    assert "tools/release_manifest.py" in _package_job()


def test_the_package_job_runs_on_windows() -> None:
    """Windows paketi Windows'ta üretilmeli."""
    assert "runs-on: windows-latest" in _package_job()


# --------------------------------------------------------------------------- #
# ARTEFAKT: basarisiz kosuda DA yuklenir
# --------------------------------------------------------------------------- #


def test_the_results_are_uploaded_as_an_artifact() -> None:
    assert "upload-artifact" in _package_job()


def test_the_artifact_is_uploaded_even_when_the_job_fails() -> None:
    """Asıl mesele bu: log en çok başarısız koşuda gerekir."""
    job = _package_job()
    upload_index = job.index("upload-artifact")
    before = job[:upload_index]

    assert "if: always()" in before[-200:], "artefakt yalniz basarili kosuda yukleniyor"


def test_the_build_log_is_among_the_uploaded_files() -> None:
    job = _package_job()
    assert "dist/build.log" in job


def test_the_manifests_are_among_the_uploaded_files() -> None:
    job = _package_job()
    assert "dist/build-manifest.json" in job
    assert "dist/release-manifest.json" in job


def test_the_clean_environment_result_is_uploaded() -> None:
    """Paketli açılışın sonucu da artefakta girer (kabul kriteri)."""
    assert "clean-env-check.json" in _package_job()


# --------------------------------------------------------------------------- #
# KALITE KAPILARI yerinde duruyor
# --------------------------------------------------------------------------- #


def test_the_quality_gates_are_still_wired() -> None:
    """Paketleme eklenirken mevcut kapılar düşmemeli."""
    text = _text()

    assert "ruff check" in text
    assert "ruff format --check" in text
    assert "pyright" in text
    assert "pytest" in text


def test_the_coverage_and_scan_gates_are_wired() -> None:
    text = _text()

    assert "tools/coverage_gate.py" in text
    assert "tools/dependency_scan.py" in text
    assert "tools/perf_smoke.py" in text


def test_the_todo_sync_check_is_still_wired() -> None:
    assert "sync_todo.py --check" in _text()
