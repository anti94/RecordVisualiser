"""Artefakt checksum ve sürüm manifesti — `F6-009`.

Kabul: **Paket sürümü, dosya adı ve hash birbiriyle eşleşir.**

Manifestin değeri hash yazmasında değil, üç kimliğin (dosya adı,
uygulamanın bildirdiği sürüm, içerik) **tutarlılığını denetlemesinde**.
Yalnız hash yazan bir manifest yanlış sürümü doğru hash'le kaydeder ve
hiçbir şey söylemez.

Bu testler tutarsızlığın gerçekten yakalandığını gösterir. Nitekim
denetim ilk koşuda kendi kodumdaki bir hatayı yakaladı: `Path.stem`,
klasör adı `sonar-analyzer-3.8.0` iken `.0`'ı uzantı sanıp sürümü `3.8`
okuyordu.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.release_manifest import (  # noqa: E402
    Artifact,
    ReleaseManifest,
    collect,
    read_version,
    sha256_of,
    version_in_filename,
)

# --------------------------------------------------------------------------- #
# DOSYA ADINDAKI SURUM
# --------------------------------------------------------------------------- #


def test_the_installer_name_yields_its_version() -> None:
    assert version_in_filename("sonar-analyzer-3.8.0-setup.exe") == "3.8.0"


def test_the_package_folder_name_yields_its_version() -> None:
    """Klasör adında uzantı yoktur; `.0` uzantı sanılmamalı."""
    assert version_in_filename("sonar-analyzer-3.8.0") == "3.8.0"


def test_a_patch_version_is_not_truncated() -> None:
    """Asıl hatanın regresyon testi: `3.8.0` -> `3.8` olmamalı."""
    for version in ("1.0.0", "3.8.0", "10.20.30"):
        assert version_in_filename(f"sonar-analyzer-{version}") == version
        assert version_in_filename(f"sonar-analyzer-{version}-setup.exe") == version


def test_an_unrelated_name_yields_nothing() -> None:
    assert version_in_filename("baska-program-1.0.0.exe") == ""


# --------------------------------------------------------------------------- #
# HASH
# --------------------------------------------------------------------------- #


def test_the_hash_matches_an_independent_computation(tmp_path: Path) -> None:
    """Hash bağımsız olarak yeniden hesaplanıp karşılaştırılır."""
    target = tmp_path / "artefakt.bin"
    payload = b"sonar" * 100_000
    target.write_bytes(payload)

    assert sha256_of(target) == hashlib.sha256(payload).hexdigest()


def test_a_one_byte_change_changes_the_hash(tmp_path: Path) -> None:
    first = tmp_path / "a.bin"
    second = tmp_path / "b.bin"
    first.write_bytes(b"\x00" * 1000)
    second.write_bytes(b"\x00" * 999 + b"\x01")

    assert sha256_of(first) != sha256_of(second)


def test_a_file_larger_than_one_chunk_hashes_correctly(tmp_path: Path) -> None:
    """Parça parça okuma doğru olmalı; 1 MiB sınırı aşılır."""
    target = tmp_path / "buyuk.bin"
    payload = bytes(range(256)) * 8192  # ~2 MiB
    target.write_bytes(payload)

    assert sha256_of(target) == hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- #
# TUTARLILIK DENETIMI
# --------------------------------------------------------------------------- #


def test_a_mismatched_installer_name_is_flagged(tmp_path: Path) -> None:
    """Dosya adı başka sürüm diyorsa manifest bunu tutarsız saymalı."""
    (tmp_path / "sonar-analyzer-9.9.9-setup.exe").write_bytes(b"MZ")
    artifacts = collect(tmp_path, "9.9.9")
    assert artifacts and artifacts[0].consistent is True

    # Ayni dosya, farkli beklenen surum: tutarsiz.
    artifacts = collect(tmp_path, "1.2.3")
    assert artifacts == []  # beklenen surumun dosyasi yok


def test_a_package_whose_app_reports_another_version_is_flagged(tmp_path: Path) -> None:
    """Klasör adı doğru ama uygulama başka sürüm diyorsa tutarsızdır."""
    folder = tmp_path / "sonar-analyzer-4.0.0"
    folder.mkdir(parents=True)
    # Calistirilamayan bir "exe": bildirilen surum bos kalir.
    (folder / "sonar-analyzer.exe").write_bytes(b"bu calismaz")

    artifacts = collect(tmp_path, "4.0.0")
    package = next(item for item in artifacts if item.kind == "package")

    assert package.consistent is False
    assert "diyor" in package.note


def test_an_empty_manifest_is_not_ok() -> None:
    """Hiç artefakt yoksa "tamam" denemez."""
    assert ReleaseManifest(version="1.0.0", created_utc="x").ok is False


def test_a_manifest_with_an_inconsistent_artifact_is_not_ok() -> None:
    manifest = ReleaseManifest(version="1.0.0", created_utc="x")
    manifest.artifacts.append(
        Artifact(name="a", kind="installer", size_bytes=1, sha256="x", consistent=True)
    )
    manifest.artifacts.append(
        Artifact(name="b", kind="package", size_bytes=1, sha256="y", consistent=False)
    )

    assert manifest.ok is False


def test_a_fully_consistent_manifest_is_ok() -> None:
    manifest = ReleaseManifest(version="1.0.0", created_utc="x")
    manifest.artifacts.append(
        Artifact(name="a", kind="installer", size_bytes=1, sha256="x", consistent=True)
    )

    assert manifest.ok is True


# --------------------------------------------------------------------------- #
# surum kaynagi
# --------------------------------------------------------------------------- #


def test_the_version_comes_from_the_version_file() -> None:
    assert read_version() == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
