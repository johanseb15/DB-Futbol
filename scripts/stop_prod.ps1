$ErrorActionPreference = "Continue"

$pidFile = ".\logs\prod_pids.json"
if (-not (Test-Path $pidFile)) {
    Write-Host "[i] PID file not found: $pidFile"
    exit 0
}

$pids = Get-Content $pidFile | ConvertFrom-Json
$targets = @(
    @{ Name = "api"; Pid = $pids.api_pid },
    @{ Name = "beat"; Pid = $pids.beat_pid },
    @{ Name = "worker"; Pid = $pids.worker_pid },
    @{ Name = "frontend"; Pid = $pids.frontend_pid }
)

foreach ($t in $targets) {
    if ($null -ne $t.Pid -and $t.Pid -gt 0) {
        try {
            Stop-Process -Id $t.Pid -Force
            Write-Host "[+] Stopped $($t.Name) PID=$($t.Pid)"
        }
        catch {
            Write-Host "[-] Could not stop $($t.Name) PID=$($t.Pid): $($_.Exception.Message)"
        }
    }
}

if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force
}

Write-Host "[ok] Production processes stopped."
