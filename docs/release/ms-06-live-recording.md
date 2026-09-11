# Milestone kabul tutanağı — `ms/06-live-recording`

- **Faz:** 5 — Canlı veri, bağlantı ve kayıt
- **Sürüm:** `v3.0.0`
- **Etiketler:** `v3.0.0` ve `ms/06-live-recording` (aynı commit)
- **Tarih:** 2026-09-11
- **Kabul işi:** `F5-041`

## 1. Faz kabul ölçütü

Plan Faz 5 kabulü: *"UDP/TCP/serial akışı, bağlantı durumu, canlı grafik,
kayıt ve tekrar okuma doğrulanmalı; dayanıklılık koşusu geçmeli."*

`F5-041` kabul kontrolü: *"Üç adaptör, yeniden okuma ve dayanıklılık
kontrolleri geçer."*

## 2. İşler ve çıktılar (41 iş: `F5-001`–`F5-041`, kabul `F5-041`)

Her iş kendi commit'i ve `vX.Y.0` etiketiyle kapandı: `v2.1.0` (`F5-001`) –
`v2.40.0` (`F5-040`), ardından bu tutanakla `v3.0.0`. Ayrıntı: `plan.md`
Bölüm 22 Faz 5 tablosu ve `docs/notes/worklog.md`.

| Blok | İşler | Çıktı |
| --- | --- | --- |
| Protokol ve bağlantı | `F5-001`–`F5-011` | Wire sözleşmesi, bağlantı durum makinesi, dosya replay kaynağı, **UDP/TCP/serial** adaptörleri |
| Canlı veri yolu | `F5-012`–`F5-018` | Sıra izleyici, canlı zaman ekseni, sabit kapasiteli halka tampon, sınırlı paket kuyruğu, yeniden bağlanma, bağlantı ayarları |
| Canlı arayüz | `F5-019`–`F5-024` | Bağlantı durumu tek kaynaktan, canlı sağlık kartı, `RecordingRepository` uyumlu canlı depo, worker, sona takip, canlı/playback ayrımı |
| Kayıt | `F5-025`–`F5-033` | Sürümlü başlık, kayıt serileştirme, 125 ms biriktirme, disk kuyruğu, güvenli kapatma, disk hatası, dosya değiştirme, Record/Stop arayüzü, kopma davranışı |
| Doğrulama | `F5-034`–`F5-040` | Canlı BIT/TX panosu, yeniden okuma karşılaştırması, seed'li bozucu, dayanıklılık koşusu ve değerlendirmesi, canlı modda mockup kontrolü |

## 3. Üç adaptör — hepsi geçti

| Adaptör | İşler | Testler | Sonuç |
| --- | --- | --- | --- |
| **UDP** | `F5-005`, `F5-006` | 26 (`test_udp_receiver`, `test_udp_live_source`) | **GEÇTİ** |
| **TCP** | `F5-007`, `F5-008` | 23 (`test_tcp_connection`, `test_tcp_live_source`) | **GEÇTİ** |
| **Serial** | `F5-009`, `F5-010` | 58 (`test_serial_connection`, `test_serial_live_source`) | **GEÇTİ** |

Üçü de aynı `LiveSource` sözleşmesini karşılar (`docs/live/protocol-contract.md`);
tüketici tarafı hangi taşıma katmanının bağlı olduğunu bilmez. Bu yüzden
kuyruk, sıra izleyici, canlı depo ve arayüz kodu üç adaptörde de aynıdır ve
ayrı ayrı test edilmesi gerekmez.

Taşımaya özgü davranışlar ayrı ayrı doğrulandı: UDP'de parça birleştirme ve
500 ms hepsi-ya-hiçbiri zaman aşımı, TCP'de uzunluk önekli çerçeveleme ile
EOF/RST ayrımı, serialde `SYNC` yeniden hizalama ve CRC32 kuyruğu.

