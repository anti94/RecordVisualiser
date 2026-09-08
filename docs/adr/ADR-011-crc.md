# ADR-011 — CRC destekleyen `.bin` format sürümü

- **Durum:** Önerildi (donanım ekibi onayı bekliyor — envanter E-03)
- **Karar tarihi:** 2026-09-08
- **İlgili işler:** `F0-008`, `F0-010`, `F2-*` decoder doğrulaması
- **Kapsam:** Profil A sürüm 2 ve Profil B

## 1. Bağlam

Profil A sürüm 1 (`docs/format/profile-a.md`) bütünlük alanı taşımaz. Bozuk bir kayıt sessizce
geçerli sayılır; yalnız `sequence_no` tutarsızlığı yakalanabilir, alan içi bit hatası yakalanamaz.
Bölüm 4.3'teki "paket kaybı ve CRC hatasını aynı zaman çizgisinde incele" senaryosu (S-05) bir
bütünlük alanı olmadan doğrulanamaz.

Gerçek cihaz formatının CRC kullanıp kullanmadığı **bilinmiyor** (E-03). Bu karar, gerçek doküman
gelene kadar geliştirme ve fixture üretimi için bir sözleşme sağlar.

## 2. Karar

### 2.1 Algoritma

**CRC-32/ISO-HDLC** (yaygın adıyla "CRC-32", zlib/PNG/Ethernet ile aynı):

| Parametre | Değer |
| --- | --- |
| Genişlik | 32 bit |
| Polinom | `0x04C11DB7` |
| Init | `0xFFFFFFFF` |
| Giriş yansıtma (`refin`) | evet |
| Çıkış yansıtma (`refout`) | evet |
| XOR out | `0xFFFFFFFF` |
| Kontrol değeri (`"123456789"`) | `0xCBF43926` |

Python'da ek bağımlılık gerektirmez: `zlib.crc32(data) & 0xFFFFFFFF`. C hızında çalışır.

### 2.2 Kapsam

- **Kayıt CRC'si:** kaydın ilk baytından `crc32` alanının hemen öncesine kadar olan **tüm** baytlar.
  CRC alanının kendisi kapsama dahil değildir. Kayıtlar birbirinden bağımsız doğrulanır; bir kaydın
  bozuk olması diğerlerini geçersiz kılmaz.
- **Header CRC'si:** header'ın ilk baytından `header_crc32` alanının öncesine kadar.
- Dosya geneli için tek bir CRC **kullanılmaz**; büyük dosyada tüm dosyayı okumadan doğrulama
  yapılamaz hâle gelirdi.

### 2.3 Alan konumu ve sürüm

Alan eklemek boyutları değiştirir, bu yüzden **yeni sürüm** gerektirir.

**Profil A sürüm 2:**

