"""Yükleme hatalarını kullanıcı diline çevirme — `F3-006`.

Kabul kriteri iki ayrı şey istiyor ve bu modül ikisini **ayırıyor**:

* **Kullanıcı mesajı anlaşılır** — "TruncatedHeaderError: kesik header:
  32 bayt gerekli, 20 bayt bulundu (offset 0)" değil, "Dosya bir SONAR
  kaydı gibi görünmüyor: başlık eksik." Kullanıcı ne olduğunu ve ne
  yapabileceğini anlar.
* **Teknik ayrıntı log'da bulunur** — hata türü, ham ileti ve dosya yolu
  uygulama log'una yazılır; teşhis için kaybolmaz.

Uydurma teşhis yok: tanınmayan bir hata türü genel bir metinle gösterilir
ama türü **gizlenmez** — kullanıcı raporunda o ad geçsin diye.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Hata türünden kullanıcı diline. Anahtarlar `io/decoders/errors.py` ve
#: yerleşik `OSError` alt sınıflarıdır.
_USER_MESSAGES: dict[str, str] = {
    "TruncatedHeaderError": (
        "Dosya bir SONAR kaydi gibi gorunmuyor: baslik eksik. Kayit en az 32 bayt baslik tasimali."
    ),
    "InvalidMagicError": (
        "Bu dosya bir SONAR kaydi degil: dosya imzasi uyusmuyor. Yanlis dosya secilmis olabilir."
    ),
    "UnsupportedVersionError": (
        "Kayit surumu bu uygulama tarafindan desteklenmiyor. "
        "Dosya daha yeni bir kayit yazilimiyla uretilmis olabilir."
    ),
    "HeaderContractError": (
        "Kayit basligi beklenen duzene uymuyor; dosya guvenilir sekilde okunamaz."
    ),
    "HeaderCrcMismatchError": (
        "Kayit basliginin butunlugu bozuk. Boyut alanlarina guvenilemedigi icin dosya acilmadi."
    ),
    "FileNotFoundError": "Dosya bulunamadi. Tasinmis veya silinmis olabilir.",
    "PermissionError": "Dosya okunamadi: erisim izni yok.",
    "IsADirectoryError": "Secilen yol bir dosya degil, klasor.",
    "OSError": "Dosya okunamadi. Surucu veya ag baglantisi kesilmis olabilir.",
}

_FALLBACK = "Dosya acilamadi. Kayit bozuk olabilir veya bu uygulamanin tanidigi bir bicimde degil."


@dataclass(frozen=True)
class LoadErrorMessage:
    """Bir yükleme hatasının kullanıcı ve log gösterimi."""

    path: Path
    error_type: str
    #: Kullanıcıya gösterilen, teknik terim içermeyen metin.
    user_text: str
    #: Log'a yazılan tam teknik satır.
    technical_text: str

    @property
    def title(self) -> str:
        return f"Dosya acilamadi: {self.path.name}"


def describe_load_error(path: Path, error_type: str, error: str) -> LoadErrorMessage:
    """Hata türünü kullanıcı diline çevirir; teknik ayrıntıyı ayrı tutar."""
    known = _USER_MESSAGES.get(error_type)
    # Taninmayan turde genel metin gosterilir ama tur adi GIZLENMEZ --
    # kullanicinin raporunda o ad gecsin diye.
    user_text = known if known is not None else f"{_FALLBACK}\n\nHata turu: {error_type}"

    detail = error.strip() or "(ayrinti yok)"
    return LoadErrorMessage(
        path=path,
        error_type=error_type,
        user_text=user_text,
        technical_text=f"{path}: {error_type}: {detail}",
    )
