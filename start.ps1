# AeroMesh 3D One-Click PowerShell Launcher
$repoRoot = $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "             AEROMESH // 4D PLATFORM               " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Start Backend in separate window
Write-Host "[1/2] Launching Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot'; `$env:PYTHONPATH='.;src'; .\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 2

# 2. Start Frontend in separate window
Write-Host "[2/2] Launching Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot'; npm run dev"

Write-Host "`n>> AeroMesh services launched!" -ForegroundColor Yellow
Write-Host ">> Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ">> Backend : http://localhost:8000 (Swagger docs at /docs)`n" -ForegroundColor Cyan
