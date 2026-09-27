# Jednorazowa instalacja pilnowania portu USB telefonu.
#
# Tworzy zadanie Harmonogramu Windows dzialajace z konta SYSTEM, uruchamiane
# co dwie minuty. Od tej chwili nic nie trzeba klikac: zadanie samo przywraca
# polaczenie z telefonem po jego restarcie, takze gdy przy komputerze nikogo
# nie ma.
#
# To jedyne miejsce, ktore wymaga podniesienia uprawnien, i tylko RAZ.
# Uprawnienia sa potrzebne, bo przelaczenie portu USB to operacja na
# urzadzeniu systemowym.
#
# Cofniecie: Unregister-ScheduledTask -TaskName 'PilnujPortuTelefonu' -Confirm:$false

$ErrorActionPreference = 'Stop'

$nazwa = 'PilnujPortuTelefonu'
$skrypt = Join-Path $PSScriptRoot 'pilnuj-portu.ps1'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
	Write-Host "Potrzebne sa uprawnienia administratora." -ForegroundColor Red
	Write-Host "Kliknij zainstaluj-pilnowanie.cmd prawym przyciskiem i wybierz"
	Write-Host "Uruchom jako administrator. To jedyny raz, kiedy trzeba to zrobic."
	exit 1
}

if (-not (Test-Path $skrypt)) {
	Write-Host "Nie znalazlem pliku $skrypt" -ForegroundColor Red
	exit 1
}

$akcja = New-ScheduledTaskAction -Execute 'powershell.exe' `
	-Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$skrypt`""

# Co dwie minuty, bez konca. Sam skrypt pilnuje, zeby nie przelaczac portu
# bez potrzeby, wiec czeste sprawdzanie nic nie kosztuje.
$wyzwalacz = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
	-RepetitionInterval (New-TimeSpan -Minutes 2)

$konto = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest

$ustawienia = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
	-DontStopIfGoingOnBatteries -StartWhenAvailable `
	-ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $nazwa -Action $akcja -Trigger $wyzwalacz `
	-Principal $konto -Settings $ustawienia -Force | Out-Null

Write-Host "Zadanie '$nazwa' utworzone." -ForegroundColor Green
Write-Host "Dziala jako SYSTEM, co dwie minuty, bez zadnego klikania."
Write-Host ""
Write-Host "Sprawdzenie teraz:"
Start-ScheduledTask -TaskName $nazwa
Start-Sleep -Seconds 5
Get-ScheduledTaskInfo -TaskName $nazwa | Select-Object TaskName, LastRunTime, LastTaskResult | Format-List
