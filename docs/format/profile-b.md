# Profil B — blok tabanlı ham akustik kayıt sözleşmesi

> Durum: **TASLAK**. Kaynak: `plan.md` Bölüm 8.3. Gerçek cihaz formatı gelene kadar
> (envanter E-01/E-03) bu sözleşme referans alınır; resmî doküman geldiğinde
> karşılaştırılıp güncellenir.
>
> Bu dosya Profil B decoder'ı (`F4-011`+), fixture üretici (`F4-010`) ve testler için
> **tek doğruluk kaynağıdır**. Bölüm 8.3 ile herhangi bir farklılık hata sayılır ve
> ikisi birlikte düzeltilerek giderilir.
>
> **Profil A değişmez.** Profil A'nın sabit 64 baytlık kayıt formatı ve `8.2`
> örneği (`docs/format/profile-a.md`, `tests/fixtures/valid_8records.bin`) bu işten
> **etkilenmez**; Profil B ayrı bir magic (`SNRBIN\x1A\x00`) ve ayrı bir dosya
> yerleşimi kullanır. İki profil aynı 125 ms kayıt ızgarasını ve `DataNNNNN`
> adlandırmasını paylaşır, bunun dışında bağımsızdır.

## 1. Genel kurallar

| Kural | Değer |
| --- | --- |
| Byte sırası | little-endian |
| Kayan nokta | IEEE 754 |
| Hizalama | Blok = `align8(16 + block_size)`; artan baytlar `0x00`, `block_size`'a girmez |
| Metin alanları | UTF-8 / ASCII, sonda `0x00` dolgu |
| Dosya yapısı | `FileHeader(256 B)` + `ChannelTable(N×64 B)` + `RecordArea` + `RecordIndex(M×32 B, ops.)` + `FileFooter(32 B)` |
| Kayıt periyodu | 125 000 000 ns (125 ms), saniyede 8 kayıt |
| Mutlak zaman | yalnız `FileHeader.t0_utc_ns`; kayıtlar buna göre offset taşır |

## 2. Bu sürümün akustik profili (48 kHz)

`F4-010` fixture'ı ve `F4-011`–`F4-013` decoder/sorgu işleri aşağıdaki **sabit**
yapılandırmayı kullanır. (Bölüm 8.3 taslağı 96 kHz / 12000 örnek örneği verir;
bu sürüm yarısıdır — sözleşme aynı, sayılar bu profile özgüdür.)

### 2.1 Kanallar

`ChannelTable`'da tanımlı akustik kanallar (`SENSOR_RAW` bloğu taşıyanlar):

| `channel_id` | Ad | Yol | Birim | `sample_rate_hz` | dtype |
| --- | --- | --- | --- | --- | --- |
| `0` | `Hydrophone 1` | `Acoustic/Hydrophone 1` | `Pa` | `48000` | `int16` (`0x01`) |
| `1` | `Hydrophone 2` | `Acoustic/Hydrophone 2` | `Pa` | `48000` | `int16` (`0x01`) |
| `2` | `Hydrophone 3` | `Acoustic/Hydrophone 3` | `Pa` | `48000` | `int16` (`0x01`) |
| `3` | `Hydrophone 4` | `Acoustic/Hydrophone 4` | `Pa` | `48000` | `int16` (`0x01`) |

`gain`/`offset` (`int16` ham → `Pa`) `ChannelTable` girdisinde taşınır; ham→fiziksel
dönüşüm yalnız görüntülenecek/analiz edilecek aralığa uygulanır (kopyasız view).

### 2.2 Blok başına örnek sayısı ve payload boyutu

Her kayıt her akustik kanal için **tam bir** `SENSOR_RAW` bloğu taşır:

