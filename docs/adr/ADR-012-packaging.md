# ADR-012 — Paketleme aracı ve dağıtım biçimi

- Durum: Kabul edildi
- İlgili işler: F6-001 (bu ADR), F6-002–F6-005 (uygulama)
- Tarih: 2026-09-11

## Bağlam

Plan Bölüm 20 Windows dağıtımı için **PyInstaller veya Nuitka** değerlendirmesi
ister; Bölüm 2018 satırındaki teknoloji tablosu kararı açıkça "spike sonrası
seç" diye erteler. `F6-001`'in kabul kontrolü de seçimin *spike kanıtına ve
hedef Windows ortamına* dayanmasını şart koşar.

Bu ADR, iki aracın da **gerçekten çalıştırıldığı** bir spike sonrası yazıldı.
Ölçümler `docs/packaging/results/packaging-spike.json` dosyasındadır.

### Spike koşulları

| | |
| --- | --- |
| Makine | Windows 10 (10.0.26200), AMD64 |
| Python | 3.9.13 (CPython, resmi dağıtım) |
| Uygulama | `sonar_analyzer` + PySide6 6.10.3 + pyqtgraph + NumPy |
| PyInstaller | 6.22.2, `--standalone` eşdeğeri (onedir), `--windowed` |
| Nuitka | 4.2.1, `--standalone --enable-plugin=pyside6 --python-flag=-m` |

### Ölçülenler

| Ölçüt | PyInstaller | Nuitka |
| --- | --- | --- |
| Derleme süresi | **~58 s** | dakikalar (459 C dosyası derlendi) |
| Dağıtım boyutu (onedir) | 164,1 MB | **142,0 MB** |
| Açılış (`--version`, 5 koşu medyanı) | 375 ms | **213 ms** |
| Üretilen ikili çalışıyor mu | evet | evet |
| Ek araç zinciri gereksinimi | **yok** | C derleyici (Nuitka MinGW indirdi) |

İki bulgu ayrıca kaydedilmelidir:

1. **Nuitka'nın ilk denemesi çalışmayan bir ikili üretti.** `__main__.py`
   doğrudan derlendiğinde ortaya çıkan ikili `ModuleNotFoundError: No module
   named 'io'` ile açılmadı. Nuitka bunu bir uyarıyla söylemişti ("paketin
   kendisini ver, `__main__.py`'yi değil"); doğru çağrıyla
   (`--python-flag=-m` + paket dizini) sorun geçti. Yani hata araçta değil
   çağrıdaydı, ama **Nuitka yanlış çağrıda sessizce bozuk artefakt üretiyor**:
   derleme başarıyla bitiyor, sorun ancak çalıştırınca görülüyor.
2. **İki araç da yanlış sürüm numarası bildirdi.** Gerçek sürüm `3.0.0` iken
   PyInstaller ikilisi `0.0.0`, Nuitka ikilisi `0.21.0` dedi. Kök neden
   ortak: `sonar_analyzer.__init__._read_version()` önce depo kökündeki
   `VERSION` dosyasını, sonra kurulu paket metadata'sını okur; paketlenmiş
   uygulamada **ikisi de yok** (ya da eski). Bu, paketleme aracının değil
   uygulamanın kusurudur ve `F6-002`'nin işidir.

## Karar

**PyInstaller kullanılacak; dağıtım biçimi `onedir` olacak.**

Nuitka ölçülen iki başlıkta (boyut %13 küçük, açılış %43 hızlı) daha iyidir ve
bu göz ardı edilmiyor. Seçim yine de PyInstaller'dan yanadır, çünkü bu projenin
kısıtları farklı bir şeyi ödüllendiriyor:

- **Ek araç zinciri yok.** Nuitka bir C derleyici ister; bu makinede MSVC ve
  gcc olmasına rağmen Nuitka kendi MinGW'sini indirdi ve "Windows SDK Visual
  Studio'da kurulu değil" uyarısı verdi. CI'da ve başka bir geliştirici
  makinesinde bu, sürümden sürüme değişebilen bir değişken demektir.
  PyInstaller saf Python'dur ve `pip install` dışında hiçbir şey istemez.
- **Derleme süresi geri bildirim döngüsüne giriyor.** 58 saniye ile dakikalar
  arasındaki fark, `F6-004`'ün "tek komutluk paket üretimi" ve `F6-005`'in
  temiz ortam kontrolü her değişiklikte koşacağı için doğrudan iş hızıdır.
- **Sessiz bozuk artefakt riski.** Nuitka yanlış çağrıda derlemeyi başarıyla
  bitirip çalışmayan bir ikili üretti. Bir dağıtım hattında en istenmeyen
  başarısızlık türü budur: kırmızı yanmayan, ancak kullanıcıda patlayan.
- **Ölçülen fark kullanıcı için belirleyici değil.** 375 ms ile 213 ms
  arasındaki 162 ms, masaüstü bir analiz uygulamasının açılışında
  algılanabilir bir fark yaratmaz; 22 MB'lık boyut farkı da tek seferlik
  kurulumda önemsizdir. Plan Bölüm 11.1'de açılış süresi için bir bütçe
  **yoktur**; hedefler veri gösterimiyle ilgilidir.

`onedir` (tek klasör) `onefile` yerine seçildi: `onefile` her açılışta kendini
geçici bir dizine açar, bu da açılışı yavaşlatır ve antivirüs yazılımlarında
daha çok soruna yol açar. `onedir`, kurulum sırasında bir kez yazılır.

## Sonuçlar

- `F6-002` PyInstaller spec'ini ekleyecek ve **sürüm kusurunu düzeltecek**:
  paketlenmiş uygulama `VERSION` değerini doğru bildirmeli.
- `F6-003` Qt platform plugin'i, tema ve ikon kaynaklarının pakete girdiğini
  doğrulayacak. Spike'ta PySide6 plugin'leri otomatik toplandı ama bu
  **doğrulanmadı**; sadece `--version` koşturuldu, pencere açılmadı.
- `F6-005` temiz ortam kontrolünü yapacak.
- Nuitka **reddedilmedi, ertelendi**: açılış süresi ya da boyut ileride bir
  kısıt hâline gelirse bu ADR yeniden açılır. O zaman şart, CI'da sabit ve
  tekrar üretilebilir bir C araç zinciridir.

## Hedef ortam hakkında bilinmeyen

Kabul kontrolü seçimin "hedef Windows ortamına" dayanmasını ister. Hedef
ölçüm bilgisayarı **hâlâ bilinmiyor** (E-10, `ms/04-mvp` §5'ten beri açık) —
sürüm, mimari, RAM ve antivirüs politikası verilmedi. Bu bilinmezlik kararı
PyInstaller'a doğru **güçlendiriyor**: ek araç zinciri gerektirmeyen, saf
Python bir araç, bilinmeyen bir ortamda daha az varsayım yapar. Hedef ortam
öğrenildiğinde doğrulanacaklar:

- [ ] Windows sürümü ve mimarisi (spike yalnız Windows 10 / AMD64'te koştu).
- [ ] Antivirüs / SmartScreen davranışı (imzasız ikili engellenir mi — `F6-012`).
- [ ] Visual C++ Redistributable'ın hedefte bulunup bulunmadığı.
- [ ] Offline kurulum gerekip gerekmediği (`F6-011`).
