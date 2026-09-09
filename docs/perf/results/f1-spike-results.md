# Faz 1 grafik spike'ı — ilk sonuçlar ve darboğaz

> `F1-043` çıktısıdır. `F1-041` (`tools/spike_fixtures.py`) ve `F1-042`
> (`tools/plot_benchmark.py`) tarafından üretilen ham sayıları
> `docs/perf/budget.md` hedefleriyle karşılaştırır ve sapmaları **açıkça**
> listeler. Hiçbir sayı gizlenmedi veya iyimser yuvarlanmadı.

Tarih: 2026-09-09 · Depo sürümü: `v0.59.0` sonrası · Kaynak veri:
[`spike-fixtures.json`](spike-fixtures.json), [`plot-benchmark.json`](plot-benchmark.json)

## 1. Ölçüm koşulları

| Alan | Değer |
| --- | --- |
| Makine | Geliştirme makinesi (`docs/perf/budget.md` §1) — **hedef ölçüm bilgisayarı değil** (E-10 hâlâ açık) |
| Qt platformu | `offscreen` — **fiziksel ekran yok, GPU hızlandırması yok** |
| Yazı tipi | `QT_QPA_FONTDIR` ayarlı (`tools/screenshot.py` ile aynı düzeltme) |
| Python | 3.9.13, PySide6 6.10.3, pyqtgraph 0.13.7 (kilitli sürümler) |
| Veri | Deterministik sinüs, 100 kHz, 440 Hz — `processing/signals.py` `sine()` |
| Kanal sayısı | **1** (mockup'taki 4 kanallı P-04 senaryosundan daha hafif bir yük) |
| Tekrar | Pan/zoom 30 kare, cursor 200 tekrarın ortalaması; tek koşu (henüz 5 tekrarlı medyan değil — `docs/perf/budget.md` §5 kuralı burada tam uygulanmadı, bkz. §5) |

**Bu ölçümler "karşılandı/karşılanmadı" kararı için yeterli değildir.**
`docs/perf/budget.md` §5 dürüstlük kuralı gereği: hedef makinede ve gerçek
ekranda tekrarlanmadan hiçbir P-XX hedefi "karşılandı" sayılmaz. Buradaki
amaç, iskelet üzerinde **ilk büyüklük mertebesini ve darboğazı** görmektir.

## 2. Girdi büyüklüğü (`F1-041`)

| Nokta sayısı | Bellek | Üretim süresi |
| --- | --- | --- |
| 1.000.000 | 11,44 MiB | 31 ms |
| 10.000.000 | 114,44 MiB | 291 ms |

Bellek ölçeklenmesi doğrusal (10× nokta → 10× bayt), beklenen davranış.
`int64` zaman + `float32` değer düzeni `DataChunk` sözleşmesiyle tutarlı.

## 3. Ölçülen sonuçlar (`F1-042`)

| Nokta sayısı | Sorgu süresi | Pan/zoom | Cursor gecikmesi |
| --- | --- | --- | --- |
| 1.000.000 | 11,9 ms | **7,4 FPS** | 0,011 ms |
| 10.000.000 | 100,4 ms | **0,8 FPS** | 0,008 ms |

## 4. Bütçeyle karşılaştırma ve sapmalar

| # | Hedef | 1M sonuç | 10M sonuç | Durum |
| --- | --- | --- | --- | --- |
| P-04 Pan/zoom | ≥ 30 FPS | 7,4 FPS | 0,8 FPS | **SAPMA** — 1M'de ~4×, 10M'de ~37× hedefin altında |
| P-05 Cursor gecikmesi | ≤ 50 ms | 0,011 ms | 0,008 ms | **Karşılanıyor** — ama bkz. §4.1 uyarısı |
| P-07 Viewport sorgusu | çoğunlukla ≤ 150 ms | 11,9 ms | 100,4 ms | **Karşılanıyor**, tek kanalda; 10M'de sınıra yaklaşıyor |

**Sapmalar açıkça:**

- **P-04 karşılanmıyor, iki büyüklükte de.** 1M noktada bile hedefin dörtte
  biri; 10M noktada saniyede birden az kare. Bu, `docs/perf/budget.md`'nin
  zaten öngördüğü downsample piramidi ihtiyacının (Bölüm 11.2, `F4-056`/
  `F4-057`) ilk somut kanıtıdır.
- **P-05 "karşılanıyor" görünümü yanıltıcı olabilir.** Ölçülen, yalnız
  `mapSceneToView()` koordinat dönüşümünün maliyeti — gerçek kullanıcı
  deneyimindeki "fare hareketinden değer etiketinin güncellenmesine" zinciri
  (crosshair çizimi, en yakın örnek arama, etiket metni güncelleme) henüz
  yok (`F3-026` ile gelecek). Bu satır **P-05'i doğrulamaz**, yalnız zincirin
  en ucuz parçasının ucuz olduğunu gösterir.
- **P-07 tek kanalla ölçüldü.** `docs/perf/budget.md` P-04 hedefi dört kanallı
  60 s'lik pencereyi varsayıyor; burada tek kanal ve tüm veri (60 s değil,
  10 s / 100 s) sorgulandı. Dört kanalda ve gerçek viewport kırpmasıyla sonuç
  farklı olabilir — bu ölçüm P-07'yi henüz **temsilen** doğrulamıyor.

