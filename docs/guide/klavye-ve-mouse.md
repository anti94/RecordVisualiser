# Klavye, mouse ve ölçekleme kılavuzu — `F6-028`

Bu belge uygulamanın **gerçekten bağlı olan** kısayollarını, fare
davranışını ve eksen ölçekleme kiplerini anlatır. Tablolar plan
Bölüm 16'ya değil, kaynaktaki iki kayda dayanır —
`ui/actions.py` (`MENU_SPECS`) ve `ui/shortcuts.py` (`SHORTCUTS`) — ve
`tests/unit/test_guide_shortcuts.py` ikisinin **çift yönlü** eşleştiğini
denetler: burada yazan her kısayol uygulamada bağlıdır, uygulamada bağlı
her kısayol burada yazar.

Çift yönlü olması önemlidir: yalnız "belgedekiler var mı" diye bakmak,
belgede hiç anılmayan bir kısayolun sessizce eklenmesini yakalamaz.

## 1. Menü kısayolları (pencere genelinde)

Bunlar menüden de erişilebilir ve **pencere odaktayken her yerde**
çalışır.

| Kısayol | İşlem | Menü | Not |
| --- | --- | --- | --- |
| `Ctrl+O` | Open .bin File... | File | |
| `Ctrl+W` | Close Recording | File | Kayıt açıkken etkinleşir |
| `Ctrl+E` | **Export Data...** | File | Kayıt açıkken etkinleşir |
| `Ctrl+Q` | Exit | File | |
| `Ctrl+1` | Data Explorer panelini aç/kapat | View | İşaretlenebilir |
| `Ctrl+2` | BIT / Analysis / Export sütununu aç/kapat | View | İşaretlenebilir |
| `Ctrl+Shift+S` | Load Simulation Data | Tools | |
| `Ctrl+Shift+C` | Connect Live Source | Tools | |
| `Ctrl+Shift+D` | Disconnect | Tools | Bağlıyken etkinleşir |
| `Ctrl+R` | Record | Tools | Veri varken etkinleşir |
| `Ctrl+Shift+R` | Stop Recording | Tools | Kayıt sürerken etkinleşir |
| `Ctrl+,` | Settings... | Tools | |

**Pasif bir eylemin kısayolu da pasiftir.** `Ctrl+E`'ye kayıt açmadan
basmak hiçbir şey yapmaz; sessizce boş bir dışa aktarma üretmez.

## 2. Pencere kısayolları

| Kısayol | İşlem |
| --- | --- |
| `Ctrl+S` | Workspace kaydet |
| `Ctrl+Z` | Düzenlemeyi geri al |
| `Ctrl+Shift+Z` | Düzenlemeyi yeniden uygula |

Geri alma **işlem zinciri ve işaret** düzenlemelerini kapsar. Görünüm
değişikliklerinin (renk, eksen) kendi geçmişi vardır ve Display
panelinden yönetilir; ikisini tek yığında toplamak, bir filtreyi geri
almak isterken rengin de değişmesine yol açardı.

## 3. Grafik kısayolları (yalnız odak merkez grafikteyken)

Bu kısayollar **tek harftir** ve bu yüzden yalnız grafik alanı ve
çocukları odaktayken çalışır (`WidgetWithChildrenShortcut`). Arama
kutusuna `x` yazarken zoom kipinin değişmemesi bu kapsam kısıtı
sayesindedir.

| Kısayol | İşlem |
| --- | --- |
| `Space` | Oynat / duraklat |
| `Home` | Görünümü sıfırla |
| `X` | X zoom kipi |
| `Y` | Y zoom kipi |
| `B` | XY zoom kipi (iki eksen) |
| `C` | Cursor (crosshair) aç/kapat |
| `R` | Region selection aç/kapat |
| `F4` | Sonraki olaya git |
| `Shift+F4` | Önceki olaya git |

## 4. Ölçekleme: üç zoom kipi

MATLAB alışkanlığındaki gibi **hangi eksenin ölçekleneceği seçilir**.
Kip hem fare tekerleğini hem programatik ölçeklemeyi etkiler.

| Kip | Kısayol | Tekerlek neyi ölçekler | Sürükleme neyi kaydırır |
| --- | --- | --- | --- |
| **X** | `X` | yalnız zaman ekseni | yalnız X |
| **Y** | `Y` | yalnız değer ekseni | yalnız Y |
| **XY** | `B` | iki eksen birden | iki eksen |

**"Yalnız X" gerçekten yalnız X demektir:** X kipinde Y ekseninin hem
aralığı hem etkileşimi dokunulmadan kalır. Genlik ölçeğini sabit tutup
zamanda gezinmek, iki ölçüm penceresini karşılaştırmanın tek güvenilir
yoludur; tekerleğin sessizce Y'yi de kaydırması bu karşılaştırmayı
bozardı.

