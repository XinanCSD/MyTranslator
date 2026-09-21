@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3"
    )
)
if not defined PYTHON_CMD (
    echo Python 3.11 or newer is required.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

where llama-server.exe >nul 2>&1
if errorlevel 1 (
    where llama-server >nul 2>&1
    if errorlevel 1 (
        echo llama-server was not found in PATH.
        echo Install llama.cpp and ensure llama-server.exe is in PATH.
        exit /b 1
    )
)

.venv\Scripts\python.exe download_model.py
if errorlevel 1 exit /b 1

echo.
echo Installation completed successfully.
endlocal
