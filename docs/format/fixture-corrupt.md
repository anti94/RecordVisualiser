# Bozuk fixture senaryoları — beklenen sonuçlar

> `F0-010` çıktısıdır. Taban dosya: `docs/format/fixture-valid-8records.md`
> (`valid_8records.bin`, 544 byte). Her senaryo o dosyadan **tek bir kusurla** türetilir;
> böylece gözlenen fark tek bir nedene bağlanabilir.
>
> Konum: `tests/fixtures/`

## 0. Ortak kurallar

- **Fail-soft:** Hiçbir senaryo uygulamayı çökertmez ve hiçbiri sessizce yutulmaz.
  Header okunabildiği sürece sağlam kayıtlar okunur ve çizilir.
- **Uydurma veri yok:** Eksik veya bozuk kayıt yerine interpolasyon, sıfır veya son değer konmaz;
  grafikte kesinti gösterilir.
- **Her bulgu konumlanabilir:** Tanılama satırı en az `kayıt adı` (biliniyorsa),
  `sequence_no` ve **dosya offseti** taşır.
- **Sayım özeti:** Kayıt özetinde bozuk kayıt sayısı, kayıp periyot sayısı ve toplam kayıp süre görünür.

| Kod | Fixture | Boyut | Kusur | Dosya açılır mı? |
| --- | --- | --- | --- | --- |
| K-01 | `truncated_header.bin` | 20 B | Header 32 byte'tan kısa | **Hayır** |
| K-02 | `truncated_last_record.bin` | 524 B | Son kayıt yarım | Evet |
| K-03 | `gap_missing_record.bin` | 544 B | `sequence_no = 5` yok | Evet |
| K-04 | `crc_error.bin` | 580 B | Bir kaydın CRC'si tutmuyor | Evet |
| K-05 | `unsupported_version.bin` | 544 B | `version = 99` | **Hayır** |
| K-06 | `name_index_mismatch.bin` | 544 B | Ad ile `sequence_no` uyuşmuyor | Evet |

---

## K-01 — Kesik header

**Üretim:** `valid_8records.bin`'in ilk **20** baytı.
**SHA-256:** `49c4c7a46803a28007700129a74544351fc0c6a14bc7dc89cf3930f4bff74651`

| Beklenen | Değer |
| --- | --- |
| Sonuç | Dosya **açılmaz** |
| Hata | `Kesik header: 32 byte gerekli, 20 byte bulundu` |
| Okunan kayıt | 0 |
| Kullanıcıya | Hata iletisi; boş çalışma alanı açılmaz, önceki durum korunur |

Doğrulama sırasının **1. adımıdır** (`profile-a.md` §3): boyut kontrolü `magic` okumadan önce yapılır,
aksi halde 20 baytlık dosyada `struct.unpack` istisna fırlatır.

---

## K-02 — Kesik son kayıt

**Üretim:** `valid_8records.bin`'in ilk **524** baytı (son kayıttan 20 byte eksik).
**SHA-256:** `ea294eba3f1f5ffcbf2fcdfd13c2fec9f4d3163bb7084122732c90a01fbd28ad`

`(524 - 32) = 492`, `492 // 64 = 7` tam kayıt, **44 byte artık**.

| Beklenen | Değer |
| --- | --- |
| Okunan kayıt | **7** (`Data00000` – `Data00006`) |
| Kapsanan aralık | 0 ms – 750 ms |
| Tanılama | `Kesik kayıt: offset 480, 44/64 byte` |
| Şiddet | Uyarı (hata değil) |
| `Data00007` | Hiç üretilmez; kısmi veri domain modeline **girmez** |

Bu senaryo canlı kayıt sırasında kesilen dosyayı temsil eder ve normal karşılanmalıdır.

---

## K-03 — Sıra boşluğu (kayıp periyot)

**Üretim:** `sequence_no = 5` yazılmadan 8 kayıt üretilir: `0, 1, 2, 3, 4, 6, 7, 8`.
**SHA-256:** `0ddd96308c58d7807004029fa4dcf19f20034eb2294ab2ec5274210c336bcaab`

Dosya yine 544 byte'tır; fiziksel konum ile `sequence_no` ayrışır:

| Fiziksel sıra | `sequence_no` | Ad | Offset |
| --- | --- | --- | --- |
| 4 | 4 | `Data00004` | 288 |
| 5 | **6** | `Data00006` | 352 |
| 6 | 7 | `Data00007` | 416 |
| 7 | 8 | `Data00008` | 480 |

