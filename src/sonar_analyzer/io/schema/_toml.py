"""TOML okuma — sürümler arası tek giriş noktası.

`tomllib` Python 3.11'de standart kütüphaneye girdi. Bu proje 3.9
üzerinde koştuğu için (`D-20`) geri taşıma `tomli` gerekiyor. İki
kütüphanenin API'si aynıdır; fark yalnız addadır.

Bu dance her çağıran yerde tekrarlanmamalı. Tekrarlansaydı iki sorun
doğardı: `try/except ModuleNotFoundError` bloğu her dosyada çoğalır ve
pyright 3.9 ayağında `tomllib`'i çözemediği için her dosyada aynı üç
hatayı verirdi.

Burada bir kez yapılır ve dönüş tipi **açıkça** bildirilir. `tomli`'nin
taslakları (stub) ortam bağımlı olduğundan tip daraltma `cast` ile
yapılır; aksi hâlde katı kipte "kısmen bilinmeyen tip" hatası çıkar.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

try:  # pragma: no cover - dala ortam karar verir
    # pyright bu depoda Python 3.9'a gore calisiyor ve `tomllib`i bulamaz;
    # 3.11+ ayaginda ise `tomli` bulunmaz. Hangi ayakta kosulursa kosulsun
    # dallardan biri cozulemez, bu yuzden ikisi de bastirilir.
    import tomllib as _toml  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - 3.9 / 3.10 ayagi
    import tomli as _toml  # pyright: ignore[reportMissingImports]

#: `tomllib` ve `tomli` ayni imzayi tasir ama taslaklari ortam bagimli
#: cozuldugu icin katı kipte "kismen bilinmeyen" sayilir. Imza burada bir
#: kez sabitlenir; cagiranlar tam tipli bir fonksiyon gorur.
_loads: Callable[[str], dict[str, Any]] = cast(
    "Callable[[str], dict[str, Any]]",
    _toml.loads,  # pyright: ignore[reportUnknownMemberType]
)


def loads(text: str) -> dict[str, Any]:
    """TOML metnini sözlüğe çevirir."""
    return _loads(text)


def load_path(path: Path) -> dict[str, Any]:
    """Bir TOML dosyasını okur.

    Dosya UTF-8 olarak okunur. TOML belirtimi UTF-8 zorunlu kılar;
    yerel kod sayfasıyla okumak Türkçe açıklamaları bozardı.
    """
    return loads(path.read_text(encoding="utf-8"))
