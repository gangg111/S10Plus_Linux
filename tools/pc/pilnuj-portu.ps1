# Pilnowanie portu USB telefonu: przywraca polaczenie bez ruszania kabla.
#
# Po co: po restarcie telefonu komputer nie widzi ani karty sieciowej, ani
# portu szeregowego. Przyczyna lezy po stronie telefonu i NIE DA SIE jej tam
# naprawic dzisiejszym portem: jego kontroler po restarcie twierdzi, ze nic
# nie jest podlaczone, bo nie ma kto powiedziec mu o napieciu z kabla (obsluga
# zlacza Type-C jest pominieta), a sterownik dwc3 w liscie swoich operacji ma
# tylko pullup, bez vbus_session, wiec nie przyjmuje takiej informacji nawet
# z wlasnego modulu jadra.
#
# Skrypt dziala jako zadanie Harmonogramu z konta SYSTEM, wiec nie wymaga
# zadnego klikania i dziala takze wtedy, gdy przy komputerze nikogo nie ma.
#
# Trzy zabezpieczenia, zeby nie przelaczac portu bez sensu (na tym samym
# koncentratorze wisza mysz i Bluetooth, ktore na kilka sekund znikaja):
#   1. Nic nie robimy, gdy telefon jest widoczny.
#   2. Nic nie robimy, gdy telefonu nie bylo widac od dawna, czyli gdy po
#      prostu zostal odlaczony, a nie restartuje sie.
#   3. Miedzy dwoma przelaczeniami musi minac odstep.

$ErrorActionPreference = 'Stop'

$identyfikator    = '*VID_18D1*'
$stanPlik         = Join-Path $env:ProgramData 'pilnuj-portu-telefonu.json'
$oknoObecnosci    = 45      # minut: jak dawno telefon musial byc widziany
$odstepPrzelaczen = 3       # minut miedzy przelaczeniami
$czekajSekund     = 30

function Telefon-Obecny {
	$n = (Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
		Where-Object { $_.InstanceId -like $identyfikator }).Count
	return ($n -gt 0)
}

function Wczytaj-Stan {
	if (Test-Path $stanPlik) {
		try { return Get-Content $stanPlik -Raw | ConvertFrom-Json } catch { }
	}
	return [pscustomobject]@{ ostatnioWidziany = $null; ostatnioPrzelaczony = $null }
}

function Zapisz-Stan($stan) {
	$stan | ConvertTo-Json | Set-Content -Path $stanPlik -Encoding UTF8
}

$stan = Wczytaj-Stan
$teraz = Get-Date

if (Telefon-Obecny) {
	$stan.ostatnioWidziany = $teraz.ToString('o')
	Zapisz-Stan $stan
	Write-Output "$teraz telefon widoczny"
	exit 0
}

# Telefonu nie widac. Czy to restart, czy po prostu go odlaczono?
if (-not $stan.ostatnioWidziany) {
	Write-Output "$teraz telefonu nie widac i nigdy go nie widzialem, nie ruszam"
	exit 0
}
$odKiedy = ($teraz - [datetime]::Parse($stan.ostatnioWidziany)).TotalMinutes
if ($odKiedy -gt $oknoObecnosci) {
	Write-Output "$teraz telefonu nie widac od $([int]$odKiedy) min, uznaje za odlaczony"
	exit 0
}

if ($stan.ostatnioPrzelaczony) {
	$odPrzelaczenia = ($teraz - [datetime]::Parse($stan.ostatnioPrzelaczony)).TotalMinutes
	if ($odPrzelaczenia -lt $odstepPrzelaczen) {
		Write-Output "$teraz przelaczalem $([int]$odPrzelaczenia) min temu, czekam"
		exit 0
	}
}

$wpis = Get-PnpDevice -ErrorAction SilentlyContinue |
	Where-Object { $_.InstanceId -like $identyfikator -and $_.Class -eq 'USB' } |
	Select-Object -First 1
if (-not $wpis) {
	Write-Output "$teraz brak zapamietanego wpisu telefonu"
	exit 0
}

$koncentrator = (Get-PnpDeviceProperty -InstanceId $wpis.InstanceId -KeyName 'DEVPKEY_Device_Parent').Data
Write-Output "$teraz przelaczam koncentrator $koncentrator"

$stan.ostatnioPrzelaczony = $teraz.ToString('o')
Zapisz-Stan $stan

Disable-PnpDevice -InstanceId $koncentrator -Confirm:$false
Start-Sleep -Seconds 3
Enable-PnpDevice -InstanceId $koncentrator -Confirm:$false

for ($i = 0; $i -lt $czekajSekund; $i++) {
	Start-Sleep -Seconds 1
	if (Telefon-Obecny) {
		$stan.ostatnioWidziany = (Get-Date).ToString('o')
		Zapisz-Stan $stan
		Write-Output "telefon wrocil po $($i + 1) s"
		exit 0
	}
}

Write-Output "telefon nie wrocil po przelaczeniu"
exit 0
