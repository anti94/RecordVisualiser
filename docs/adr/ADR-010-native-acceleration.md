# ADR-010 — Native hızlandırmaya geçiş ölçütleri

- Durum: Kabul edildi
- İlgili işler: F4-064, F4-065, F4-067
- Tarih: 2026-09-11

## Bağlam

Plan Bölüm 11.3 native hızlandırmayı bir sıraya bağlar: önce gerçekçi veri
setiyle benchmark, sonra profiler ile ölçülmüş darboğaz, sonra algoritma ve
veri kopyalama düzeltmeleri, **ancak ondan sonra** kanıtlanmış sıcak noktalar
için C++/Cython/Numba/Rust değerlendirmesi. Bu ADR o sıranın ilk üç adımı
tamamlandıktan sonra yazılmıştır.

`F4-064` ölçtü, `F4-065` karara bağladı (`docs/perf/results/large-file.json`,
`large-file-verdict.json`). 64 MB / 256 MB / 1 GB Profil B dosyalarında dört
§11.1 hedefinden biri geçti, üçü saptı:

| Hedef | §11.1 | Ölçülen | Durum |
| --- | --- | --- | --- |
| `metadata_seconds` | ≤ 5 s | 0,148 ms | geçti |
| `query_ms` | çoğu durumda ≤ 150 ms | 0/15 sorgu bütçede | saptı |
| `pipeline_fps` | ≥ 30 FPS | 0,24 FPS (1 GB) | saptı |
| `memory_scaling` | doğrusal büyümemeli | bayt başına tepe 5,11 → 5,11 | saptı |

`cProfile` sapmanın kaynağını gösterdi: 64 MB dosyada 0,1 s'lik tek bir
pencere sorgusunun %70'i `channel_sample_times_ns`, %25'i `channel_samples`.
`query_acoustic_channel` kanalın **tamamının** zaman ve örnek dizisini
üretip sonra `searchsorted` ile diliyor; ikisi de dosyayı baştan sona
dolaşıyor. 166 s'lik kayıtta 0,1 s görmek için 7,98 milyon örnek çözülüyor.
Sorgu süresinin pencere genişliğinden bağımsız (0,01 s → 236 ms,
0,1 s → 240 ms), dosya boyutundan ise doğrusal (240 → 968 → 4024 ms) olması
bu tanıyı doğruluyor.

## Karar

**Native hızlandırmaya geçilmez.** Ölçülen darboğaz native hız eksikliği
değil, sorgunun sınırsız olmasıdır; saf Python/NumPy sorgu sınırlandığında
§11.1 bütçesini üç büyüklük mertebesi payla karşılamaktadır.

Kanıt `tools/bounded_query_probe.py`: kayıt ızgarası aritmetikle adreslenip
yalnız pencereye düşen bloklar okunduğunda, **aynı 1 GB dosyada**, aynı
makinede:

| Pencere | Bugünkü sorgu | Blok sınırlı sorgu | Kazanç |
| --- | --- | --- | --- |
| 0,01 s | 4001 ms | 0,09 ms | ~44.000x |
| 0,1 s | 4024 ms | 0,17 ms | ~23.700x |
| 1 s | 4069 ms | 0,52 ms | ~7.800x |
| 10 s | 4663 ms | 4,99 ms | ~930x |

0,1 s'lik sorgu 150 ms bütçesinin ~880 katı içinde kalır. Sonda referans
decoder'la **bit düzeyinde aynı** sonucu verir ve dosya 10x büyürken
dokunduğu kayıt sayısı değişmez; ikisi de `tests/unit/test_bounded_query_probe.py`
ile denetlenir. Sonda üretim kodu değildir — kalite bayrağı, CRC ve düzensiz
kayıt sırası sorumluluklarını üstlenmez; yalnız bu ADR'nin dayandığı sayıyı
yeniden üretilebilir kılar. Gerçek düzeltme Profil B okuma yoluna Profil
A'daki gibi bir kayıt indeksi eklemektir ve **ayrı bir iş** olarak planlanır.

Doğrusal bellek de aynı yerden gelir ve aynı düzeltmeyle kapanır: sınırlı
okuma pencere kadar bellek ayırır, dosya kadar değil.

## Geçiş ölçütleri

Native modül ancak aşağıdakilerin **hepsi** sağlandığında değerlendirilir.
Herhangi biri eksikse karar yeniden "geçilmez"dir.

1. **Algoritmik düzeltme yapılmış ve ölçülmüştür.** Profil B okuma yolu
   kayıt indeksiyle sınırlandırılmış, `F4-064` koşusu yeniden koşulmuştur.
2. **Sapma düzeltmeden sonra da vardır.** `F4-065` kararı ilgili hedef için
   hâlâ `sapti` üretir ve sapma **en az 2x**'tir (ölçülen değer bütçenin iki
   katından kötüdür). Bütçeye yakın bir sapma native gerekçesi değildir.
3. **Tek bir sıcak nokta kanıtlanmıştır.** Profiler çıktısında tek bir işlev
   kare süresinin **≥ %40**'ını tutar ve bu işlev NumPy ile
   vektörleştirilemez (döngü örnek başına dallanma, durum makinesi veya
   örnek başına bit işlemi içerir).
4. **Sıcak nokta kararlıdır.** Aynı sıcak nokta **en az iki makinede** ve
   **en az iki dosya boyutunda** aynı payla görünür; makine bilgisi
   `F4-064` raporundaki `machine` alanıyla kayda geçer.