> **Serial bağımlılığı:** `pyserial` isteğe bağlı bir ekstradır (`live`) ve bu
> makinede **kurulu değildir**. Serial testleri enjekte edilen bir
> `transport_factory` ile gerçek kodu koşturur; `pyserial` yokluğunda
> `SerialConnection.connect()` açık bir hata verir, sessizce başarısız olmaz.
> Gerçek seri port donanımıyla doğrulama yapılmadı (Bölüm 8).

## 4. Yeniden okuma — geçti

`F5-035`: canlı akış kaydedilip **üretim dosya deposuyla**
(`FileRecordingRepository`) yeniden açıldı ve geri okunanlar akışın
*kendisiyle* karşılaştırıldı. Referans yazıcıdan ya da okuyucudan
sorulmadı; testin paketleri kurarken kullandığı değerler.

| Karşılaştırılan | Sonuç |
| --- | --- |
| Örnekler (8 kanal × 24 pencere, değer ve zaman damgası) | **eşleşti** |
| 125 ms sınırları (ardışık fark, boşluk sonrası ızgara) | **eşleşti** (fark kümesi tam `{125 ms}`) |
| Olaylar (BIT arızası, doğru pencere; TX aralığı sınırları) | **eşleşti** |

Bu iş **gerçek bir kusuru** ortaya çıkardı ve düzeltti: `RecordAccumulator`
`bit_status` ve `tx_status` alanlarını her zaman `0` yazıyordu, yani canlı
akışta bir bileşen arızalansa bile kayıt dosyası "her şey yolunda" olarak
geri okunuyordu — sessiz veri kaybı. İkisi de artık paketteki gerçek
BIT/TX verisinden, okuma tarafının **kendi tablolarından** türetiliyor.

## 5. Dayanıklılık — geçti

### 5.1 Bozucu ile ölçüm (`F5-036`, `F5-037`)

Seed'li `ImpairedSource` kayıp, sıra dışı, tekrar ve burst üretir; kaç paket
bozduğu bilindiği için canlı katmanın sayaçlarının **doğru** olup olmadığı
söylenebilir. Dört yüzey doğrulandı: sayaçlar, kuyruk sınırı (burst altında
her `put()` sonrası ölçülerek), yeniden bağlanma (başarı, vazgeçme, tavanlı
backoff) ve UI tepkisi.

Tekrar üretilebilirlik, iki aynı seed'li koşu arasına 1000 global
`random.random()` çağrısı sıkıştırılarak kanıtlandı: modül global
rastgeleliğe dokunmadığı için çıktı bit bit aynı kaldı.

### 5.2 2 saatlik koşu (`F5-038`, `F5-039`)

`docs/live/results/endurance.json` → `endurance-verdict.json`; yorum
`docs/live/endurance-report.md`.

| Ölçüt | Ölçülen | Kural | Sonuç |
| --- | --- | --- | --- |
| Bellek bütçesi | son çeyrek / ilk çeyrek = **1,0034** | ≤ 1,10 | **GEÇTİ** |
| Beklenen kayıp | **617/57 600 = %1,07** (profil %1) ve 56 983 + 617 = 57 600 | ≤ %25 bağıl sapma **ve** korunum yasası | **GEÇTİ** |
| Kayıt bütünlüğü | **56 983 kayıt** geri okundu, CRC/sıra/artık bayt kusursuz | tek kusur bile bozar | **GEÇTİ** |

Koşu 57 600 adet 125 ms penceresi (tam 2 saatlik veri) üretti. Bütünlük,
yazıcının sayacına bakarak değil dosyalar kapandıktan sonra **geri
okunarak** ölçüldü; her kaydın CRC'si ADR-011 §2.2'ye göre `zlib.crc32` ile
yeniden hesaplandı.

## 6. Canlı modda çalışan mockup panosu

`F5-040`: canlı akış sürerken **ve** kayıt alınırken mockup'ın dokuz
bölgesinin hepsi yerinde ve görünür (bölge tanımı
`tests/gui/test_mvp_mockup_regions.py` ile birebir paylaşılıyor); üç sütunlu
yerleşim korunuyor; canlı sekmesi Overview'in yerini almıyor, yanına
ekleniyor.

