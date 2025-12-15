@echo off
echo Starting PDF to OFX Converter...
echo Please wait while we set up the environment...

cd web_tool

:: Check if venv exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate venv and install requirements
call venv\Scripts\activate
echo Installing dependencies...
pip install -r requirements.txt > nul 2>&1

echo.
echo ========================================================
echo                SERVER STARTED SUCCESSFULLY
echo ========================================================
echo.
echo Access the tool using one of the following URLs:
echo.
python -c "import socket; host = socket.gethostname(); ip = socket.gethostbyname(host); print(f'   Local (You):      http://localhost:8000'); print(f'   Network (IP):     http://{ip}:8000'); print(f'   Network (Name):   http://{host}:8000')"
echo.
echo ========================================================
echo.
echo Press Ctrl+C to stop the server.
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level error

pause
