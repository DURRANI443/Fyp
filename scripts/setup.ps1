param([switch]$WithEmbeddings)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        & py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.13 and rerun setup.' }
    }
    & $PythonExe -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
    if ($WithEmbeddings) {
        & $PythonExe -m pip install -r backend/requirements-ai.txt
        if ($LASTEXITCODE -ne 0) { throw 'Local embedding dependency installation failed.' }
        Push-Location (Join-Path $ProjectRoot 'backend')
        try {
            & $PythonExe scripts/ai_download_model.py
            if ($LASTEXITCODE -ne 0) { throw 'Embedding model download failed.' }
        } finally { Pop-Location }
    }
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    Push-Location (Join-Path $ProjectRoot 'frontend')
    try {
        Write-Host 'Installing frontend dependencies. Stop Vite and frontend tests before running setup.'
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
    Push-Location (Join-Path $ProjectRoot 'backend')
    try {
        & $PythonExe -m app.bootstrap
        if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
    } finally { Pop-Location }
    Write-Host 'Setup complete. Run .\scripts\start.ps1'
} finally { Pop-Location }
