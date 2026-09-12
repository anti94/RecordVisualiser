# TOML şema sözleşmesi — C++ struct tanımlarının tarifi

Kayıt dosyalarını C++ tarafı üretir (`D-29`). Bu şema onların **tarifidir**, tanımı değil.
Fark önemlidir: tarif yanlışsa dosya değişmez, yalnız biz yanlış okuruz.

Bir C++ struct'ını TOML'a taşırken kaybolan bilgi, derleyicinin sessizce eklediği
bilgidir: dolgu baytları, hizalama, bit alanı yerleşimi, enum'un temel tipi. Bu belge
o bilginin nasıl açıkça yazılacağını tanımlar.

## 1. Tarif neyi garanti eder, neyi etmez

| Garanti eder | Etmez |
| --- | --- |
| Her alanın offseti ve boyutu | Alanın anlamını (birim, ölçek, geçerlilik) |
| Bayt sırası (endianness) | C++ tarafının o alanı gerçekten böyle yazdığını |
| Enum değerlerinin isimleri | Enum'un eksiksiz olduğunu |

Son sütun bu belgenin var oluş nedenidir. Tarif ile gerçek dosya ayrışırsa okuyucu
**hata vermez**; her alan kaymış hâlde okunur, CRC tutar, bayt sayısı tutar. Bu yüzden
şemanın kendisi yeterli değildir; §7'deki üç kapı gerekir.

## 2. Temel tip eşlemesi

C++ tipi, Python `struct` kodu ve NumPy dtype'ı arasındaki eşleme **tek kaynaktan**
gelir. Üçü ayrı yerlerde yazılsaydı biri güncellenip diğerleri unutulurdu.

| C++ tipi | Bayt | `struct` kodu | NumPy dtype | Aralık / not |
| --- | --- | --- | --- | --- |
| `uint8_t` | 1 | `B` | `u1` | 0 … 255 |
| `int8_t` | 1 | `b` | `i1` | −128 … 127 |
| `uint16_t` | 2 | `H` | `u2` | 0 … 65.535 |
| `int16_t` | 2 | `h` | `i2` | −32.768 … 32.767 |
| `uint32_t` | 4 | `I` | `u4` | 0 … 4.294.967.295 |
| `int32_t` | 4 | `i` | `i4` | ±2,1 × 10⁹ |
| `uint64_t` | 8 | `Q` | `u8` | 0 … 1,8 × 10¹⁹ |
| `int64_t` | 8 | `q` | `i8` | ±9,2 × 10¹⁸ — zaman damgası için |
| `float` | 4 | `f` | `f4` | IEEE 754 tek duyarlık |
| `double` | 8 | `d` | `f8` | IEEE 754 çift duyarlık |
| `char[N]` | N | `Ns` | `SN` | Sabit uzunluk, sıfır dolgulu |
| `std::complex<float>` | 8 | `2f` | `c8` | I önce, Q sonra |
| `std::complex<int16_t>` | 4 | `2h` | `c8` okunamaz | Elle I/Q ayrıştırılır |

Son satırın uyarısı bilinçlidir: NumPy'da tamsayı tabanlı complex dtype yoktur.
`std::complex<int16_t>` verisi `i2` çiftleri olarak okunup elle birleştirilmelidir.
Bu profilde örnek tipi `std::complex<float>`'tır (`D-28`), yani `c8` doğrudan kullanılır.

**`bool` ve `long` yasaktır.** `bool` boyutu derleyiciye bağlıdır, `long` platforma
bağlıdır (Windows'ta 4, Linux'ta 8 bayt). İkisi de `uint8_t` ya da açık genişlikli bir
tiple yazılmalıdır. Şema bu iki adı görürse hata verir.

## 3. Bayt sırası

Şema dosya başında bir kez bildirilir:

```toml
[schema]
endianness = "little"   # "little" | "big"
```

Alan bazında bayt sırası **desteklenmez**. Tek bir dosyada karışık bayt sırası,
gerçek bir C++ struct'ında oluşamaz; desteklemek yalnız yanlış şema yazmayı
kolaylaştırırdı.

`little` öntanımdır: x86 ve ARM'ın ikisi de küçük uçludur.

## 4. Hizalama ve dolgu

Bu, tarifte en sık kaybolan bilgidir. C++ derleyicisi bir struct'ta alanları kendi
hizalama kurallarına göre yerleştirir ve **görünmeyen dolgu baytları** ekler:

```cpp
struct Ornek {
    uint8_t  a;   // offset 0
                  // offset 1-3: DERLEYICININ EKLEDIGI 3 BAYT DOLGU
    uint32_t b;   // offset 4
};                // toplam 8 bayt, 5 degil
```

Şema iki kipten birini bildirir:

```toml
[schema]
packing = "packed"    # "packed" | "natural"
```

| Kip | Anlamı | Ne zaman |
| --- | --- | --- |
| `packed` | Dolgu yok, alanlar bitişik | C++ tarafı `#pragma pack(1)` kullanıyorsa |
| `natural` | Derleyici hizalaması geçerli | Varsayılan C++ davranışı |

**Hangi kipte olursa olsun her alanın offseti açıkça yazılır.** Kip yalnız
**doğrulama** için kullanılır: `natural` kipte bir `uint32_t` alanı 4'e bölünmeyen
bir offsette duruyorsa şema hatalıdır ve bu yakalanır. `packed` kipte böyle bir
denetim yapılmaz.

