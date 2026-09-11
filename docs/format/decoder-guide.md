# Format ve decoder kılavuzu — `F6-027`

Bu belge **üç format sürümünü** birbirinden ayırır. Üçü de `.bin` uzantısı
taşır ve dosya adına bakarak ayırt edilemezler. Karıştırıldıklarında
decoder yanlış bayt sınırlarından okur ve **makul görünen yanlış veri**
üretir — bu, açıkça hata veren bir okumadan daha tehlikelidir.

Ayırt etmenin tek doğru yolu **dosyanın kendi başlığıdır**: magic ve
sürüm alanı. Dosya adı, klasör ya da boyut ipucu değildir.

## 1. Üç sürüm, tek bakışta

| | **Profil A v1** | **Profil A v2** | **Profil B** |
| --- | --- | --- | --- |
| Magic | `SONARBIN` | `SONARBIN` | `SNRBIN\x1a\x00` |
| Sürüm alanı | `1` | `2` | `1` (kendi uzayında) |
| Dosya başlığı | **32 bayt** | **36 bayt** | 256 bayt + kanal tablosu |
| Kayıt | **64 bayt** | **68 bayt** | değişken; blok tabanlı |
| CRC | **yok** | **var** (header + kayıt) | var (header, kayıt, indeks) |
| Kanal | sabit **8** | sabit **8** | kanal tablosundan (bu profilde 4 hidrofon) |
| Kanal başına örnek | kayıt başına **1** | kayıt başına **1** | kayıt başına **6000** |
| Örnekleme hızı | 8 Hz | 8 Hz | **48 kHz** |
| Örnek tipi | `float32` | `float32` | `int16` (ham) |
| Sabitler | `io/profile_a_format.py` | aynı modül | `io/profile_b_format.py` |

**Dört bayt, dosyanın tamamını kaydırır.** Bir v2 dosyasını v1 sözleşmesiyle
okursanız ilk kaydın sonundan itibaren her alan 4 bayt kayar: ad alanına
sayı, sayı alanına zaman düşer. `struct` hata vermez; sonuç sadece
yanlış olur.

## 2. Sürüm nasıl belirlenir

Sürüm **tahmin edilmez, okunur**. Profil A başlığının ilk alanları
(`FILE_HEADER_V1 = "<8sHHIIIQ"`):

| Offset | Boyut | Alan |
| --- | --- | --- |
| 0 | 8 | `magic` = `SONARBIN` |
| 8 | 2 (`uint16`) | **`version`** — 1 ya da 2 |
| 10 | 2 (`uint16`) | `header_size` |
| 12 | 4 (`uint32`) | `record_size` |
| 16 | 4 (`uint32`) | `period_us` |
| 20 | 4 (`uint32`) | `channel_count` |
| 24 | 8 (`uint64`) | `start_time_utc_ns` |
| 32 | 4 (`uint32`) | `header_crc32` — **yalnız v2** |

`version` alanı **her iki sürümde de aynı yerdedir: offset 8**. Bu tesadüf
değil, tasarım kararıdır: sürümü öğrenmek için önce sürümü bilmek
gerekmesin diye. `peek_version()` tam başlığı çözmeden yalnız bu alanı
okur, `select_decoder()` da doğru okuyucu çiftini seçer.

### 2.1 Sürüm tek başına yeterli değil — çapraz doğrulanır

`version`, `header_size` ve `record_size` **birlikte** denetlenir:

| version | header_size | record_size |
| --- | --- | --- |
| 1 | 32 | 64 |
| 2 | 36 | 68 |

Uyuşmazlıkta dosya **reddedilir** (`HeaderContractError`, offset 10 ya da
12). "Sürüm 2 diyor ama 64 baytlık kayıt bildiriyor" durumunda hangisine
güvenileceğini tahmin etmek, sessizce yanlış okumanın kapısını açardı.
Bildirilen boyutlara güvenip ileri okuma da yapılmaz: sabit `struct`
sözleşmesi kullanılır, böylece bozuk bir boyut alanı aşırı bellek
ayırmaya veya sınır dışı okumaya yol açamaz.

