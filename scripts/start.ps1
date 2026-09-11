# Start LandLekha for a demo on Windows: API on :8000, UI on :5173.
#   powershell -ExecutionPolicy Bypass -File scripts\start.ps1          # dev UI (hot reload)
#   powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Built   # single port, built UI at :8000
#   ... -Fresh   wipes storage\ first (empty database for a clean demo)
param([switch]$Built, [switch]$Fresh)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($Fresh -and (Test-Path storage)) {
    Remove-Item -Recurse -Force storage
    Write-Host "storage\ cleared"
}

if ($Built) {
    Push-Location frontend
    if (-not (Test-Path node_modules)) { npm install }
    npm run build
    Pop-Location
    Write-Host "LandLekha at http://localhost:8000  (API docs: /docs)"
    python -m uvicorn backend.api.main:app --port 8000
    exit
}

$api = Start-Process python -ArgumentList "-m uvicorn backend.api.main:app --port 8000" -PassThru -NoNewWindow
try {
    Push-Location frontend
    if (-not (Test-Path node_modules)) { npm install }
    Write-Host "UI at http://localhost:5173   API docs at http://localhost:8000/docs"
    npm run dev
} finally {
    Pop-Location
    Stop-Process -Id $api.Id -ErrorAction SilentlyContinue
}
