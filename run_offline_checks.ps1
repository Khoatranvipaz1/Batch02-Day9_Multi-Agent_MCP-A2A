$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing .venv. Run 'uv sync' first."
}

# These checks use deterministic mocks and must never call OpenRouter.
Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue

Push-Location $PSScriptRoot
try {
    & $python -m evals.offline_eval
    if ($LASTEXITCODE -ne 0) {
        throw "Offline multi-agent evaluation failed."
    }

    & $python -m evals.cost_estimator `
        --scenario both `
        --queries 100 `
        --max-budget 0.25 `
        --json-output artifacts\cost_estimate.json `
        --markdown-output artifacts\cost_estimate.md
    if ($LASTEXITCODE -ne 0) {
        throw "Offline cost estimation failed."
    }
}
finally {
    Pop-Location
}
