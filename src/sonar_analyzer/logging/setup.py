"""Dönen dosya log'u ve oturum kimliği — `F1-010`.

Kurallar (plan Bölüm 18, 19):

* Log dosyası boyutla **döner**; disk sınırsız dolmaz.
* Her satırda uygulama **sürümü** ve **oturum kimliği** görünür; farklı
  koşuların satırları birbirine karışmaz.
* **Ham sensör verisi log'a yazılmaz.** Uzun ikili/dizi argümanlar otomatik
  olarak özetle değiştirilir; bu kural belgeye değil filtreye bağlıdır.

Not: bu paketin adı `logging`'dir ama Python 3 mutlak içe aktarma kullandığı
için buradaki ``import logging`` standart kütüphaneyi getirir.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sonar_analyzer import __version__

LOGGER_NAME = "sonar_analyzer"

#: Tek bir log dosyasinin ust siniri ve saklanan yedek sayisi.
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 5

#: Bu uzunlugu asan ikili/dizi argumanlar log'a ozet olarak yazilir.
PAYLOAD_PREVIEW_LIMIT = 32

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(app_version)s %(session_id)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def new_session_id() -> str:
    """Bu koşuyu diğerlerinden ayıran kısa kimlik."""
    return uuid.uuid4().hex[:8]


#: Log dizinini disaridan degistirmeye yarar (test ve CI icin).
LOG_DIR_ENV = "SONAR_ANALYZER_LOG_DIR"


def default_log_dir() -> Path:
    """Log dizini: önce ortam değişkeni, sonra platform varsayılanı."""
    override = os.environ.get(LOG_DIR_ENV)
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "SonarAnalyzer" / "logs"


class SessionContextFilter(logging.Filter):
    """Her kayda sürüm ve oturum kimliği ekler."""

    def __init__(self, session_id: str, app_version: str = __version__) -> None:
        super().__init__()
        self.session_id = session_id
        self.app_version = app_version

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = self.session_id
        record.app_version = self.app_version
        return True


class PayloadRedactingFilter(logging.Filter):
    """Ham sensör verisinin log'a sızmasını engeller.

    ``bytes``, ``bytearray``, ``memoryview`` ve NumPy dizisi gibi büyük
    argümanlar, içerikleri yerine tür ve uzunluk özetiyle yazılır.
    """

    def __init__(self, limit: int = PAYLOAD_PREVIEW_LIMIT) -> None:
        super().__init__()
        self.limit = limit

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(self._redact(arg) for arg in record.args)
            elif isinstance(record.args, dict):
                mapping: dict[str, Any] = record.args
                record.args = {key: self._redact(value) for key, value in mapping.items()}
        return True

    def _redact(self, value: object) -> object:
        if isinstance(value, (bytes, bytearray)):
            if len(value) > self.limit:
                return f"<{type(value).__name__} len={len(value)} icerik yazilmadi>"
            return value

        if isinstance(value, memoryview):
            view = cast("memoryview[Any]", value)
            if view.nbytes > self.limit:
                return f"<memoryview len={view.nbytes} icerik yazilmadi>"
            # Kisa gorunumler okunabilir kalsin diye bayta cevrilir.
            return bytes(view)

        # NumPy'yi ice aktarmadan, dizi benzeri nesneleri ozelliklerinden tani.
        shape = getattr(value, "shape", None)
        dtype = getattr(value, "dtype", None)
        if shape is not None and dtype is not None:
            size = getattr(value, "size", None)
            if size is None or size > self.limit:
                return f"<dizi shape={shape} dtype={dtype} icerik yazilmadi>"
        return value


@dataclass(frozen=True)
class LoggingSetup:
    """Kurulan log yapılandırmasının özeti."""

    session_id: str
    log_file: Path
    level: int


def setup_logging(
    log_dir: Path | None = None,
    level: int = logging.INFO,
    session_id: str | None = None,
    console: bool = True,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> LoggingSetup:
    """Dönen dosya log'unu kurar ve oturum bilgisini döndürür."""
    directory = log_dir or default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / "sonar_analyzer.log"
    session = session_id or new_session_id()

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    context = SessionContextFilter(session)
    redactor = PayloadRedactingFilter()

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context)
    file_handler.addFilter(redactor)
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(context)
        stream_handler.addFilter(redactor)
        logger.addHandler(stream_handler)

    logger.info("Oturum basladi: surum %s, oturum %s", __version__, session)
    return LoggingSetup(session_id=session, log_file=log_file, level=level)