5. **Ucuz seçenekler tükenmiştir.** §11.2'deki yöntemler (mmap, görünür
   aralık sorgusu, `max_points`, min/max envelope, çok seviyeli özet, LRU
   cache, worker thread, throttle/debounce, ring buffer, gizli panelde
   render kısma) ilgili yolda uygulanmış ve ölçülmüştür.
6. **Python referansı korunacaktır.** §11.3 gereği native modülün yanında
   saf Python uygulaması doğrulama amacıyla kalır; ikisi aynı golden
   fixture'lara karşı aynı sonucu vermek zorundadır ve bu bir testle
   sabitlenir.

## Zorunlu native kapsamı ayrı bölünür

Ölçütler sağlanırsa native iş **kendi bölümü olarak** planlanır; sürmekte
olan özellik işlerine karıştırılmaz. Bunun nedeni yönetimseldir: native bir
bağımlılık derleyici zinciri, çapraz platform paketleme (ADR-012), hata
ayıklama ve dağıtım maliyeti getirir — bu maliyet bir özellik işinin içine
gizlenirse geri alınması zorlaşır.

Kapsam kuralları:

- **Aday listesi kapalıdır.** Yalnız ölçütleri geçen işlev native olur.
  Bugünkü ölçümlere göre olası adaylar, hiçbiri şu an ölçütleri geçmeden:
  (a) çok GB'lık dosyada kayıt indeksi kurma, (b) 10⁸ üstü örnekte
  `int16 → float64` dönüşümü ve min/max envelope, (c) CRC doğrulama.
- **Her aday kendi işini alır.** Ölçüm, native uygulama, Python referansı,
  eşdeğerlik testi ve geri düşüş yolu ayrı ayrı planlanır.
- **Geri düşüş zorunludur.** Native modül yüklenemezse uygulama Python
  yoluyla çalışmaya devam eder; bu bir kabul kriteridir, iyileştirme değil.
- **Araç seçimi bu ADR'nin konusu değildir.** C++/pybind11, Cython, Numba ve
  Rust arasındaki seçim, ölçütler sağlandığında ilgili adayın ölçülen
  profiline göre ayrı bir ADR'de yapılır.

## Değerlendirilen alternatifler

- **Şimdi native'e geçmek.** Reddedildi: ölçülen darboğaz native'in
  çözebileceği bir darboğaz değil. 4024 ms'lik sorgunun tamamı gereksiz iştir;
  o işi C++'ta yapmak da yavaştır. Sınırlı okuma aynı işi 0,17 ms'ye indirir.
- **Numba ile mevcut döngüleri JIT etmek.** Reddedildi: `channel_samples` ve
  `channel_sample_times_ns` zaten NumPy vektör işlemleri; sıcak nokta döngü
  hızı değil, işlenen veri miktarı. Ayrıca Numba bir çalışma zamanı
  bağımlılığı ve ilk çağrıda derleme gecikmesi ekler.
- **Hiçbir şey yapmamak, hedefleri gevşetmek.** Reddedildi: §11.1 hedefleri
  kullanıcı deneyimi sözleridir ve ölçüm bunların **karşılanabilir** olduğunu
  gösteriyor. Karşılanabilir bir hedefi gevşetmek için gerekçe yok.
- **Kararı ertelemek.** Reddedildi: F4-065 sonucu elde, tetikleyici iş
  (F4-067) burada. Kararı uygulayan ilk işten sonra yazılan ADR gerekçe değil
  savunma olur (`docs/adr/README.md` kuralı).

## Sonuçlar

Olumlu:

- Derleyici zinciri, çapraz platform derleme ve native hata ayıklama maliyeti
  şimdilik alınmaz; dağıtım saf Python kalır.
- Düzeltme yönü ölçüyle belirlendi: kayıt indeksi + blok düzeyinde seek. Aynı
  düzeltme üç sapan hedefi birden kapatır.
- "Ne zaman native'e geçilir" sorusu artık ölçülebilir bir eşiktir; tartışma
  değil, `F4-064`/`F4-065` çıktısıdır.

Olumsuz:

- Üç §11.1 hedefi bu ADR yazıldığı anda hâlâ sapmaktadır; ADR düzeltmeyi
  yapmaz, yönünü belirler.
- Blok sınırlı okumanın üretim sürümü (kalite bayrağı, CRC, düzensiz kayıt
  sırası, kesik son kayıt) sondadan daha karmaşıktır; sondanın ölçtüğü süre
  bir **alt sınırdır**, üretimde bir miktar üstüne çıkacaktır. Bütçeye göre
  payın büyüklüğü (~880x) bu farkın kararı değiştirmeyeceğini gösterir.
- Sonda üretim kodu olmadığı hâlde depoda durur; ADR ve testleri bunu açıkça
  söyler, yoksa yanlışlıkla üretim yolu sanılabilir.

## Doğrulama

- Ölçüm: `docs/perf/results/large-file.json` (`F4-064`), karar
  `large-file-verdict.json` (`F4-065`). Karar makine tarafından üretilir ve
  `tests/unit/test_large_file_verdict.py` ölçümden yeniden üretilebilirliğini
  denetler.
- Bu ADR'nin dayandığı karşı ölçüm: `tools/bounded_query_probe.py`,
  doğruluğu ve sınırlılığı `tests/unit/test_bounded_query_probe.py`.
- Karar yeniden değerlendirilir: Profil B okuma yolu sınırlandırıldıktan
  sonra `F4-064` koşusu tekrarlanır; `F4-065` kararı hâlâ `sapti` üretiyorsa
  yukarıdaki altı ölçüt tek tek kontrol edilir.