İkinci Y ekseni kullanılıyorsa (farklı birimli seri), Y
yakınlaştırmasında **o eksen de aynı oranda** ölçeklenir; aksi hâlde iki
eksen birbirinden kopar ve üst üste çizilen iki seri yanıltıcı biçimde
hizalanmış görünürdü.

**Ölçekleme veriyi değiştirmez.** Zoom, pan ve bölge seçimi yalnız
görünümdür; dışa aktarılan değerler görünür aralıktan seçilir ama
*değerleri* yeniden ölçeklenmez.

### 4.1 Görünümü sıfırlamak

`Home` grafiği **ev aralığına** döndürür: veri neredeyse oraya. Kayıp
bir seriyi aramak yerine bir tuşla geri dönülür.

### 4.2 Kip nerede görünür

Kip değiştiğinde **Log / Mesajlar** panelinde (Bölge 8) `Zoom modu: X`
gibi bir satır belirir ve kip **workspace'e kaydedilir**; dosya yeniden
açıldığında son kip geri gelir.

> **Bilinen fark:** plan Bölüm 16 kipin *araç çubuğu durumunda* açıkça
> gösterilmesini istiyor. Bu sürümde kip log satırı ve workspace
> üzerinden bildirilir; araç çubuğunda kalıcı bir kip göstergesi
> **yoktur**.

## 5. Fare davranışı

### 5.1 Grafik alanında

| Hareket | Sonuç |
| --- | --- |
| Sol tuş sürükleme | Görünümü kaydırır (pan), etkin kipin eksenlerinde |
| Tekerlek | Yakınlaştırır/uzaklaştırır, etkin kipin eksenlerinde |
| Fare hareketi | Durum çubuğunda imleç zamanını gösterir (göreli ve UTC) |

Varsayılan fare kipi **pan**'dır; sürükleme bir seçim dikdörtgeni
açmaz. Bölge seçimi ayrı bir kiptir (`R`) ve tanımı gereği **iki
eksenlidir** — bölge seçerken zoom kipi fark etmez.

**Canlı akışta grafikte gezindiğiniz anda sona takip kapanır.**
İncelediğiniz yerden zorla koparılmazsınız; takibi yeniden açmak için
sona dönün.

### 5.2 Kanal ağacında (Bölge 1)

| Hareket | Sonuç |
| --- | --- |
| Çift tık | Kanalı grafiğe ekler |
| Sürükle–bırak | Kanalı grafiğe bırakır (ağaç yalnız **kaynaktır**, dışarıdan bir şey kabul etmez) |
| `Ctrl` / `Shift` + tık | Çoklu seçim; **Grafiğe Ekle** ile hepsi tek komutla eklenir |
| Sağ tık | **Plot · Inspect · Copy Path** menüsü |

## 6. Plan Bölüm 16 ile farklar

Bölüm 16 bir **başlangıç listesidir**; bu sürümde iki maddesi farklı
uygulandı. Farkları gizlemek yerine burada yazıyoruz, çünkü çalışmayan
bir kısayolu denemek, hiç olmadığını bilmekten daha kötüdür.

| Bölüm 16 | Bu sürümde | Neden |
| --- | --- | --- |
| `Ctrl+E` → Event paneline odaklan | `Ctrl+E` → **Export Data...** | `Ctrl+E` menüde dışa aktarmaya bağlandı; olay gezinme zaten `F4` / `Shift+F4` ile yapılıyor ve ayrı bir odak kısayoluna ihtiyaç kalmadı |
| `Ctrl+K` → Command palette | **yok** | Komut paleti bu sürümde uygulanmadı |

Bölüm 16'nın geri kalan **on bir kısayolu** (`Ctrl+O`, `Ctrl+S`,
`Space`, `Home`, `X`, `Y`, `B`, `C`, `R`, `F4`, `Shift+F4`) tabloda
yazdığı gibi çalışır. Ayrıca Bölüm 16'da bulunmayan **on iki kısayol**
eklendi: kapatma, dışa aktarma, çıkış, iki panel anahtarı, simülasyon,
canlı bağlantı, bağlantı kesme, kayıt başlat/durdur, ayarlar ve
geri/ileri alma.

## 7. İlgili belgeler

- Ana ekran ve bölgeler: `docs/guide/ana-ekran.md`
- Canlı bağlantı ve kayıt: `docs/guide/canli-baglanti.md`
- Filtre ve spektral analiz: `docs/guide/filtre-ve-spektral-analiz.md`
