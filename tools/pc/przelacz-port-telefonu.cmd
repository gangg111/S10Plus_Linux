@echo off
rem Uruchamia przelaczenie portu USB telefonu z uprawnieniami administratora.
rem Kliknij prawym przyciskiem i wybierz "Uruchom jako administrator".
setlocal
set SKRYPT=%~dp0przelacz-port-telefonu.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%SKRYPT%"
echo.
pause
