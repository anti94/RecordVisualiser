# Profil A — sabit kayıt formatı sözleşmesi

> Durum: **TASLAK**. Kaynak: `plan.md` Bölüm 8.2. Gerçek cihaz formatı gelene kadar (envanter E-01/E-02)
> bu sözleşme referans alınır; resmî doküman geldiğinde karşılaştırılıp güncellenir.
>
> Bu dosya decoder, fixture üretici ve testler için **tek doğruluk kaynağıdır**. Bölüm 8.2 ile
> herhangi bir farklılık hata sayılır ve bu dosya lehine değil, ikisi birlikte düzeltilerek giderilir.

## 1. Genel kurallar

| Kural | Değer |
| --- | --- |
| Byte sırası | little-endian |
| Kayan nokta | IEEE 754 `float32` |
| Hizalama | Alanlar bitişiktir; örtük padding **yoktur** |
| Metin alanları | ASCII, sonda `0x00` dolgu |
| Dosya yapısı | 32 byte header + N × 64 byte kayıt |
| Kayıt periyodu | 125 000 µs (125 ms), saniyede 8 kayıt |

## 2. File header (32 byte)

Offsetler dosya başlangıcına göredir.

| Offset | Alan | Tip | Boyut | Değer / kural |
| --- | --- | --- | --- | --- |
| 0 | `magic` | `char[8]` | 8 | ASCII `SONARBIN`. Farklıysa dosya bu profil değildir. |
| 8 | `version` | `uint16` | 2 | `1`. Bilinmeyen sürümde decoder açmayı reddeder ve sürümü raporlar. |
| 10 | `header_size` | `uint16` | 2 | `32`. İlk kayıt bu offsetten başlar. |
| 12 | `record_size` | `uint32` | 4 | `64`. Tüm kayıtlar aynı boyuttadır. |
| 16 | `period_us` | `uint32` | 4 | `125000`. Nominal kayıt periyodu. |
| 20 | `channel_count` | `uint32` | 4 | `8`. Kayıt içindeki `sensor_values` uzunluğuyla tutarlı olmalıdır. |
| 24 | `start_time_utc_ns` | `uint64` | 8 | `Data00000`'ın başlangıcı; Unix epoch'tan UTC nanosaniye. |

**Toplam: 32 byte.** `24 + 8 = 32` → `header_size` ile birebir eşleşir.

### 2.1 Makine sözleşmesi

```python
FILE_HEADER = struct.Struct("<8sHHIIIQ")   # 32 byte
assert FILE_HEADER.size == 32

MAGIC = b"SONARBIN"
SUPPORTED_VERSIONS = {1}
EXPECTED_HEADER_SIZE = 32
EXPECTED_RECORD_SIZE = 64
EXPECTED_PERIOD_US = 125_000
```

### 2.2 Örnek header — hexdump

`start_time_utc_ns` örneği: `2026-09-08T21:00:00Z` → `1788901200000000000`.

```text
offset  bytes                     alan               değer
------  ------------------------  -----------------  ---------------------------
+0x00   53 4F 4E 41 52 42 49 4E   magic              "SONARBIN"
+0x08   01 00                     version            1
+0x0A   20 00                     header_size        32
+0x0C   40 00 00 00               record_size        64
+0x10   48 E8 01 00               period_us          125000
+0x14   08 00 00 00               channel_count      8
+0x18   00 20 45 D4 29 74 D3 18   start_time_utc_ns  1788901200000000000
```

Tam 32 byte:

```text
53 4F 4E 41 52 42 49 4E 01 00 20 00 40 00 00 00
48 E8 01 00 08 00 00 00 00 20 45 D4 29 74 D3 18
```

## 3. Header doğrulama kuralları

Decoder dosyayı açarken sırayla kontrol eder:

1. Dosya boyutu ≥ 32 byte. Değilse: `kesik header` hatası, dosya açılmaz.
2. `magic == b"SONARBIN"`. Değilse: bu profil değil; diğer profil algılamaları denenir.
3. `version in SUPPORTED_VERSIONS`. Değilse: `desteklenmeyen sürüm` hatası, sürüm numarası raporlanır.
4. `header_size == 32` ve `record_size == 64`. Farklıysa: sözleşme ihlali; okuma durdurulur.
5. `period_us == 125000`. Farklıysa: uyarı verilir, değer header'dan alınır (kod içinde sabitlenmez).
6. `channel_count == 8`. Farklıysa: uyarı; `sensor_values` uzunluğu 8 sabit olduğu için okuma reddedilir.
7. `(dosya_boyutu - 32) % 64 == 0`. Değilse: son kayıt kesiktir; sağlam kayıtlar okunur, kesik kayıt raporlanır.

Kayıt sayısı: `record_count = (dosya_boyutu - header_size) // record_size`.

## 4. Genişletme politikası

- Alan eklemek header boyutunu değiştirir → `version` artar ve `header_size` yeni değeri gösterir.
- Decoder `header_size` değerini okuyup **bilmediği kuyruğu atlar**; böylece eski decoder yeni dosyayı
  en azından kayıt düzeyinde okuyabilir. Bu nedenle ilk kayıt offseti kod içinde `32` olarak sabitlenmez,
  daima `header_size` üzerinden hesaplanır.
- CRC alanı bu sürümde **yoktur**; CRC'li sürüm ayrı karar kaydında tanımlanır (`F0-008`, envanter E-03).

## 5. Kayıt sözleşmesi

64 byte `DataNNNNN` kaydının alan tablosu `F0-005` ile bu dosyanın 6. bölümüne eklenir.