Offseti hesaplatmak yerine yazdırmanın nedeni şudur: hesaplama derleyicinin kuralını
taklit etmeye çalışır ve o kural derleyiciye, sürüme ve `#pragma`'ya bağlıdır.
Yazılmış bir offset ise ölçülebilir.

### 4.1 Dolgu açıkça bildirilebilir

Anlamsız dolgu baytları bildirilirse şema boyutu kendi kendini doğrular:

```toml
[[structs.FrameHeader.fields]]
name = "_pad0"
type = "uint8_t"
offset = 13
count = 3
note = "derleyici dolgusu"
```

Bildirilmeyen boşluk hata değil **uyarıdır**: bilinçli olabilir. Ama bildirilen
boyut ile alanların kapladığı alan tutmuyorsa bu hatadır (§6).

## 5. Bit alanları

C++ bit alanlarının yerleşimi **standart tarafından tanımlanmamıştır**; derleyiciye
ve ABI'ye bağlıdır. Bu yüzden şema bit alanlarını bir C++ özelliği olarak değil,
bir tamsayının içindeki maskeler olarak tarif eder:

```toml
[[structs.FrameHeader.fields]]
name = "status"
type = "uint16_t"
offset = 20

[[structs.FrameHeader.fields.bits]]
name = "tx_active"
mask = 0x0001
[[structs.FrameHeader.fields.bits]]
name = "clock_locked"
mask = 0x0002
[[structs.FrameHeader.fields.bits]]
name = "channel_mask"
mask = 0x00FC
shift = 2
```

Maske ve kaydırma açıkça yazılır. Örtüşen maskeler hata verir; kullanılmayan bitler
serbesttir.

## 6. Boyut doğrulaması

Her struct bildirilen bir boyut taşır:

```toml
[structs.FrameHeader]
size = 64
```

Şema yüklenirken şu denetimler zorunludur:

| Denetim | Hata durumu |
| --- | --- |
| Alan offseti + boyutu ≤ struct boyutu | Alan struct'ın dışına taşıyor |
| İki alanın aralığı örtüşmüyor | Offset çakışması |
| Bildirilen boyut ≥ en son alanın sonu | Boyut alanları kapsamıyor |
| `natural` kipte hizalama tutuyor | Hizalama ihlali |
| Tip tabloda tanımlı | Bilinmeyen tip |
| Enum değerleri yinelenmiyor | Enum çakışması |

Her hata **hangi alan, hangi offset ve ne beklendiğini** söyler. "Şema geçersiz"
diyen bir mesaj, şemayı düzeltmeye yardım etmez.

## 7. Şema ile kaydın ayrışması

Doğru yazılmış bir şema bile **yanlış dosyaya** uygulanabilir. Üç bağımsız kapı:

1. **Sihirli sayı** — dosyanın bu profile ait olduğunu söyler.
2. **Şema kimliği ve sürümü** — dosya header'ında taşınır, TOML'daki değerle
   karşılaştırılır. Tutmazsa kayıt açılmaz.
3. **Boyut denklemi** — ölçülebilir bir tutarlılık sınavı:

```text
dosya_boyutu = dosya_header + frame_sayısı × (frame_header + S × N × B)
```

Üçü de geçtiğinde okuma başlar. Biri düşerse kayıt açılmaz ve hangi kapının neden
düştüğü söylenir.

Üçüncü kapı en değerlisidir çünkü **şema kimliği unutulsa bile** çalışır: frame
header'ın boyutu bir bayt bile değişse denklem tutmaz.

## 8. Şema dosyasının iskeleti

```toml
[schema]
id = "sonar-profile-c"
version = 1
endianness = "little"
packing = "packed"

[enums.ChannelSource]
underlying = "uint8_t"
values = { UNKNOWN = 0, ACOUSTIC = 1, REFERENCE = 2, MONITOR = 3 }

[structs.FileHeader]
size = 64
# alanlar…

[structs.FrameHeader]
size = 64
# alanlar…

[payload]
sensor_count = 32
frame_samples = 820
sample_type = "std::complex<float>"
layout = "sensor_major"   # "sensor_major" | "sample_major"
```

`layout` alanı bilinçli olarak ayrıdır: 32 × 820 bir dizi iki farklı sırada yazılabilir
ve ikisi **aynı bayt sayısını** tutar. Yanlış seçim hiçbir boyut denetimini düşürmez,
yalnız sensörleri birbirine karıştırır. Bu, bu profildeki en sessiz hata olurdu.

Tam ve çalışır bir örnek `F7-006` ile eklenecektir; alan alan doldurulmuş `FrameHeader`
ve enum tanımları orada olacaktır.

## 9. Neden TOML

| Seçenek | Neden seçilmedi |
| --- | --- |
| JSON | Yorum satırı yok; offset tablosunda gerekçe yazılamaz |
| YAML | Girinti duyarlı, tip çıkarımı sürprizli (`NO` → `false`) |
| Doğrudan C++ başlığı ayrıştırmak | Derleyici ön işlemcisi gerekir; `#ifdef` ve makrolarla baş edilemez |
| Python modülü | Şema veri olmalı, kod değil; kullanıcı düzenleyebilmeli |

TOML yorum destekler, tipleri açıktır ve Python 3.11'den beri standart kütüphanede
(`tomllib`) bulunur. Bu projede Python 3.9 çalıştığı için `tomli` geri taşıması
kullanılır (`D-20`).
