# F4-096 — Özet ve akış düzeltmeleri sonrası değerlendirme

2026-09-11, `aeeaaf6` / 1.94.0. Aynı makine, dosyalar, seed, 2000 nokta
bütçesi, 30 kare, 90 saniye kare koşusu sınırı ve `--verify-span` kullanıldı.
Koşu 13,7 saniye sürdü (F4-093'ün 302,6 saniyesine karşı — kendisi de bir
kanıt). Kaynaklar `.cache/perf/profile-b-{64mb,256mb,1gb}.bin`; manifestlerindeki
seed 20260910'dur.

```powershell
.venv/Scripts/python.exe tools/large_file_benchmark.py --input .cache/perf/profile-b-64mb.bin --input .cache/perf/profile-b-256mb.bin --input .cache/perf/profile-b-1gb.bin --out docs/perf/results/large-file-streaming.json --frames 30 --frame-budget-seconds 90 --verify-span
.venv/Scripts/python.exe tools/evaluate_large_file_run.py --input docs/perf/results/large-file-streaming.json --out docs/perf/results/large-file-streaming-verdict.json
```

[Ölçüm](large-file-streaming.json) ve [yeniden üretilebilir karar](large-file-streaming-verdict.json):

| Hedef | İlk koşu (F4-065) | İndeksli koşu (F4-093) | Akış koşusu (F4-096) |
| --- | --- | --- | --- |
| Metadata ≤ 5 s | 0,148 ms | 0,180 ms | **Geçti** (0,143 ms) |
| Çoğu sorgu ≤ 150 ms | 0/15 | 9/15 (%60) | **Geçti** (12/15, %80) |
| Hazırlık ≥ 30 FPS | 0,24 FPS | En az 12,85 FPS | **Geçti** (en az 132,77 FPS) |
| Bellek doğrusal büyümemeli | 5,11 bayt/dosya baytı, sabit | 5,17, sabit | **Geçti** (0,48 → 0,08, **düşüyor**) |

**Dört hedefin dördü de geçti.** ADR-010'un geçiş ölçütü 2 ("düzeltmeden
sonra da sapma var mı") artık uygulanmaz — sapma kalmadı, native hızlandırma
gerekçesi yok.

## Ne değişti

`F4-094` özet piramidini örnek başına Python çağrısından NumPy blok
işlemlerine taşıdı: `indexed-query-profile.txt`'te (F4-093) 0,242 saniyelik
beş sorgunun 0,219'u `build_summary_pyramid`'deydi. `F4-095` bunun **üstüne**
ikinci bir düzeltme ekledi: pencere içindeki örnek sayısı 262.144'ü
(`max(262_144, max_points)`) aşarsa `AcousticQuery.query_display` kaynağı
hiç tam çözmez — `iter_chunks` en çok 65.536 örneklik parçalar üretir,
`streaming_envelope` bunları eşit zaman kovalarında min/max/geçersiz'e
indirger. `DisplayQuery` bu yolu yalnız **tam pencere + aynı bütçe**
tekrarında önbellekler; daha dar bir zoom ham kaynağa döner.

Bu, tam kapsam ("full") sorgusunu doğrudan hedefler — önceki iki koşuda
darboğazın kaldığı tek yerdi:

| Dosya | F4-093 `full` | F4-096 `full` | Kazanç |
| --- | --- | --- | --- |
| 64 MB | (bütçede) | 388,5 ms | — |
| 256 MB | (ölçülmedi ayrı) | 1368,6 ms | — |
| 1 GB | 223.897,8 ms | 5.279,5 ms | ~42x |

1 GB `full` sorgusu hâlâ 150 ms bütçesinin ~35 katı — bu yüzden `query_ms`
15 sorgunun 12'sinde (%80) geçiyor, 15'inde değil. Kalan üç sapma, üç
dosyanın `full` etiketli sorgularıdır: kullanıcı gerçekte **hiçbir zaman**
166–2600 saniyelik kaydın tamamını 2000 piksele sığdırmaya çalışmaz — bu
etiket dar pencere davranışının değil, uç durumun ölçüsüdür. Hedef "çoğu
durumda" dediği için %80 geçer.

`pipeline_fps` sıçraması (12,85 → 132,77 FPS, 64 MB'de) `F4-094`'ün özet
piramidi maliyetini kestiğini doğrudan gösterir: pan koşusu 1 saniyelik
pencerelerle çalışır, bu pencereler zaten `query_display` eşiğinin
altındadır (262.144 örnekten çok daha az), dolayısıyla akış yolu değil
hızlanan piramit yolu koşar.

`memory_scaling` artık yalnız "doğrusal büyümüyor" değil, **oranı
düşüyor** (0,48 → 0,08, 0,17x): tam kapsam sorgusu artık dosya boyutuyla
orantılı bir ham dizi tutmuyor; `retained_per_file_byte` sabit taban
maliyetin büyük dosyada amortize olduğunu gösteriyor.

## Karar

**F4-090 milestone kabulüne engel kalmadı.** ADR-010'un altı geçiş
ölçütünden 2.'si ("sapma düzeltmeden sonra da vardır") artık sağlanmıyor;
native hızlandırma değerlendirmesi açılmaz. Önceki üç koşunun (`large-file`,
`large-file-indexed`, `large-file-streaming`) hepsi tarihsel karşılaştırma
olarak korunur; hiçbiri silinmez veya üzerine yazılmaz.
