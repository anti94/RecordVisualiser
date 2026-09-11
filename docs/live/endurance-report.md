# Dayanıklılık koşusu raporu — `F5-039`

**Kabul kriteri:** Bellek bütçesi, beklenen kayıp ve kayıt bütünlüğü sonuçları kanıtlıdır.

**Sonuç: üç ölçüt de geçti.** Kararlar `docs/live/results/endurance-verdict.json`
dosyasındadır ve `tools/evaluate_endurance_run.py` ile üretilir; ölçümün kendisi
`docs/live/results/endurance.json` dosyasındadır ve `tools/live_endurance_run.py`
(`F5-038`) ile üretilir. Bu belge o sayıların **ne anlama geldiğini** ve neyin hâlâ
kanıtlanmadığını yazar.

## 1. Koşu

| | |
| --- | --- |
| Süre | **2 saat** (57 600 adet 125 ms penceresi) |
| Seed | `20260911` — koşu birebir tekrar üretilebilir (`F5-036`) |
| Bozulma profili | `loss_ratio = 0,01` (ağda %1 paket kaybı) |
| Duvar saati | 15,2 s |
| Makine | Windows 10 (10.0.26200), Python 3.9.13, AMD64 |

Koşu **simüle edilmiş zamanda** ilerler: 2 saat beklenmez, 2 saatlik *veri*
üretilir. Ölçülen üç şeyin hiçbiri süreye değil paket sayısına bağlıdır —
bellek tampon kapasitelerine, kayıp paket sayısına, dosya boyutu kayıt
sayısına. Gerçek saat beklenseydi ölçüm hiç koşturulamaz ve "hazırlandı"
demekten öteye gidilemezdi.

## 2. Bellek bütçesi — `geçti`

| Ölçülen | Kural |
| --- | --- |
| son çeyrek / ilk çeyrek = **1,0034** | oran ≤ 1,10 |

İki saatlik akış boyunca 114 örnek alındı; tutulan bellek ilk çeyrekte ortalama
32,98 MB, son çeyrekte 33,09 MB. Aradaki fark **%0,34**.

Ölçüt neden *oran*, neden tepe değil: tepe bellek geçici bir tahsisten de
gelebilir ve tek bir sayı eğilimi göstermez. Aranan şey belleğin **süreyle
büyümemesi**; canlı katman sabit kapasiteli yapılar kullandığı için
(`LiveRingBuffer`, `BoundedPacketQueue`, sınırlı olay/BIT/TX kuyrukları) doğru
davranış yatay bir çizgidir. Bu, `docs/perf/budget.md` P-09'un canlı
karşılığıdır: orada bellek dosya boyutuyla, burada süreyle doğrusal
büyümemelidir.

%10'luk pay tahsis edici gürültüsü ve `tracemalloc`'un kendi defterleri içindir.
Gerçek bir sızıntı 2 saatte bu payı çok aşar — ölçülen %0,34 ile sınır arasında
yaklaşık 30 kat yer vardır.

## 3. Beklenen kayıp — `geçti`

| Ölçülen | Kural |
| --- | --- |
| 617 / 57 600 = **%1,07** | beklenen %1'den en çok %25 bağıl sapma |
| 56 983 + 617 + 0 = **57 600** | üretilen = kaydedilen + ağda düşen + diskte düşen |

İki ayrı şey doğrulanır ve ikisi de gereklidir:

1. **Oran beklenene yakın.** Bozucu %1 kayıp üretmek üzere ayarlandı; gözlenen
   %1,07. 57 600 denemede bu sapma rastgeleliğin kendisidir.
2. **Korunum yasası sağlanıyor.** Üretilen her pencere ya kaydedildi ya da
   sayılan bir kaleme düştü. Bu kontrol olmasaydı, kaybolan bir pencere hiçbir
   kaleme yazılmadan yok olabilir ve rapor yine de tutarlı görünürdü — sessiz
   veri kaybının tam da böyle görüneceği yer burasıdır.

