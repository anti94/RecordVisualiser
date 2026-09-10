"""Oturum log'unda ayrı, monoton süre ölçümleri — F4-062."""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from contextlib import contextmanager
from time import perf_counter

logger = logging.getLogger("sonar_analyzer.performance")


@contextmanager
def measure(
    operation: str, **fields: str | int | float | bool | None
) -> Generator[None, None, None]:
    """Süreyi başarı/hata ile yazar; asıl istisnayı çağırana iletir.

    Ek alanlar yalnız sayaç/kimlik/kip gibi küçük skaler metadata'dır;
    sensör örnekleri ölçüme geçirilmez. Oturum kimliği mevcut log filtresinden gelir.
    """
    started = perf_counter()
    succeeded = False
    try:
        yield
        succeeded = True
    finally:
        duration_ms = (perf_counter() - started) * 1000
        record = {
            **fields,
            "operation": operation,
            "duration_ms": duration_ms,
            "status": "ok" if succeeded else "error",
        }
        logger.info("performance %s", json.dumps(record, ensure_ascii=True, allow_nan=False))
