# ADR-003 — Kanonik zaman birimi ve time-base modeli

- **Durum:** Kabul edildi (uygulama kararı); cihaz tarafı parametreler onay bekliyor — envanter E-07
- **Karar tarihi:** 2026-09-08
- **İlgili işler:** `F0-011`, `F0-006`, `F2-*` decoder, `F5-*` canlı veri
- **İlgili belge:** `docs/format/timing-and-naming.md`

## 1. Bağlam

Uygulama tek zaman ekseninde üç ayrı kaynağı birleştirir: sensör örnekleri, BIT sonuçları ve
transmisyon durumları. Kaynaklar farklı çözünürlük ve farklı saat kaynağı kullanabilir:

- Profil A kaydı yalnız `start_time_utc_ns` (dosya ankoru) ve `elapsed_us` (nominal ızgara) taşır;
  **ham cihaz sayacı yoktur**.
- Profil B kaydı ayrıca `device_ticks` (ham sayaç) ve `device_tick_hz` taşır.
- Gerçek cihazın saat kaynağı, tick frekansı, GPS/PPS disiplini ve drift beklentisi **bilinmiyor** (E-07).

"Bu anormallik ne zaman oldu, aynı anda hangi olay gerçekleşti?" sorusu, zaman dönüşümünün kayıpsız ve
geri izlenebilir olmasını gerektirir.

## 2. Karar

### 2.1 Kanonik birim: `int64` nanosaniye, Unix epoch, UTC

Uygulama içindeki **tek** zaman temsili budur. Tüm domain modelleri (`DataChunk.timestamps_ns`,
`Event.timestamp_ns`, `TimeRange`) bu birimi kullanır.

| Gerekçe | Değer |
| --- | --- |
| Menzil | ±292 yıl — fazlasıyla yeterli |
| Çözünürlük | 1 ns — 96 kHz örnek aralığının (10 417 ns) çok altında |
| Karşılaştırma | Tamsayı; eşitlik ve sıralama kayıpsız, yuvarlama belirsizliği yok |
| NumPy | `np.int64` / `datetime64[ns]` ile doğrudan uyumlu |

**Reddedilen:** `float64` saniye. 2026 tarihlerinde ulp yaklaşık **238 ns**'dir; değer büyüdükçe
çözünürlük sessizce düşer ve iki zamanın eşitliği güvenilmez hâle gelir.

### 2.2 Üç zaman, üç ayrı alan

Hiçbiri diğerinin yerine geçmez ve hiçbiri kaybedilmez:

| Zaman | Tanım | Kullanım |
| --- | --- | --- |
| **Kanonik UTC ns** | `int64`, epoch tabanlı | Tüm iç hesaplar, korelasyon, sorgu |
| **Geçen süre (elapsed)** | Kayıt başlangıcına göre ns | Grafik ekseni öntanımlı gösterimi, playback |
| **Orijinal cihaz değeri** | `device_ticks` / `elapsed_us`, ham hâliyle | Tanılama, drift analizi, hata raporu |

Yerel saat yalnız **görüntüleme katmanında** üretilir; veri modelinde saklanmaz. Kullanıcı arayüzünde
UTC / yerel / geçen süre seçimi açıkça etiketlenir; üçü aynı anda aynı eksende karıştırılmaz.

### 2.3 Time-base modeli

```python
@dataclass(frozen=True)
class TimeBase:
    id: str                  # "device0", "host", "gps"
    epoch_utc_ns: int        # tick 0'in UTC karsiligi
    tick_hz: int             # 0 => sayac yok (Profil A)
    source: str              # "gps_pps" | "ptp" | "local_oscillator" | "unknown"
    drift_ppm: float = 0.0   # olculmus/bildirilmis sapma; 0 => duzeltme yok
```

Dönüşüm (tamsayı aritmetiği, yuvarlama hatası birikmez):

```python
def ticks_to_utc_ns(tb: TimeBase, ticks: int, ticks0: int) -> int:
    return tb.epoch_utc_ns + (ticks - ticks0) * 1_000_000_000 // tb.tick_hz
```

Her kanal bir `time_base_id` taşır (bkz. `ChannelMetadata`). Farklı time-base'lerdeki kanallar
karşılaştırıldığında, korelasyon toleransı ve senkron kalitesi kullanıcıya gösterilir.

**Profil A için:** `tick_hz = 0`, zaman doğrudan `start_time_utc_ns + elapsed_us * 1000`'dir.
Cihaz sayacı olmadığı için jitter/drift **ölçülemez**; bu dosyalarda senkron kalitesi
`bilinmiyor` olarak işaretlenir ve düzeltme uygulanmaz.

### 2.4 Sayaç sarması (wraparound)

Sarma, ardışık iki kayıtta `ticks` **azaldığında** aday olarak işaretlenir:

```python
if ticks < prev_ticks:
    delta = (ticks + 2**bits) - prev_ticks        # sarma varsayimi
    if 0 < delta <= max_plausible_delta:          # nominal periyodun birkac kati
        ticks_unwrapped += 2**bits                # sarma kabul edilir
    else:
        mark("sayac geri gitti / reset")          # sarma degil
```

| Sayaç genişliği | 10 MHz'de sarma süresi | Değerlendirme |
| --- | --- | --- |
| `uint64` (Profil B) | ~58 500 yıl | Pratikte hiç sarmaz |
| `uint32` | **429 s (~7 dk)** | Sarma **beklenir**; unwrap zorunlu |
| `uint32` @ 1 MHz | ~71,6 dk | Uzun kayıtta sarma beklenir |

Profil B `uint64` kullandığı için sarma beklenmez; yine de kontrol uygulanır, çünkü gerçek cihazın
sayaç genişliği bilinmiyor (E-07). Sarma tespiti **kayıt sınırında** yapılır ve unwrap edilmiş değer
ayrı tutulur; ham değer asla üzerine yazılmaz.

