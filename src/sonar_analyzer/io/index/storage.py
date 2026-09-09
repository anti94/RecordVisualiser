"""İndeks dosyasını atomik kaydetme — `F2-031`.

`settings/store.py::save_settings()`'teki aynı atomik yazma deseni: geçici
dosya hedefle **aynı dizinde** oluşturulur, yazılır ve `fsync` edilir,
sonra `Path.replace()` ile hedefin üzerine taşınır. Aynı dosya sistemindeki
değiştirme tamamlanmadan geçici dosya geçerli indeks olarak kullanılmaz.

Yazma sırasında kesinti (çökme, disk dolması) olursa yarım geçici dosya
**hiçbir zaman** hedefin yerine geçmez: rename adımına hiç gelinmemişse
eski geçerli indeks olduğu gibi kalır; `load_index_json` da yalnızca
`target`'ı okur, `.tmp` uzantılı dosyaları hiç görmez.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, cast


def save_index_atomic(target: Path, payload: dict[str, Any]) -> Path:
    """`payload`'i JSON olarak `target`'a atomik yazar.

    Yazma sırasında herhangi bir hata olursa geçici dosya silinir ve
    istisna yeniden yükseltilir; `target` (varsa) dokunulmadan kalır —
    yarım geçici dosya asla geçerli indeksin üzerine alınmaz (kabul kriteri).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    text += "\n"

    fd, temp_name = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=target.name + ".",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(target)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return target


def load_index_json(path: Path) -> dict[str, Any] | None:
    """İndeks dosyasını okur; yoksa veya bozuksa `None` döner (`F2-032`: yeniden üretilir).

    Yalnızca `path`'in kendisi okunur — aynı dizinde kalmış yarım `.tmp`
    dosyaları hiç dikkate alınmaz.
    """
    if not path.exists():
        return None
    try:
        loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return cast(dict[str, Any], loaded)
