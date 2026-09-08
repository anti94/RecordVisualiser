# İş günlüğü — atlanan işler ve notlar

> Bu dosya Bölüm 22 iş tablosunun yerine geçmez. Amaç, **yapılamayan veya eksik bilgiyle
> yapılan işleri** kaybetmeden kaydetmektir. Bir iş burada `ATLANDI` ise plan tablosunda
> `[ ]` olarak kalır ve engeli kalkınca tekrar ele alınır.

Durum kodları: `TAMAM` · `ATLANDI` (engel var) · `KISMİ` (varsayımla yapıldı, doğrulama bekliyor)

## Koşu: 2026-09-08 gecesi

| İş ID | Durum | Not |
| --- | --- | --- |
| `F0-001` | TAMAM | Depo `main` dalında başlatıldı, `v0.1.0`. `.gitattributes` da eklendi: golden `.bin` fixture'larının satır sonu dönüşümüyle bozulmaması için gerekliydi. |
| `F0-002` | TAMAM | `docs/scenarios.md`, beş senaryo. |
| `F0-003` | TAMAM | `docs/format/inventory.md`. Depoda gerçek `.bin` yok; E-01..E-10 eksik girdiler işaretlendi. |

## Açık engeller

Ayrıntı ve hangi işleri engelledikleri: `docs/format/inventory.md` Bölüm 2.

- **E-01/E-02 — gerçek `.bin` kaydı ve resmî format dokümanı yok.** Bu nedenle Faz 0'ın format
  işleri (`F0-004`, `F0-005`, `F0-008`) yalnız Bölüm 8.2/8.3 **taslağına** göre yazılabilir.
  Bu işler `KISMİ` sayılır: çıktı üretilir, ancak gerçek doküman geldiğinde karşılaştırılıp
  güncellenmesi gerekir. Sentetik doğrulama gerçek donanım kanıtı olarak sunulmaz.
- **E-03 — CRC tanımı yok.** `F0-008` karar kaydı bir öneri sunar; algoritma seçimi donanım
  ekibi onayı olmadan kesinleşmez.
- **E-10 — hedef ölçüm bilgisayarı bilinmiyor.** `F0-014` performans bütçesi ölçüm ortamı
  olmadan yalnız hedef olarak yazılabilir.

## Kullanıcıya sorulacaklar

- `.claude/settings.local.json` depoda izlenmiyor ve `.gitignore` içinde de yok. Yerel izin
  ayarlarının yanlışlıkla commit edilmemesi için ignore kuralına eklenmesi öneriliyor.
- `SONAR Veri Analiz Panosu Mockup’ı.7z` arşivi izlenmiyor; kaynak PNG depoda olduğu için
  gerekli görülmedi. Silinsin mi, yoksa kalsın mı?