Kayıp üç ayrı kalemde tutulur (ağ / kuyruk / disk) çünkü üçü ayrı nedendir ve
ayrı çözümler ister. Bu koşuda kuyruk ve disk kaybı sıfırdır: akış doğrudan
tüketildiği için kuyruk basıncı oluşmadı ve disk yetişti.

Sıra izleyicinin gözlediği eksik de 617'dir; yani ağda düşen her paket
izleyicide de görüldü. (`F5-037`'de gösterildiği gibi izleyici, ilk gözlenen
paketten *önceki* kaybı göremez; bu koşuda ilk paket düşmediği için iki sayı
birebir tutuyor.)

## 4. Kayıt bütünlüğü — `geçti`

| Ölçülen | Kural |
| --- | --- |
| **56 983 kayıt** geri okundu | CRC tutar, sıra artar, artık bayt yok, başlık geçerli |

Bütünlük, yazıcının sayacına bakarak iddia edilemez: dosyanın okunabildiği
ancak **okunarak** bilinir. Koşu bittikten ve dosyalar kapandıktan sonra
(`F5-029`'un garantisi ancak kapanmış dosya için geçerlidir) yazılan dosya
baştan sona çözüldü:

- başlık `read_validated_header` ile doğrulandı,
- her kaydın CRC'si ADR-011 §2.2'ye göre **kendi alanı hariç** `zlib.crc32` ile
  yeniden hesaplanıp karşılaştırıldı — yazıcının kendi CRC yardımcısı
  kullanılsaydı kontrol yalnız kodun kendisiyle tutarlılığı ölçerdi,
- dosyanın tam bir kayıt sınırında bittiği doğrulandı (artık bayt: 0),
- sıra numaralarının arttığı doğrulandı.

Kusur sayısı her kalemde sıfırdır ve okunan kayıt sayısı yazılanla birebir
aynıdır. Dosya boyutu da bağımsız olarak tutuyor: 3 874 880 bayt = 36 baytlık
başlık + 56 983 × 68 baytlık kayıt.

## 5. Kanıtlanmayanlar

Rapor yalnız ölçtüğünü söyler; aşağıdakiler bu koşunun **kapsamı dışındadır**:

- [ ] **Gerçek zamanlı davranış.** Koşu simüle edilmiş zamandadır; gerçek bir
      ağ kaynağının 2 saat boyunca zamanlama davrandığı ölçülmedi. Ölçülen
      şeyler (bellek, kayıp muhasebesi, bütünlük) zamana bağlı olmadığı için
      bu kapsam sınırı bilinçlidir.
- [ ] **Kuyruk ve disk baskısı altında 2 saat.** Bu koşuda kuyruk ve disk
      kaybı sıfırdı. Burst altında kuyruk sınırı ve taşma `F5-037`'de ayrıca
      doğrulandı, ama iki saat boyunca sürekli baskı denenmedi.
- [ ] **Süreç RSS'i.** Ölçülen `tracemalloc` ile *tutulan Python belleğidir*;
      işletim sistemi çalışma kümesi (fragmentasyon, NumPy arenaları) ayrıca
      ölçülmedi.
- [ ] **2 saatten uzun koşu.** Alt sınır olan 2 saat karşılandı; daha uzun
      sürelerde davranış bu koşudan çıkarılamaz — ancak bellek oranı 2 saatte
      yatay olduğu için doğrusal bir sızıntı beklenmez.

## 6. Tekrar üretmek

```powershell
.venv\Scripts\python.exe tools\live_endurance_run.py --hours 2
.venv\Scripts\python.exe tools\evaluate_endurance_run.py --markdown docs\live\results\endurance-verdict.md
```

Değerlendirici, ölçütlerden biri saparsa **sıfırdan farklı** çıkış kodu verir;
raporun "geçti" görünürken sürecin sessizce devam etmesi istenmez.
