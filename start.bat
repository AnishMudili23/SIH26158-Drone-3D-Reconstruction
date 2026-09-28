@echo off
cd /d "%~dp0"
title AeroMesh 3D Launcher
echo ===================================================
echo             AEROMESH // 4D PLATFORM
echo ===================================================
echo [1/2] Starting Backend Server (FastAPI :8000)...
start "AeroMesh Backend (:8000)" cmd /k "cd /d ""%~dp0"" && set PYTHONPATH=.;src && .venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Frontend App (Next.js :3000)...
start "AeroMesh Frontend (:3000)" cmd /k "cd /d ""%~dp0"" && npm run dev"

echo.
echo ===================================================
echo AeroMesh services are launching!
echo   Frontend : http://localhost:3000
echo   Backend  : http://localhost:8000 (Docs: /docs)
echo ===================================================
echo.
pause
