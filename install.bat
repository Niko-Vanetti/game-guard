@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   Game Guard - Instalacion
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado.
    echo Descargalo desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Instalando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    pause
    exit /b 1
)

set "STARTUP_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "APP_CMD=pythonw.exe \"%CD%\main.py\""

reg add "%STARTUP_KEY%" /v "GameGuard" /t REG_SZ /d %APP_CMD% /f >nul

echo.
echo Instalacion completada.
echo - Game Guard se iniciara automaticamente con Windows.
echo - Ejecuta "iniciar.bat" para probarlo ahora.
echo - La configuracion se guarda en %%APPDATA%%\GameGuard\
echo.
pause
