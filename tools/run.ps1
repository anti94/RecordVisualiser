<#
.SYNOPSIS
    SONAR Data Analyzer uygulamasini projenin sanal ortamiyla baslatir.

.DESCRIPTION
    Calisma klasorunden bagimsiz olarak .venv icindeki Python'u kullanir.
    Kurulum yapmaz; uygulamanin cikis kodunu cagirana aktarir.

.PARAMETER Version
    Pencere acmadan uygulama surumunu yazdirir.

.PARAMETER NoWindow
    Ana pencereyi gostermeden olusturup kapatarak baslatmayi dogrular.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/run.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/run.ps1 -NoWindow
#>
[CmdletBinding()]
param(
    [switch]$Version,
    [switch]$NoWindow
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    $SetupScript = Join-Path $PSScriptRoot 'setup-dev.ps1'
    throw "Sanal ortam bulunamadi. Once: powershell -NoProfile -ExecutionPolicy Bypass -File `"$SetupScript`" -WithGui -Locked"
}

$AppArguments = @()
if ($Version) { $AppArguments += '--version' }
if ($NoWindow) { $AppArguments += '--no-window' }

Push-Location -LiteralPath $RepoRoot
try {
    & $VenvPython -m sonar_analyzer @AppArguments
    $AppExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $AppExitCode
