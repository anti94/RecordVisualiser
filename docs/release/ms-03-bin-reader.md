# Milestone kabul tutanağı — `ms/03-bin-reader`

- **Faz:** 2 — Parser, indeks ve kayıtlı veri
- **Sürüm:** `v0.102.0`
- **Etiketler:** `v0.102.0` ve `ms/03-bin-reader` (aynı commit)
- **Tarih:** 2026-09-09
- **Kabul işi:** `F2-041`

## 1. Faz kabul ölçütü

Plan Bölüm 22.3: *"Örnek dosya güvenilir çözümlenmeli; kanal, olay ve zaman
sorguları referans değerlerle eşleşmeli."*

`F2-041` kabul kontrolü: *"Geçerli, bozuk, CRC'li, çoklu dosya ve sorgu
kontrolleri geçer."*

## 2. İşler ve çıktılar (41 iş)

| İş | Çıktı | Commit |
| --- | --- | --- |
| `F2-001` | Profil A alan sabitleri ve veri modeli | `7011f27` |
| `F2-002` | Little-endian header/kayıt okuyucusu | `572b0f1` |
| `F2-003` | Magic ve sürüm doğrulaması | `b8a049e` |
| `F2-004` | Eksik header ve boyut sınırları | `d7f4361` |
| `F2-005` | Tek `Data` kaydını çözümleme | `6063b13` |
| `F2-006` | Ardışık kayıt iterator'u | `6821a9d` |
| `F2-007` | 125 ms kayıt zamanı → kanonik ns | `643f92d` |
| `F2-008` | Sıra ve zaman boşluğu raporu | `799b5b7` |
| `F2-009` | Kesik son kayıt raporu | `c5a0609` |
| `F2-010` | Ad / `sequence_no` tutarlılığı | `36dead5` |
| `F2-011` | Tekrarlı ve sıra dışı kayıt raporu | `9b992de` |
| `F2-012` | Sürüme göre decoder seçimi | `74088ab` |
| `F2-013` | CRC-32/ISO-HDLC hesaplaması | `a172271` |
| `F2-014` | CRC alanlı format doğrulaması | `ded1933` |
| `F2-015` | Bilinmeyen paket teşhisi ve resync | `cadcb56` |
| `F2-016` | 32/64 byte fixture yazıcısı | `01ffa02` |
| `F2-017` | Kesik/bozuk/boşluklu fixture'lar (K-01,02,03,05,06) | `be5e96c` |
| `F2-018` | CRC destekli fixture (K-04) | `2ec1560` |
| `F2-019` | Sensör alanı → kanal metadata eşlemesi | `8be2bbe` |
| `F2-020` | Scale ve offset dönüşümü | `2fb0c87` |
| `F2-021` | Calibration seçimi ve kalite eşlemesi | `33ad0ba` |
| `F2-022` | BIT maskesi → durum ve geçiş olayları | `b61ab4c` |
| `F2-023` | TX durumu → başlangıç/bitiş aralıkları | `7be2eae` |
| `F2-024` | Parser teşhisleri → sistem olayları | `42a3abb` |
| `F2-025` | Cihaz tick dönüşüm adaptörü | `85e428d` |
| `F2-026` | Wraparound / saat reseti ayrımı | `0bd93b5` |
| `F2-027` | Tanımlı drift düzeltmesi | `c088986` |
| `F2-028` | Kayıt offseti ve zaman indeksi | `e23f038` |
| `F2-029` | Kanal ve olay indeksleri | `210fc91` |
| `F2-030` | Kaynak fingerprint + parser sürümü | `adf20e6` |
| `F2-031` | İndeks dosyasının atomik yazımı | `a45ae98` |
| `F2-032` | Geçerli indeksin yeniden kullanımı | `4516fc7` |
| `F2-033` | Dosya metadata ve kanal listesi | `b8799af` |
| `F2-034` | İndeksli zaman aralığı sorgusu | `2f30c9b` |
| `F2-035` | Zaman ve kategoriye göre olay sorgusu | `7cb05e6` |
| `F2-036` | Çoklu kayıt, ayrı kimlikler | `90652ed` |
| `F2-037` | Decoded öğeden ham offsete erişim | `ae0ee1e` |
| `F2-038` | Okuyucu kaynaklarının güvenli kapanışı | `e072e74` |
| `F2-039` | Bağımsız golden sonuçlarıyla karşılaştırma | `03d0460` |
| `F2-040` | Kaynak dosyanın değişmediğinin doğrulanması | `80823d0` |
| `F2-041` | Bu tutanak ve milestone kabul koşusu | *(bu commit)* |

