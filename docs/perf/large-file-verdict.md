# Büyük dosya koşusunun değerlendirmesi — F4-065

`F4-064` ölçtü (`docs/perf/results/large-file.json`); bu belge o ölçümü
Bölüm 11.1 hedeflerine karşı **karara** çevirir. Karar makine tarafından
üretilir (`tools/evaluate_large_file_run.py` →
`docs/perf/results/large-file-verdict.json`) ve
`tests/unit/test_large_file_verdict.py` depodaki kararın depodaki ölçümden
yeniden üretilebildiğini doğrular. Aşağıdaki tablo elle yazılmamıştır.

Koşu: AMD Ryzen 16 çekirdek, 32 GiB RAM, Windows 11, Python 3.9.13,
NumPy 2.0.2. Ölçülen dosyalar 64 MB, 256 MB ve 1 GB (Profil B, seed 20260910).

## Karar

| Hedef | §11.1 | Ölçülen | Durum |
| --- | --- | --- | --- |
| `metadata_seconds` | ≤ 5 s | 0,148 ms (64 MB) | **geçti** |
| `query_ms` | çoğu durumda ≤ 150 ms | 0/15 sorgu bütçede (%0) | **saptı** |
| `pipeline_fps` | ≥ 30 FPS | 0,24 FPS (1 GB, koşu kesildi) | **saptı** |
| `memory_scaling` | dosya boyutuyla doğrusal büyümemeli | bayt başına tepe 5,11 → 5,11 (1,00x) | **saptı** |

Dört hedeften biri geçer, üçü sapar. Sapmalar tek bir nedene bağlıdır.

## Kanıt: ölçek serisi

| Dosya | 0,01 s sorgu | 0,1 s sorgu | 1 s sorgu | 10 s sorgu | Tam kapsam | `pipeline_fps` | Tepe bellek |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64 MB | 236 ms | 240 ms | 312 ms | 948 ms | 12,3 s | 3,20 | 327 MB |
| 256 MB | 974 ms | 968 ms | 1030 ms | 1670 ms | 47,8 s | 0,98 | 1309 MB |
| 1 GB | 4001 ms | 4024 ms | 4069 ms | 4663 ms | 190,9 s | 0,24 | 5112 MB |

Üç gözlem sapmaların niteliğini belirler:

1. **Sorgu süresi pencere genişliğinden neredeyse bağımsızdır.** 64 MB'de
   0,01 s'lik bir pencere 236 ms, 0,1 s'lik pencere 240 ms sürer — pencere
   10 kat genişlerken süre %2 artar. Maliyeti belirleyen istenen aralık değil,
   **dosya boyutudur**.
2. **Sorgu süresi dosya boyutuyla doğrusaldır.** Dosya 4x büyürken 0,1 s
   sorgusu 240 → 968 → 4024 ms olur (4,03x ve 4,16x).
3. **Bayt başına tepe bellek sabittir (5,11).** Kullanım sabit olsaydı bu oran
   64 MB → 1 GB geçişinde ~0,06x'e inerdi; 1,00x kalması kullanımın dosya
   boyutuyla doğrusal büyüdüğünü gösterir. 1 GB dosya için tepe süreç working
   set'i 7,09 GB ölçülmüştür.

Üçü birlikte tek bir cümleye iner: **her viewport sorgusu kanalın tamamını
çözer.**

## Kök neden (ölçülmüş, tahmin değil)

64 MB dosyada 0,1 s'lik tek bir pencere sorgusunun `cProfile` dökümü:

| Aşama | Süre | Pay |
| --- | --- | --- |
| `channel_sample_times_ns` (F4-012) | 101 ms | %70 |
| `channel_samples` (F4-011) | 36 ms | %25 |
| `query_acoustic_channel` kendi dilimlemesi | 6 ms | %4 |

`query_acoustic_channel` önce kanalın **bütün** zaman dizisini ve **bütün**
örneklerini üretir, sonra `searchsorted` ile 0,1 s'lik dilimi alır. Her ikisi de
`iter_records` üzerinden dosyayı baştan sona dolaşır — sorgu başına iki tam
geçiş (profilde `iter_records` 1330 kayıt için 2662 kez çağrılır). 166 s'lik bir
kayıtta 0,1 s görmek için 7,98 milyon örnek çözülür ve `float64`'e genişletilir.

Bu, `plan.md` §11.2'de sayılan yöntemlerden **"görünür zaman aralığını
sorgulama"** maddesinin Profil B okuma yolunda henüz uygulanmamış olması
demektir. Profil A tarafında bu vardır: `FileRecordingRepository._query_raw`
`bisect_left` ile yalnız ilgili kayıtları okur. Profil B'de eşdeğer bir kayıt
indeksi yoktur.

Doğrusal bellek de aynı yerden gelir: 1 GB dosyanın 124,7 milyon `int16` örneği
`float64`'e genişletildiğinde tek başına ~1 GB, `ViewportSummary` bunun zaman
dizisiyle birlikte kopyasını aldığında birkaç GB'ye çıkar.

## Sapmayan hedef

`metadata_seconds` her boyutta 0,15 ms'nin altında kalır ve boyuttan
bağımsızdır: kayıt aralığı `FileHeader`'dan `O(1)` türetilir, kanal listesi
yalnız ilk kaydı çözer. `--verify-span` ile tüm dosya taranıp header'ın doğru
olduğu ayrıca doğrulanmıştır (tarama süreye dahil edilmez). Hedef 5 s;
ölçülen 0,000148 s — yaklaşık 34.000x pay.

## Hedeflerin durumu ve sonraki iş

* **Ölçülemeyen hedef yok.** Bellek doğrusallığı için gereken çok boyutlu koşu
  yapılmış, karar `yetersiz` değil `saptı` çıkmıştır.
* **F4-059 LRU önbelleği sapmanın nedeni değildir.** 1 GB koşusunda önbellek
  bütçesinin (64 MiB) yalnız 18 MB'si kullanılmış, hiç çıkarma olmamış, bir tek
  ret (tam kapsam özeti bütçeden büyük) sayılmıştır. Önbellek isabet sayısı
  sıfırdır çünkü pan penceresi her karede yeni bir aralığa gider; sorunu
  önbellek büyütmek çözmez, sorgunun kendisi pahalıdır.
* **Sapmalar mimari, parametrik değil.** `max_points`, önbellek bütçesi veya
  kare aralığı değiştirilerek kapanmazlar; Profil B okuma yoluna kayıt indeksi
  ve blok düzeyinde seek eklenmesi gerekir.
* Bu sonuç `F4-066` (indeks kesintisi ve cache kurtarma) ve `F4-067` (profil
  sonucuyla native hızlandırma ADR'si) için girdi olur. §11.3'ün "önce
  algoritma, veri kopyalama ve cache sorunlarını düzelt" maddesi burada
  doğrudan uygulanır: darboğaz native kod eksikliği değil, gereksiz tam-dosya
  çözümüdür.

Koşuyu yeniden üretme komutları `docs/perf/large-file-benchmark.md`
belgesindedir. Kararı yeniden üretmek için:

```powershell
.venv/Scripts/python.exe tools/evaluate_large_file_run.py `
  --input docs/perf/results/large-file.json `
  --out docs/perf/results/large-file-verdict.json
```