| Yapı | v1 | v2 |
| --- | --- | --- |
| `header_size` | 32 | **36** (`header_crc32` offset 32'de, `uint32`) |
| `record_size` | `24 + 4·ch + 8` | **`24 + 4·ch + 8 + 4`** (`crc32` kaydın sonunda) |
| 8 kanallı kayıt | 64 byte | **68 byte** |
| 8 kayıtlık dosya | 544 byte | **580 byte** |

`version = 2` olur. Decoder `version`'a bakarak CRC doğrulamasını açar; v1 dosyada CRC aranmaz.
Boyutlar yine `header_size` / `record_size` alanlarından okunur, kodda sabitlenmez.

**Profil B:** zaten CRC taşır ve değişmez — kayıt sonundaki `RecordTrailer.crc32`
(Bölüm 8.3.4) ve `FileHeader.header_crc32` (offset `0xFC`). Bu ADR yalnız bu alanların
**algoritmasını ve kapsamını** yukarıdaki tanıma sabitler.

### 2.4 Hata davranışı

- CRC hatası kaydı **atmaz**: kayıt `CRC_ERROR` işaretlenir, verisi çizilmez, olay listesinde
  kayıt adı, `sequence_no` ve dosya offseti ile raporlanır.
- Dosya açılmaya devam eder; sağlam kayıtlar normal okunur (senaryo S-05).
- Header CRC hatası farklıdır: header güvenilmezse boyut alanları da güvenilmez → dosya açılmaz,
  kullanıcıya "header bütünlüğü bozuk" hatası verilir.
- CRC hatası sayısı kayıt özetinde ve dışa aktarılan raporda görünür.

## 3. Referans vektörler

Doğrulama testleri bu değerleri kullanır (`tests/unit/test_crc.py`).

| Girdi | CRC-32 | Little-endian bayt |
| --- | --- | --- |
| `b"123456789"` | `0xCBF43926` | `26 39 F4 CB` |
| `b""` | `0x00000000` | `00 00 00 00` |
| 64 × `0x00` | `0x758D6336` | `36 63 8D 75` |
| Örnek `Data00001` kaydı (v1 gövdesi, 64 byte) | `0x6B7E1EEF` | `EF 1E 7E 6B` |
| Örnek header (v2 gövdesi, 32 byte) | `0x7CB1047D` | `7D 04 B1 7C` |

Örnek `Data00001` kaydı `docs/format/profile-a.md` §5.3'teki bayt dizisidir. v2 kaydında bu 64 bayt
korunur ve sonuna `EF 1E 7E 6B` eklenir → 68 byte.

Örnek header gövdesi: `magic="SONARBIN"`, `version=2`, `header_size=36`, `record_size=68`,
`period_us=125000`, `channel_count=8`, `start_time_utc_ns=1788901200000000000`.

## 4. Değerlendirilen alternatifler

| Seçenek | Neden seçilmedi |
| --- | --- |
| **CRC yok (v1'de kal)** | Bit hatası sessizce geçer; S-05 senaryosu ve `F0-010` fixture'ı doğrulanamaz. |
| **CRC-16/CCITT** | 2 byte yer kazandırır; 64–68 byte kayıtta yeterli olurdu ancak çoklu bit hatası tespiti belirgin biçimde zayıf ve Python'da hazır uygulama yok. |
| **CRC-32C (Castagnoli)** | Hata tespiti biraz daha iyi ve SSE4.2 ivmesi var; Python standart kütüphanesinde **yok**, ek bağımlılık veya saf Python yavaşlığı getirir. Kazanç bu veri hızında gerekçelendirilemedi. |
| **xxHash / MD5 / SHA** | Bunlar hata **tespit kodu** değil karma fonksiyonudur; ardışık bit hatalarında CRC'nin garantilerini vermez. MD5/SHA ayrıca gereksiz yavaştır. |
| **Kayıt yerine dosya geneli tek CRC** | Doğrulama için tüm dosyayı okumak gerekir; 2,6 GiB kayıtta açılış bütçesini yok eder ve bozuk bölgeyi konumlandıramaz. |

## 5. Sonuçlar

**Olumlu**

- Kayıt düzeyinde bozulma tespiti; bozuk bölge dosya offseti ile gösterilebilir.
- Standart kütüphaneyle sıfır ek bağımlılık, C hızında hesap.
- Profil A ve Profil B aynı algoritma ve kapsam kuralını paylaşır; tek doğrulama kodu yeter.
- `F0-010` bozuk fixture senaryoları üretilebilir hâle gelir.

**Olumsuz**

- Kayıt başına %6,25 boyut artışı (64 → 68 byte). 8 kanallı 1 saatlik kayıtta
  `28 800 × 4 byte ≈ 113 KiB`; ihmal edilebilir.
- v1 ve v2 için iki okuma yolu bakımı gerekir.
- Yazma tarafında kayıt başına CRC hesabı gerekir; 8 kayıt/s'te maliyet ölçülemeyecek kadar küçüktür.
- **Gerçek cihaz farklı bir CRC kullanıyorsa bu ADR değiştirilir.** Sentetik fixture ile geçen test,
  gerçek donanım doğrulaması sayılmaz.

## 6. Doğrulama

- `tests/unit/test_crc.py`: yukarıdaki beş referans vektör.
- `tests/integration/`: `crc_error.bin` fixture'ı açıldığında yalnız bozuk kaydın işaretlenmesi,
  diğer kayıtların okunabilmesi.
- Karar kesinleştiğinde `docs/format/profile-a.md` §4'teki "CRC alanı bu sürümde yoktur" notu
  v2 tablosuna bağlanır.