## 3. Zorunlu kontroller

`F2-041` kabul kontrolündeki beş başlığın dayanağı
`tests/integration/test_ms03_bin_reader.py`'dir (15 test); ayrıntılı alan-alan
doğrulama ilgili işlerin kendi testlerindedir.

| # | Kontrol | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 3.1 | **Geçerli dosya**: örnek dosya güvenilir çözümlenir | **GEÇTİ** | `valid_8records.bin` → 8 kayıt, 8 kanal, 544 byte, v1, 1000 ms pencere; hiçbir kalite bayrağı yok. `RecordingRepository` protokolü (`F1-016`) gerçek okuyucuyla da karşılanıyor |
| 3.2 | **Bozuk dosya**: K-01–K-06 önceden belirlenen sonucu üretir | **GEÇTİ** | K-02 → 7 tam kayıt; K-03 → 8 kayıt + `GAP_BEFORE` bayrağı (interpolasyon yok); K-06 → 8 kayıt, kayıt atılmaz; K-01 ve K-05 → tipli `FormatError` ile reddedilir. Ayrıntı: `test_corrupt_fixtures.py` (14 test) |
| 3.3 | **CRC'li dosya**: tek byte bozulması yakalanır | **GEÇTİ** | Sağlam v2 (580 byte) → CRC hatası yok; `crc_error.bin` → yalnız `Data00003` işaretli (offset 240), verisi NaN, diğer 7 kayıt sağlam, 1 `ERROR` olayı. Ayrıntı: `test_crc_fixture.py` (8 test) |
| 3.4 | **Çoklu dosya**: kimlikler çakışmaz | **GEÇTİ** | İki dosya aynı anda açık: 2 farklı `recording_id`, 16 benzersiz kanal kimliği (`<id>:<kanal>`), olaylar kaynak kaydı koruyor, `close_all()` sonrası koleksiyon boş |
| 3.5 | **Sorgu**: zaman aralığı, bütçe ve filtreler | **GEÇTİ** | `[başlangıç, bitiş)` sınırları (1 kayıt / 4 kayıt / aralık dışı → boş ama geçerli `DataChunk`); `max_points` bütçesi uygulanıyor; olay filtreleri kaynak ve severity'ye göre yalnız eşleşenleri döndürüyor; bilinmeyen kanal `KeyError` |
| 3.6 | Referans değerlerle eşleşme (bağımsız golden) | **GEÇTİ** | `F2-039`, 17 test: beklenen değerlerin tamamı `fixture-valid-8records.md` ve `channel-map.md` §2'den elle aktarıldı — kanal yolları/birimleri, §3 tablosundaki her örnek değeri, zaman ızgarası, 1 BIT arızası (t=500 ms, bit 8), 1 TX aralığı (250→750 ms, ±125 ms), dosya SHA-256 ve CRC-32 `0x7314EC15` |
| 3.7 | Ham verinin değişmezliği | **GEÇTİ** | `F2-040`, 23 test: sekiz fixture'ın (geçerli v1/v2 + K-01–K-06) aç/kapat öncesi ve sonrası SHA-256'sı aynı; salt okunur dosya bile açılabiliyor; türetilmiş indeks ayrı `.sidx` dosyası |
| 3.8 | Dosya tanıtıcısı ve kilit sızıntısı yok | **GEÇTİ** | `F2-038`, 4 test: kapanıştan sonra kaynak rename+unlink edilebiliyor (Windows'ta açık handle olsa hata verirdi); başarısız açılış da kilit bırakmıyor; 20 ac/kapat döngüsü temiz |
| 3.9 | Kod kalitesi: lint, biçim, tip | **GEÇTİ** | `ruff check` temiz, `ruff format --check` temiz (175 dosya), `pyright` strict 0 hata |
| 3.10 | Test paketi | **GEÇTİ** | **858 test**, 0 hata, 0 atlanan |
| 3.11 | Her iş kendi commit'i ve `vX.Y.0` etiketiyle kapandı | **GEÇTİ** | `v0.62.0` – `v0.102.0`, 41 sürüm etiketi |

**Zorunlu kontrollerin tamamı geçti.**

## 4. Ölçülen performans değerleri

1 saatlik Profil A dosyası (`28 800` kayıt, 1,76 MiB) `tools/make_fixture.py` ile
üretilip ölçüldü. Geliştirme makinesi, Python 3.9.13. Tek koşu; kabul için
`F4` performans işlerinde 5 tekrarın medyanı kullanılacaktır.

| Ölçüm | Sonuç | Bütçe | Değerlendirme |
| --- | --- | --- | --- |
| Dosya açılışı (indeks cache'i yok) | **230 ms** | P-02 ≤ 2 s | Bütçe içinde; ancak P-02 tanımı kanal ağacının dolmasını da kapsıyor, o zincir henüz bağlı değil (§5) |
| Dosya açılışı (indeks yeniden kullanıldı) | **98 ms** | — | `F2-032` cache'inin ölçülen kazancı: 2,4× |
| Tam aralık sorgusu (`max_points=2000`) | **122 ms** | P-07 ≤ 150 ms | Bütçe içinde |
| Olay taraması (ilk çağrı, tüm dosya) | **768 ms** | — | Tanımlı bütçesi yok; ikinci çağrı **0,01 ms** (önbellekli). Faz 4'te izlenecek: P-06 (event'e gitme ≤ 200 ms) ilk taramanın açılışa kaydırılmasını gerektirebilir |

## 5. Gerçek veri ve donanımla doğrulanmayan maddeler

> Faz 0 ve Faz 1 tutanaklarındaki kuralın devamı: aşağıdakiler "doğrulandı"
> sayılmaz. Sentetik fixture ile geçen test, gerçek donanım doğrulaması değildir.

| Konu | Durum | Neden |
| --- | --- | --- |
| Gerçek cihaz `.bin` kaydı | **DOĞRULANMADI** | Elde gerçek kayıt yok (D-01). Tüm doğrulama, Faz 0'da **kendi yazdığımız** format sözleşmesine (`profile-a.md`) uyan sentetik dosyalarla yapıldı. Gerçek format farklı çıkarsa bu fazın decoder'ı değişir |
| CRC algoritması ve kapsamı | **SÖZLEŞME, ONAY BEKLİYOR** | `ADR-011` durumu hâlâ "Önerildi" (E-03). CRC-32/ISO-HDLC seçimi ve alan konumu bizim kararımız; gerçek cihaz farklı bir CRC kullanıyorsa `F2-013`/`F2-014` yeniden yazılır |
| Kanal kataloğu (CH0–CH7 yolları, birimler) | **ÖNERİ** | `channel-map.md` açıkça "gerçek kanal kataloğu değildir" diyor (E-04/E-05). `F2-019` o öneriyi kodluyor; gerçek katalog gelince değişecek |
| Profil A'da tick/jitter/drift | **ÖLÇÜLEMEZ** | Profil A ham sayaç taşımıyor (`tick_hz = 0`); `F2-025`–`F2-027` yalnız sentetik değerlerle ve ADR-003'ün kendi referans örnekleriyle test edildi. Gerçek `tick_hz` bilinmiyor (E-07) |
| Profil B (~2,6 GiB, 96 kHz) okuma | **YAPILMADI** | Bu faz Profil A ile sınırlıydı. P-03 (büyük kayıtta metadata ≤ 5 s) ve P-09 (bellek doğrusal büyümemeli) **ölçülmedi**; mmap/lazy yükleme Faz 4 işi |
| UI'dan `.bin` açma | **BAĞLI DEĞİL** | Okuyucu çalışıyor ama **Open .bin File** düğmesi henüz repository'ye bağlanmadı; bu `F3-001` ve sonrasının işi. README bu durumu açıkça yazıyor |
| P-01, P-04, P-05, P-06, P-08 | **DEĞİŞMEDİ** | Faz 1 tutanağındaki durum geçerli; özellikle P-04 sapması (1M noktada 7,4 FPS) hâlâ açık ve `F4-056`/`F4-057`'ye bağlı |

## 6. Bu fazda bulunan ve düzeltilen tutarsızlıklar

| Bulgu | Nerede | Çözüm |
| --- | --- | --- |
| Kabuk aracı heredoc içindeki `\xNN` kaçış dizilerini kaynak dosyaya yazmadan önce yorumluyor, dosyaya gerçek NUL bayt sızdırıyordu | `F2-010` fixture üreticisi | `\x00` yerine `bytes(3)`; dosya içeriği Write/Edit araçlarıyla yazılıyor. Ders commit mesajına işlendi |
| `Union` yazımı Python 3.9'da çalışma anında `X | Y` ile kurulamıyor (tip takma adı gövdede değerlendiriliyor) | `F2-011` | `typing.Union` kullanıldı; `from __future__ import annotations` yalnız açıklamaları erteliyor |
| Aynı formül iki yerde (test yardımcısı + araç) tekrarlanıyordu | `F2-016`, `F2-018` | Geçerli v1/v2 fixture formülleri `tools/make_fixture.py`'ye taşındı; `tests/golden_bytes.py` oradan içe aktarıyor. Tek doğruluk kaynağı |
| `Event` modeli parser teşhislerinin bayt offsetini taşıyamıyordu | `F2-024` | `Event.source_offset` eklendi (geriye dönük uyumlu, negatif değer reddediliyor) |
| Kabul kontrolü "kaynak offseti" isterken `SequenceGap` kendi offsetini taşımıyor (kayıp kayıt hiç yazılmadı) | `F2-024` | Dönüştürücü, boşluktan sonraki kaydın offsetini çağırandan alıyor; `fixture-corrupt.md` K-03'teki "offset 352 öncesinde" çerçevesiyle aynı |
| Belge BIT grubunu kısaca `Thermal` yazıyor, katalogdaki ad `Thermal Management` | `F2-039` | Test bit numarası (8) ve durumu tam eşleştiriyor, ad için önek kontrolü yapıyor; fark tutanakta kayıtlı |
| Milestone testinde son kaydın offseti `dosya_boyutu - 64` varsayılmıştı; v2 (68 byte) ve kesik kuyruklu dosyada yanlış | `F2-041` | İlk kaydın offseti (= header boyutu) kullanılıyor; her iki sürümde ve kesik dosyada geçerli |

## 7. Sonraki faza taşınan açık işler

| Konu | Takip |
| --- | --- |
| `.bin` okuyucusunun UI'ya bağlanması (dosya seçici → repository → kanal ağacı) | `F3-001`–`F3-005` |
| Olay taramasının ilk çağrı maliyeti (768 ms/1 saat) | Faz 4 performans işleri; P-06 ile birlikte |
| Downsample piramidi (P-04 sapması) | `F4-056`, `F4-057` |
| Profil B, mmap/lazy yükleme, P-03 ve P-09 ölçümü | Faz 4 |
| Gerçek kayıt gelince: format, CRC ve kanal kataloğu farkının işlenmesi | E-03, E-04, E-05, E-07 |
| Gerçek `tick_hz` ile tick/drift doğrulaması | E-07 |

## 8. Karar

**Milestone `ms/03-bin-reader` kapatılır.**

Gerekçe: fazın kabul ölçütü karşılanmıştır — örnek dosya güvenilir
çözümleniyor; kanal, olay ve zaman sorguları Faz 0'da **parser yazılmadan
önce** sabitlenmiş referans değerlerle birebir eşleşiyor (`F2-039`). Bozuk
dosyaların altı senaryosu da önceden belirlenen sonucu üretiyor ve hiçbiri
uygulamayı çökertmiyor ya da sessizce yutulmuyor. Ham veri değişmezliği
ölçülerek kanıtlandı (`F2-040`), dosya tanıtıcısı sızıntısı yok (`F2-038`).

Fazın sınırı net: doğrulama, gerçek cihaz formatı yerine **kendi yazdığımız
sözleşmeye** karşıdır. §5 bunu madde madde ayırıyor; gerçek kayıt geldiğinde
farkın nerede işleneceği açık işlere bağlanmıştır.

**Uyarı:** Faz 3 (`ms/04-mvp`) kabulü, gerçek `.bin` kaydı ve
P-01/P-04/P-05/P-06/P-08 hedeflerinin gerçek ekranda doğrulanması olmadan
kapatılamaz.

| | |
| --- | --- |
| Hazırlayan | Geliştirme (otomatik koşu, 2026-09-09) |
| Onay | ☐ Proje sahibi ☐ Test mühendisliği |
