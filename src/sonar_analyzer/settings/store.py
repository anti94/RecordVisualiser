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
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from sonar_analyzer.domain.correlation import DEFAULT_TOLERANCE_NS
from sonar_analyzer.io.live.connection_settings import LiveConnectionSettings

#: Ayar semasinin surumu. Alan eklendiginde/anlamı degistiginde artar.
#: v2 (`F3-017`): `favorite_groups` alani eklendi.
#: v3 (`F5-018`): `live_connection` alani eklendi.
SCHEMA_VERSION = 3

#: `save_settings`'in imzasi — kalici hale getirmeyi enjekte etmek icin
#: (testler gercek ayar dosyasina yazmasin diye, bkz. `F3-008`).
SettingsWriter = Callable[["AppSettings"], Path]

THEMES = ("dark", "light")
TIME_DISPLAYS = ("utc", "local", "elapsed")


def _empty_str_list() -> list[str]:
    """`field(default_factory=list)` tip denetiminde list[Unknown] uretir."""
    return []


def _empty_group_list() -> list[FavoriteGroup]:
    return []


def _default_live_connection() -> LiveConnectionSettings:
    return LiveConnectionSettings()


@dataclass(frozen=True)
class FavoriteGroup:
    """Adlandırılmış bir kanal kimliği kümesi — `F3-017`.

    Kayıttan bağımsız saklanır: bir grup, o an açık olmayan (hatta artık
    var olmayan) kanalları da içerebilir. Grubu yeniden açarken var
    olmayanlar `favorite_groups.resolve()` ile ayrı raporlanır.
    """

    name: str
    channel_ids: list[str] = field(default_factory=_empty_str_list)


@dataclass(frozen=True)
class AppSettings:
    """Uygulamanın kalıcı temel ayarları."""

    schema_version: int = SCHEMA_VERSION
    theme: str = "dark"
    time_display: str = "utc"
    last_directory: str = ""
    window_geometry: str = ""
    recent_files: list[str] = field(default_factory=_empty_str_list)
    favorite_groups: list[FavoriteGroup] = field(default_factory=_empty_group_list)
    #: Canlı bağlantı ve tampon yapılandırması (`F5-018`).
    live_connection: LiveConnectionSettings = field(default_factory=_default_live_connection)
    #: Olay ↔ örnek eşleme toleransı, nanosaniye (plan Bölüm 9).
    #: Cihazın kayıt periyodu değişebilir ve `D-08` hâlâ açıktır; sabit
    #: bir sayıya gömmek, cevap geldiğinde kodun içinde aranmasını
    #: gerektirirdi.
    correlation_tolerance_ns: int = DEFAULT_TOLERANCE_NS
    #: Profil C sema dosyasinin yolu (`F7-048`). Bos ise Profil C kaydi
    #: acilamaz ve kullaniciya bunun NEDENI soylenir — sessizce bos bir
    #: kayit gostermek, dosyalarin bozuk oldugu izlenimi verirdi.
    #: Sema C++ struct tanimlarinin tarifidir (`D-29`); her kurulumda
    #: farkli olabilir, bu yuzden koda gomulmez.
    profile_c_schema_path: str = ""
    #: Son acilan kayit KLASORLERI (`F7-046`). `recent_files` dosya
    #: yollarini tasir ve bozulmadan kalir; klasorler ayri tutulur cunku
    #: ikisi farkli acma yollarina gider.
    recent_folders: list[str] = field(default_factory=_empty_str_list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LoadResult:
    """Yükleme sonucu: ayarlar ve kullanıcıya gösterilecek uyarılar."""

    settings: AppSettings
    warnings: list[str] = field(default_factory=_empty_str_list)
    used_defaults: bool = False

    @property
    def ok(self) -> bool:
        return not self.warnings


#: Ayar dosyasini disaridan degistirmeye yarar (test ve CI icin).
SETTINGS_PATH_ENV = "SONAR_ANALYZER_SETTINGS"


def default_settings_path() -> Path:
    """Ayar dosyası: önce ortam değişkeni, sonra platform varsayılanı."""
    override = os.environ.get(SETTINGS_PATH_ENV)
    if override:
        return Path(override)
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

    tolerance = raw.get("correlation_tolerance_ns", defaults.correlation_tolerance_ns)
    if not isinstance(tolerance, int) or isinstance(tolerance, bool) or tolerance < 0:
        warnings.append(
            f"Gecersiz korelasyon toleransi {tolerance!r}; "
            f"{defaults.correlation_tolerance_ns} kullanildi."
        )
        tolerance = defaults.correlation_tolerance_ns

    recent = _string_list(raw.get("recent_files", []), warnings)
    recent_folders = _string_list(raw.get("recent_folders", []), warnings)
    favorites = _favorite_groups(raw.get("favorite_groups", []), warnings)

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
        favorite_groups=favorites,
        live_connection=_live_connection(raw.get("live_connection"), warnings),
        correlation_tolerance_ns=tolerance,
        profile_c_schema_path=_text("profile_c_schema_path", defaults.profile_c_schema_path),
        recent_folders=recent_folders,
    )


