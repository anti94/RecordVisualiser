# Fixture: `valid_8records.bin` — beklenen sonuçlar

> `F0-009` çıktısıdır. Bu dosya **sözleşmedir**: fixture üretici bu baytları birebir üretmeli,
> decoder testleri bu değerleri birebir doğrulamalıdır. Profil A sürüm 1
> (`docs/format/profile-a.md`), CRC yoktur.
>
> Konum: `tests/fixtures/valid_8records.bin`

## 1. Üretim kuralları (deterministik)

`start_time_utc_ns = 1788901200000000000` → `2026-09-08T21:00:00.000Z`, `channel_count = 8`.

`n = 0..7` için:

| Slot | Kanal | Formül | Birim |
| --- | --- | --- | --- |
| CH0 | `Sensors/Pressure` | `100.0 + 0.5 × n` | bar |
| CH1 | `Sensors/Temperature` | `25.0` (sabit) | °C |
| CH2 | `Sensors/Accelerometer/X` | `0.125 × n` | g |
| CH3 | `Sensors/Accelerometer/Y` | `0.0 - 0.125 × n` | g |
| CH4 | `Sensors/Accelerometer/Z` | `1.0` (sabit) | g |
| CH5 | `Acoustic/Hydrophone 1` | `+2.5` (çift `n`), `-2.5` (tek `n`) | Pa |
| CH6 | `Navigation/Depth` | `10.0 + 0.25 × n` | m |
| CH7 | `Vehicle / Transmission/Voltage` | `48.0` (sabit) | V |

- `bit_status` = `0x00000100` yalnız `n = 4`'te (bit 8 → Thermal / amplifikatör sıcaklığı yüksek),
  diğer kayıtlarda `0`.
- `tx_status` = `1` (ACTIVE) `n = 2..5` için, diğerlerinde `0` (IDLE).

Tüm değerler ikilik kesirlerdir; `float32` dönüşümü **kayıpsızdır**. Test karşılaştırmaları
tolerans kullanmadan `==` ile yapılabilir.

> **CH3 ve negatif sıfır:** formül `0.0 - 0.125 × n` biçiminde yazılmalıdır. `-0.125 * n` yazılırsa
> `n = 0` için sonuç `-0.0` olur ve baytlar `00 00 00 80` çıkar; beklenen `00 00 00 00`'dır.

## 2. Beklenen header

| Alan | Değer |
| --- | --- |
| `magic` | `SONARBIN` |
| `version` | 1 |
| `header_size` | 32 |
| `record_size` | 64 |
| `period_us` | 125000 |
| `channel_count` | 8 |
| `start_time_utc_ns` | 1788901200000000000 |

## 3. Beklenen kayıtlar

| `n` | Ad | `elapsed_us` | UTC | Offset | CH0 | CH2 | CH3 | CH5 | CH6 | `bit_status` | `tx_status` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `Data00000` | 0 | 21:00:00.000 | 32 | 100.0 | 0.0 | 0.0 | 2.5 | 10.0 | `0x00000000` | 0 |
| 1 | `Data00001` | 125000 | 21:00:00.125 | 96 | 100.5 | 0.125 | -0.125 | -2.5 | 10.25 | `0x00000000` | 0 |
| 2 | `Data00002` | 250000 | 21:00:00.250 | 160 | 101.0 | 0.25 | -0.25 | 2.5 | 10.5 | `0x00000000` | 1 |
| 3 | `Data00003` | 375000 | 21:00:00.375 | 224 | 101.5 | 0.375 | -0.375 | -2.5 | 10.75 | `0x00000000` | 1 |
| 4 | `Data00004` | 500000 | 21:00:00.500 | 288 | 102.0 | 0.5 | -0.5 | 2.5 | 11.0 | **`0x00000100`** | 1 |
| 5 | `Data00005` | 625000 | 21:00:00.625 | 352 | 102.5 | 0.625 | -0.625 | -2.5 | 11.25 | `0x00000000` | 1 |
| 6 | `Data00006` | 750000 | 21:00:00.750 | 416 | 103.0 | 0.75 | -0.75 | 2.5 | 11.5 | `0x00000000` | 0 |
| 7 | `Data00007` | 875000 | 21:00:00.875 | 480 | 103.5 | 0.875 | -0.875 | -2.5 | 11.75 | `0x00000000` | 0 |

CH1 = `25.0`, CH4 = `1.0`, CH7 = `48.0` tüm kayıtlarda sabittir.

## 4. Dosya düzeyi beklentiler

