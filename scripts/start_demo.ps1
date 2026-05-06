param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8031,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Test-PortOpen {
    param(
        [string]$HostName,
        [int]$PortNumber
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $async = $client.BeginConnect($HostName, $PortNumber, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(500, $false)
        if ($connected) {
            $client.EndConnect($async)
        }
        $client.Close()
        return $connected
    } catch {
        return $false
    }
}

Write-Host "== Vehicle Multi-Agent Demo ==" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

if (Test-Path ".env") {
    Write-Host ".env: found; the server will load it automatically" -ForegroundColor Green
} else {
    Write-Host ".env: not found; mock/offline defaults will be used" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Provider status" -ForegroundColor Cyan
$providerProbe = @'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.env_loader import load_env_file
from web_demo.app_model import get_initial_payload
load_env_file()
payload = get_initial_payload()
providers = payload.get("providers", {})
for key in ("llm", "local_llm", "orchestrator", "map", "weather", "charge"):
    print(f"- {key}: {providers.get(key, '-')}")
print("- DEEPSEEK_API_KEY: configured" if __import__("os").getenv("DEEPSEEK_API_KEY") else "- DEEPSEEK_API_KEY: not configured")
print("- AMAP_API_KEY: configured" if __import__("os").getenv("AMAP_API_KEY") else "- AMAP_API_KEY: not configured")
'@
$probeDir = Join-Path $ProjectRoot "runtime"
New-Item -ItemType Directory -Force -Path $probeDir | Out-Null
$probePath = Join-Path $probeDir "_start_demo_provider_probe.py"
Set-Content -Path $probePath -Value $providerProbe -Encoding ASCII
try {
    & $Python $probePath
} finally {
    Remove-Item -Path $probePath -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Starting Web Demo..." -ForegroundColor Cyan
$url = "http://$HostAddress`:$Port"
if (Test-PortOpen -HostName $HostAddress -PortNumber $Port) {
    Write-Host "Port is already reachable; reuse existing service: $url" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "- Full check: powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -BaseUrl $url"
    Write-Host "- Unit tests: $Python -m pytest tests"
    Write-Host "- Acceptance report: reports/acceptance_report.md"
    Write-Host "- Web QA report: reports/web_qa_report.md"
    return
}

$serverArgs = @(
    "-m",
    "web_demo.server",
    "--host",
    $HostAddress,
    "--port",
    [string]$Port
)

$process = Start-Process `
    -FilePath $Python `
    -ArgumentList $serverArgs `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Demo started: $url" -ForegroundColor Green
Write-Host "Process ID: $($process.Id)"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "- Full check: powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -BaseUrl $url"
Write-Host "- Unit tests: $Python -m pytest tests"
Write-Host "- Acceptance report: reports/acceptance_report.md"
Write-Host "- Web QA report: reports/web_qa_report.md"
Write-Host ""
Write-Host "Safety note: this script only shows whether DEEPSEEK_API_KEY / AMAP_API_KEY are configured; it never prints key values."
