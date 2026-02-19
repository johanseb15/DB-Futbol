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

$python = Resolve-Python

Write-Host "[i] API health"
Invoke-Checked -FilePath $python -Arguments @("-c", "import json, urllib.request; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5).read().decode('utf-8')))")

Write-Host "[i] Frontend health"
Invoke-Checked -FilePath $python -Arguments @("-c", "import urllib.request; print({'frontend_http_status': urllib.request.urlopen('http://127.0.0.1:3000', timeout=5).status})")

Write-Host "[i] Docker services"
Invoke-Checked -FilePath "docker" -Arguments @("compose", "ps")

Write-Host "[i] Recent pipeline status (last 1h)"
Invoke-Checked -FilePath "docker" -Arguments @(
    "exec",
    "football_db",
    "psql",
    "-U",
    "football",
    "-d",
    "football_data",
    "-c",
    "SELECT status, COUNT(*) FROM scrape_jobs WHERE started_at >= NOW() - INTERVAL '1 hour' GROUP BY status ORDER BY status;"
)

Write-Host "[i] Data quality summary"
Invoke-Checked -FilePath $python -Arguments @("-c", "import json, urllib.request; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8001/quality/summary', timeout=10).read().decode('utf-8')))")

Write-Host "[ok] Health checks completed."
