"""Sürümlü uygulama ayarları — `F1-009`.

Kurallar:

* Ayar dosyası yoksa varsayılanlar kullanılır ve bu bir hata değildir.
* Dosya bozuksa uygulama açılmaya devam eder; kullanıcıya **anlaşılır** bir
  geri bildirim üretilir ve bozuk dosya `.bozuk` uzantısıyla saklanır, üzerine
  yazılarak kaybedilmez.
* Yazma **atomiktir**: geçici dosyaya yazılıp yerine taşınır. Yarım kalan bir
  yazma, çalışan ayar dosyasını bozmaz (plan Bölüm 14.1).
* Şema sürümü taşınır; bilinmeyen sürüm sessizce yorumlanmaz.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, cast

#: Ayar semasinin surumu. Alan eklendiginde/anlamı degistiginde artar.
SCHEMA_VERSION = 1

THEMES = ("dark", "light")
TIME_DISPLAYS = ("utc", "local", "elapsed")


@dataclass(frozen=True)
class AppSettings:
    """Uygulamanın kalıcı temel ayarları."""

    schema_version: int = SCHEMA_VERSION
    theme: str = "dark"
    time_display: str = "utc"
    last_directory: str = ""
    window_geometry: str = ""
    recent_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LoadResult:
    """Yükleme sonucu: ayarlar ve kullanıcıya gösterilecek uyarılar."""

    settings: AppSettings
    warnings: list[str] = field(default_factory=list)
    used_defaults: bool = False

    @property
    def ok(self) -> bool:
        return not self.warnings


def default_settings_path() -> Path:
    """Windows'ta %APPDATA%, diğerlerinde ~/.config altındaki ayar dosyası."""
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "SonarAnalyzer" / "settings.json"


def _coerce(raw: dict[str, Any], warnings: list[str]) -> AppSettings:
    """Sözlüğü ayarlara çevirir; geçersiz alanlarda varsayılana döner."""
    defaults = AppSettings()

    theme = raw.get("theme", defaults.theme)
    if theme not in THEMES:
        warnings.append(f"Bilinmeyen tema {theme!r}; {defaults.theme!r} kullanildi.")
        theme = defaults.theme

    time_display = raw.get("time_display", defaults.time_display)
    if time_display not in TIME_DISPLAYS:
        warnings.append(
            f"Bilinmeyen zaman gosterimi {time_display!r}; {defaults.time_display!r} kullanildi."
        )
        time_display = defaults.time_display

    recent = _string_list(raw.get("recent_files", []), warnings)

    def _text(key: str, fallback: str) -> str:
        value = raw.get(key, fallback)
        if not isinstance(value, str):
            warnings.append(f"{key} metin degil; varsayilan kullanildi.")
            return fallback
        return value

    return AppSettings(
        schema_version=SCHEMA_VERSION,
        theme=theme,
        time_display=time_display,
        last_directory=_text("last_directory", defaults.last_directory),
        window_geometry=_text("window_geometry", defaults.window_geometry),
        recent_files=recent,
    )


def _string_list(value: object, warnings: list[str]) -> list[str]:
    """Yalnızca metin öğelerinden oluşan listeyi kabul eder."""
    if isinstance(value, list):
        items = cast("list[object]", value)
        if all(isinstance(item, str) for item in items):
            return [item for item in items if isinstance(item, str)]
    warnings.append("recent_files listesi okunamadi; bos liste kullanildi.")
    return []


def _migrate(raw: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    """Eski şema sürümlerini güncel şemaya taşır."""
    version = raw.get("schema_version")

    if version is None:
        warnings.append("Ayar dosyasinda surum yok; surum 1 varsayildi.")
        return raw

    if not isinstance(version, int):
        warnings.append(f"Ayar surumu sayi degil ({version!r}); varsayilanlara donuldu.")
        return {}

    if version > SCHEMA_VERSION:
        warnings.append(
            f"Ayar dosyasi daha yeni bir surumden ({version} > {SCHEMA_VERSION}). "
            "Taninmayan alanlar yok sayildi; kaydedince eski surume donusur."
        )
        return raw

    # version < SCHEMA_VERSION oldugunda buraya gocurme adimlari eklenir.
    return raw


def load_settings(path: Path | None = None) -> LoadResult:
    """Ayarları okur. Hiçbir durumda istisna fırlatmaz."""
    target = path or default_settings_path()
    warnings: list[str] = []

    if not target.exists():
        return LoadResult(AppSettings(), warnings, used_defaults=True)

    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        warnings.append(
            f"Ayar dosyasi okunamadi ({exc.strerror or exc}); varsayilanlar kullanildi."
        )
        return LoadResult(AppSettings(), warnings, used_defaults=True)

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        backup = _quarantine(target, warnings)
        warnings.append(
            f"Ayar dosyasi bozuk (satir {exc.lineno}, sutun {exc.colno}); "
            f"varsayilanlar kullanildi. Bozuk dosya: {backup.name}"
        )
        return LoadResult(AppSettings(), warnings, used_defaults=True)

    if not isinstance(raw, dict):
        backup = _quarantine(target, warnings)
        warnings.append(
            f"Ayar dosyasi beklenen bicimde degil; varsayilanlar kullanildi. "
            f"Bozuk dosya: {backup.name}"
        )
        return LoadResult(AppSettings(), warnings, used_defaults=True)

    data = cast("dict[str, Any]", raw)
    migrated = _migrate(data, warnings)
    settings = _coerce(migrated, warnings)
    return LoadResult(settings, warnings, used_defaults=not migrated)


def _quarantine(path: Path, warnings: list[str]) -> Path:
    """Bozuk dosyayı yanına `.bozuk` uzantısıyla taşır; üzerine yazılmasını önler."""
    backup = path.with_suffix(path.suffix + ".bozuk")
    try:
        if backup.exists():
            backup.unlink()
        path.replace(backup)
    except OSError as exc:  # pragma: no cover - dosya sistemi engeli
        warnings.append(f"Bozuk ayar dosyasi saklanamadi: {exc}")
    return backup


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    """Ayarları atomik olarak yazar ve yazılan yolu döndürür."""
    target = path or default_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = replace(settings, schema_version=SCHEMA_VERSION).to_dict()
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

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
