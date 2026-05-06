param(
    [string]$BaseUrl = "http://127.0.0.1:8031",
    [string]$Python = "python",
    [switch]$SkipScreenshots,
    [switch]$SkipWebQa
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan
    $started = Get-Date
    & $Command
    $elapsed = (Get-Date) - $started
    Write-Host "PASS: $Name ($([math]::Round($elapsed.TotalSeconds, 2))s)" -ForegroundColor Green
}

Write-Host "== Vehicle Multi-Agent Full Check ==" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "BaseUrl: $BaseUrl"

Run-Step "unit tests" {
    Write-Host "pytest tests"
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    & $Python -m pytest tests -p no:cacheprovider
}

Run-Step "acceptance matrix" {
    Write-Host "scripts/run_acceptance.py"
    & $Python scripts/run_acceptance.py
}

if (-not $SkipWebQa) {
    Run-Step "web qa" {
        Write-Host "scripts/web_qa.py"
        if ($SkipScreenshots) {
            & $Python scripts/web_qa.py --base-url $BaseUrl
        } else {
            Write-Host "--screenshots"
            & $Python scripts/web_qa.py --base-url $BaseUrl --screenshots
        }
    }
} else {
    Write-Host ""
    Write-Host "SKIP: web qa" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "== Checks completed ==" -ForegroundColor Green
Write-Host "reports/acceptance_report.md"
Write-Host "reports/web_qa_report.md"
