"""Pytest ortak yapılandırması — `F1-005`.

GUI testleri `gui` işaretiyle ayrılır ve PySide6 kurulu değilse atlanır. Böylece
çekirdek katman testleri Qt olmadan da koşabilir (plan Bölüm 7.1 katman ayrımı).
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

# Qt pencerelerini gorunur acmadan test etmek icin. Ortamda zaten bir deger
# varsa (ornegin gercek ekranda hata ayiklama) ona dokunulmaz.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """PySide6 yoksa `gui` işaretli testleri atlar."""
    del config
    if importlib.util.find_spec("PySide6") is not None:
        return
    skip_gui = pytest.mark.skip(reason='PySide6 kurulu degil (pip install -e ".[gui]")')
    for item in items:
        if "gui" in item.keywords:
            item.add_marker(skip_gui)


@pytest.fixture()
def fixtures_dir() -> Path:
    """Sentetik `.bin` fixture dizininin yolu."""
    path = Path(__file__).resolve().parent / "fixtures"
    path.mkdir(parents=True, exist_ok=True)
    return path
