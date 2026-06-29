@echo off

setlocal

cd /d "%~dp0"



echo ========================================

echo   Program Guard - Instalacion

echo ========================================

echo.



python --version >nul 2>&1

if errorlevel 1 (

    echo ERROR: Python no esta instalado.

    pause

    exit /b 1

)



python -m pip install -r requirements.txt

if errorlevel 1 (

    echo ERROR: No se pudieron instalar las dependencias.

    pause

    exit /b 1

)



for /f "delims=" %%P in ('python -c "import sys, pathlib; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))"') do set "PYW=%%P"

set "APP_CMD=%PYW% \"%CD%\main_client.py\""



reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ProgramGuard" /t REG_SZ /d "%APP_CMD%" /f >nul

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "GameGuard" /f >nul 2>&1



echo.

echo Instalacion completada.

echo - Cliente: iniciar.bat  ^(PC controlado^)

echo - Admin:   iniciar_admin.bat  ^(PC controlador^)

echo - Solo codigo de 6 digitos — conexion automatica

echo.

pause

