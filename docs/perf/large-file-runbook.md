# Büyük dosya üretim koşusu — F4-063

Profil B: dört kanal, 48 kHz, int16; kayıt başına kanal başına 6000 örnek
(125 ms). Header ve kanal tablosu toplam 512 bayt, her kayıt 48.120 bayttır.
Boyutlar ondalık GB'dir (1 GB = 1.000.000.000 bayt); son kayıt bölünmediği için
istenen alt sınır bir kayıttan az aşılır.

| Koşu | Seed | Beklenen kayıt | Kesin dosya baytı | Kanal başına örnek |
| --- | --- | --- | --- | --- |
| 1 GB | 20260910 | 20.782 | 1.000.030.352 | 124.692.000 |
| 10 GB | 20260910 | 207.814 | 10.000.010.192 | 1.246.884.000 |
| 20 GB stres hedefi | 20260910 | 415.628 | 20.000.019.872 | 2.493.768.000 |

Gerçek cihazın hedef kayıt boyutu henüz verilmediğinden 20 GB, 10 GB üzerindeki
ölçeklemeyi değerlendirmek için seçilmiş yerel stres hedefidir. Kesin donanım kabul
boyutu değildir; `--bytes` ile değiştirilebilir. Üç dosya birlikte yaklaşık 31 GB
disk alanı gerektirir; indeks ve ölçüm çıktıları ayrıca yer ister.

Proje kökünde PowerShell komutları:

```powershell
.venv/Scripts/python.exe tools/make_synthetic_bin.py --out .cache/perf/profile-b-1gb.bin --bytes 1000000000 --seed 20260910
.venv/Scripts/python.exe tools/make_synthetic_bin.py --out .cache/perf/profile-b-10gb.bin --bytes 10000000000 --seed 20260910
.venv/Scripts/python.exe tools/make_synthetic_bin.py --out .cache/perf/profile-b-20gb.bin --bytes 20000000000 --seed 20260910
```

Her komuta `--dry-run` eklemek dosya yazmadan kesin sayıları verir. Gerçek üretim
bir seferde tek kayıt tutar, artımlı SHA-256 hesaplar ve dosyanın yanına `.bin.json`
manifestini yazar. Manifestte seed, üretici sürümü, kayıt/örnek sayıları, kesin boyut,
süre ve içerik özeti bulunur. Kaynak tonlarının fazı seed ile belirlenir; seed 0
mevcut küçük golden fixture ile bayt düzeyinde aynıdır.

Tamamlanmadan çıktı `.bin.partial` adını taşır. Var olan final, manifest veya
partial üzerine yazılmaz. Kesilen koşuyu farklı çıktı adıyla yeniden başlatmak
mümkündür. Büyük dosyalar izlenmeyen `.cache/` altında kalır; yalnız raporlar Git'e girer.

Bu adım üretim komutlarını hazırlar. Büyük dosyaların üretilip ölçüldüğünün kanıtı
F4-064/F4-065 sonuçları ve dosya manifestleridir; dry-run üretim kanıtı sayılmaz.
