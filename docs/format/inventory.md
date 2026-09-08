# Örnek dosya ve format envanteri

> `F0-003` çıktısıdır. Amaç, decoder geliştirmesine başlamadan önce **elimizde ne olduğunu** ve
> **neyin eksik olduğunu** tek yerde göstermektir.
>
> Kural (Bölüm 22.1): sentetik veri, gerçek donanım doğrulaması sayılmaz. Sentetik fixture ile geçen bir iş,
> gerçek kayıt gerektiren kabul maddesini kapatmaz. Eksik dış girdiler burada ve `F0-015` içinde izlenir.

Envanter tarihi: 2026-09-08 · Depo sürümü: `v0.2.0`

## 1. Mevcut girdiler

| Dosya | Tür | Boyut | Depoda | Ne işe yarar |
| --- | --- | --- | --- | --- |
| `plan.md` | Belge | ~171 KiB | evet | Ürün ve geliştirme planı; format taslakları Bölüm 8.2/8.3 |
| `SONAR Veri Analiz Panosu Mockup’ı.png` | Görsel | ~1,74 MiB | evet | Ana ürün hedefi; görsel kabul kaynağı (Bölüm 5.1) |
| `sonar_temel_kavramlar_ve_algoritmalar.md` | Belge | ~9,3 KiB | evet | SONAR temel kavram ve algoritma notları |
| `docs/scenarios.md` | Belge | ~5,3 KiB | evet | Beş kabul senaryosu (`F0-002`) |
| `SONAR Veri Analiz Panosu Mockup’ı.7z` | Arşiv | ~1,49 MiB | hayır | PNG'nin sıkıştırılmış kopyası; izlenmiyor, kaynak PNG yeterli |

**Sonuç: depoda hiçbir `.bin` kaydı yoktur.** Parser geliştirmesi bugün yalnız sentetik veriyle ilerleyebilir.

## 2. Eksik girdiler — gerçek kayıt ve sözleşmeler

| # | Eksik girdi | Neden gerekli | Kaynak | Engellediği işler | Durum |
| --- | --- | --- | --- | --- | --- |
| E-01 | Gerçek `.bin` kaydı (en az bir tam kayıt, tercihen 1+ dk) | Byte düzeninin, endian'ın ve gerçek alan sırasının doğrulanması | Donanım/test ekibi | `F2-*` gerçek veri kabulü, `F0-017` | **EKSİK** |
| E-02 | Resmî `.bin` format dokümanı | Bölüm 8.2/8.3 taslakları yerine kesin sözleşme | Donanım/firmware ekibi | `F0-004`, `F0-005`, `F0-008` | **EKSİK** |
| E-03 | CRC/checksum tanımı (algoritma, polinom, kapsam, alan konumu) | Bozuk kayıt tespitinin doğrulanabilmesi | Firmware ekibi | `F0-008`, `F0-010` | **EKSİK** |
| E-04 | Kanal kataloğu (kanal adı, birim, sample rate, gain/offset) | Ham → fiziksel dönüşüm ve Data Explorer ağacı | Sistem mühendisliği | `F0-007`, `F1-011` | **EKSİK** |
| E-05 | BIT test kataloğu (`test_id`, `component_id`, kod → anlam) | BIT sonucunun okunabilir gösterimi | Donanım ekibi | `F3-047` civarı BIT paneli | **EKSİK** |
| E-06 | Transmisyon alan tanımı ve START/STOP ilişkilendirme kuralı | `TransmissionInterval` türetimi | Sistem mühendisliği | `F1-015`, `F3-050` | **EKSİK** |
| E-07 | Zaman kaynağı bilgisi (tick frekansı, GPS/PPS var mı, drift beklentisi) | Kanonik ns dönüşümü ve senkron kalite göstergesi | Donanım ekibi | `F0-011` | **EKSİK** |
| E-08 | Firmware/format sürüm listesi | Decoder sürüm seçimi ve uyumluluk tablosu | Firmware ekibi | `F0-008`, `F2-*` sürüm testi | **EKSİK** |
| E-09 | Canlı akış protokol tanımı (taşıma, port, paket, bant genişliği) | Faz 5 canlı kaynak | Sistem/yazılım ekibi | `F5-*` | **EKSİK** (Faz 5'e kadar bloke değil) |
| E-10 | Hedef ölçüm bilgisayarı özellikleri | Performans bütçesinin gerçek donanımda ölçülmesi | Proje sahibi | `F0-014` | **EKSİK** |

E-01 ve E-02 gelene kadar Bölüm 8.2/8.3 **taslak** olarak kalır; bu taslağa göre yazılan decoder, gerçek dosya geldiğinde
`format detection` ve sürüm alanı üzerinden ayrıştırılacak biçimde tasarlanır.

## 3. Üretilecek sentetik girdiler

Bunlar eksikliği kapatmaz, yalnız geliştirmeyi ilerletir. Hepsi `tests/fixtures/` altında izlenir
(`.gitignore` bu yolu `*.bin` kuralından muaf tutar).

| Fixture | Profil | İçerik | Üreten iş |
| --- | --- | --- | --- |
| `valid_8records.bin` | A | 8 kayıt, `Data00000`–`Data00007`, 0–875 ms, 544 byte | `F0-009` |
| `gap_missing_record.bin` | A | `Data00005` eksik; sıra boşluğu | `F0-010` |
| `truncated_header.bin` | A | 32 byte header kesik | `F0-010` |
| `truncated_last_record.bin` | A | Son kayıt yarım | `F0-010` |
| `crc_error.bin` | A + CRC | Bir kaydın CRC'si bozuk | `F0-010` (E-03'e bağlı) |
| `acoustic_5s_4ch.bin` | B | 4 × 96 kHz hidrofon, 5 s, bilinen 5 kHz ton | `F4-009` civarı |
| `large_1h.bin` | B | ~2,6 GiB, performans ölçümü | Faz 4 performans işleri |

## 4. Format sürüm envanteri

| Sürüm | Tanım yeri | Durum | Not |
| --- | --- | --- | --- |
| Profil A (32 B header + 64 B kayıt) | Bölüm 8.2 | Taslak | CRC alanı yok; `F0-008` ayrı sürüm tanımlar |
| Profil B (blok tabanlı, TLV) | Bölüm 8.3 | Taslak | Ham akustik veri için; `F4-009` |
| Gerçek cihaz formatı | — | **Bilinmiyor** | E-01/E-02 gelene kadar tanımsız |

## 5. Güncelleme kuralı

Yeni bir örnek dosya veya sözleşme geldiğinde: ilgili satır `EKSİK` → `MEVCUT` yapılır, dosya adı ve alınma tarihi yazılır,
etkilediği iş kimlikleri gözden geçirilir. Bu tablo `F0-015` ve `F0-017` kabul işlerinde tekrar kontrol edilir.
