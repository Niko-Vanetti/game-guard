@echo off
setlocal
cd /d "%~dp0"

echo Eliminando Program Guard del inicio de Windows...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ProgramGuard" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "GameGuard" /f >nul 2>&1

echo.
echo Program Guard ya no iniciara con Windows.
echo Para borrar la configuracion, elimina: %%APPDATA%%\ProgramGuard\
echo.
pause
