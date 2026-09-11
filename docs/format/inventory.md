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

Aşağıdaki tablo **depoda gerçekten bulunan** fixture'ları listeler
(`F6-027` ile gerçek dosyalara göre düzeltildi; sürüm sütunu
`docs/format/decoder-guide.md` ile aynı ayrımı kullanır).

| Fixture | Sürüm | Boyut | İçerik | Üreten |
| --- | --- | --- | --- | --- |
| `valid_8records.bin` | A v1 | 544 B | 8 kayıt, `Data00000`–`Data00007`, 0–875 ms | `tools/make_fixture.py` (`F0-009`) |
| `valid_8records_v2.bin` | **A v2** | 580 B | Aynı içerik, header ve kayıt CRC'leriyle | `tools/make_corrupt_fixtures.py` → `build_valid_v2_fixture()` (`F2-014`) |
| `gap_missing_record.bin` | A v1 | 544 B | `Data00005` eksik; sıra boşluğu | `tools/make_corrupt_fixtures.py` (`F0-010`) |
| `name_index_mismatch.bin` | A v1 | 544 B | Ad ile `sequence_no` uyuşmuyor | `tools/make_corrupt_fixtures.py` |
| `truncated_header.bin` | A (kesik) | 20 B | Header 32 bayta tamamlanmıyor | `tools/make_corrupt_fixtures.py` |
| `truncated_last_record.bin` | A v1 | 524 B | Son kayıt yarım (7,69 kayıt) | `tools/make_corrupt_fixtures.py` |
| `unsupported_version.bin` | A (`version=99`) | 544 B | Desteklenmeyen sürüm alanı | `tools/make_corrupt_fixtures.py` |
| `crc_error.bin` | **A v2** | 580 B | Bir kaydın CRC'si bozuk; diğerleri sağlam | `tools/make_corrupt_fixtures.py` (`F2-014`) |
| `acoustic_8records.bin` | **B** | 385 472 B | 4 hidrofon × 8 kayıt, 48 kHz `int16`, kanal başına 997/1499/2003/3001 Hz ton | `tools/make_acoustic_fixture.py` (`F4-010`) |

Profil B fixture'ı **48 kHz**'dir (taslaktaki 96 kHz değil) ve kayıt
başına kanal başına **6000** örnek taşır. SHA-256'sı üreticide sabit
tutulur; fixture yeniden üretildiğinde değişirse bu bir hata sayılır.

Büyük (~GiB) performans dosyaları depoda tutulmaz; performans ölçümleri
gerektiğinde yerel olarak üretilir.

## 4. Format sürüm envanteri

> `F6-027` ile güncellendi. Üç sürüm **ayrı** sözleşmelerdir ve
> karıştırılmazlar; ayrıntılı karşılaştırma ve decoder eşlemesi için
> `docs/format/decoder-guide.md`.

| Sürüm | Magic / sürüm alanı | Boyutlar | CRC | Durum | Not |
| --- | --- | --- | --- | --- | --- |
| **Profil A v1** | `SONARBIN`, `version=1` | 32 B header + 64 B kayıt | **yok** | Uygulanmış — **okunur**, yazılmaz | Bölüm 8.2 taslağının ilk hâli; `valid_8records.bin` (544 B) |
| **Profil A v2** | `SONARBIN`, `version=2` | 36 B header + 68 B kayıt | **var** (header + kayıt) | Uygulanmış — **okunur ve yazılır** | `ADR-011`; uygulamanın ürettiği sürüm (`DEFAULT_FORMAT_VERSION = 2`); `valid_8records_v2.bin` (580 B) |
| **Profil B** | `SNRBIN\x1a\x00`, `version=1` | 256 B dosya başlığı + 64 B/kanal + blok tabanlı kayıt | **var** | Uygulanmış — okunur | Ham akustik, 48 kHz `int16`, kayıt başına 6000 örnek/kanal; `F4-009`; `acoustic_8records.bin` |
| Gerçek cihaz formatı | — | — | — | **Bilinmiyor** | E-01/E-02 gelene kadar tanımsız; yukarıdakiler plan taslağına dayanır |

**Sürüm alanı her iki Profil A sürümünde de offset 8'dedir** (`uint16`);
sürümü öğrenmek için önce sürümü bilmek gerekmez. `version`,
`header_size` ve `record_size` çapraz doğrulanır — uyuşmazlıkta dosya
reddedilir, en yakın sürüme düşülmez.

**Sürümler arası dönüştürme yapılmaz.** Bir v1 dosyası v1 olarak kalır:
CRC'si hiç olmamış veriye sonradan CRC hesaplamak, yalnız dönüştürme
anındaki baytları doğrulayan — yani hiçbir şeyi doğrulamayan — bir alan
üretirdi. `is_crc_validated(version)` bu ayrımı açıkça taşır.

## 5. Güncelleme kuralı

Yeni bir örnek dosya veya sözleşme geldiğinde: ilgili satır `EKSİK` → `MEVCUT` yapılır, dosya adı ve alınma tarihi yazılır,
etkilediği iş kimlikleri gözden geçirilir. Bu tablo `F0-015` ve `F0-017` kabul işlerinde tekrar kontrol edilir.
