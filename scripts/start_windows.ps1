# NahaVideo Windows launcher
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python 3.11+ is required. Install Python and make sure 'python' is on PATH."
}

$versionText = & python --version
Write-Host "Using $versionText"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating .venv..."
    python -m venv .venv
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
Write-Host "Installing base dependencies..."
& $venvPython -m pip install -q -r requirements.txt

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Warning "FFmpeg was not found on PATH. Upload/analyse/render operations will fail until FFmpeg is installed."
} else {
    Write-Host "FFmpeg: $((& ffmpeg -version | Select-Object -First 1))"
}

Write-Host ""
Write-Host "Starting NahaVideo at http://127.0.0.1:8000"
& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
