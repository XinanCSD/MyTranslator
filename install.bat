@echo off
setlocal EnableExtensions

cd /d "%~dp0"

REM Prefer an existing Python 3.11+ interpreter from python/py.
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
    echo.
    echo Detected Python runtimes:
    where python
    py --list 2>nul
    echo.
    echo Please install Python 3.11+ and run install.bat again.
    exit /b 1
)

echo Using Python: %PYTHON_CMD%

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        exit /b 1
    )
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install Python dependencies.
    exit /b 1
)

.venv\Scripts\python.exe download_model.py
if errorlevel 1 (
    echo Failed to download or prepare the translation model.
    exit /b 1
)

echo.
echo Installation completed successfully.
endlocal
