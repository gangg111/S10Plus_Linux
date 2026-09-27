# R18: temperatura SoC

Runda osiemnasta. Cel: jądro ma wiedzieć, jak gorący jest układ, i wyłączyć
telefon porządnie, zanim zrobi to sprzęt. Bez tego jedyną ochroną był
sprzętowy trip, który odcina zasilanie bez zamykania systemu, a port pmOS
opisywał właśnie takie „twarde odcięcie” przy obciążeniu ośmiu rdzeni.

**Stan na 24.09.2026: działa na telefonie (jądro #58).** Pięć stref
w `/sys/class/thermal`: big, mid, little, gpu, isp, każda z progiem
krytycznym 100 °C. Pomiar: `measurements/2026-09-24-termika/`.

## Jak producent czyta temperaturę

Jądro producenta nie czyta temperatury z bloków TMU. Pyta firmware na APM
przez ACPM (kanał 9, węzeł `acpm_tmu`), a firmware odpowiada w całych
stopniach dla pięciu stref. Mainline 7.2 ma już ten protokół
(`drivers/firmware/samsung/exynos-acpm-tmu.c`, pisany dla gs101), ale żadnego
odbiorcy w `drivers/thermal`. Zmierzone modułem jednorazowym: firmware 9820
odpowiada na polecenia z mainline bez żadnej zmiany.

| strefa firmware | co mierzy | blok |
| --- | --- | --- |
| 0 | klaster big (M4) | TOP `0x10090000`, SPI 478 |
| 1 | klaster mid (A75) | TOP |
| 2 | klaster little (A55) | TOP |
| 3 | GPU | SUB `0x100a0000`, SPI 479 |
| 4 | ISP | SUB |

Bezczynność: 43-46 °C. Po 20 s pełnego obciążenia 8 rdzeni: big 58 °C,
czyli +12 °C przy zegarach zostawionych przez bootloader.

## Sprzętowy trip już jest

S-Boot uzbraja trip w obu blokach: rejestr CONTROL (`0x50`) ma
`0x00009503` (CORE_EN, THERM_TRIP_EN), a najwyższy próg to kod `0x17b`,
czyli 115 °C według kalibracji z TRIMINFO0 tego egzemplarza. Dlatego próg
krytyczny jądra stoi na 100 °C: 15 °C zapasu na porządne wyłączenie.
Sterownik nie rusza tripu, tylko ostrzega przy starcie, jeśli go nie zastanie.

Wyłączanie potrafi zawisnąć na synchronizacji pamięci podręcznej UFS
(`wylaczanie-wiesza-sie-na-ufs`), więc fragment konfiguracji ustawia
`CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=5000`: 5 s po progu krytycznym
jądro wyłącza telefon samo.

## Łatki

1. **0106** binding `samsung,exynos9820-tmu-top` / `-sub`: węzeł na blok,
   komórka specyfikatora to numer strefy firmware.
2. **0107** sterownik `drivers/thermal/samsung/exynos9820-tmu.c`: odpytywanie
   przez ACPM, zegar szyny bloku trzymany przez cały czas życia urządzenia
   (firmware czyta sondy przez niego), kontrola tripu. Bez przerwań i bez
   własnych progów. Komunikatów uśpienia do firmware jeszcze nie wysyła:
   platforma nie ma uśpienia systemu, na którym dałoby się je sprawdzić.
3. **0108** etap 14 generatora `exynos9820.dtsi`: dwa węzły i pięć stref.

Poprawki z przeglądu (trzech recenzentów, 24.09.2026) weszły przed wgraniem:
węzeł na blok zamiast jednego na oba, dane bloku w match data, kolejność
w probe (ACPM, zegar, INIT, kontrola tripu), nagłówek `device-id/of.h`.

## Czego jeszcze nie ma

Urządzeń chłodzących: bez cpufreq i cpuidle jądro nie ma czym dławić, więc
jedyną reakcją jest wyłączenie. Następny krok to DVFS przez ACPM (kanał 5),
który daje cpufreq i razem z nim chłodzenie klastrów według progów
producenta (83 °C dla big i mid).