| Beklenen | Değer |
| --- | --- |
| Okunan kayıt | 8 |
| Kayıp periyot | **1** (`sequence_no = 5`, 625 ms) |
| Kayıp süre | 125 ms |
| Tanılama | `Sıra boşluğu: 5 numaralı kayıt yok (625 ms), offset 352 öncesinde` |
| Grafik | 500 ms ile 750 ms arasında **kesinti**; iki nokta birleştirilmez |
| Kapsanan aralık | 0 ms – 1000 ms |

**Ek kontrol:** `32 + 6 × 64 = 416` offseti `Data00006`'yı **göstermez** (gerçek offset 352).
Bu fixture, `sequence_no` ile doğrudan seek yapan bir uygulamayı yakalar.

---

## K-04 — CRC hatası

**Profil A sürüm 2** (ADR-011): `header_size = 36`, `record_size = 68`, dosya `36 + 8 × 68 = 580` byte.
**Üretim:** Tüm kayıtlar geçerli CRC ile yazılır, ardından `Data00003`'ün CH0 alanının ilk baytı
`0x00 → 0x01` yapılır. CRC alanı **değiştirilmez**.
**SHA-256:** `d23348d74ce425532c534713fa83fa875d91d185b335f2298f067f08051f8aaf`

| Beklenen | Değer |
| --- | --- |
| Okunan kayıt | 8 (biri işaretli) |
| Bozuk kayıt | **1** — `Data00003`, `sequence_no = 3`, offset 240 |
| Saklanan CRC | `0xAA7584BF` |
| Hesaplanan CRC | `0x053116F8` |
| Tanılama | `CRC hatası: Data00003 (seq 3), offset 240` |
| `Data00003` verisi | **Çizilmez**; grafikte kesinti |
| Diğer 7 kayıt | Normal okunur ve çizilir |
| Header CRC | Geçerli; dosya açılır |

Bozuk alanın çözülmüş değeri `101.50000762939453` olur (beklenen `101.5`). Bu, CRC olmasaydı
**fark edilmeden geçecek** tek bitlik bir hatadır; senaryonun amacı tam olarak budur.

---

## K-05 — Desteklenmeyen sürüm

**Üretim:** `valid_8records.bin`'de `version` alanı (offset 8) `1 → 99`.
**SHA-256:** `cc1f6eeb520486415e13b1e8f2c00a669ea1a5a712630d6abc2e4596ebd27bfe`

| Beklenen | Değer |
| --- | --- |
| Sonuç | Dosya **açılmaz** |
| Hata | `Desteklenmeyen format sürümü: 99 (desteklenen: 1, 2)` |
| Okunan kayıt | 0 |
| Kural | Sürüm numarası kullanıcıya **gösterilir**; "bozuk dosya" gibi genel hata verilmez |

Decoder, tanımadığı sürümü tahmin ederek okumaya çalışmaz; yanlış yorumlanmış veri, okunamayan
veriden daha tehlikelidir.

---

## K-06 — Ad / `sequence_no` uyuşmazlığı

**Üretim:** `sequence_no = 2` olan kaydın `name` alanı `Data00099` yapılır; diğer alanlar dokunulmaz.
**SHA-256:** `b1f807cf1bbea070273ce48d9d2b45d06a402a46241cd1bd576b290e0cb14a84`

| Beklenen | Değer |
| --- | --- |
| Okunan kayıt | 8 (hepsi) |
| Tutarsızlık | **1** — offset 160 |
| Tanılama | `Ad tutarsızlığı: "Data00099" beklenen "Data00002" (seq 2), offset 160` |
| Kullanılan değer | **`sequence_no = 2`** — zaman ve sıralama bundan hesaplanır |
| Veri | Normal okunur; kayıt atılmaz |
| Şiddet | Uyarı |

`timing-and-naming.md` §2'deki "sayısal alan yetkilidir" kuralının testidir.

---

## Kabul kontrol listesi

Bir decoder sürümü aşağıdakilerin **tümünü** karşılamadan `F2` kabul işlerinden geçemez:

- [ ] K-01 ve K-05 dosyayı açmayı reddeder; hata iletisi nedeni ve sayısal ayrıntıyı içerir.
- [ ] K-02, K-03, K-04, K-06 dosyayı açar ve sağlam kayıtları eksiksiz okur.
- [ ] Dört farklı kusur dört **ayrı** tanılama türü üretir; tek bir "bozuk dosya" mesajına indirgenmez.
- [ ] Her tanılama satırı dosya offseti taşır.
- [ ] Hiçbir senaryoda uydurma/interpolasyon değer üretilmez.
- [ ] Hiçbir senaryoda işlenmemiş istisna kullanıcıya sızmaz.
