# Przelaczenie portu USB, do ktorego podpiety jest telefon.
#
# Po co: po restarcie telefonu komputer nie widzi ani karty sieciowej, ani
# portu szeregowego, dopoki nie wyjmie sie i nie wlozy kabla. Przyczyna lezy
# po stronie telefonu: jego kontroler USB po restarcie twierdzi, ze nic nie
# jest podlaczone ("not attached"), bo nie ma kto powiedziec mu o napieciu
# z kabla (obsluga zlacza Type-C jest w tym porcie pominieta), a sterownik
# dwc3 nie obsluguje zgloszenia napiecia z poziomu oprogramowania: w jego
# liscie operacji jest tylko pullup, nie ma vbus_session.
#
# Skoro telefonowi nie da sie tego powiedziec, robi to komputer: wylaczenie
# i wlaczenie koncentratora odcina i przywraca zasilanie portow, czyli daje
# dokladnie ten sam skutek, co wyjecie i wlozenie kabla.
#
# UWAGA: na tym samym koncentratorze wisza inne urzadzenia (mysz, Bluetooth).
# Znikna one na czas przelaczenia, czyli na kilka sekund. Dlatego skrypt robi
# to TYLKO wtedy, gdy telefonu naprawde nie widac, i od razu przywraca
# koncentrator.
#
# Wymaga uprawnien administratora.

$ErrorActionPreference = 'Stop'

$identyfikatorTelefonu = '*VID_18D1*'
$czekajSekund = 25

function Telefon-Obecny {
	$n = (Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
		Where-Object { $_.InstanceId -like $identyfikatorTelefonu }).Count
	return ($n -gt 0)
}

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
	Write-Host "Ten skrypt musi dzialac jako administrator." -ForegroundColor Red
	Write-Host "Uruchom przelacz-port-telefonu.cmd prawym przyciskiem, jako administrator."
	exit 1
}

if (Telefon-Obecny) {
	Write-Host "Telefon jest juz widoczny, nie ruszam portu." -ForegroundColor Green
	exit 0
}

# Koncentrator znajdujemy po ZAPAMIETANYM wpisie telefonu: Windows pamieta,
# gdzie byl podpiety, nawet gdy urzadzenia nie widac.
$wpis = Get-PnpDevice -ErrorAction SilentlyContinue |
	Where-Object { $_.InstanceId -like $identyfikatorTelefonu -and $_.Class -eq 'USB' } |
	Select-Object -First 1

if (-not $wpis) {
	Write-Host "Windows nie pamieta tego telefonu; podepnij kabel raz recznie." -ForegroundColor Yellow
	exit 1
}

$koncentrator = (Get-PnpDeviceProperty -InstanceId $wpis.InstanceId -KeyName 'DEVPKEY_Device_Parent').Data
Write-Host "Telefon byl podpiety do: $koncentrator"

$co = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.InstanceId -like 'USB\VID*' } |
	Where-Object { (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data -eq $koncentrator }
if ($co) {
	Write-Host "Na czas przelaczenia zniknie takze:"
	$co | ForEach-Object { Write-Host ("  " + $_.FriendlyName) }
}

Write-Host "Wylaczam koncentrator..."
Disable-PnpDevice -InstanceId $koncentrator -Confirm:$false
Start-Sleep -Seconds 3
Write-Host "Wlaczam koncentrator..."
Enable-PnpDevice -InstanceId $koncentrator -Confirm:$false

Write-Host "Czekam na telefon (do $czekajSekund s)..."
for ($i = 0; $i -lt $czekajSekund; $i++) {
	Start-Sleep -Seconds 1
	if (Telefon-Obecny) {
		Write-Host "Telefon widoczny po $($i + 1) s." -ForegroundColor Green
		exit 0
	}
}

Write-Host "Telefon nadal niewidoczny. Zostaje wyjecie i wlozenie kabla." -ForegroundColor Yellow
exit 1
