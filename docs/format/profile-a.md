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

## 5. Kayıt sözleşmesi — `DataNNNNN` (64 byte)

Offsetler **kaydın kendi başlangıcına** göredir. Kayıt `n`'in dosya offseti: `header_size + n * record_size`.

| Offset | Alan | Tip | Boyut | Değer / kural |
| --- | --- | --- | --- | --- |
| 0 | `name` | `char[12]` | 12 | ASCII `Data00000`; kalan byte `0x00`. Etikettir, yetkili alan `sequence_no`'dur. |
| 12 | `sequence_no` | `uint32` | 4 | `0`, `1`, `2`, … Monoton artar; atlama zaman boşluğu demektir. |
| 16 | `elapsed_us` | `uint64` | 8 | Kayıt başından geçen süre: `sequence_no × 125000`. |
| 24 | `sensor_values` | `float32[8]` | 32 | CH0–CH7 anlık değerleri, sabit kanal sırası. |
| 56 | `bit_status` | `uint32` | 4 | Bit maskesi; bit *k* = test *k* FAIL. `0` → tümü PASS. |
| 60 | `tx_status` | `uint32` | 4 | `0 = IDLE`, `1 = ACTIVE`, `2 = FAULT`. |

**Toplam: 64 byte.** `60 + 4 = 64` → `record_size` ile birebir eşleşir.

### 5.1 Makine sözleşmesi

```python
DATA_RECORD = struct.Struct("<12sIQ8fII")   # 64 byte
assert DATA_RECORD.size == 64

RECORD_PERIOD_US = 125_000
TX_STATES = {0: "IDLE", 1: "ACTIVE", 2: "FAULT"}


def record_name(sequence_no: int) -> str:
    return f"Data{sequence_no:05d}"


def record_offset(sequence_no: int, header_size: int = 32, record_size: int = 64) -> int:
    return header_size + sequence_no * record_size
```

### 5.2 Alan kuralları

- **`name`** — `record_name(sequence_no)` ile üretilir. En az 5 hane sıfır dolgusu; `Data99999`'dan sonra
  `Data100000` gelir, **sayaç sıfırlanmaz**. `char[12]` en fazla `Data9999999` + sonlandırıcı sıfırı alır;
  bu sınıra gelmeden yeni dosyaya geçilir. Ad ile `sequence_no` uyuşmazsa tutarsızlık raporlanır.
- **`sequence_no`** — sıralama, indeksleme ve korelasyonda yetkili alandır. Kayıp periyotta kayıt yazılmaz;
  numara atlar. Geri giden numara dosya bozulması veya yeniden başlatma sayılır.
- **`elapsed_us`** — nominal ızgara `sequence_no × 125000`. Mutlak zaman:
  `start_time_utc_ns + elapsed_us × 1000`. Nominal ızgaradan sapma jitter olarak raporlanır.
- **`sensor_values`** — birim ve kanal adı bu profilde **taşınmaz**; kanal kataloğundan gelir (envanter E-04).
  `NaN` değer "ölçüm yok" anlamındadır ve grafikte kesinti olarak gösterilir, `0.0`'a çevrilmez.
- **`bit_status`** — 32 test kapasitesi. Bit → test eşlemesi bu profilde yoktur; BIT kataloğundan gelir
  (envanter E-05). Eşleme yokken UI ham bit numarasını gösterir, uydurma test adı üretmez.
- **`tx_status`** — tanımsız bir kod gelirse değer ham olarak gösterilir ve `bilinmeyen durum` işaretlenir.
  `TransmissionInterval`, ardışık kayıtlardaki `IDLE → ACTIVE` / `ACTIVE → IDLE` geçişlerinden türetilir;
  sınırlar 125 ms belirsizlik taşır.

### 5.3 Örnek kayıt — `Data00001` hexdump

`sequence_no = 1`, `elapsed_us = 125000`, CH0–CH7 = `12.5, -3.25, 0.0, 101.75, 7.125, -0.5, 48.0, 1000.0`,
`bit_status = 0` (tümü PASS), `tx_status = 1` (ACTIVE).

```text
+0x00   44 61 74 61 30 30 30 30 31 00 00 00 01 00 00 00
+0x10   48 E8 01 00 00 00 00 00 00 00 48 41 00 00 50 C0
+0x20   00 00 00 00 00 80 CB 42 00 00 E4 40 00 00 00 BF
+0x30   00 00 40 42 00 00 7A 44 00 00 00 00 01 00 00 00
```

Alan ayrımı:

```text
+0x00  44 61 74 61 30 30 30 30 31 00 00 00   name        = "Data00001"
+0x0C  01 00 00 00                           sequence_no = 1
+0x10  48 E8 01 00 00 00 00 00               elapsed_us  = 125000
+0x18  00 00 48 41                           CH0         = 12.5
+0x1C  00 00 50 C0                           CH1         = -3.25
+0x20  00 00 00 00                           CH2         = 0.0
+0x24  00 80 CB 42                           CH3         = 101.75
+0x28  00 00 E4 40                           CH4         = 7.125
+0x2C  00 00 00 BF                           CH5         = -0.5
+0x30  00 00 40 42                           CH6         = 48.0
+0x34  00 00 7A 44                           CH7         = 1000.0
+0x38  00 00 00 00                           bit_status  = 0
+0x3C  01 00 00 00                           tx_status   = 1 (ACTIVE)
```

### 5.4 Dosya düzeyi tutarlılık

| Kontrol | Beklenen |
| --- | --- |
| `n` numaralı kaydın offseti | `32 + n × 64` |
| 8 kayıtlık dosya boyutu | `32 + 8 × 64 = 544` byte |
| İlk saniye `[0, 1000 ms)` | `Data00000` – `Data00007` |
| `Data00008` zamanı | `1 000 000 µs` = 1000 ms |
| Kayıt sayısı | `(dosya_boyutu - 32) // 64` |

## 6. Bu profilin sınırı

Kayıt başına kanal başına **tek anlık değer** taşınır; efektif örnekleme hızı 8 Hz'dir. Bu, trend, durum,
BIT ve TX izleme için yeterlidir; FFT/PSD/spektrogram gerektiren ham akustik veri için yetersizdir.
Ham akustik kayıt düzeni `plan.md` Bölüm 8.3'teki Profil B'de tanımlıdır.