Bu iş de iki **gerçek kusur** buldu ve düzeltti:

1. Saf canlı modda merkez alan "veri yok" ekranında kalıyordu — canlı veri
   çizilirken bölge 3 görünmüyordu.
2. Durum çubuğu ile kayıt kartı, henüz dosya oluşmamışken farklı boşluk
   işareti kullanıyordu.

## 7. Zorunlu kontroller

| # | Kontrol | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 7.1 | Kod kalitesi: lint, biçim, tip | **GEÇTİ** | `ruff check` temiz, `ruff format --check` temiz (533 dosya), `pyright` strict **0 hata** |
| 7.2 | Test paketi | **GEÇTİ** | 4576 test toplandı; tam koşu yeşil (çıkış kodu 0, 0 FAILED) |
| 7.3 | Üç adaptör | **GEÇTİ** | Bölüm 3 — UDP 26, TCP 23, serial 58 test |
| 7.4 | Yeniden okuma | **GEÇTİ** | Bölüm 4 — `F5-035`, 15 test |
| 7.5 | Dayanıklılık koşusu | **GEÇTİ** | Bölüm 5 — `F5-037` 18 test, `F5-038` 14 test, `F5-039` 26 test, üç ölçüt de `gecti` |
| 7.6 | Canlı modda mockup yerleşimi | **GEÇTİ** | Bölüm 6 — `F5-040`, 20 test |
| 7.7 | Kayıt güvenliği (flush, disk hatası, dosya değiştirme) | **GEÇTİ** | `F5-029`/`F5-030`/`F5-031`; hata durumunda "başarılı kayıt" mesajı verilmiyor |
| 7.8 | Her iş kendi commit + `vX.Y.0` etiketi | **GEÇTİ** | `v2.1.0` – `v2.40.0` (40 etiket) + `v3.0.0` |

**Zorunlu kontrollerin tamamı geçti.**

## 8. Gerçek veri ve donanımla doğrulanmayan maddeler

> `ms/04-mvp` §5'teki kural sürüyor: sentetik fixture ile geçen test, gerçek
> donanım doğrulaması değildir. Aşağıdaki maddeler **açık** kalır.

| Konu | Durum | Takip |
| --- | --- | --- |
| Gerçek sonar cihazından UDP/TCP akışı | **DOĞRULANMADI** | Elde cihaz yok (D-01); doğrulama `docs/live/protocol-contract.md` sözleşmesine karşı yapıldı. Gerçek cihaz farklı bir çerçeveleme kullanıyorsa adaptör uyarlanır, tüketici katmanı değişmez |
| Gerçek seri port donanımı | **DOĞRULANMADI** | `pyserial` bu makinede kurulu değil; testler enjekte edilen transport ile gerçek çözümleme kodunu koşturuyor |
| Gerçek ağ koşulları (gerçek kayıp, jitter, MTU parçalanması) | **SİMÜLE EDİLDİ** | `F5-036` bozucusu seed'li ve tekrar üretilebilir; gerçek ağ davranışı bundan çıkarılamaz |
| 2 saatlik koşu gerçek zamanda | **SİMÜLE EDİLDİ** | Koşu 2 saatlik *veri* üretir, 2 saat beklemez. Ölçülen üç şey (bellek eğilimi, kayıp muhasebesi, bütünlük) süreye değil paket sayısına bağlı; ayrıntı `docs/live/endurance-report.md` §5 |
| 2 saat boyunca sürekli kuyruk/disk baskısı | **YAPILMADI** | Burst altında kuyruk sınırı `F5-037`'de ayrıca doğrulandı, ama iki saat sürekli baskı denenmedi |
| Süreç RSS'i (işletim sistemi çalışma kümesi) | **ÖLÇÜLMEDİ** | Ölçülen `tracemalloc` ile tutulan Python belleği; fragmentasyon ve NumPy arenaları kapsam dışı |
| Paketlenmiş uygulamada canlı bağlantı | **YAPILMADI** | Paketleme Faz 6 (`F6-*`); kabul turu `F6-034` |
