@echo off
setlocal
cd /d "%~dp0"

for /f "delims=" %%P in ('python -c "import sys, pathlib; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))"') do set "PYW=%%P"

if not exist "%PYW%" (
    echo ERROR: No se encontro pythonw.exe
    pause
    exit /b 1
)

start "" "%PYW%" "%~dp0main_client.py"
