"""Sürümün tek kaynaktan (VERSION dosyası) geldiğini doğrular — `F1-001`."""

from __future__ import annotations

import re
from pathlib import Path

import sonar_analyzer

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = REPO_ROOT / "VERSION"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_version_file_exists_and_is_semver() -> None:
    text = VERSION_FILE.read_text(encoding="utf-8").strip()
    assert SEMVER.match(text), f"VERSION icerigi MAJOR.MINOR.PATCH olmali, bulundu: {text!r}"


def test_package_version_matches_version_file() -> None:
    expected = VERSION_FILE.read_text(encoding="utf-8").strip()
    assert sonar_analyzer.__version__ == expected
    assert sonar_analyzer.version() == expected


def test_version_is_not_fallback() -> None:
    assert sonar_analyzer.__version__ != "0.0.0", "surum VERSION dosyasindan okunamadi"
