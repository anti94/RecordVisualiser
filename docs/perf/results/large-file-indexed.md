# F4-093 — İndeksli sorgu sonrası değerlendirme

2026-09-11, `c3f559e` / 1.91.0. Aynı makine, dosyalar, seed, 2000 nokta
bütçesi, 30 kare, 90 saniye kare koşusu sınırı ve `--verify-span` kullanıldı.
Koşu 302,6 saniye sürdü. Kaynaklar `.cache/perf/profile-b-{64mb,256mb,1gb}.bin`;
manifestlerindeki seed 20260910'dur.

```powershell
.venv/Scripts/python.exe tools/large_file_benchmark.py --input .cache/perf/profile-b-64mb.bin --input .cache/perf/profile-b-256mb.bin --input .cache/perf/profile-b-1gb.bin --out docs/perf/results/large-file-indexed.json --frames 30 --frame-budget-seconds 90 --verify-span
.venv/Scripts/python.exe tools/evaluate_large_file_run.py --input docs/perf/results/large-file-indexed.json --out docs/perf/results/large-file-indexed-verdict.json
```

[Ölçüm](large-file-indexed.json) ve [yeniden üretilebilir karar](large-file-indexed-verdict.json):

| Hedef | İlk koşu | İndeksli koşu | Son durum |
| --- | --- | --- | --- |
| Metadata ≤ 5 s | 0,148 ms | 0,180 ms | Geçti |
| Çoğu sorgu ≤ 150 ms | 0/15 | 9/15 (%60) | Geçti |
| Hazırlık ≥ 30 FPS | 0,24 FPS | En az 12,85 FPS | Saptı |
| Bellek doğrusal büyümemeli | 5,11 bayt / dosya baytı | 5,17 → 5,17 | Saptı |

1 GB dosyada 0,1 s sorgu 4024 ms'den 9,81 ms'ye, 1 s sorgu 4069 ms'den
76,21 ms'ye indi. Her boyutta 30 kare tamamlandı. İndeks kurma 1 GB'da
2,00 saniye sürdü; bu maliyet metadata ve pencere sorgusundan ayrı raporlandı.
`pipeline_fps` Qt paint'i içermez ve gerçek ekran FPS'inin üst sınırıdır.

Tam kapsam sorunu devam ediyor: 1 GB dosya için 223,9 saniye ve 5,169 GB
tracemalloc tepe kullanımı ölçüldü. Dar sorgu sınırlansa da bütün kayıt istendiğinde
`AcousticQuery.query` bütün örnekleri birleştiriyor; `ViewportSummary` bunları
kopyalıyor ve her 32 örnek için bir Python özet çağrısı yapıyor.

[Profiler çıktısı](indexed-query-profile.txt), indeks önceden kurulmuşken beş
soğuk 1 s sorguyu ölçer: toplam yaklaşık 0,242 saniyenin 0,219 saniyesi
`build_summary_pyramid`, 0,189 saniyesi `extrema_indices` alt çağrılarında.
Bu koşu cProfile içindir; benchmark sürelerinin yerine kullanılmaz.

Karar: F4-090 milestone'u açık kalır. Native hızlandırma gerekçesi oluşmadı;
önce özet oluşturmadaki örnek/blok başına Python çağrıları azaltılmalı (F4-094),
sonra büyük çizim aralıkları tam ham dizi kurmadan indirgenmelidir (F4-095).
Aynı benchmark F4-096'da yeniden çalıştırılacaktır. Önceki F4-064/F4-065
artefaktları tarihsel karşılaştırma olarak korunmuştur.
