@echo off
echo ==========================================
echo    Iniciando Auditor Contabil Web Dev
echo ==========================================

echo [1/2] Iniciando Backend  (FastAPI)...
start "Backend API" cmd /k "python -m uvicorn src.api.main:app --reload --port 8000"

echo [2/2] Iniciando Frontend (Vite)...
cd src/web
start "Frontend Web" cmd /k "npm run dev"

echo.
echo Tudo pronto! Acesse: http://localhost:5173
echo.
pause
