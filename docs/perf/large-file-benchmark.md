# Büyük dosya benchmark koşusu — F4-064

`F4-063` üretim komutlarını hazırladı; bu adım o dosyaların **ölçüm** koşusunu
hazırlar ve ilk sonucu üretir. Araç `tools/large_file_benchmark.py`, sonuç
`docs/perf/results/large-file.json`. Değerlendirme (§11.1 hedeflerinin geçtiği
veya saptığı) `F4-065`'in işidir; bu belge yalnız ne ölçüldüğünü ve nasıl
yeniden üretileceğini anlatır.

## Ne ölçülür

Dört sonuç ailesi `plan.md` §11.1 satırlarına birebir bağlanır:

| Aile | JSON alanı | §11.1 hedefi |
| --- | --- | --- |
| Metadata | `metadata.seconds` | Büyük kayıtta metadata görünmesi ≤ 5 s |
| Sorgu | `queries[].duration_ms` | Viewport veri sorgusu çoğu durumda ≤ 150 ms |
| FPS | `frame_rate.pipeline_fps` | Pan/zoom etkileşimi algılanan ≥ 30 FPS |
| Bellek | `memory.*_per_file_byte` | Dosya boyutuyla doğrusal büyümemeli |

Hedefler raporun içine `targets` alanı olarak da yazılır, böylece sonuç dosyası
tek başına okunabilir. Her sonuç `machine` bilgisiyle (işlemci, çekirdek sayısı,
fiziksel bellek, Python ve NumPy sürümü, platform) birlikte üretilir; farklı
bilgisayarların sayıları karıştırılamaz.

## Ölçüm sözleşmesi

* **Gerçek yığın koşar.** `MappedSource` (F4-053) eşlemesi üzerinden
  `query_acoustic_channel` (F4-013) okur, `DisplayQuery` (F4-058 özet seviyesi +
  F4-059 bellek sınırlı LRU) sunar. Hiçbir aşama taklit edilmez.
* **`pipeline_fps` Qt paint süresini içermez.** Sorgu + downsample aşamasının
  üst sınırıdır; algılanan FPS bundan **yüksek olamaz**, düşük olabilir.
* **Sorgular soğuk ölçülür.** Her genişlikten önce önbellek boşaltılır: hedef
  kullanıcının yeni bir pencereye ilk gidişini tanımlar, önbellekten dönen
  ikinci gidişi değil.
* **FPS koşusu kendi ısınmasını içerir.** Önbellek koşunun başında bir kez
  boşaltılır ki sorgu ölçümünden kalan tam-kapsam penceresi her kareyi isabete
  çevirip FPS'i ölçüm sırasının yan etkisiyle şişirmesin; koşu içinde önbellek
  korunur, çünkü gerçek pan'de kullanıcı sıcak önbellekle gezinir.
* **Bellek iki ayrı kaynaktan okunur.** `tracemalloc` yalnız Python
  ayırmalarını, tepe working set eşlenmiş dosya sayfalarını da görür. Ölçülemeyen
  bir platformda alan `null` kalır — uydurma değer üretilmez.
* **Uzun koşu kesilebilir.** `--frame-budget-seconds` aşılırsa döngü durur ve
  `frame_rate.truncated` `true` olur; FPS tamamlanan kareler üzerinden hesaplanır
  ve yine gerçektir.
* **Aralık header'dan `O(1)` gelir.** `--verify-span` verilirse tüm dosya
  taranıp header aralığı doğrulanır; bu tarama metadata süresine **dahil
  edilmez**, yalnız header'ın doğru olduğunu kanıtlar.

## Yeniden üretme

Önce `F4-063` komutlarıyla dosyaları üretin (izlenmeyen `.cache/` altında
kalırlar), sonra:

```powershell
.venv/Scripts/python.exe tools/large_file_benchmark.py `
  --input .cache/perf/profile-b-64mb.bin `
  --input .cache/perf/profile-b-256mb.bin `
  --input .cache/perf/profile-b-1gb.bin `
  --out docs/perf/results/large-file.json `
  --frames 30 --frame-budget-seconds 90 --verify-span
```

Birden çok `--input` vermek şarttır: "bellek dosya boyutuyla doğrusal
büyümemeli" hedefi tek bir boyutla değerlendirilemez. Ölçek serisi
`retained_per_file_byte` ve `peak_per_file_byte` oranlarının boyutla sabit
kalıp kalmadığını gösterir.

Diğer bayraklar: `--max-points` (piksel bütçesi, öntanımlı 2000),
`--frame-window-seconds` (pan penceresi genişliği), `--cache-bytes`
(gösterim önbelleği bütçesi, öntanımlı 64 MiB).

## Bu makinedeki ilk koşu

`docs/perf/results/large-file.json`, AMD Ryzen (16 çekirdek), 32 GiB RAM,
Windows 11, Python 3.9.13, NumPy 2.0.2:

| Dosya | Metadata | 0,1 s sorgu | 1 s sorgu | Tam kapsam | `pipeline_fps` | Tepe bellek / dosya baytı |
| --- | --- | --- | --- | --- | --- | --- |
| 64 MB | 0,1 ms | 240 ms | 312 ms | 12,3 s | 3,20 | 5,11 |
| 256 MB | 0,1 ms | 968 ms | 1030 ms | 47,8 s | 0,98 | 5,11 |
| 1 GB | 0,1 ms | 4024 ms | 4069 ms | 190,9 s | 0,24 | 5,11 |

Sorgu süresi ve FPS dosya boyutuyla doğrusal, tepe bellek oranı sabit çıkar.
Metadata her boyutta `O(1)` kalır. 1 GB koşusunda FPS döngüsü 30 karenin
22'sinde bütçeyi aşıp kesildi (`truncated: true`); kesilen koşunun FPS'i yine
tamamlanan karelerden hesaplanmıştır.

Bu tablo bir **ölçüm kaydıdır**, hedeflere karşı karar değildir. Hangi hedefin
geçtiği, hangisinin saptığı ve nedeni `F4-065`'te yazılır.
