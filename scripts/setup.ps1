# One-time setup of a new laptop (Windows).
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 `
#       -Name "Your Name" -Email "you@users.noreply.github.com" `
#       -Bundle "D:\landlekha-bundle.zip"
#
# -Name/-Email  your git identity for THIS repo only (see GIT_RULES: never --global)
# -Bundle       optional zip copied from a set-up laptop: OCR models (saves a slow ~300 MB
#               download) and the generated dataset with cached OCR (saves ~1 hour)
param([string]$Name, [string]$Email, [string]$Bundle)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "$cmd not found - install $hint first" }
}
Need python "Python 3.11+ (python.org, tick 'Add to PATH')"
Need node "Node.js 18+ (nodejs.org)"
Need git "Git for Windows"
Write-Host "python $(python --version)  node $(node --version)  git $(git --version)"

if ($root -match "OneDrive|Dropbox") {
    Write-Warning "This folder is synced by OneDrive/Dropbox - OCR will run much slower. Prefer C:\dev\Land-Lekha."
}

if ($Name -and $Email) {
    git config user.name $Name
    git config user.email $Email
    Write-Host "git identity for this repo: $(git config user.name) <$(git config user.email)>"
} else {
    Write-Warning "No -Name/-Email given. Current identity: $(git config user.name) <$(git config user.email)>"
}

Write-Host "`n== Python packages (torch is large, first time takes a while)"
python -m pip install -r backend\requirements.txt

if ($Bundle) {
    Write-Host "`n== Restoring bundle $Bundle"
    $tmp = Join-Path $env:TEMP "landlekha-bundle"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Expand-Archive -Path $Bundle -DestinationPath $tmp
    $models = Join-Path $HOME ".EasyOCR\model"
    New-Item -ItemType Directory -Force $models | Out-Null
    Copy-Item "$tmp\models\*" $models -Force
    New-Item -ItemType Directory -Force "data\generated" | Out-Null
    Copy-Item "$tmp\generated\*" "data\generated" -Recurse -Force
    Remove-Item -Recurse -Force $tmp
    Write-Host "OCR models -> $models ; dataset + OCR caches -> data\generated"
}

Write-Host "`n== Frontend packages"
Push-Location frontend
npm install
Pop-Location

Write-Host "`n== Checks"
python -m pytest tests -q
Write-Host "`nDone. Start the app with:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
