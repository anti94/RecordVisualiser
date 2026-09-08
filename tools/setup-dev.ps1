<#
.SYNOPSIS
    Tek komutluk gelistirici kurulumu (F1-002).

.DESCRIPTION
    Sanal ortami olusturur, paketi gelistirme ekstralariyla kurar ve kurulumu dogrular.
    Betik yeniden calistirilabilir (idempotent): mevcut .venv varsa yeniden kullanilir.

.PARAMETER Recreate
    Mevcut .venv silinip sifirdan olusturulur.

.PARAMETER WithGui
    PySide6 ve PyQtGraph ekstrasini da kurar.

.PARAMETER Locked
    Bagimliliklari requirements-dev.lock icindeki sabit surumlerden kurar.
    Yeniden uretilebilir ortam gerektiginde (CI, hata ayiklama) kullanilir.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools/setup-dev.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools/setup-dev.ps1 -Recreate -WithGui
#>
[CmdletBinding()]
param(
    [switch]$Recreate,
    [switch]$WithGui,
    [switch]$Locked
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $RepoRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$TargetPython = '3.12'   # plan Bolum 2 hedefi; acik karar D-20

function Write-Step { param([string]$Text) Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Warn { param([string]$Text) Write-Host "!!  $Text" -ForegroundColor Yellow }

Push-Location $RepoRoot
try {
    # 1. Python bulun ve surumu bildir
    Write-Step 'Python araniyor'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { throw 'python bulunamadi. Python 3.12 kurup PATH ekleyin.' }

    # Not: PowerShell, native komutlara gecen argumanlardaki cift tirnaklari soyar.
    # Bu yuzden -c ile verilen Python ifadesinde tirnak KULLANILMAZ.
    $pyVersion = (& python -c 'import sys; print(sys.version.split()[0])').Trim()
    Write-Host "    python $pyVersion  ($($py.Source))"

    $major, $minor = $pyVersion.Split('.')[0, 1]
    if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 9)) {
        throw "Python 3.9 veya ustu gerekli, bulunan: $pyVersion"
    }
    if ("$major.$minor" -ne $TargetPython) {
        Write-Warn "Hedef surum $TargetPython, bulunan $pyVersion. Kurulum devam ediyor; bkz. acik karar D-20."
    }

    # 2. Sanal ortam
    if ($Recreate -and (Test-Path $VenvDir)) {
        Write-Step 'Mevcut .venv siliniyor'
        Remove-Item -Recurse -Force $VenvDir
    }
    if (Test-Path $VenvPython) {
        Write-Step '.venv mevcut, yeniden kullaniliyor'
    }
    else {
        Write-Step '.venv olusturuluyor'
        & python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw 'venv olusturulamadi' }
    }

    # 3. Kurulum
    Write-Step 'pip guncelleniyor'
    & $VenvPython -m pip install --quiet --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip guncellenemedi' }

    $extras = if ($WithGui) { '.[dev,gui]' } else { '.[dev]' }
    if ($Locked) {
        $lockFile = Join-Path $RepoRoot 'requirements-dev.lock'
        if (-not (Test-Path $lockFile)) { throw "Kilit dosyasi yok: $lockFile" }
        Write-Step 'Bagimliliklar kilitten kuruluyor'
        & $VenvPython -m pip install --quiet -r $lockFile
        if ($LASTEXITCODE -ne 0) { throw 'kilitli bagimliliklar kurulamadi' }
        Write-Step 'Paket kuruluyor (bagimliliklar kilitten geldi)'
        & $VenvPython -m pip install --quiet --no-deps -e .
        if ($LASTEXITCODE -ne 0) { throw 'paket kurulamadi' }
    }
    else {
        Write-Step "Paket kuruluyor: pip install -e `"$extras`""
        & $VenvPython -m pip install --quiet -e $extras
        if ($LASTEXITCODE -ne 0) { throw 'paket kurulamadi' }
    }

    # 4. Dogrulama
    Write-Step 'Kurulum dogrulaniyor'
    $checks = @(
        @{ Name = 'paket import'; Cmd = { & $VenvPython -c 'import sonar_analyzer; print(sonar_analyzer.__version__)' } },
        @{ Name = 'ruff lint';    Cmd = { & $VenvPython -m ruff check . } },
        @{ Name = 'ruff format';  Cmd = { & $VenvPython -m ruff format --check . } },
        @{ Name = 'pyright';      Cmd = { & $VenvPython -m pyright } },
        @{ Name = 'pytest';       Cmd = { & $VenvPython -m pytest } }
    )
    foreach ($check in $checks) {
        $output = & $check.Cmd 2>&1
        if ($LASTEXITCODE -ne 0) {
            $output | ForEach-Object { Write-Host "    $_" }
            throw "Dogrulama basarisiz: $($check.Name)"
        }
        Write-Host "    OK  $($check.Name)"
    }

    $version = (& $VenvPython -c 'import sonar_analyzer; print(sonar_analyzer.__version__)').Trim()

    Write-Host ''
    Write-Host "Kurulum tamam. sonar-analyzer $version" -ForegroundColor Green
    Write-Host ''
    Write-Host 'Siradaki komutlar:'
    Write-Host '    .venv\Scripts\python.exe -m pytest        # testler'
    Write-Host '    .venv\Scripts\python.exe -m ruff check .  # lint'
    Write-Host '    .venv\Scripts\Activate.ps1                # ortami etkinlestir'
    if (-not $WithGui) {
        Write-Host ''
        Write-Host 'Arayuz katmani icin: tools\setup-dev.ps1 -WithGui'
    }
}
finally {
    Pop-Location
}
