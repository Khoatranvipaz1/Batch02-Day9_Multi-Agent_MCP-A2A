$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing .venv. Run 'uv sync' before starting the services."
}

$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    throw "Missing .env. Create it and add a valid OpenRouter API key, model, and registry URL."
}

$envValues = @{}
foreach ($line in Get-Content $envFile -Encoding UTF8) {
    if ($line -match '^\s*#' -or $line -notmatch '=') {
        continue
    }

    $name, $value = $line -split '=', 2
    $envValues[$name.Trim()] = $value.Trim()
}

$apiKey = $envValues["OPENROUTER_API_KEY"]
if (-not $apiKey -or $apiKey -eq "your_key_here") {
    throw "OPENROUTER_API_KEY is not configured in .env."
}

$model = $envValues["OPENROUTER_MODEL"]
if (-not $model) {
    throw "OPENROUTER_MODEL is not configured in .env."
}

$registryUrl = $envValues["REGISTRY_URL"]
if (-not $registryUrl) {
    throw "REGISTRY_URL is not configured in .env."
}

$services = @(
    @{ Name = "Registry"; Module = "registry"; Port = 10000 },
    @{ Name = "Tax Agent"; Module = "tax_agent"; Port = 10102 },
    @{ Name = "Compliance Agent"; Module = "compliance_agent"; Port = 10103 },
    @{ Name = "Law Agent"; Module = "law_agent"; Port = 10101 },
    @{ Name = "Customer Agent"; Module = "customer_agent"; Port = 10100 }
)

$logsDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$env:PYTHONUNBUFFERED = "1"

$processes = @()

try {
    foreach ($service in $services) {
        Write-Host "Starting $($service.Name) on port $($service.Port)..."
        $stdoutLog = Join-Path $logsDir "$($service.Module).out.log"
        $stderrLog = Join-Path $logsDir "$($service.Module).err.log"
        $processes += Start-Process `
            -FilePath $python `
            -ArgumentList "-m", $service.Module `
            -WorkingDirectory $PSScriptRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog `
            -PassThru

        if ($service.Module -eq "registry") {
            Start-Sleep -Seconds 2
        }
        elseif ($service.Module -eq "compliance_agent") {
            Start-Sleep -Seconds 3
        }
        elseif ($service.Module -eq "law_agent") {
            Start-Sleep -Seconds 3
        }
    }

    Write-Host ""
    Write-Host "All services started:"
    Write-Host "  Registry:         $registryUrl"
    Write-Host "  Customer Agent:   http://localhost:10100"
    Write-Host "  Law Agent:        http://localhost:10101"
    Write-Host "  Tax Agent:        http://localhost:10102"
    Write-Host "  Compliance Agent: http://localhost:10103"
    Write-Host ""
    Write-Host "Run in another terminal:"
    Write-Host "  .\.venv\Scripts\python.exe test_client.py"
    Write-Host "Logs:"
    Write-Host "  .\logs\*.err.log"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all services."

    Wait-Process -Id $processes.Id
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}
