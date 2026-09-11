# Merge ve yayın kalite kapıları — `F6-018`

**Kabul:** Remote varsa gerekli kontroller uygulanır; yoksa yerel eşdeğer komutlar
kayıtlıdır.

Plan Bölüm 21: *"Ana branch korumalı olmalı; başarısız kalite kapılarıyla release
üretilmemelidir."* Bu belge o cümlenin karşılığını yazar: hangi kontroller zorunlu,
remote'ta nasıl uygulanır ve remote yokken (ya da koruma açılana kadar) yerel
eşdeğeri nedir.

## 1. Merge için zorunlu kontroller

`.github/workflows/quality.yml` her push ve pull request'te koşar. Merge için
zorunlu olması gereken **status check** adları:

| Kontrol | İş / adım | Ne yakalar |
| --- | --- | --- |
| `Windows / Python 3.9` | `quality` matrisi | Lint, biçim, tip, test — hedef Python |
| `Windows / Python 3.12` | `quality` matrisi | Aynısı, plan Bölüm 2'nin hedef sürümünde |
| `Windows paketi uretilip aciliyor mu` | `package-smoke` | Paket üretiliyor ve **açılıyor** mu (`F6-016`) |
| `todo.md plan.md ile guncel mi` | `todo-sync` | Plan ile not defteri ayrışmış mı |

`quality` işi içinde ayrıca şunlar koşar ve kırıldığında iş başarısız olur:
lint (`ruff check`), biçim (`ruff format --check`), tip (`pyright`, strict),
testler, **coverage eşikleri** (`F6-013`), **performans smoke** (`F6-015`) ve
**bağımlılık taraması** (`F6-014`).

## 2. Yayın için zorunlu kontroller

`.github/workflows/release.yml` yalnız `v*` etiketiyle tetiklenir. İlk adımı
sürüm kapısıdır (`F6-017`): **etiket ile `VERSION` aynı değilse hiçbir artefakt
üretilmez.** Kapı üretimden sonra manifestle birlikte bir kez daha koşar.

## 3. Remote'ta dal koruması nasıl açılır

Dal koruması deponun **yönetici ayarıdır**; kod içinden uygulanamaz ve deponun
sahibinin kararıdır. Bu yüzden burada yalnız adımlar yazılıdır:

1. GitHub → depo → **Settings → Branches → Add branch protection rule**
2. Branch name pattern: `main`
3. Şunlar işaretlenir:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging** → yukarıdaki dört kontrol
   - **Require branches to be up to date before merging**
   - **Do not allow bypassing the above settings**

`gh` CLI varsa aynısı şu komutla yapılabilir:

```bash
gh api -X PUT repos/:owner/:repo/branches/main/protection \
  --input docs/ci/branch-protection.json
```

> **Bu depoda uygulanmadı.** Remote mevcut (`origin`), ancak `gh` CLI kurulu
> değil ve dal koruması deponun sahibinin vereceği bir karardır. Kapıların
> kendisi çalışır durumdadır; yalnız "merge'i engelle" zorlaması açılmamıştır.

## 4. Yerel eşdeğer — `tools/local_gate.py`

Dal koruması açılana kadar (ya da hiç açılmazsa) aynı kontroller tek komutla
koşturulur:

```powershell
.venv\Scripts\python.exe tools\local_gate.py
```

Tek tek de koşturulabilir:

```powershell
.venv\Scripts\python.exe tools\local_gate.py --only lint tip test
```

Kapı adları CI iş akışıyla **aynıdır**; üç yerde farklı isim kullanmak, hangisinin
kırıldığını aramaya dönüşürdü.

| Kapı | Yerel komut |
| --- | --- |
| `lint` | `python -m ruff check .` |
| `bicim` | `python -m ruff format --check .` |
| `tip` | `python -m pyright` |
| `test` | `python -m pytest -q` |
| `coverage` | `python -m pytest -q --cov --cov-report=json` + `python tools/coverage_gate.py` |
| `perf-smoke` | `python tools/perf_smoke.py` |
| `bagimlilik-taramasi` | `python tools/dependency_scan.py` |
| `todo-sync` | `python tools/sync_todo.py --check` |

Araç **hepsini koşar**, ilk kırıkta durmaz: "daha ne kırık" sorusu tek tek
koşturarak öğrenilmemelidir.

## 5. Yayın öncesi yerel kontrol

```powershell
.venv\Scripts\python.exe tools\release_guard.py --tag v3.18.0
.venv\Scripts\python.exe tools\build_package.py
.venv\Scripts\python.exe tools\build_installer.py
.venv\Scripts\python.exe tools\release_manifest.py
.venv\Scripts\python.exe tools\signing_check.py
```