### 4.1 Ek bulgu: PyQtGraph'ın hazır optimizasyonları yetmiyor

Raporlanan koşunun dışında, hızlı bir kontrol yapıldı (bu koşuya dahil
değildir, tekrarlanabilir ama ayrı script'e taşınmadı): `curve.setClipToView(True)`
ve `curve.setDownsampling(auto=True, method="peak")` açıldığında 1M noktada
FPS 7,8 → 9,9'a çıktı — **hedefin hâlâ üçte biri**. Sonuç: mesele yalnızca bir
bayrağı unutmak değil; asıl darboğaz **her kare tüm noktaların PyQtGraph'a
gönderilmesi**. Bu, planın zaten seçtiği yönü doğruluyor: veri kendi
downsample piramidimizde (Bölüm 11.2) viewport'a önceden indirgenmeli,
PyQtGraph'ın çalışma zamanı indirgemesine güvenilmemeli.

## 5. Darboğaz teşhisi

Ölçülen üç adımdan (sorgu, pan/zoom, cursor) yalnız **pan/zoom** bütçeyi
belirgin biçimde aşıyor. Sorgu süresi (`set_channel`) ve cursor koordinat
dönüşümü büyüklük başına doğrusala yakın ve bütçe içinde.

**Kanıtlanan darboğaz:** her `setXRange`/`setYRange` çağrısı, PyQtGraph'ın
tüm nokta dizisi üzerinde sınır/downsample yeniden hesabı yapmasına yol
açıyor — nokta sayısıyla orantılı maliyet (10× nokta → FPS ~9× düşüyor,
7,4 → 0,8). Bu **algoritmik** bir sorun (görünen aralık ne olursa olsun
tüm veri işleniyor), rastgele bir yavaşlık değil.

Plan Bölüm 11.3 sırasını izleyerek:

1. ~~Gerçekçi veri setiyle benchmark~~ — bu belge.
2. ~~Profiler ile darboğazı ölç~~ — doğrudan büyüklük taraması yeterli
   oldu, ayrı bir `cProfile`/`py-spy` koşusu gerekmedi: FPS'in nokta
   sayısıyla orantılı düşmesi darboğazı zaten gösteriyor.
3. **Sıradaki adım algoritmik:** downsample piramidi (`F4-056` min/max
   envelope, `F4-057` çok seviyeli özet). Native hızlandırma (C++/Rust/
   Numba) bu adımdan **önce** değerlendirilmemeli — plan bunu zaten
   söylüyor (§11.3 madde 4) ve bu ölçüm native'e geçmeden önce cevaplanması
   gereken soruyu değiştirmiyor.

## 6. Sonraki ölçüm için not

- Bu koşu tek tekrar; `docs/perf/budget.md` §5 kuralı 5 tekrar/medyan istiyor.
  Sonraki koşuda `tools/plot_benchmark.py`'ye tekrar döngüsü eklenmeli.
- Dört kanallı senaryo (P-04'ün tam tanımı) henüz ölçülmedi.
- Gerçek ekranda (offscreen değil) tekrarlanmadan bu sayılar nihai kabul
  kanıtı sayılmaz; yalnız Faz 1 spike'ının "büyük veri gerçekten sorun mu"
  sorusuna erken ve dürüst bir cevaptır: **evet, downsample olmadan sorun.**
