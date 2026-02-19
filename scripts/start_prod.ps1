param(
    [switch]$SkipBootstrap
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    if (Test-Path ".\venv313\Scripts\python.exe") { return ".\venv313\Scripts\python.exe" }
    if (Test-Path ".\venv\Scripts\python.exe") { return ".\venv\Scripts\python.exe" }
    return "python"
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$ProcessArgs,
        [string]$LogPath
    )

    if (-not $ProcessArgs -or $ProcessArgs.Count -eq 0) {
        throw "Empty argument list for process '$Name'."
    }

    $errLog = "$LogPath.err"
    $proc = Start-Process -FilePath $FilePath -ArgumentList $ProcessArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $LogPath -RedirectStandardError $errLog
    Write-Host "[+] Started $Name PID=$($proc.Id)"
    return $proc.Id
}

New-Item -ItemType Directory -Force -Path ".\logs" | Out-Null
$python = Resolve-Python
Write-Host "[i] Using Python: $python"

Write-Host "[i] Starting docker services..."
Invoke-Checked -FilePath "docker" -Arguments @("compose", "up", "-d")

if (-not $SkipBootstrap) {
    Write-Host "[i] Running DB migrations..."
    Invoke-Checked -FilePath $python -Arguments @("-m", "pipeline.runner", "--init-db")

    Write-Host "[i] Seeding reference data..."
    Invoke-Checked -FilePath $python -Arguments @("scripts\seed.py")

    Write-Host "[i] Ensuring data marts..."
    Invoke-Checked -FilePath $python -Arguments @(
        "-c",
        "import pathlib, psycopg; sql=pathlib.Path('scripts/data_marts.sql').read_text(encoding='utf-8'); conn=psycopg.connect('postgresql://football:football123@localhost:5432/football_data'); conn.execute(sql); conn.commit(); conn.close(); print('data_marts_ok')"
    )
    Invoke-Checked -FilePath $python -Arguments @(
        "-c",
        "import pathlib, psycopg; sql=pathlib.Path('scripts/refresh_data_marts.sql').read_text(encoding='utf-8'); conn=psycopg.connect('postgresql://football:football123@localhost:5432/football_data'); conn.execute(sql); conn.commit(); conn.close(); print('refresh_ok')"
    )
}

$workerPid = Start-ManagedProcess -Name "celery-worker" -FilePath $python -ProcessArgs @("-m", "celery", "-A", "pipeline.celery_app:celery_app", "worker", "-l", "INFO", "--pool=solo") -LogPath ".\logs\celery_worker.log"
$beatPid = Start-ManagedProcess -Name "celery-beat" -FilePath $python -ProcessArgs @("-m", "celery", "-A", "pipeline.celery_app:celery_app", "beat", "-l", "INFO") -LogPath ".\logs\celery_beat.log"
$apiPid = Start-ManagedProcess -Name "internal-api" -FilePath $python -ProcessArgs @("-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001") -LogPath ".\logs\api.log"
$frontendPid = Start-ManagedProcess -Name "frontend" -FilePath $python -ProcessArgs @("-m", "http.server", "3000", "--directory", "frontend") -LogPath ".\logs\frontend.log"

$pidData = @{
    started_at = (Get-Date).ToString("o")
    worker_pid = $workerPid
    beat_pid = $beatPid
    api_pid = $apiPid
    frontend_pid = $frontendPid
}
$pidData | ConvertTo-Json | Set-Content ".\logs\prod_pids.json"

Write-Host "[i] Running smoke checks..."
Start-Sleep -Seconds 3
Invoke-Checked -FilePath $python -Arguments @("-c", "import json, urllib.request; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5).read().decode('utf-8')))")

Write-Host "[ok] Production stack started."
Write-Host "API: http://127.0.0.1:8001"
Write-Host "Metrics: http://127.0.0.1:8001/metrics"
Write-Host "Frontend: http://127.0.0.1:3000"