def _live_connection(value: object, warnings: list[str]) -> LiveConnectionSettings:
    """Canlı bağlantı ayarlarını savunmacı okur — `F5-018`.

    Tek bir bozuk alan tüm bloğu düşürmez: o alan varsayılanına döner ve
    uyarı üretilir. **Geçerlilik burada denetlenmez**; ayar dosyasında
    duran değer geçersiz olabilir (kullanıcı elle düzenlemiş olabilir) ve
    bunu bağlantıdan önce `LiveConnectionSettings.validate()` açıklar.
    """
    defaults = LiveConnectionSettings()
    if value is None:
        return defaults
    if not isinstance(value, dict):
        warnings.append("live_connection bolumu okunamadi; varsayilanlar kullanildi.")
        return defaults

    record = cast("dict[str, object]", value)

    def _str_field(key: str, fallback: str) -> str:
        raw_value = record.get(key, fallback)
        if not isinstance(raw_value, str):
            warnings.append(f"live_connection.{key} metin degil; varsayilan kullanildi.")
            return fallback
        return raw_value

    def _int_field(key: str, fallback: int) -> int:
        raw_value = record.get(key, fallback)
        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            warnings.append(f"live_connection.{key} tam sayi degil; varsayilan kullanildi.")
            return fallback
        return raw_value

    def _bool_field(key: str, fallback: bool) -> bool:
        raw_value = record.get(key, fallback)
        if not isinstance(raw_value, bool):
            warnings.append(f"live_connection.{key} mantiksal degil; varsayilan kullanildi.")
            return fallback
        return raw_value

    return LiveConnectionSettings(
        protocol=_str_field("protocol", defaults.protocol),
        host=_str_field("host", defaults.host),
        port=_int_field("port", defaults.port),
        serial_port=_str_field("serial_port", defaults.serial_port),
        baud_rate=_int_field("baud_rate", defaults.baud_rate),
        ring_capacity_samples=_int_field("ring_capacity_samples", defaults.ring_capacity_samples),
        queue_maxsize=_int_field("queue_maxsize", defaults.queue_maxsize),
        drop_policy=_str_field("drop_policy", defaults.drop_policy),
        auto_reconnect=_bool_field("auto_reconnect", defaults.auto_reconnect),
    )


def _string_list(value: object, warnings: list[str]) -> list[str]:
    """Yalnızca metin öğelerinden oluşan listeyi kabul eder."""
    if isinstance(value, list):
        items = cast("list[object]", value)
        if all(isinstance(item, str) for item in items):
            return [item for item in items if isinstance(item, str)]
    warnings.append("recent_files listesi okunamadi; bos liste kullanildi.")
    return []


def _favorite_groups(value: object, warnings: list[str]) -> list[FavoriteGroup]:
    """Favori grup listesini savunmacı biçimde okur — `F3-017`.

    Beklenen biçim: `[{"name": str, "channel_ids": [str, ...]}, ...]`.
    Adı boş/metin olmayan ya da biçimi bozuk girdiler **atlanır** (uyarı
    üretilir); tek bir bozuk girdi tüm listeyi düşürmez.
    """
    if not isinstance(value, list):
        warnings.append("favorite_groups listesi okunamadi; bos liste kullanildi.")
        return []

    groups: list[FavoriteGroup] = []
    for entry in cast("list[object]", value):
        if not isinstance(entry, dict):
            warnings.append("Bir favori grup girdisi sozluk degil; atlandi.")
            continue
        record = cast("dict[str, object]", entry)
        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            warnings.append("Adi olmayan bir favori grup girdisi atlandi.")
            continue
        raw_ids = record.get("channel_ids", [])
        if not isinstance(raw_ids, list) or not all(
            isinstance(item, str) for item in cast("list[object]", raw_ids)
        ):
            warnings.append(f"{name!r} favori grubunun kanal listesi bozuk; atlandi.")
            continue
        ids = list(cast("list[str]", raw_ids))
        groups.append(FavoriteGroup(name=name.strip(), channel_ids=ids))
    return groups


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

    # version < SCHEMA_VERSION: eksik alanlar `_coerce`'de varsayilanina
    # duser. v1 -> v2 (`F3-017`): `favorite_groups` yoksa bos liste olur.
    # v2 -> v3 (`F5-018`): `live_connection` yoksa varsayilan yapilandirma
    # kullanilir. Ikisi de yalnizca **ekleme**; donusum gerekmez.
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