| Büyüklük | Formül | Değer |
| --- | --- | --- |
| Blok başına örnek sayısı | `sample_rate_hz × 0.125 s` = `48000 × 0.125` | **`6000`** |
| dtype boyutu | `int16` | `2 B` |
| **Payload boyutu** (`BlockHeader.block_size`) | `sample_count × dtype_size` = `6000 × 2` | **`12000 B`** |
| `BlockHeader` | sabit | `16 B` |
| Bloğun kayıttaki toplam alanı | `align8(16 + 12000)` = `align8(12016)` | `12016 B` (zaten 8'in katı) |
| Kayıt başına akustik veri (4 kanal) | `4 × 12016` | `48064 B` |

- `sample_count` **alanı yoktur**; `sample_count = block_size / dtype_size` olarak
  türetilir ve `block_size % 2 == 0` doğrulanır (`6000 × 2 = 12000` tam bölünür).
- 125 ms sınırında **örnek tekrarı yoktur**: `DataNNNNN` bloğu `[n·125ms, (n+1)·125ms)`
  yarı-açık penceresinin 6000 örneğini taşır; bir sonraki kayıt `(n+1)·125ms`'ten
  başlar (`F4-012`).
- 1 saniye = 8 kayıt × 6000 örnek = **48000 örnek/kanal/s** → tam olarak
  `sample_rate_hz`.

### 2.3 Bir kaydın bayt bütçesi (bu profil)

| Bölüm | Boyut |
| --- | --- |
| `RecordHeader` | `48 B` |
| `SENSOR_RAW` × 4 (ch0–ch3) | `4 × 12016 = 48064 B` |
| `TX_STATUS` × 1 | `align8(16 + 24) = 40 B` |
| `BIT_STATUS` (yalnız her 8. kayıt) | `align8(16 + 12·n)` |
| `EVENT_LOG` (yalnız olay varsa) | değişken |
| `RecordTrailer` | `8 B` |
| **Tipik kayıt (BIT/EVENT yok)** | `48 + 48064 + 40 + 8 = 48160 B` |

1 saniyelik dosya ≈ `8 × 48160 ≈ 385 KB`; 1 dakika ≈ `23 MB`; 1 saat ≈ `1,35 GB`
(BIT/EVENT ihmal edilebilir). Bu ölçek Profil B'nin belleğe **sığmadığı** ve
mmap/lazy okuma gerektirdiği anlamına gelir (Bölüm 11).

## 3. Bayt yerleşimi

### 3.1 FileHeader (256 B, sabit)

| Offset | Alan | Tip | Değer / kural |
| --- | --- | --- | --- |
| `0x00` | `magic` | `char[8]` | `53 4E 52 42 49 4E 1A 00` → `"SNRBIN\x1A\x00"` (Profil A'dan farklı) |
| `0x08` | `version_major` | `uint16` | `1` |
| `0x0A` | `version_minor` | `uint16` | `0` |
| `0x0C` | `header_size` | `uint16` | `256` |
| `0x0E` | `channel_count` | `uint16` | `4` (bu profil) |
| `0x10` | `channel_table_size` | `uint32` | `channel_count × 64` = `256` |
| `0x14` | `record_period_ns` | `uint32` | `125000000` |
| `0x18` | `flags` | `uint32` | bit0 = "kayıt tamamlanmadı" (canlı kesinti) |
| `0x1C` | `t0_utc_ns` | `uint64` | `Data00000`'ın başlangıcı, Unix epoch UTC ns |
| `0x24` | `device_id` | `char[16]` | ASCII, `0x00` dolgu |
| `0x34` | `record_count` | `uint32` | biliniyorsa kayıt sayısı, canlı kesintide `0` |
| `0x38` | `reserved` | `byte[196]` | `0x00` |
| `0xFC` | `header_crc32` | `uint32` | `0x00..0xF8` üzerinde CRC-32/ISO-HDLC |

`struct`: `<8sHHHHIIIQ16sI196sI` → `256 B` (bkz. §8.3.11).

### 3.2 ChannelTable girdisi (64 B/kanal)

| Alan | Tip | Açıklama |
| --- | --- | --- |
| `channel_id` | `uint16` | `0..3` |
| `source` | `uint8` | `2` = `ACOUSTIC` |
| `dtype` | `uint8` | `0x01` = `int16` |
| `path` | `char[24]` | `"Acoustic/Hydrophone 1"` … `0x00` dolgu |
| `unit` | `char[8]` | `"Pa"` `0x00` dolgu |
| `sample_rate_hz` | `float32` | `48000.0` |
| `gain` | `float32` | ham `int16` → `Pa` |
| `offset` | `float32` | |
| `calibration_id` | `uint16` | `0` = yok |
| `reserved` | `uint16` | `0` |
| `name` | `char[12]` | kısa ad, `"Hydrophone 1"` |

`struct`: `<HBB24s8sfffHH12s` → `64 B`.

### 3.3 RecordHeader (48 B) + Trailer (8 B)

`plan.md` §8.3.4 ile aynı: `name` (`char[12]`, `record_name(index)`),
`record_index` (`uint32`), `record_size` (`uint32`, blok zinciri + `RecordHeader`
+ `Trailer`, 8'in katı), `block_count` (`uint16`), `flags` (`uint16`),
`t_start_offset_ns` (`int64`), `device_ticks` (`uint64`), `payload_crc32`
(`uint32`), `reserved` (`uint32`). Trailer: `payload_crc32` tekrarı (`uint32`) +
`b"ENDR"`.

### 3.4 BlockHeader (16 B)

```text
 0        2        4                8        10   11   12            16
 │ type   │ flags  │ block_size     │ ch_id  │dtyp│rsv │ t_offset_ns │ payload →
 │ uint16 │ uint16 │ uint32         │ uint16 │ u8 │ u8 │ int32       │
```

`SENSOR_RAW` akustik bloğu için bu profil:

| Alan | Değer |
| --- | --- |
| `type` | `0x0001` (`SENSOR_RAW`) |
| `block_size` | `12000` |
| `ch_id` | `0..3` |
| `dtype` | `0x01` (`int16`, 2 B) |
| `t_offset_ns` | `0` (blok kayıt başlangıcıyla hizalı) |
| payload | `6000 × int16` little-endian, `np.frombuffer(mm, "<i2", count=6000, offset=…)` |

Sonraki blok: `next = align8(cur + 16 + 12000)` = `cur + 12016`.

## 4. Doğrulama kuralları (bu profile özgü eklemeler)

`plan.md` §8.3.12'deki genel kurallara ek olarak parser her akustik blokta:

- [ ] `block_size == 12000` (`sample_count == 6000`); farklıysa blok işaretlenir,
      okuma durmaz.
- [ ] `dtype == 0x01` (`int16`); başka dtype "beklenmeyen akustik dtype" raporlanır.
- [ ] `sample_rate_hz == 48000` (`ChannelTable`); tutarsızsa uyarı, blok atılmaz.
- [ ] Kayıt başına kanal başına **tam bir** `SENSOR_RAW` bloğu; eksik kanal
      `GAP_BEFORE` benzeri kalite bayrağıyla işaretlenir.
- [ ] 8 kayıtta kanal başına toplam `48000` örnek; sapma zaman/örnek tutarsızlığı
      olarak raporlanır (`F4-012`).

## 5. Bu taslakla doğrulanmayan maddeler

| Konu | Durum |
| --- | --- |
| Gerçek cihazın akustik blok formatı | **BİLİNMİYOR** (E-01/E-03). Bu sözleşme kendi kararımızdır. |
| Gerçek `sample_rate_hz` (48 k mı 96 k mı, kanal sayısı) | **ÖNERİ**. Fixture ve testler bu profile göre kurulur; gerçek değerler gelince güncellenir. |
| `int16` ham ölçek / `gain`/`offset` | **ÖNERİ**. |
| CRC algoritması | `ADR-011` "Önerildi" — Profil A ile aynı (CRC-32/ISO-HDLC). |
