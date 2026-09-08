<#
.SYNOPSIS
    CI ile ayni kalite kontrollerini yerelde calistirir (F1-006).

.DESCRIPTION
    .github/workflows/quality.yml icindeki adimlarin aynisini sirayla kosar:
    ruff check, ruff format --check, pyright, pytest (gui haric ve gui) ve
    todo.md guncellik kontrolu. Amac, "bende gecti CI'da kaldi" farkini onlemektir.

.PARAMETER Fix
    Duzeltilebilir lint bulgularini ve bicimi otomatik uygular.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools/check.ps1
#>
[CmdletBinding()]
param(
    [switch]$Fix
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $VenvPython)) {
    throw "Sanal ortam yok. Once: powershell -ExecutionPolicy Bypass -File tools/setup-dev.ps1"
}

Push-Location $RepoRoot
try {
    if ($Fix) {
        Write-Host '==> ruff check --fix' -ForegroundColor Cyan
        & $VenvPython -m ruff check --fix .
        Write-Host '==> ruff format' -ForegroundColor Cyan
        & $VenvPython -m ruff format .
        Write-Host '==> tools/sync_todo.py' -ForegroundColor Cyan
        & $VenvPython tools/sync_todo.py
    }

    $steps = [ordered]@{
        'ruff check'   = { & $VenvPython -m ruff check . }
        'ruff format'  = { & $VenvPython -m ruff format --check . }
        'pyright'      = { & $VenvPython -m pyright }
        'pytest !gui'  = { & $VenvPython -m pytest -m "not gui" -q }
        'pytest gui'   = { & $VenvPython -m pytest -m gui -q }
        'todo.md sync' = { & $VenvPython tools/sync_todo.py --check }
    }

    $failed = @()
    foreach ($name in $steps.Keys) {
        Write-Host "==> $name" -ForegroundColor Cyan
        $output = & $steps[$name] 2>&1
        if ($LASTEXITCODE -ne 0) {
            $output | ForEach-Object { Write-Host "    $_" }
            $failed += $name
            Write-Host "    BASARISIZ  $name" -ForegroundColor Red
        }
        else {
            Write-Host "    OK  $name" -ForegroundColor Green
        }
    }

    Write-Host ''
    if ($failed.Count -gt 0) {
        Write-Host "Basarisiz adimlar: $($failed -join ', ')" -ForegroundColor Red
        exit 1
    }
    Write-Host 'Tum kalite kontrolleri gecti.' -ForegroundColor Green
}
finally {
    Pop-Location
}