| Kontrol | Beklenen değer |
| --- | --- |
| Dosya boyutu | **544 byte** (`32 + 8 × 64`) |
| Kayıt sayısı | 8 |
| Kapsanan aralık | `0 ms` – `875 ms` (son kaydın başlangıcı) |
| Kayıt penceresi toplamı | `1000 ms` (son kayıt 875–1000 ms aralığını temsil eder) |
| Sıra boşluğu | **yok** (`sequence_no` 0..7 kesintisiz) |
| CRC hatası | yok (bu sürümde CRC alanı yok) |
| SHA-256 | `5094b9b0bc585518cf7fa9dc372d3e997f32b59caeb156cb4c0f9ab9d039fce9` |
| CRC-32 (tüm dosya) | `0x7314EC15` |

## 5. Türetilmiş beklentiler

Decoder'ın domain modeline çevirdiğinde üretmesi gerekenler:

- **`RecordingMetadata`** — başlangıç `2026-09-08T21:00:00.000Z`, bitiş `21:00:01.000Z`, 8 kayıt, 8 kanal.
- **Kanal listesi** — `docs/format/channel-map.md` §2'deki 8 yol; her biri 8 örnek, örnekleme 8 Hz.
- **BIT olayı** — tam **1** adet: `t = 500 ms`, grup `Thermal`, bit 8, durum `FAIL`.
  Diğer 7 kayıtta BIT olayı üretilmez.
- **`TransmissionInterval`** — tam **1** adet: başlangıç `250 ms` (ilk ACTIVE kayıt),
  bitiş `750 ms` (ilk sonraki IDLE kayıt), süre `500 ms`. Sınırlar ±125 ms belirsizlik taşır.
- **Boşluk raporu** — boş liste.

## 6. Tam hexdump (544 byte)

```text
0000  53 4F 4E 41 52 42 49 4E 01 00 20 00 40 00 00 00
0010  48 E8 01 00 08 00 00 00 00 20 45 D4 29 74 D3 18
0020  44 61 74 61 30 30 30 30 30 00 00 00 00 00 00 00
0030  00 00 00 00 00 00 00 00 00 00 C8 42 00 00 C8 41
0040  00 00 00 00 00 00 00 00 00 00 80 3F 00 00 20 40
0050  00 00 20 41 00 00 40 42 00 00 00 00 00 00 00 00
0060  44 61 74 61 30 30 30 30 31 00 00 00 01 00 00 00
0070  48 E8 01 00 00 00 00 00 00 00 C9 42 00 00 C8 41
0080  00 00 00 3E 00 00 00 BE 00 00 80 3F 00 00 20 C0
0090  00 00 24 41 00 00 40 42 00 00 00 00 00 00 00 00
00A0  44 61 74 61 30 30 30 30 32 00 00 00 02 00 00 00
00B0  90 D0 03 00 00 00 00 00 00 00 CA 42 00 00 C8 41
00C0  00 00 80 3E 00 00 80 BE 00 00 80 3F 00 00 20 40
00D0  00 00 28 41 00 00 40 42 00 00 00 00 01 00 00 00
00E0  44 61 74 61 30 30 30 30 33 00 00 00 03 00 00 00
00F0  D8 B8 05 00 00 00 00 00 00 00 CB 42 00 00 C8 41
0100  00 00 C0 3E 00 00 C0 BE 00 00 80 3F 00 00 20 C0
0110  00 00 2C 41 00 00 40 42 00 00 00 00 01 00 00 00
0120  44 61 74 61 30 30 30 30 34 00 00 00 04 00 00 00
0130  20 A1 07 00 00 00 00 00 00 00 CC 42 00 00 C8 41
0140  00 00 00 3F 00 00 00 BF 00 00 80 3F 00 00 20 40
0150  00 00 30 41 00 00 40 42 00 01 00 00 01 00 00 00
0160  44 61 74 61 30 30 30 30 35 00 00 00 05 00 00 00
0170  68 89 09 00 00 00 00 00 00 00 CD 42 00 00 C8 41
0180  00 00 20 3F 00 00 20 BF 00 00 80 3F 00 00 20 C0
0190  00 00 34 41 00 00 40 42 00 00 00 00 01 00 00 00
01A0  44 61 74 61 30 30 30 30 36 00 00 00 06 00 00 00
01B0  B0 71 0B 00 00 00 00 00 00 00 CE 42 00 00 C8 41
01C0  00 00 40 3F 00 00 40 BF 00 00 80 3F 00 00 20 40
01D0  00 00 38 41 00 00 40 42 00 00 00 00 00 00 00 00
01E0  44 61 74 61 30 30 30 30 37 00 00 00 07 00 00 00
01F0  F8 59 0D 00 00 00 00 00 00 00 CF 42 00 00 C8 41
0200  00 00 60 3F 00 00 60 BF 00 00 80 3F 00 00 20 C0
0210  00 00 3C 41 00 00 40 42 00 00 00 00 00 00 00 00
```

Okuma ipucu: `0x0150` satırındaki `00 01 00 00` `bit_status = 0x00000100`'dür (little-endian);
bu, `Data00004`'ün Thermal FAIL kaydıdır.
