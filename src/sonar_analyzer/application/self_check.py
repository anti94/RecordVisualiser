"""Paketlenmiş açılışın kendini denetlemesi — `F6-003`.

Kabul: **Paketli açılışta tema, ikon ve platform plugin'i yüklenir.**

Bu üç şeyin paketlenmiş uygulamada yüklendiği, ancak **paketlenmiş
uygulama çalıştırılarak** bilinebilir; kaynak ağacında geçen bir test
paketin içinde ne olduğunu söylemez. `--self-check` bu yüzden vardır:
paket açılır, üç kontrolü yapar, sonucu satır satır yazar ve kusur varsa
**sıfırdan farklı** çıkış kodu döner.

Kontroller tek tek anlamlıdır:

* **platform plugin** — Qt'nin pencere sistemi eklentisi yüklenmediyse
  uygulama hiç pencere açamaz. Paketlemede en sık kaybolan parça budur.
* **tema** — stil sayfası boş dönerse arayüz Qt'nin varsayılanıyla açılır;
  çalışır ama mockup'a benzemez, yani sessiz bir bozulmadır.
* **ikon** — paket veri dosyasını taşımıyorsa ikon boş kalır.
* **ana ekran** — pencere gerçekten **gösterilebiliyor** mu (`F6-005`).
  Pencerenin kurulabilmesi yetmez; Qt bir pencereyi oluşturup ekrana
  alamadığında hata vermeden görünmez kalabilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sonar_analyzer.resources import app_icon_path


@dataclass(frozen=True)
class SelfCheckReport:
    """Denetimin sonucu; her satır kullanıcıya gösterilir."""

    lines: list[str] = field(default_factory=lambda: [])
    failures: list[str] = field(default_factory=lambda: [])

    @property
    def ok(self) -> bool:
        return not self.failures


def run_self_check(app: object, window: object) -> SelfCheckReport:
    """Tema, ikon ve platform plugin'ini denetler.

    `app` ve `window` tip olarak gevşek alınır: bu modül Qt'yi **içe
    aktarmaz**, böylece Qt kurulu olmayan bir ortamda içe aktarılması bile
    hata vermez. Denetim çağrıldığında zaten bir Qt uygulaması vardır.
    """
    lines: list[str] = []
    failures: list[str] = []

    platform_name = _platform_name(app)
    if platform_name:
        lines.append(f"platform plugin: {platform_name}")
    else:
        failures.append("platform plugin")
        lines.append("platform plugin: YOK")

    stylesheet = _stylesheet(window) or _stylesheet(app)
    if stylesheet:
        lines.append(f"tema: {len(stylesheet)} karakterlik stil sayfasi")
    else:
        failures.append("tema")
        lines.append("tema: YOK")

    window_size = _shown_window_size(window)
    if window_size is None:
        failures.append("ana ekran")
        lines.append("ana ekran: ACILAMADI")
    else:
        lines.append(f"ana ekran: {window_size[0]}x{window_size[1]}")

    icon_path = app_icon_path()
    if icon_path is None:
        failures.append("ikon")
        lines.append("ikon: YOK (kaynak bulunamadi)")
    elif _icon_is_empty(app):
        failures.append("ikon")
        lines.append(f"ikon: YUKLENEMEDI ({icon_path})")
    else:
        lines.append(f"ikon: {icon_path.name}")

    lines.append("sonuc: " + ("TAMAM" if not failures else "EKSIK -> " + ", ".join(failures)))
    return SelfCheckReport(lines=lines, failures=failures)


def _shown_window_size(window: object) -> tuple[int, int] | None:
    """Pencereyi gösterip boyutunu döner; gösterilemiyorsa `None`.

    Pencere **gerçekten gösterilir**: kurulabilmesi tek başına "ana ekran
    açılır" demek değildir. Denetim sonunda kapatılır, çünkü bu bir
    otomatik kontroldür, oturum değil.
    """
    show = getattr(window, "show", None)
    is_visible = getattr(window, "isVisible", None)
    width = getattr(window, "width", None)
    height = getattr(window, "height", None)
    if not all(callable(item) for item in (show, is_visible, width, height)):
        return None
    try:
        show()  # type: ignore[misc]
        if not bool(is_visible()):  # type: ignore[misc]
            return None
        size = (int(width()), int(height()))  # type: ignore[misc]
    except Exception:  # pragma: no cover - Qt beklenmedik durum
        return None
    return size if size[0] > 0 and size[1] > 0 else None


def _platform_name(app: object) -> str:
    """Qt'nin kullandığı platform eklentisinin adı; bilinemezse boş."""
    getter = getattr(app, "platformName", None)
    if not callable(getter):
        return ""
    try:
        return str(getter())
    except Exception:  # pragma: no cover - Qt beklenmedik durum
        return ""


def _stylesheet(target: object) -> str:
    getter = getattr(target, "styleSheet", None)
    if not callable(getter):
        return ""
    try:
        return str(getter())
    except Exception:  # pragma: no cover - Qt beklenmedik durum
        return ""


def _icon_is_empty(app: object) -> bool:
    """Uygulamaya atanmış ikon boş mu?"""
    getter = getattr(app, "windowIcon", None)
    if not callable(getter):
        return True
    try:
        icon = getter()
    except Exception:  # pragma: no cover - Qt beklenmedik durum
        return True
    is_null = getattr(icon, "isNull", None)
    return bool(is_null()) if callable(is_null) else True
