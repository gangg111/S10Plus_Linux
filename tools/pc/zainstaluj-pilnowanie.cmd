@echo off
rem Jednorazowa instalacja pilnowania portu USB telefonu.
rem Kliknij prawym przyciskiem i wybierz "Uruchom jako administrator".
rem Po tym jednym razie wszystko dzieje sie samo, takze bez uzytkownika.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zainstaluj-pilnowanie.ps1"
echo.
pause