Desteklenmeyen bir sürüm (`unsupported_version.bin` fixture'ında `99`)
`UnsupportedVersionError` ile reddedilir — en yakın sürüme düşülmez.

## 3. Profil A v1 — 32/64, CRC'siz

Faz 0'da tanımlanan ilk sözleşme. Referans fixture:
`tests/fixtures/valid_8records.bin` — 32 + 8 × 64 = **544 bayt**
(hexdump: `docs/format/fixture-valid-8records.md`).

Kayıt düzeni (`DATA_RECORD_V1 = "<12sIQ8fII"`):

| Offset | Boyut | Alan |
| --- | --- | --- |
| 0 | 12 | `name` — `DataNNNNN`, `char[12]` |
| 12 | 4 | `sequence_no` (`uint32`) |
| 16 | 8 | `elapsed_us` (`uint64`) |
| 24 | 32 | `sensor_values` — 8 × `float32` |
| 56 | 4 | `bit_status` (`uint32`) |
| 60 | 4 | `tx_status` (`uint32`) |

**CRC alanı yoktur.** Bozulma yalnız **yapısal** kurallarla yakalanır: ad
ile sıra numarasının uyuşması, `elapsed_us`'un 125 ms ızgarasına
oturması, dosya boyutunun kayıt boyutuna tam bölünmesi. Bu kurallar bit
düzeyinde bozulmayı **göremez**; `is_crc_validated(1)` bu yüzden `False`
döner — CRC'si olmayan bir dosya hiçbir yerde sessizce "doğrulanmış"
sayılmaz.

## 4. Profil A v2 — 36/68, CRC'li

`ADR-011`'in getirdiği sürüm. Uygulamanın **yazdığı** sürüm budur
(`recording/header_writer.py`, `DEFAULT_FORMAT_VERSION = 2`). Referans
fixture: `tests/fixtures/valid_8records_v2.bin` — 36 + 8 × 68 =
**580 bayt**.

- Başlık = v1 gövdesi + `uint32 header_crc32` (offset 32).
- Kayıt = v1 kayıt gövdesi + `uint32 record_crc32` (offset 64).
- CRC **CRC-32/ISO-HDLC**'dir ve **kendi alanı hariç** hesaplanır:
  yapının ilk baytından CRC alanının hemen öncesine kadar (ADR-011 §2.2).
  Header için ilk 32 bayt, kayıt için ilk 64 bayt.

### 4.1 İki CRC hatası aynı şey değildir

| | Header CRC hatası | Kayıt CRC hatası |
| --- | --- | --- |
| Sonuç | **Fatal** — dosya açılmaz | Fatal **değil** — okuma sürer |
| Tip | `HeaderCrcMismatchError` (yükseltilir) | `RecordCrcMismatch` (döndürülür) |
| Neden | Header güvenilmezse boyut alanları da güvenilmez | Tek kayıt bozuk; diğerleri sağlam |

Bozuk kayıt **atılmaz**, `CRC_ERROR` işaretlenir ve verisi çizilmez.
Bozuk bir kaydı ortalamaya katmak, o kaydı hiç görmemekten daha
zararlıdır; sessizce atmak ise kullanıcıdan bilgi saklamak olurdu.

### 4.2 v1 ve v2 birlikte yaşar

Uygulama **ikisini de okur**, yalnız v2 yazar. v1 → v2 dönüştürme
**yapılmaz**: dönüştürme, CRC'si hiç olmamış veriye sonradan CRC
hesaplamak olurdu ve o CRC yalnız *dönüştürme anındaki* baytları
doğrulardı — yani hiçbir şeyi. Bir v1 dosyası v1 olarak kalır.

## 5. Profil B — akustik, blok tabanlı

Tamamen ayrı bir sözleşme (`docs/format/profile-b.md`), ayrı magic
(`SNRBIN\x1a\x00`) ve ayrı decoder yolu. Profil A okuyucusuna hiç
girmez; karışma riski pratikte **v1 ile v2 arasındadır**.

Yerleşim: 256 baytlık dosya başlığı + kanal başına 64 baytlık tablo
girdisi, ardından kayıtlar. Her kayıt 48 baytlık başlık + bloklar +
8 baytlık `ENDR` fragman sonu taşır; her blok 16 baytlık başlık ve
8 bayta hizalı payload'dan oluşur.

- Bir kayıt **125 ms**'lik pencereyi taşır (Profil A ile aynı ızgara).
- Bir `SENSOR_RAW` bloğu kanal başına **6000 örnek** `int16` içerir
  (48 000 × 0,125 = 6000; payload 12 000 bayt).
- **Bilinmeyen blok türü atlanır, dosya reddedilmez:** blok başlığı
  okunur, payload çözülmez, `block_size` kadar ilerlenir.
  Genişletilebilirlik böyle sağlanır. Buna karşılık `SENSOR_RAW`
  içindeki **tanınmayan dtype kodu reddedilir** — orada veriyi yanlış
  yorumlama riski vardır.
- Adlandırma Profil A ile **aynı** kuralı kullanır
  (`docs/format/timing-and-naming.md`).

Referans fixture: `tests/fixtures/acoustic_8records.bin` — 4 kanal ×
8 kayıt, 385 472 bayt.

## 6. Hangi modül neyi okur

| Modül | Sorumluluk |
| --- | --- |
| `io/profile_a_format.py` | Profil A v1/v2 sabitleri ve `struct` sözleşmeleri |
| `io/profile_b_format.py` | Profil B sabitleri |
| `io/decoders/version_dispatch.py` | `peek_version` + `select_decoder` |
| `io/readers/binary_reader.py` | v1/v2 header ve kayıt okuma |
| `io/readers/recording_reader.py` | Dosya açılışındaki ortak header doğrulaması |
| `io/decoders/limits.py` | Boyut/sözleşme sınırları (v1 yolu) |
| `io/decoders/crc.py`, `crc_validation.py` | ADR-011 CRC hesabı ve karar kuralları |
| `io/decoders/profile_a.py` | Magic doğrulama, kayıt alanı yürüyüşü |
| `io/decoders/profile_b*.py` | Profil B blokları, zaman, indeks, sorgu |

Profil A ve Profil B yolları **ayrıdır**. Ortak olan tek şey 125 ms zaman
ızgarası ve `DataNNNNN` adlandırmasıdır.

## 7. Sık karıştırılan dört şey

1. **32/64 ile 36/68.** Sürüm alanını okumadan varsayım yapmayın.
   Dört baytlık fark bütün dosyayı kaydırır ve hata vermez.
2. **"125 ms kayıt" ile "125 ms blok".** Profil A'da bir kayıt, kanal
   başına **bir** değerdir; Profil B'de bir kayıt, kanal başına **6000**
   örnektir. Aynı ızgarayı paylaşırlar, taşıdıkları veri üç mertebe
   farklıdır.
3. **Header CRC ile kayıt CRC.** İlki dosyayı açtırmaz, ikincisi tek
   kaydı işaretler. İkisini aynı sertlikte ele almak ya bütün dosyayı
   gereksiz yere kaybettirir ya da bozuk veriyi sessizce geçirir.
4. **Uygulama sürümü ile format sürümü.** `VERSION` dosyasındaki
   `3.27.0` uygulamanındır; formatın sürümü `1` ya da `2`'dir ve
   uygulama sürümü arttıkça artmaz.

## 8. İlgili belgeler

- `docs/format/profile-a.md` — v1/v2 bayt düzeni ve doğrulama sırası
- `docs/format/profile-b.md` — akustik blok sözleşmesi
- `docs/format/fixture-valid-8records.md` — v1 fixture hexdump'ı
- `docs/format/timing-and-naming.md` — 125 ms ızgarası ve `DataNNNNN`
- `docs/format/inventory.md` §4 — format sürüm envanteri
- `docs/adr/ADR-011-crc.md` — CRC algoritması, kapsamı ve hata davranışı
- `docs/format/channel-map.md` — `bit_status` / `tx_status` eşlemesi
