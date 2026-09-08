# Mockup kanal grupları → örnek veri sözlüğü

> `F0-007` çıktısıdır. Mockup'taki `Channels` / `Data Tree` grupları (Bölüm 5.2) ile Profil A kayıt
> alanları (`docs/format/profile-a.md`) arasındaki eşlemedir.
>
> **Bu bir öneridir, gerçek kanal kataloğu değildir** (envanter E-04/E-05). Gerçek katalog geldiğinde
> slot sırası ve birimler buradan güncellenir; UI kanal adını asla kod içinde sabitlemez, katalogdan okur.

## 1. Kayıt boyutu ile kanal sayısı ilişkisi

Profil A kaydı sabit uzunluktadır ve `channel_count` header alanından türetilir:

```text
record_size = 24 + 4 × channel_count + 8
              │        │                └─ bit_status (4) + tx_status (4)
              │        └─ sensor_values: channel_count × float32
              └─ name (12) + sequence_no (4) + elapsed_us (8)
```

| `channel_count` | `record_size` | 8 kayıtlık dosya |
| --- | --- | --- |
| 8 | 64 byte | 544 byte |
| 12 | 80 byte | 672 byte |
| 16 | 96 byte | 800 byte |

Decoder `record_size`'ı **header'dan okur**; 64 değerini sabitlemez. `record_size` ile
`24 + 4 × channel_count + 8` uyuşmazsa sözleşme ihlali raporlanır.

## 2. Minimal sözlük — `channel_count = 8` (fixture profili)

`F0-009`/`F0-010` fixture'ları bu sözlüğü kullanır. Amaç en küçük geçerli dosyadır.

| Slot | Kanal yolu | Grup | Birim | Tipik aralık | Not |
| --- | --- | --- | --- | --- | --- |
| CH0 | `Sensors/Pressure` | Sensors | bar | 0 – 300 | Gövde dış basıncı |
| CH1 | `Sensors/Temperature` | Sensors | °C | -5 – 60 | Elektronik bölme |
| CH2 | `Sensors/Accelerometer/X` | Sensors | g | -4 – 4 | |
| CH3 | `Sensors/Accelerometer/Y` | Sensors | g | -4 – 4 | |
| CH4 | `Sensors/Accelerometer/Z` | Sensors | g | -4 – 4 | |
| CH5 | `Acoustic/Hydrophone 1` | Acoustic | Pa | -10 – 10 | **8 Hz temsilî değer**, bkz. 5. bölüm |
| CH6 | `Navigation/Depth` | Navigation | m | 0 – 500 | |
| CH7 | `Vehicle / Transmission/Voltage` | Vehicle / Transmission | V | 0 – 60 | Besleme gerilimi |

## 3. Genişletilmiş sözlük — `channel_count = 12` (mockup demosu)

Mockup'taki beş grubun tamamının dolu görünmesi için kullanılır; `record_size = 80` olur.

| Slot | Kanal yolu | Grup | Birim | Not |
| --- | --- | --- | --- | --- |
| CH0 | `Sensors/Pressure` | Sensors | bar | |
| CH1 | `Sensors/Temperature` | Sensors | °C | |
| CH2 | `Sensors/Accelerometer/X` | Sensors | g | |
| CH3 | `Sensors/Accelerometer/Y` | Sensors | g | |
| CH4 | `Sensors/Accelerometer/Z` | Sensors | g | |
| CH5 | `Acoustic/Hydrophone 1` | Acoustic | Pa | |
| CH6 | `Acoustic/Hydrophone 2` | Acoustic | Pa | |
| CH7 | `Navigation/Position (GPS)/Latitude` | Navigation | ° | `float32` çözünürlüğü ~1 m; bkz. 6. bölüm |
| CH8 | `Navigation/Position (GPS)/Longitude` | Navigation | ° | Aynı uyarı |
| CH9 | `Navigation/Heading` | Navigation | ° | 0 – 360 |
| CH10 | `Navigation/Depth` | Navigation | m | |
| CH11 | `Vehicle / Transmission/RPM` | Vehicle / Transmission | rpm | |

