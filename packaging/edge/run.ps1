# DriveGuard edge agent: camera + models run here, only metadata JSON goes to the backend.
# powershell -ExecutionPolicy Bypass -File run.ps1 [extra edge_agent.main args]
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\python.exe)) { Write-Error "Run install.ps1 first." }
if (-not (Test-Path edge.env)) { Write-Error "Missing edge.env (copy edge.env.example)." }
Get-Content edge.env | Where-Object { $_ -match '^\s*[^#].*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    Set-Item "env:$($k.Trim())" $v.Trim()
}
if (-not $env:DG_DEVICE_KEY -or $env:DG_DEVICE_KEY -like "dgk_paste*") { Write-Error "Put your device key in edge.env." }

$url = $env:DG_BACKEND_URL.TrimEnd("/")
$hud = "$url/#/hud"
Start-Job { Start-Sleep 6; Start-Process $using:hud } | Out-Null
Write-Host "[run] HUD: $hud  (Chrome / Edge; allow local network access if asked)"
& .venv\Scripts\python -m edge_agent.main --source 0 --backend $url --device-id $env:DG_DEVICE_ID --hud-origin $url @args
