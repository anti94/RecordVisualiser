"""Şema hatalarını kullanıcıya taşıyan mesajlar — `F7-018`.

Bir istisna metni geliştiriciye yazılır: kısa, teknik, bağlamsız. Arayüzde
gösterilecek mesaj başka bir şeydir; üç soruyu birden cevaplamalıdır:

1. **Ne oldu** — hangi struct, hangi alan, hangi offset.
2. **Neden önemli** — bu hata görmezden gelinirse ne olur.
3. **Ne yapmalı** — düzeltmek için nereye bakılacak.

Üçüncüsü en çok atlanan ve en çok gerekenidir. "Şema geçersiz" diyen bir
diyalog, kullanıcıyı yüz alanlı bir TOML dosyasının başına oturtur.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.schema.errors import (
    SchemaError,
    SchemaLayoutError,
    SchemaMismatchError,
    SchemaTypeError,
    SchemaValueError,
)

DOC_CONTRACT = "docs/format/toml-schema.md"
DOC_PROFILE = "docs/format/profile-c.md"


@dataclass(frozen=True)
class SchemaErrorReport:
    """Kullanıcıya gösterilecek hâliyle bir şema hatası."""

    title: str
    detail: str
    action: str
    #: Kayit acilabilir mi. Uyarilar icin True, hatalar icin False.
    recoverable: bool = False

    def as_text(self) -> str:
        """Tek parçalı metin — günlük ve konsol için."""
        return f"{self.title}\n\n{self.detail}\n\nNe yapmalı: {self.action}"


def describe(error: SchemaError) -> SchemaErrorReport:
    """Bir şema hatasını kullanıcıya gösterilecek hâle çevirir."""
    if isinstance(error, SchemaTypeError):
        return _describe_type(error)
    if isinstance(error, SchemaLayoutError):
        return _describe_layout(error)
    if isinstance(error, SchemaMismatchError):
        return _describe_mismatch(error)
    if isinstance(error, SchemaValueError):
        return SchemaErrorReport(
            title="Şema dosyası okunamadı",
            detail=str(error),
            action=f"Eksik ya da hatalı alanı düzeltin. Sözleşme: {DOC_CONTRACT}",
        )
    return SchemaErrorReport(
        title="Şema hatası",
        detail=str(error),
        action=f"Şema dosyasını sözleşmeye göre gözden geçirin: {DOC_CONTRACT}",
    )


def _describe_type(error: SchemaTypeError) -> SchemaErrorReport:
    where = f" ({error.field} alanında)" if error.field else ""
    if error.hint:
        detail = (
            f"{error.type_name!r} tipi{where} bilinçli olarak desteklenmiyor: {error.hint}. "
            f"Genişliği garantili olmayan bir tip, aynı şemanın iki makinede "
            f"farklı okunmasına yol açar."
        )
        action = f"Tipi açık genişlikli karşılığıyla değiştirin. Tip tablosu: {DOC_CONTRACT} §2"
    else:
        detail = (
            f"{error.type_name!r} tipi{where} tip tablosunda yok. Bilinmeyen bir tipin "
            f"kaç bayt tuttuğu bilinemez, dolayısıyla sonraki bütün alanların offseti kayar."
        )
        action = f"Desteklenen tiplerden birini kullanın. Tip tablosu: {DOC_CONTRACT} §2"
    return SchemaErrorReport(title="Şemada desteklenmeyen tip", detail=detail, action=action)


def _describe_layout(error: SchemaLayoutError) -> SchemaErrorReport:
    return SchemaErrorReport(
        title=f"Şema yerleşimi tutarsız: {error.struct_name}",
        detail=(
            f"{error}. Yerleşim tutarsızsa dosya okunabilir ama alanlar kaymış olur; "
            f"bayt sayısı tutar, hiçbir istisna oluşmaz ve değerler sessizce yanlış çıkar."
        ),
        action=(
            f"Offsetleri ve bildirilen boyutu karşılaştırın. "
            f"Hizalama ve dolgu kuralları: {DOC_CONTRACT} §4"
        ),
    )


def _describe_mismatch(error: SchemaMismatchError) -> SchemaErrorReport:
    return SchemaErrorReport(
        title="Şema ile kayıt uyuşmuyor",
        detail=(
            f"{error}. Bu kayıt, yüklü şemanın tarif ettiği yerleşimde değil. "
            f"Okumaya devam edilseydi her alan kaymış hâlde çözülür ve sonuçlar "
            f"hatasız görünürdü."
        ),
        action=(
            f"Kaydı üreten C++ sürümüne ait şemayı yükleyin. Üç kapı ve nedenleri: {DOC_PROFILE} §7"
        ),
    )


def describe_warnings(warnings: tuple[str, ...]) -> SchemaErrorReport | None:
    """Yükleme uyarılarını tek bir rapora toplar.

    Uyarı kaydı açmayı engellemez; bu yüzden `recoverable` doğrudur.
    Uyarı yoksa `None` döner — boş bir diyalog göstermek gürültüdür.
    """
    if not warnings:
        return None
    listed = "\n".join(f"  • {line}" for line in warnings)
    return SchemaErrorReport(
        title=f"Şema yüklendi, {len(warnings)} uyarı var",
        detail=(
            f"Aşağıdaki boşluklar şemada bildirilmemiş:\n{listed}\n\n"
            f"Bildirilmemiş boşluk bilinçli olabilir (derleyici dolgusu). "
            f"Ama beklenmiyorsa bir alanın unutulduğunu gösterir."
        ),
        action=f"Bilinçliyse dolgu alanı olarak bildirin: {DOC_CONTRACT} §4.1",
        recoverable=True,
    )
