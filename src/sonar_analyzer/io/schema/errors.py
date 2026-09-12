"""Şema hataları — `F7-007`+.

Her hata **hangi alanın, hangi offsette ve ne beklendiğini** söyler.
"Şema geçersiz" diyen bir mesaj, şemayı düzeltmeye yardım etmez; kullanıcı
dosyayı baştan sona okumak zorunda kalır.

Hata sınıfları ayrı tutulur çünkü çağıran taraf bazılarını farklı işler:
bilinmeyen bir tip şemayı tamamen kullanılamaz kılar, ama bildirilmemiş
bir boşluk yalnız uyarıdır.
"""

from __future__ import annotations


class SchemaError(Exception):
    """Şema katmanının tüm hatalarının ortak atası."""


class SchemaTypeError(SchemaError):
    """Bilinmeyen ya da yasaklı bir C++ tipi.

    Yasaklı bir tip için `hint`, **yerine ne yazılması gerektiğini**
    söyler. Yalnız "desteklenmiyor" demek kullanıcıyı belgede aratır;
    `long` yazan biri onun neden reddedildiğini bilmez.
    """

    def __init__(
        self, type_name: str, *, field: str | None = None, hint: str | None = None
    ) -> None:
        where = f" (alan: {field})" if field else ""
        tail = (
            f" — {hint}"
            if hint
            else (" Desteklenen tipler docs/format/toml-schema.md Bolum 2'de listelidir.")
        )
        super().__init__(f"desteklenmeyen tip: {type_name!r}{where}.{tail}")
        self.type_name = type_name
        self.field = field
        self.hint = hint


class SchemaLayoutError(SchemaError):
    """Offset, boyut ya da hizalama tutarsızlığı."""

    def __init__(self, message: str, *, struct_name: str, field: str | None = None) -> None:
        where = f"{struct_name}.{field}" if field else struct_name
        super().__init__(f"{where}: {message}")
        self.struct_name = struct_name
        self.field = field


class SchemaValueError(SchemaError):
    """Şema dosyasındaki bir değer geçersiz (enum çakışması, eksik alan)."""


class SchemaMismatchError(SchemaError):
    """Şema ile kayıt dosyası ayrışıyor.

    Bu hata en önemlisidir: engellenmese veri **hatasız ama yanlış**
    okunurdu. Bayt sayısı tutar, CRC tutar, hiçbir istisna oluşmaz; yalnız
    her alan kaymış olur.
    """

    def __init__(self, message: str, *, expected: object, found: object) -> None:
        super().__init__(f"{message} (beklenen: {expected!r}, bulunan: {found!r})")
        self.expected = expected
        self.found = found
