@echo off
setlocal EnableExtensions EnableDelayedExpansion
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
        echo.
        echo llama-server was not found.
        where winget >nul 2>&1
        if errorlevel 1 (
            echo WinGet is not available.
            echo Install llama.cpp manually, then ensure llama-server.exe is in PATH.
            exit /b 1
        )

        echo Installing llama.cpp with WinGet...
        winget install --id ggml.llamacpp --exact --accept-source-agreements --accept-package-agreements
        if errorlevel 1 (
            echo Failed to install llama.cpp with WinGet.
            echo Install llama.cpp manually, then ensure llama-server.exe is in PATH.
            exit /b 1
        )
    )
)

REM WinGet command aliases may not be visible until a new shell starts.
REM Locate the installed executable and add its directory to this process PATH.
where llama-server.exe >nul 2>&1
if errorlevel 1 (
    for /f "delims=" %%P in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" llama-server.exe 2^>nul') do (
        set "LLAMA_SERVER_DIR=%%~dpP"
        goto :llama_found
    )
)
goto :after_llama

:llama_found
set "PATH=!LLAMA_SERVER_DIR!;!PATH!"
echo Found llama-server.exe: !LLAMA_SERVER_DIR!llama-server.exe

:after_llama
where llama-server.exe >nul 2>&1
if errorlevel 1 (
    echo.
    echo llama-server.exe is installed but could not be located.
    echo Open a new terminal and run "where llama-server.exe" to verify it.
    exit /b 1
)

.venv\Scripts\python.exe download_model.py
if errorlevel 1 exit /b 1

echo.
echo Installation completed successfully.
endlocal
