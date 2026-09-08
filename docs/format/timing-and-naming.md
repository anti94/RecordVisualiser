# 125 ms periyot ve kayıt adı kuralları

> `F0-006` çıktısıdır. **Her iki profil için bağlayıcıdır** (Profil A: Bölüm 8.2, Profil B: Bölüm 8.3).
> Kayıt adlandırması ve zaman ızgarası tek yerde tanımlanır; profiller yalnız kayıt gövdesinde ayrışır.

## 1. Zaman ızgarası

| Kural | Değer |
| --- | --- |
| Nominal periyot | 125 ms = 125 000 µs = 125 000 000 ns |
| Kayıt hızı | 8 kayıt/saniye |
| Izgara | `elapsed_us(n) = n × 125000` |
| Mutlak zaman | `start_time_utc_ns + elapsed_us × 1000` |
| Ankor | Yalnız dosya header'ında (`start_time_utc_ns` / `t0_utc_ns`); kayıtlar offset taşır |

Türev büyüklükler: 1 saniye = 8 kayıt · 1 dakika = 480 kayıt · 1 saat = 28 800 kayıt.

## 2. Kayıt adı

```python
def record_name(sequence_no: int) -> str:
    return f"Data{sequence_no:05d}"
```

- Önek `Data`, **en az 5 hane**, sıfır dolgulu.
- `sequence_no` 99 999'u aştığında hane sayısı büyür: `Data99999` → `Data100000`.
  **Sayaç sıfırlanmaz, ad sarmaz.** Böylece bir dosya içinde ad benzersizdir ve `Data00042` araması
  tek bir kaydı bulur.
- `char[12]` alanı en fazla `Data9999999` (7 hane) + sonlandırıcı sıfırı taşır. Bu sınır
  `9 999 999 × 0,125 s ≈ 14,5 gün`'e karşılık gelir; çok daha önce yeni dosyaya geçilir.
- **Ad bir etikettir.** Sıralama, indeksleme, korelasyon ve arama daima sayısal alan üzerinden yapılır
  (Profil A `sequence_no`, Profil B `record_index`). Ad ile sayı uyuşmazsa tutarsızlık raporlanır ve
  sayısal alan esas alınır.

> **Karar (F0-006):** Bu kural Profil B için de geçerlidir. `plan.md` Bölüm 8.3.8'in önceki taslağında
> ad 5 hanede sarıyordu (`record_index % 100000`); bu, uzun kayıtlarda aynı adın birden çok kayda
> denk gelmesine yol açıyordu. Sarma kaldırıldı; her iki profil aynı `record_name()` fonksiyonunu kullanır.
> Profil B header'ındaki `record_name_digits` alanı artık **asgari** hane sayısıdır.

## 3. Kayıpsız dosya örneği

`start_time_utc_ns = 2026-09-08T21:00:00Z`, Profil A (32 B header + 64 B kayıt):

| `sequence_no` | Ad | `elapsed_us` | UTC | Dosya offseti |
| --- | --- | --- | --- | --- |
| 0 | `Data00000` | 0 | 21:00:00.000 | 32 |
| 1 | `Data00001` | 125 000 | 21:00:00.125 | 96 |
| 2 | `Data00002` | 250 000 | 21:00:00.250 | 160 |
| 3 | `Data00003` | 375 000 | 21:00:00.375 | 224 |
| 7 | `Data00007` | 875 000 | 21:00:00.875 | 480 |
| 8 | `Data00008` | 1 000 000 | 21:00:01.000 | 544 |

İlk saniye `[0, 1000 ms)` aralığı tam olarak `Data00000`–`Data00007`'dir; `Data00008` ikinci saniyenin
ilk kaydıdır. 8 kayıtlık dosya `32 + 8 × 64 = 544` byte olur.

## 4. Sıra boşluğu (kayıp periyot)

Kayıp periyot için **kayıt yazılmaz**; dolgu kayıt üretilmez. Aşağıda `sequence_no = 5` kaybolmuştur:

| Fiziksel sıra | `sequence_no` | Ad | `elapsed_us` | Dosya offseti |
| --- | --- | --- | --- | --- |
| 0 | 0 | `Data00000` | 0 | 32 |
| 1 | 1 | `Data00001` | 125 000 | 96 |
| 2 | 2 | `Data00002` | 250 000 | 160 |
| 3 | 3 | `Data00003` | 375 000 | 224 |
| 4 | 4 | `Data00004` | 500 000 | 288 |
| 5 | **6** | `Data00006` | 750 000 | 352 |
| 6 | 7 | `Data00007` | 875 000 | 416 |
| 7 | 8 | `Data00008` | 1 000 000 | 480 |

Dosya yine 8 kayıt ve 544 byte'tır, ancak **`Data00005` yoktur**.

### 4.1 Tespit

Ardışık iki kayıtta `sequence_no` farkı 1'den büyükse boşluk vardır:

```python
delta = rec.sequence_no - prev.sequence_no
if delta > 1:
    missing = delta - 1                      # kayıp periyot sayısı
    gap_us = missing * RECORD_PERIOD_US      # 1 kayıp -> 125000 µs
```

Yukarıdaki örnekte fiziksel 5. kayıt okunduğunda `sequence_no = 6`, beklenen `elapsed_us = 625000`
yerine `750000` görülür → tek periyotluk boşluk raporlanır.

### 4.2 Sonuçlar

- **Offset formülü yalnız kayıpsız dosyada geçerlidir.** Boşluklu dosyada
  `32 + sequence_no × 64` yanlış kaydı gösterir (örnekte `Data00006` için `32 + 6×64 = 416`,
  gerçek offset `352`). `sequence_no` ile doğrudan seek yapılmaz; indeks kullanılır
  veya dosya sıralı taranır.
- Boşluk grafikte **kesinti** olarak çizilir; interpolasyon veya sıfır dolgu yapılmaz.
- Boşluk bir hata değil, veri kalitesi bilgisidir: sayısı ve toplam süresi kayıt özetinde gösterilir.
- Geri giden `sequence_no` boşluk değildir; dosya bozulması veya cihaz yeniden başlatması sayılır
  ve ayrı raporlanır.

## 5. Nominal ızgara ile gerçek zaman

`elapsed_us` nominal ızgaradır. Cihazın gerçek zamanlaması ham sayaçtan gelir
(Profil B `device_ticks`; Profil A'da ham sayaç alanı yoktur).

- Sapma toleransı yapılandırılabilir; öntanımlı ±%1 (±1,25 ms).
- Tolerans aşılırsa kayıt `jitter` işaretlenir; veri atılmaz.
- UTC, yerel saat ve geçen süre kullanıcıya **ayrı** gösterilir; birbirine dönüştürülürken
  kullanılan ankor her zaman header'daki başlangıç zamanıdır.
- Ayrıntılı zaman kaynağı/drift kararı `F0-011`'de yazılır (envanter E-07).
