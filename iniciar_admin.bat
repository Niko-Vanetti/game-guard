@echo off
setlocal
cd /d "%~dp0"

for /f "delims=" %%P in ('python -c "import sys, pathlib; print(pathlib.Path(sys.executable).with_name('python.exe'))"') do set "PY=%%P"

if not exist "%PY%" (
    echo ERROR: No se encontro python.exe
    pause
    exit /b 1
)

start "" "%PY%" "%~dp0main_admin.py"
