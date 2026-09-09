"""Pytest ortak yapılandırması — `F1-005`.

GUI testleri `gui` işaretiyle ayrılır ve PySide6 kurulu değilse atlanır. Böylece
çekirdek katman testleri Qt olmadan da koşabilir (plan Bölüm 7.1 katman ayrımı).
"""

from __future__ import annotations

import importlib.util
import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from sonar_analyzer.logging.setup import LOG_DIR_ENV, LOGGER_NAME
from sonar_analyzer.settings.store import SETTINGS_PATH_ENV

# Qt pencerelerini gorunur acmadan test etmek icin. Ortamda zaten bir deger
# varsa (ornegin gercek ekranda hata ayiklama) ona dokunulmaz.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Offscreen platform sistem yazi tiplerini kendiliginden bulmuyor; ayarlanmazsa
# tum metinler kutu (tofu) olarak ciziliyor. Metin genisligi widget'larin
# asgari boyutunu belirledigi icin bu, yerlesim testlerini de etkiler.
if "QT_QPA_FONTDIR" not in os.environ and Path("C:/Windows/Fonts").is_dir():
    os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"


@pytest.fixture(autouse=True)
def block_native_file_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hiçbir testin **yerel dosya diyaloğu** açmasına izin vermez — `F3-001`.

    `action_open` artık gerçek bir `QFileDialog` açıyor. Diyalog modal ve
    kullanıcı girdisi beklediği için, onu tetikleyen bir test (örneğin
    yalnız sinyalin yayıldığını doğrulayan `test_empty_state`) tüm paketi
    süresiz kilitler. Bu bir kez yaşandı; ağ kalıcı olarak buraya kondu.

    Yama "kullanıcı iptal etti" davranışı üretir: seçici hiçbir talep
    yaymaz ve oturum korunur. Kendi diyaloğunu veren testler
    (`tests/gui/test_file_open.py`) bundan etkilenmez.
    """
    if importlib.util.find_spec("PySide6") is None:
        return

    from sonar_analyzer.ui import file_open

    def refuse(_parent: object, _start_directory: str) -> tuple[str, ...]:
        return ()

    monkeypatch.setattr(file_open, "_default_dialog", refuse)


@pytest.fixture(autouse=True)
def block_modal_error_box(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yükleme hatası kutusunun testte modal açılmasını engeller — `F3-006`.

    `block_native_file_dialog` ile aynı gerekçe: modal kutu kullanıcı girdisi
    bekler ve paketi kilitler. Yamalı sürüm hiçbir şey göstermez; kutuyu
    doğrulayan testler kendi kaydedicisini enjekte eder.
    """
    if importlib.util.find_spec("PySide6") is None:
        return

    from sonar_analyzer.ui import error_dialogs

    def silent(_parent: object, _message: object) -> None:
        return None

    monkeypatch.setattr(error_dialogs, "message_box_notifier", silent)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """PySide6 yoksa `gui` işaretli testleri atlar."""
    del config
    if importlib.util.find_spec("PySide6") is not None:
        return
    skip_gui = pytest.mark.skip(reason='PySide6 kurulu degil (pip install -e ".[gui]")')
    for item in items:
        if "gui" in item.keywords:
            item.add_marker(skip_gui)


@pytest.fixture(autouse=True, scope="session")
def redirect_user_paths(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Testlerin kullanıcının gerçek AppData'sına yazmasını engeller.

    `main()` gerçek `setup_logging()` ve `load_settings()` çağırır. Yönlendirme
    olmasaydı test koşusu kullanıcının log ve ayar dosyalarını değiştirirdi.
    """
    root = tmp_path_factory.mktemp("user-paths")
    previous = {
        LOG_DIR_ENV: os.environ.get(LOG_DIR_ENV),
        SETTINGS_PATH_ENV: os.environ.get(SETTINGS_PATH_ENV),
    }
    os.environ[LOG_DIR_ENV] = str(root / "logs")
    os.environ[SETTINGS_PATH_ENV] = str(root / "settings.json")

    yield

    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(autouse=True)
def restore_app_logger() -> Iterator[None]:
    """Her testten sonra uygulama logger'ını eski hâline getirir.

    `setup_logging` handler ekler ve `propagate` bayrağını kapatır. Geri
    konmazsa bir testin kurduğu log yapılandırması, sonraki testlerdeki
    `caplog` beklentilerini sessizce bozar.
    """
    logger = logging.getLogger(LOGGER_NAME)
    saved_handlers = list(logger.handlers)
    saved_level = logger.level
    saved_propagate = logger.propagate

    yield

    for handler in list(logger.handlers):
        if handler not in saved_handlers:
            logger.removeHandler(handler)
            handler.close()
    for handler in saved_handlers:
        if handler not in logger.handlers:
            logger.addHandler(handler)
    logger.setLevel(saved_level)
    logger.propagate = saved_propagate


@pytest.fixture()
def fixtures_dir() -> Path:
    """Sentetik `.bin` fixture dizininin yolu."""
    path = Path(__file__).resolve().parent / "fixtures"
    path.mkdir(parents=True, exist_ok=True)
    return path
