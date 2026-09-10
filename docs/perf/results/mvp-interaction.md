# MVP etkileşim bütçesi ölçümü

> `F3-077` çıktısı. `tools/mvp_interaction_benchmark.py` gerçek `MainWindow` üzerinde
> dört MVP etkileşiminin medyan gecikmesini ölçer ve `docs/perf/budget.md` §3
> hedefleriyle karşılaştırır. Ham sayılar `mvp-interaction.json` dosyasındadır.
>
> **Sınırlama:** ölçüm Qt `offscreen` yazılım rasterlayıcısında alınmıştır; GPU
> hızlandırmalı gerçek bir ekranı temsil etmez. Sayılar Python + Qt çağrı
> maliyetini yansıtır. Hedef ölçüm bilgisayarı hâlâ bilinmiyor (envanter E-10);
> kabul kanıtı hedef donanımda tekrarlanınca oluşur.

## Ortam

Geliştirme makinesi (bkz. `docs/perf/budget.md` §1), Python 3.9.13, PySide6,
`QT_QPA_PLATFORM=offscreen`. `MockRecordingRepository(duration_s=30)`, `ch0` çizili,
25 tekrarın medyanı.

## Sonuçlar

| Etkileşim | Ölçüm | Bütçe (`budget.md`) | Sonuç | Bütçenin oranı |
| --- | --- | --- | --- | --- |
| Cursor geri bildirimi | ~0,05 ms | ≤ 50 ms (P-05) | GEÇTİ | %0,1 |
| Play/pause tepkisi | ~0,05 ms | ≤ 100 ms (P-08) | GEÇTİ | %0,05 |
| Event'e gitme | ~1,3 ms | ≤ 200 ms (P-06) | GEÇTİ | %0,7 |
| Kanal ağacı sonucu | ~0,12 ms | ≤ 100 ms (MVP hedefi) | GEÇTİ | %0,1 |

Ölçülen değerler (`what` sütunundaki iş):

- **Cursor** — `PlotPanel.set_cursor(x)` + `cursor_readout_text()` (en yakın örneğe
  kenetlenme + değer etiketi metni).
- **Play/pause** — oynat düğmesinin `toggle()`'ı; `PlaybackMachine` geçişi +
  kaydırıcı/etiket senkronizasyonu.
- **Event'e gitme** — `PlaybackDock.goto_next_event()` (`event_navigation` +
  imleç konumu + grafiğin o zamana ortalanması).
- **Kanal ağacı** — arama kutusuna metin girip ağacın filtrelenmesi
  (`processEvents` dahil).

## Yorum

Dört etkileşim de bütçelerinin **binde biri** mertebesinde; MVP ölçeğinde
(Profil A, tek kanal) etkileşim gecikmesi kullanıcı için algılanamaz. Asıl risk
Faz 4'te büyük Profil B verisinde viewport sorgusu (P-07) ve pan/zoom (P-04)
tarafındadır; bunlar `F4-053`+ altında ayrı ölçülür.
