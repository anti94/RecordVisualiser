# Oturum süre ölçümleri — F4-062

Mevcut dönen uygulama log'undaki `sonar_analyzer.performance` satırları
`performance ` öneki ve JSON gövdesi taşır. Her satırın mevcut log başlığında aynı
uygulama sürümü ve oturum kimliği bulunur. Gövde alanları:

- `operation`: `index`, `index.fallback`, `query`, `render.plot`, `render.overlay`
  veya `render.analysis`.
- `duration_ms`: `perf_counter()` ile ölçülen geçen süre; duvar saati ayarından etkilenmez.
- `status`: başarılı işlemde `ok`, çağırana yeniden iletilen hatada `error`.
- İşleme göre kanal kimliği, kaynak bayt sayısı, zaman aralığı, örnek sayısı,
  panel adı veya `analysis`/`display` sorgu kipi.

`index`, parmak izi doğrulaması, indeks yükleme/üretme ve diske kaydı kapsar.
Cache yazılamazsa ilk hata ve bellekte yeniden indeksleme (`index.fallback`) ayrı
ölçülür. `query` repository okumasını, varsa özet üretimini ve azaltımı kapsar.
`render.plot` sorgudan sonra grafiğe veri aktarımıdır. `render.analysis` görünür
panelin FFT/STFT/istatistik hesaplarını ve çizim nesnelerine aktarımı kapsar.
Gizli analiz sekmesine render ölçümü yazılmaz.

Bunlar CPU tarafındaki çağrı süreleridir; Qt'nin sonraki paint olayı, GPU sunumu
ve gerçek ekran FPS'i ayrı benchmark ile ölçülmelidir. Sensör değerleri ve örnek
dizileri log'a gönderilmez. Ölçümler ayrıca bellekte biriktirilmez; mevcut log
döndürme sınırlarına tabidir.
