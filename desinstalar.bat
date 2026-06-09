@echo off
setlocal
cd /d "%~dp0"

echo Eliminando Game Guard del inicio de Windows...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "GameGuard" /f >nul 2>&1

echo.
echo Game Guard ya no iniciara con Windows.
echo Para borrar la configuracion, elimina: %%APPDATA%%\GameGuard\
echo.
pause
