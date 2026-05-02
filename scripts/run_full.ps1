<#
.SYNOPSIS
  Helper to run the full pipeline on Windows PowerShell.

USAGE
  From repository root:
    .\scripts\run_full.ps1 [-SkipNews] [-SkipTrain] [-NoInstall] [-Venv ".\\venv"]

DESCRIPTION
  Activates the virtualenv if present, installs requirements (unless -NoInstall),
  creates DB schema, then runs `scripts/run_pipeline.py` with optional flags.
#>

param(
    [switch]$SkipNews,
    [switch]$SkipTrain,
    [switch]$NoInstall,
    [string]$Venv = ".\venv"
)

function Write-Info($msg) { Write-Host $msg }

$python = "python"
if (Test-Path "$Venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtualenv: $Venv"
    . "$Venv\Scripts\Activate.ps1"
    $python = Join-Path $Venv "Scripts\python.exe"
} else {
    Write-Host "Virtualenv not found at $Venv. Using system python."
}

if (-not $NoInstall) {
    Write-Host "Installing requirements..."
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
}

Write-Host "Creating DB schema..."
& $python -m database.schema

$flags = @()
if ($SkipNews) { $flags += "--skip-news" }
if ($SkipTrain) { $flags += "--skip-train" }

$arguments = @('scripts\run_pipeline.py') + $flags

Write-Host "Running pipeline: $python $($arguments -join ' ')"
& $python @arguments
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pipeline exited with code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Pipeline completed successfully." -ForegroundColor Green