### 2.5 Reset davranışı

Sarma olarak açıklanamayan geri gidiş **cihaz reset'i** sayılır:

- Reset noktasından sonrası **yeni bir time-base segmenti** olur (`device0#1`, `device0#2`, …).
- Segmentler arası zaman ilişkisi bilinmez; uygulama iki segmenti **tek sürekli eksen gibi çizmez**.
- Kullanıcıya `Cihaz sayacı sıfırlandı — bu noktadan sonraki zamanlar önceki bölümle
  karşılaştırılamaz` uyarısı gösterilir.
- Reset, dosyayı geçersiz kılmaz; her segment kendi içinde tutarlıdır.

### 2.6 Drift

- Drift **ölçülür, sessizce düzeltilmez**. Ölçüm: kayıt başı `device_ticks` ile nominal 125 ms
  ızgarasının farkının zamana göre eğimi.
- Öntanımlı jitter toleransı nominal periyodun **%1**'i = **1,25 ms**. Aşan kayıt `jitter` işaretlenir;
  veri atılmaz.
- Ölçek fikri: **50 ppm** sapma 125 ms'te yalnız **6,25 us**, ancak 1 saatte **180 ms** — yani
  1,4 kayıt periyodu. Uzun kayıtta düzeltmesiz korelasyon kayar.
- Düzeltme uygulanırsa (`drift_ppm` sıfırdan farklı) bu **açıkça işaretlenir**; ham zaman erişilebilir
  kalır ve dışa aktarılan veride hangi zamanın kullanıldığı belirtilir.
- GPS/PPS disiplinli kaynakta düzeltme uygulanmaz; disiplinsiz osilatörde düzeltme opsiyoneldir ve
  öntanımlı **kapalıdır**.

### 2.7 Kayıp, tekrarlı ve sırasız zaman damgası

| Durum | Politika |
| --- | --- |
| Kayıp periyot | Kayıt yazılmaz; boşluk raporlanır, grafikte kesinti (bkz. `timing-and-naming.md` §4) |
| Aynı zaman iki kez | İkisi de saklanır, `duplicate` işaretlenir; sessizce ilki/sonuncusu seçilmez |
| Sırasız (out-of-order) | Okuma sırasında yeniden sıralanır; sıralama gerektiği **raporlanır** |
| Geri giden `sequence_no` | Reset veya bozulma (bkz. 2.5); sıralama düzeltmesiyle gizlenmez |

### 2.8 Senkron kalitesi

Her kayıt için üç durumdan biri hesaplanır ve talep edilince arayüzde gösterilir:

| Durum | Koşul |
| --- | --- |
| `iyi` | Sapma tolerans içinde, disiplinli saat kaynağı |
| `şüpheli` | Tolerans aşıldı veya kaynak `local_oscillator` |
| `bilinmiyor` | Ham sayaç yok (Profil A) veya time-base tanımsız |

Korelasyon toleransı (sensör ile BIT ve TX eşleştirmesi) yapılandırılabilir; öntanımlı **1 kayıt
periyodu (125 ms)**'dur, çünkü bu profillerde bir olayın konumu en fazla o kadar kesin bilinir.

## 3. Değerlendirilen alternatifler

| Seçenek | Neden seçilmedi |
| --- | --- |
| `float64` saniye | 2026 tarihlerinde ulp yaklaşık 238 ns; çözünürlük tarihe bağlı olarak sessizce değişir, eşitlik güvenilmez. |
| `datetime` nesnesi | Mikrosaniye çözünürlük (1 us) — 96 kHz için yetersiz; nesne başına bellek maliyeti milyonlarca örnekte kabul edilemez. |
| Cihaz tick'ini kanonik yapmak | Farklı time-base'li kaynaklar ortak eksende karşılaştırılamaz; UTC ankoru olmadan BIT/TX korelasyonu yapılamaz. |
| Sadece geçen süre (elapsed) | Kayıtlar arası karşılaştırma ve gerçek dünya olaylarıyla eşleştirme imkânsız hâle gelir. |
| Drift'i sessizce düzeltmek | Ölçüm verisinin zamanı sessizce değiştirilirse rapor kanıt değeri taşımaz. |

## 4. Sonuçlar

**Olumlu**

- Tek tamsayı temsili; karşılaştırma ve sorgu kayıpsız.
- Ham cihaz değeri korunduğu için her dönüşüm geri izlenebilir.
- Sarma ve reset ayrı ayrı ele alındığından, "zaman geri gitti" durumu veri kaybına yol açmaz.
- Senkron kalitesi kullanıcıya görünür; belirsizlik gizlenmez.

**Olumsuz**

- Her kanal için `time_base_id` taşımak veri modelini büyütür.
- Reset segmentleri arayüzde ek karmaşıklık (eksen kesintisi) gerektirir.
- Profil A dosyalarında jitter/drift ölçülemez; bu dosyalarda zaman kalitesi hakkında iddia edilemez.
- `tick_hz` gerçek değeri bilinmeden (E-07) dönüşüm doğrulanamaz; şimdilik header'daki değere güvenilir.

## 5. Doğrulama

- `tests/unit/test_time_base.py`: tick'ten UTC'ye dönüşüm, `uint32` sarma unwrap, reset tespiti,
  sırasız damga sıralaması, tolerans sınırları.
- `tests/integration/`: `gap_missing_record.bin` üzerinde boşluk süresinin 125 ms çıkması.
- Gerçek kayıt geldiğinde: nominal ızgara ile `device_ticks` farkının eğimi ölçülür ve
  `drift_ppm` bu ADR'ye işlenir.
