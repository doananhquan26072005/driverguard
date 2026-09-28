# DriveGuard edge agent: one-time setup on Windows.
# powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = $null
foreach ($v in "3.12", "3.11") {
    & py "-$v" -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break }
}
if (-not $py) { Write-Error "Need Python 3.11 or 3.12 (https://www.python.org/downloads/)." }

& $py[0] $py[1] -m venv .venv
& .venv\Scripts\python -m pip install --upgrade pip | Out-Null
& .venv\Scripts\python -m pip install -r requirements.txt
if (-not (Test-Path edge.env)) { Copy-Item edge.env.example edge.env }
Write-Host "[install] done. Put your device key in edge.env, then run: powershell -ExecutionPolicy Bypass -File run.ps1"