`Vehicle / Transmission/Voltage` bu sözlükte yer almaz; 16 kanallı sürümde CH12 olur.

## 4. `sensor_values` dışından gelen ağaç düğümleri

Mockup ağacındaki her düğüm bir `float32` slotu değildir:

| Ağaç düğümü | Kaynak alan | Dönüşüm |
| --- | --- | --- |
| `Vehicle / Transmission/TX State` | `tx_status` (`uint32`) | `0 = IDLE`, `1 = ACTIVE`, `2 = FAULT`; durum kanalı olarak çizilir (basamak grafiği) |
| `BIT/Power Supply` | `bit_status` bit 0–3 | Herhangi biri 1 → grup `FAIL` |
| `BIT/Communication` | `bit_status` bit 4–7 | Aynı kural |
| `BIT/Thermal` | `bit_status` bit 8–11 | Aynı kural |
| `BIT` (kök) | `bit_status` ≠ 0 | Kayıtta en az bir FAIL varsa kök uyarı gösterir |
| `Derived` | — | Kayıtta yoktur; kullanıcı tanımlı türetilmiş kanallar (Faz 4) |

`bit_status` bit 12–31 bu sözlükte **atanmamıştır**. Atanmamış bir bit 1 olursa UI
`Bilinmeyen test (bit 17)` biçiminde ham bit numarasını gösterir; uydurma test adı üretmez.

### 4.1 BIT bit haritası

| Bit | Test | Grup |
| --- | --- | --- |
| 0 | Ana besleme gerilimi aralık dışı | Power Supply |
| 1 | İkincil besleme arızası | Power Supply |
| 2 | Akım limiti aşıldı | Power Supply |
| 3 | Ayrılmış | Power Supply |
| 4 | Veri yolu zaman aşımı | Communication |
| 5 | Paket kaybı eşiği aşıldı | Communication |
| 6 | Sensör bağlantısı yok | Communication |
| 7 | Ayrılmış | Communication |
| 8 | Amplifikatör sıcaklığı yüksek | Thermal |
| 9 | Elektronik bölme sıcaklığı yüksek | Thermal |
| 10 | Soğutma arızası | Thermal |
| 11 | Ayrılmış | Thermal |
| 12–31 | Atanmamış | — |

## 5. Acoustic grubunun sınırı

Profil A'da bir hidrofon kanalı **kayıt başına tek değer** taşır → efektif 8 Hz. Bu, mockup'ta
`Acoustic` grubunun görünmesi ve zaman serisi çizilmesi için yeterlidir; **FFT, PSD ve spektrogram için
yeterli değildir**. Mockup'un spektral hücreleri gerçek sonuç üretecekse veri Profil B'den
(Bölüm 8.3, 96 kHz blok) gelmelidir.

Kural: Profil A verisiyle spektral analiz paneli **gerçek sonuç izlenimi veren sahte çıktı göstermez**;
`v2.0.0 ile kullanılabilir` durumunda kalır (Bölüm 3.1).

## 6. Bilinen sınırlamalar

- **GPS `float32`** — enlem/boylam için `float32` yaklaşık 1 m çözünürlük verir. Gerçek formatta
  konum ayrı bir `float64` çift veya tamsayı ölçekli alan olmalıdır. Şimdilik demo amaçlıdır.
- **Birim ve gain/offset kayıtta taşınmaz** — Profil A ham `float32` değeri fiziksel birimde varsayar.
  Ham ADC değeri taşınacaksa gain/offset kanal kataloğundan gelmelidir (E-04).
- **Slot sırası sözleşmedir** — sıra değişirse `version` artmalıdır; aksi halde eski dosyalar yanlış
  kanal adıyla çizilir.
- **`NaN`** — "ölçüm yok" demektir; grafikte kesinti olarak gösterilir, `0.0`'a çevrilmez.
