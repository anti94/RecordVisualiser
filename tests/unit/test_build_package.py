"""Tek komutluk paket üretim akışı — `F6-004`.

Kabul: **Komut sürümlü çıktı klasörü ve build logu üretir.**

Gerçek PyInstaller koşusu dakikalar sürer ve akışın kendisini sınamak için
gerekmez; bu yüzden koşucu enjekte edilir ve asıl sorular sorulur:

* çıktı klasörü **sürümü taşıyor** mu (iki sürüm birbirini ezmemeli),
* log **her durumda** yazılıyor mu — özellikle başarısız koşuda, çünkü
  "neden bozuldu" sorusu ancak o zaman cevaplanabilir,
* manifest üretimde rol alan araç sürümlerini kaydediyor mu (`F6-010`
  hash farklarını bunlarla açıklayacak).

Gerçek bir paket üretimi ayrıca yapıldı; sonucu
`docs/packaging/results/packaging-spike.json` içindedir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_package import (  # noqa: E402
    BUILD_LOG_NAME,
    MANIFEST_NAME,
    build,
    measure_output,
    read_version,
    tool_versions,
)


def _fake_success(output_dir: Path, text: str = "PyInstaller: tamam\n"):
    """Paket üretmiş gibi davranan koşucu."""

    def runner(_command: list[str]) -> tuple[int, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "sonar-analyzer.exe").write_bytes(b"MZ sahte")
        (output_dir / "_internal").mkdir(exist_ok=True)
        (output_dir / "_internal" / "VERSION").write_text("x", encoding="utf-8")
        return (0, text)

    return runner


def _fake_failure(text: str = "PyInstaller: HATA\n"):
    def runner(_command: list[str]) -> tuple[int, str]:
        return (1, text)

    return runner


# --------------------------------------------------------------------------- #
# SURUMLU CIKTI KLASORU
# --------------------------------------------------------------------------- #


def test_the_output_folder_carries_the_version(tmp_path: Path) -> None:
    version = read_version()
    target = tmp_path / f"sonar-analyzer-{version}"
    result = build(dist_root=tmp_path, work_root=tmp_path / "w", runner=_fake_success(target))

    assert result.version == version
    assert Path(result.output_dir).name == f"sonar-analyzer-{version}"
    assert Path(result.output_dir).is_dir()


def test_two_versions_do_not_overwrite_each_other(tmp_path: Path) -> None:
    """Sürümlü klasörün asıl gerekçesi: eski paket kaybolmamalı."""
    older = tmp_path / "sonar-analyzer-1.0.0"
    older.mkdir(parents=True)
    (older / "eski.txt").write_text("kalmali", encoding="utf-8")

    target = tmp_path / f"sonar-analyzer-{read_version()}"
    build(dist_root=tmp_path, work_root=tmp_path / "w", runner=_fake_success(target))

    assert (older / "eski.txt").read_text(encoding="utf-8") == "kalmali"


def test_clean_removes_only_the_current_version(tmp_path: Path) -> None:
    version = read_version()
    target = tmp_path / f"sonar-analyzer-{version}"
    target.mkdir(parents=True)
    (target / "artik.txt").write_text("silinmeli", encoding="utf-8")
    older = tmp_path / "sonar-analyzer-0.1.0"
    older.mkdir(parents=True)
    (older / "kalan.txt").write_text("kalmali", encoding="utf-8")

    build(dist_root=tmp_path, work_root=tmp_path / "w", clean=True, runner=_fake_success(target))

    assert not (target / "artik.txt").exists()
    assert (older / "kalan.txt").exists()


# --------------------------------------------------------------------------- #
# BUILD LOGU
# --------------------------------------------------------------------------- #


def test_the_build_log_is_written(tmp_path: Path) -> None:
    target = tmp_path / f"sonar-analyzer-{read_version()}"
    build(
        dist_root=tmp_path,
        work_root=tmp_path / "w",
        runner=_fake_success(target, "satir bir\nsatir iki\n"),
    )

    log = tmp_path / BUILD_LOG_NAME
    assert log.is_file()
    assert "satir bir" in log.read_text(encoding="utf-8")


def test_a_failed_build_still_writes_its_log(tmp_path: Path) -> None:
    """Başarısız koşu kaydedilmezse "neden bozuldu" sorusu cevapsız kalır."""
    result = build(dist_root=tmp_path, work_root=tmp_path / "w", runner=_fake_failure())

    assert result.succeeded is False
    assert result.exit_code == 1
    assert (tmp_path / BUILD_LOG_NAME).read_text(encoding="utf-8").strip() == "PyInstaller: HATA"


def test_a_failure_is_not_reported_as_success(tmp_path: Path) -> None:
    """Çıkış kodu sıfır olsa bile klasör yoksa üretim başarılı sayılmaz."""

    def runner(_command: list[str]) -> tuple[int, str]:
        return (0, "hicbir sey uretmedim")

    result = build(dist_root=tmp_path, work_root=tmp_path / "w", runner=runner)
    assert result.succeeded is False


# --------------------------------------------------------------------------- #
# MANIFEST
# --------------------------------------------------------------------------- #


def test_the_manifest_records_the_run(tmp_path: Path) -> None:
    target = tmp_path / f"sonar-analyzer-{read_version()}"
    build(dist_root=tmp_path, work_root=tmp_path / "w", runner=_fake_success(target))

    payload = json.loads((tmp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert payload["version"] == read_version()
    assert payload["succeeded"] is True
    assert payload["file_count"] >= 1
    assert payload["total_bytes"] > 0


def test_the_manifest_records_the_tool_versions(tmp_path: Path) -> None:
    """`F6-010` hash farklarını bu sürümlerle açıklayacak."""
    target = tmp_path / f"sonar-analyzer-{read_version()}"
    build(dist_root=tmp_path, work_root=tmp_path / "w", runner=_fake_success(target))

    payload = json.loads((tmp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert payload["tools"]["python"]
    assert payload["tools"]["pyinstaller"]


def test_the_manifest_is_written_for_a_failed_run_too(tmp_path: Path) -> None:
    build(dist_root=tmp_path, work_root=tmp_path / "w", runner=_fake_failure())

    payload = json.loads((tmp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert payload["succeeded"] is False
    assert payload["exit_code"] == 1


def test_the_tool_versions_are_real() -> None:
    versions = tool_versions()
    assert versions["python"].startswith("3.")
    assert versions["pyinstaller"] != ""


# --------------------------------------------------------------------------- #
# olcum
# --------------------------------------------------------------------------- #


def test_measuring_a_missing_folder_is_zero(tmp_path: Path) -> None:
    assert measure_output(tmp_path / "yok") == (0, 0)


def test_measuring_counts_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "alt").mkdir()
    (tmp_path / "a.bin").write_bytes(b"12345")
    (tmp_path / "alt" / "b.bin").write_bytes(b"123")

    assert measure_output(tmp_path) == (2, 8)
