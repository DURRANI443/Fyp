param([int]$Port = 8000, [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Run .\scripts\setup.ps1 first.' }
if (-not $SkipBuild -or -not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'frontend/dist/index.html'))) {
    Push-Location (Join-Path $ProjectRoot 'frontend')
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
Push-Location (Join-Path $ProjectRoot 'backend')
try {
    & $PythonExe -m app.bootstrap
    if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
    Write-Host "Open http://127.0.0.1:$Port in your browser. Press Ctrl+C to stop."
    & $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Application server stopped with an error.' }
} finally { Pop-Location }
